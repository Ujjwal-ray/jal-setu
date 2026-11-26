"""Paying for an order.

JalSetu adds its fee (SERVICE_FEE) to every order's bill. Once the jars arrive, the customer ticks "I've received my
jars" and pays, either by UPI through Razorpay or in cash to the delivery person (the supplier then taps "Cash
received").

A UPI payment through Razorpay is split automatically ("Razorpay Route"): the supplier's share goes on to the
supplier's own bank account, and JalSetu's fee stays in JalSetu's. On a cash order the supplier keeps everything,
so they owe JalSetu the fee. It is kept back from their next online payment, or an admin records it when the
supplier pays it directly.

JALSETU_PAYMENTS: "off" (cash only, the default), "demo" (a pretend UPI payment for trying the app: no money moves),
or "razorpay" (real payments: needs RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET and RAZORPAY_WEBHOOK_SECRET, and each
supplier's Razorpay linked account, which an admin enters on the Payments tab)."""
import base64
import hashlib
import hmac
import json
import re
import secrets
import time
import urllib.error
import urllib.request

from flask import Blueprint, current_app, g, jsonify, request

from . import db
from .auth import auth
from .util import body, fail, number, text

bp = Blueprint("payments", __name__)

RAZORPAY_API = "https://api.razorpay.com"
REUSE_SECONDS = 15 * 60    # pressing Pay again within this time reuses the same payment, instead of starting another
RESERVE_SECONDS = 60 * 60  # fees kept back by a payment that hasn't gone through yet stay set aside this long
ACCOUNT = re.compile(r"acc_[A-Za-z0-9]{8,20}")  # a Razorpay linked account ID, e.g. acc_GRWKk7qQsLnDjX


def _paise(rupees):
    """Razorpay counts in paise: ₹85.50 -> 8550."""
    return int(round(rupees * 100))


def _supplier_total(o):
    """What the supplier is owed for an order: the jars and the delivery charge, at the prices quoted."""
    return round((o["price"] or 0) * o["qty"] + (o["delivery_charge"] or 0), 2)


def _order(oid, side):
    """The order, if the signed-in person is its customer (side="customer") or its supplier."""
    o = db.query("""SELECT o.*, s.user_id supplier_user, s.business_name FROM orders o
                    JOIN suppliers s ON s.id = o.supplier_id WHERE o.id = ?""", (oid,), one=True)
    if not o or g.user["id"] != (o["user_id"] if side == "customer" else o["supplier_user"]):
        fail("Request not found", 404)
    return o


def mode():
    return current_app.config["PAYMENTS"]


def _signature_ok(message, signature, secret):
    """Razorpay signs what it sends with a shared secret (HMAC-SHA256). Only Razorpay and JalSetu know the secret,
    so a matching signature proves the message came from Razorpay and wasn't changed on the way."""
    if not secret or not isinstance(signature, str):
        return False
    data = message if isinstance(message, bytes) else message.encode()
    expected = hmac.new(secret.encode(), data, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def _razorpay(path, payload):
    """POST to Razorpay's API with JalSetu's keys and return its JSON answer."""
    cfg = current_app.config
    login = base64.b64encode(f"{cfg['RAZORPAY_KEY_ID']}:{cfg['RAZORPAY_KEY_SECRET']}".encode()).decode()
    req = urllib.request.Request(RAZORPAY_API + path, data=json.dumps(payload).encode(), method="POST",
                                 headers={"Content-Type": "application/json", "Authorization": "Basic " + login})
    try:
        with urllib.request.urlopen(req, timeout=15) as reply:
            return json.load(reply)
    except urllib.error.HTTPError as e:
        current_app.logger.error("Razorpay refused %s: %s %s", path, e.code, e.read()[:500])
        fail("The payment service refused this payment. Try again, or pay in cash", 502)
    except (urllib.error.URLError, TimeoutError) as e:
        current_app.logger.error("Razorpay unreachable: %s", e)
        fail("Couldn't reach the payment service. Try again, or pay in cash", 502)


# ---------------------------------------------------------------------------
# What a supplier owes JalSetu

def ledger(sid):
    """Fees on the supplier's cash orders, what was kept back from their online payments, what they paid the
    admin directly, and what they still owe (owed = cash_fees - recovered - settled)."""
    row = db.query("""SELECT
        (SELECT COALESCE(SUM(service_fee), 0) FROM orders
            WHERE supplier_id = :sid AND payment_status = 'paid' AND payment_method = 'cash') cash_fees,
        (SELECT COALESCE(SUM(p.fee_recovered), 0) FROM payments p JOIN orders o ON o.id = p.order_id
            WHERE o.supplier_id = :sid AND p.status = 'paid') recovered,
        (SELECT COALESCE(SUM(amount), 0) FROM fee_settlements WHERE supplier_id = :sid) settled""", {"sid": sid}, one=True)
    row["owed"] = round(row["cash_fees"] - row["recovered"] - row["settled"], 2)
    return row


def _set_aside(sid, now):
    """Fees kept back by this supplier's online payments that were started recently but haven't gone through."""
    return db.query("""SELECT COALESCE(SUM(p.fee_recovered), 0) n FROM payments p JOIN orders o ON o.id = p.order_id
                       WHERE o.supplier_id = ? AND p.status = 'created' AND p.created > ?""",
                    (sid, now - RESERVE_SECONDS), one=True)["n"]


# ---------------------------------------------------------------------------
# The customer's side

@bp.get("/payments/info")
def info():
    """For the order form and My requests: JalSetu's fee, and whether UPI payment is on."""
    return jsonify(service_fee=current_app.config["SERVICE_FEE"], online=mode() in ("demo", "razorpay"), demo=mode() == "demo")


@bp.post("/orders/<int:oid>/received")
@auth()
def received(oid):
    """The customer ticks "I've received my jars". If the supplier hadn't marked it delivered yet, this does."""
    o = _order(oid, "customer")
    if o["received_at"]:
        fail("You've already confirmed this delivery", 409)
    if o["status"] not in ("out_for_delivery", "delivered"):
        fail("You can confirm once your jars are on the way", 409)
    now = int(time.time())
    if not db.execute("""UPDATE orders SET received_at = ?, status = 'delivered', delivered_at = COALESCE(delivered_at, ?)
                         WHERE id = ? AND received_at IS NULL AND status IN ('out_for_delivery', 'delivered')""",
                      (now, now, oid)).rowcount:
        fail("This request was just updated. Refresh and try again", 409)
    return jsonify(id=oid, status="delivered", received_at=now)


@bp.post("/orders/<int:oid>/pay")
@auth()
def start(oid):
    """Start paying an order by UPI. Answers what the frontend needs to open the payment window."""
    cfg = current_app.config
    how = mode()
    if how not in ("demo", "razorpay"):
        fail("Online payment isn't available yet. Pay the delivery person in cash", 409)
    o = _order(oid, "customer")
    if o["payment_status"] != "unpaid":
        fail("This request is already paid" if o["payment_status"] == "paid" else "This request can't be paid online", 409)
    if not o["received_at"]:
        fail("Tick \"I've received my jars\" first", 409)
    account = None
    if how == "razorpay":
        if not (cfg["RAZORPAY_KEY_ID"] and cfg["RAZORPAY_KEY_SECRET"]):
            fail("Online payment isn't set up on the server yet. Pay the delivery person in cash", 503)
        row = db.query("SELECT razorpay_account FROM payout_accounts WHERE supplier_id = ?", (o["supplier_id"],), one=True)
        if not row:
            fail("This supplier can't take online payments yet. Pay the delivery person in cash", 409)
        account = row["razorpay_account"]

    now = int(time.time())
    p = db.query("""SELECT * FROM payments WHERE order_id = ? AND provider = ? AND status = 'created' AND created > ?
                    ORDER BY id DESC""", (oid, how, now - REUSE_SECONDS), one=True)
    if not p:
        share = _supplier_total(o)
        amount = round(share + (o["service_fee"] or 0), 2)
        # keep back fees this supplier owes from cash orders (never more than their share of this order)
        keep = round(min(max(ledger(o["supplier_id"])["owed"] - _set_aside(o["supplier_id"], now), 0), share), 2)
        if how == "razorpay":
            payload = {"amount": _paise(amount), "currency": "INR", "receipt": f"jalsetu-{oid}-{now}",
                       "notes": {"jalsetu_order": str(oid)}}
            if share - keep > 0:  # Route: this much goes on to the supplier's bank; the rest stays with JalSetu
                payload["transfers"] = [{"account": account, "amount": _paise(share - keep), "currency": "INR",
                                         "notes": {"jalsetu_order": str(oid)}}]
            provider_order_id = _razorpay("/v1/orders", payload)["id"]
        else:
            provider_order_id = "demo_" + secrets.token_hex(8)
        db.execute("""INSERT INTO payments(order_id,provider,provider_order_id,amount,supplier_amount,fee_recovered,created)
                      VALUES(?,?,?,?,?,?,?)""", (oid, how, provider_order_id, amount, round(share - keep, 2), keep, now))
        p = db.query("SELECT * FROM payments WHERE provider_order_id = ?", (provider_order_id,), one=True)

    return jsonify(provider=how, key=cfg["RAZORPAY_KEY_ID"] if how == "razorpay" else None,
                   provider_order_id=p["provider_order_id"], amount=p["amount"], amount_paise=_paise(p["amount"]),
                   supplier_amount=p["supplier_amount"], fee=o["service_fee"] or 0, fee_recovered=p["fee_recovered"],
                   business_name=o["business_name"], phone=g.user["phone"], name=g.user["name"])


def _mark_paid(provider_order_id, payment_id):
    """Record a payment that went through. Safe to call twice for the same payment (the browser and Razorpay's
    webhook both report it). If the order was already paid, this one is marked 'duplicate' for a refund."""
    now = int(time.time())
    con = db.get()
    with con:
        p = con.execute("SELECT id, order_id, status FROM payments WHERE provider_order_id = ?", (provider_order_id,)).fetchone()
        if not p:
            return None
        if p["status"] == "created":
            if con.execute("""UPDATE orders SET payment_status = 'paid', payment_method = 'upi', paid_at = ?
                              WHERE id = ? AND payment_status = 'unpaid'""", (now, p["order_id"])).rowcount:
                status = "paid"
            else:
                status = "duplicate"
                current_app.logger.error("Order %s was paid twice (payment %s): refund it in Razorpay", p["order_id"], payment_id)
            con.execute("UPDATE payments SET status = ?, paid_at = ?, provider_payment_id = ? WHERE id = ? AND status = 'created'",
                        (status, now, payment_id, p["id"]))
    return db.query("SELECT payment_status, payment_method, paid_at FROM orders WHERE id = ?", (p["order_id"],), one=True)


@bp.post("/orders/<int:oid>/pay/verify")
@auth()
def verify(oid):
    """The payment window says it went through. For Razorpay, the signature proves it really did."""
    d = body()
    _order(oid, "customer")
    provider_order_id = text(d, "provider_order_id", 64)
    payment_id = text(d, "payment_id", 64)
    p = db.query("SELECT provider FROM payments WHERE provider_order_id = ? AND order_id = ?", (provider_order_id, oid), one=True)
    if not p or (p["provider"] == "demo" and mode() != "demo"):  # a pretend payment only counts while demo mode is on
        fail("Payment not found", 404)
    if p["provider"] == "razorpay" and not _signature_ok(f"{provider_order_id}|{payment_id}", d.get("signature"),
                                                         current_app.config["RAZORPAY_KEY_SECRET"]):
        fail("We couldn't confirm this payment. If money left your account, call JalSetu support", 400)
    return jsonify(_mark_paid(provider_order_id, payment_id or "demo"))


@bp.post("/payments/razorpay/webhook")
def webhook():
    """Razorpay calls this when an order is paid, even if the customer closed the page before JalSetu heard."""
    raw = request.get_data()
    if not _signature_ok(raw, request.headers.get("X-Razorpay-Signature"), current_app.config["RAZORPAY_WEBHOOK_SECRET"]):
        fail("Bad signature", 400)
    try:
        event = json.loads(raw)
        if event.get("event") == "order.paid":
            _mark_paid(event["payload"]["order"]["entity"]["id"], event["payload"]["payment"]["entity"]["id"])
    except (ValueError, KeyError, TypeError):
        fail("Unexpected webhook", 400)
    return jsonify(ok=True)


# ---------------------------------------------------------------------------
# The supplier's side

@bp.post("/orders/<int:oid>/cash")
@auth("supplier")
def cash(oid):
    """The supplier was paid in cash. JalSetu's fee on it is then owed by the supplier."""
    o = _order(oid, "supplier")
    if o["payment_status"] != "unpaid":
        fail("This request is already paid" if o["payment_status"] == "paid" else "Payments weren't recorded for this request", 409)
    if o["status"] != "delivered":
        fail("Mark the jars delivered first", 409)
    if not db.execute("""UPDATE orders SET payment_status = 'paid', payment_method = 'cash', paid_at = ?
                         WHERE id = ? AND payment_status = 'unpaid'""", (int(time.time()), oid)).rowcount:
        fail("This request was just paid. Refresh to see how", 409)
    return jsonify(id=oid, payment_status="paid", payment_method="cash")


@bp.get("/my-payments")
@auth("supplier")
def mine():
    """The supplier's payments in short: online payments received, and JalSetu fees owed from cash orders."""
    shop = db.query("SELECT id FROM suppliers WHERE user_id = ?", (g.user["id"],), one=True)
    if not shop:
        return jsonify(None)
    sid = shop["id"]
    online = db.query("""SELECT COUNT(*) n, COALESCE(SUM(p.supplier_amount), 0) amount FROM payments p
                         JOIN orders o ON o.id = p.order_id WHERE o.supplier_id = ? AND p.status = 'paid'""", (sid,), one=True)
    has_account = bool(db.query("SELECT 1 FROM payout_accounts WHERE supplier_id = ?", (sid,), one=True))
    return jsonify(mode=mode(), service_fee=current_app.config["SERVICE_FEE"], online_count=online["n"],
                   online_amount=online["amount"], payout_account=has_account, **ledger(sid))


# ---------------------------------------------------------------------------
# The admin's side

@bp.get("/admin/payments")
@auth("admin")
def admin_payments():
    """Every supplier's payments and fees, and the latest online payments."""
    suppliers = db.query("""SELECT s.id, s.business_name, pa.razorpay_account payout_account,
        (SELECT COUNT(*) FROM payments p JOIN orders o ON o.id = p.order_id WHERE o.supplier_id = s.id AND p.status = 'paid') online_count,
        (SELECT COALESCE(SUM(p.amount), 0) FROM payments p JOIN orders o ON o.id = p.order_id WHERE o.supplier_id = s.id AND p.status = 'paid') online_amount,
        (SELECT COALESCE(SUM(p.supplier_amount), 0) FROM payments p JOIN orders o ON o.id = p.order_id WHERE o.supplier_id = s.id AND p.status = 'paid') sent_to_supplier,
        (SELECT COUNT(*) FROM orders o WHERE o.supplier_id = s.id AND o.payment_status = 'paid' AND o.payment_method = 'cash') cash_count
        FROM suppliers s LEFT JOIN payout_accounts pa ON pa.supplier_id = s.id ORDER BY s.business_name""")
    for s in suppliers:
        s.update(ledger(s["id"]))
    recent = db.query("""SELECT p.id, p.order_id, p.provider, p.provider_payment_id, p.amount, p.supplier_amount,
        p.fee_recovered, p.status, p.created, p.paid_at, s.business_name, u.name customer
        FROM payments p JOIN orders o ON o.id = p.order_id JOIN suppliers s ON s.id = o.supplier_id
        JOIN users u ON u.id = o.user_id WHERE p.status != 'created' ORDER BY p.id DESC LIMIT 50""")
    fees = db.query("SELECT COALESCE(SUM(service_fee), 0) n FROM orders WHERE payment_status = 'paid'", one=True)["n"]
    return jsonify(mode=mode(), service_fee=current_app.config["SERVICE_FEE"], fees_earned=fees,
                   suppliers=suppliers, recent=recent)


@bp.post("/admin/suppliers/<int:sid>/payout-account")
@auth("admin")
def set_payout_account(sid):
    """Where Razorpay sends this supplier's share: their Razorpay linked account ID (created in the Razorpay
    Dashboard under Route, with the supplier's bank details). Empty removes it."""
    account = text(body(), "account", 40)
    if not db.query("SELECT 1 FROM suppliers WHERE id = ?", (sid,), one=True):
        fail("Supplier not found", 404)
    if not account:
        db.execute("DELETE FROM payout_accounts WHERE supplier_id = ?", (sid,))
        return jsonify(payout_account=None)
    if not ACCOUNT.fullmatch(account):
        fail("That doesn't look like a Razorpay linked account ID. It starts with acc_, like acc_GRWKk7qQsLnDjX")
    db.execute("""INSERT INTO payout_accounts(supplier_id, razorpay_account, updated, updated_by) VALUES(?,?,?,?)
                  ON CONFLICT(supplier_id) DO UPDATE SET razorpay_account = excluded.razorpay_account,
                  updated = excluded.updated, updated_by = excluded.updated_by""", (sid, account, int(time.time()), g.user["id"]))
    return jsonify(payout_account=account)


@bp.post("/admin/suppliers/<int:sid>/settlements")
@auth("admin")
def settle(sid):
    """The supplier paid JalSetu (part of) the fees they owe from cash orders, directly."""
    d = body()
    if not db.query("SELECT 1 FROM suppliers WHERE id = ?", (sid,), one=True):
        fail("Supplier not found", 404)
    owed = ledger(sid)["owed"]
    if owed <= 0:
        fail("This supplier doesn't owe JalSetu anything", 409)
    amount = number(d, "amount", "Amount", lo=0.01, hi=owed)
    db.execute("INSERT INTO fee_settlements(supplier_id, amount, note, ts, by_admin) VALUES(?,?,?,?,?)",
               (sid, round(amount, 2), text(d, "note", 200), int(time.time()), g.user["id"]))
    return jsonify(ledger(sid)), 201
