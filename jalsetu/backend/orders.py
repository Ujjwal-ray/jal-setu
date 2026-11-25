"""Delivery requests: customers place and cancel them, suppliers move them along."""
import re
import time

from flask import Blueprint, g, jsonify

from . import db
from .auth import auth
from .util import body, fail, normalize_phone, number, text

bp = Blueprint("orders", __name__)

# price and delivery_charge come from the order itself: what the customer was quoted when they ordered.
# `reported`: the person viewing has an open problem report on this order.
ORDER_SQL = """SELECT o.*, s.business_name, s.contact, u.name customer, u.phone customer_phone,
  EXISTS (SELECT 1 FROM reviews r WHERE r.order_id = o.id) rated,
  EXISTS (SELECT 1 FROM reports rp WHERE rp.order_id = o.id AND rp.user_id = ? AND rp.status = 'open') reported
  FROM orders o JOIN suppliers s ON s.id = o.supplier_id JOIN users u ON u.id = o.user_id"""

# problems a customer or a supplier can report on an order (the frontend shows each side its own subset)
REPORT_CATEGORIES = ("quality", "quantity", "late", "behaviour", "payment", "address", "other")

LABEL = {"pending": "pending", "accepted": "accepted", "out_for_delivery": "out for delivery",
         "delivered": "delivered", "rejected": "rejected", "cancelled": "cancelled"}
# what a supplier may do next from each status; a customer may only cancel a pending request
SUPPLIER_NEXT = {"pending": ("accepted", "rejected"), "accepted": ("out_for_delivery", "rejected"),
                 "out_for_delivery": ("delivered",)}

EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")


def _orders(where, args):
    rows = db.query(f"{ORDER_SQL} WHERE {where} ORDER BY o.id DESC", (g.user["id"],) + args)
    for r in rows:
        r["rated"], r["reported"] = bool(r["rated"]), bool(r["reported"])
        r["total"] = (r["price"] or 0) * r["qty"] + (r["delivery_charge"] or 0)
    return rows


@bp.post("/orders")
@auth()
def create_order():
    d = body()
    sid = number(d, "supplier_id", "Supplier", integer=True)
    s = db.query("""SELECT s.id, s.user_id, p.price, p.delivery_charge, p.availability
                    FROM suppliers s JOIN products p ON p.supplier_id = s.id WHERE s.id = ? AND s.verified = 1""",
                 (sid,), one=True)
    if not s:
        fail("Supplier not found", 404)
    if s["user_id"] == g.user["id"]:
        fail("You can't order from your own listing")
    if not s["availability"]:
        fail("This supplier is out of stock right now. Pick another one", 409)

    qty = number(d, "qty", "Number of jars", default=1, lo=1, hi=50, integer=True)
    address = text(d, "address", 300)
    if not address:
        fail("Enter the delivery address")
    raw_phone = text(d, "phone", 20)
    phone = normalize_phone(raw_phone) if raw_phone else normalize_phone(g.user["phone"])
    if raw_phone and not phone:
        fail("Enter a 10-digit phone number")
    email = text(d, "email", 120)
    if email and not EMAIL.fullmatch(email):
        fail("That e-mail address doesn't look right")

    oid = db.execute("""INSERT INTO orders(user_id,supplier_id,qty,address,note,status,ts,phone,slot,email,price,delivery_charge)
                        VALUES(?,?,?,?,?,'pending',?,?,?,?,?,?)""",
                     (g.user["id"], sid, qty, address, text(d, "note", 300), int(time.time()),
                      phone, text(d, "slot", 40), email, s["price"], s["delivery_charge"] or 0)).lastrowid
    return jsonify(id=oid, status="pending"), 201


@bp.get("/orders")
@auth()
def my_orders():
    return jsonify(_orders("o.user_id = ?", (g.user["id"],)))


@bp.get("/supplier/orders")
@auth("supplier")
def supplier_orders():
    return jsonify(_orders("s.user_id = ?", (g.user["id"],)))


@bp.patch("/orders/<int:oid>")
@auth()
def update_order(oid):
    new = body().get("status")
    if new not in LABEL:
        fail("Unknown status")
    o = db.query("""SELECT o.user_id, o.status, s.user_id supplier_user FROM orders o
                    JOIN suppliers s ON s.id = o.supplier_id WHERE o.id = ?""", (oid,), one=True)
    me = g.user["id"]
    if not o or me not in (o["user_id"], o["supplier_user"]):
        fail("Request not found", 404)

    customer_cancels = new == "cancelled" and me == o["user_id"] and o["status"] == "pending"
    supplier_moves = me == o["supplier_user"] and new in SUPPLIER_NEXT.get(o["status"], ())
    if not (customer_cancels or supplier_moves):
        fail(f"A request that is {LABEL[o['status']]} can't be marked {LABEL[new]}", 409)

    # only succeeds if nobody changed the status since we read it
    delivered_at = int(time.time()) if new == "delivered" else None
    if not db.execute("UPDATE orders SET status = ?, delivered_at = COALESCE(?, delivered_at) WHERE id = ? AND status = ?",
                      (new, delivered_at, oid, o["status"])).rowcount:
        fail("This request was just updated. Refresh and try again", 409)
    return jsonify(id=oid, status=new)


@bp.post("/orders/<int:oid>/reports")
@auth()
def report_problem(oid):
    """The order's customer or its supplier tells the admin something went wrong."""
    d = body()
    category = d.get("category")
    if category not in REPORT_CATEGORIES:
        fail("Pick what went wrong")
    message = text(d, "message", 1000)
    if category == "other" and not message:
        fail("Tell us what went wrong")
    o = db.query("""SELECT o.user_id, s.user_id supplier_user FROM orders o
                    JOIN suppliers s ON s.id = o.supplier_id WHERE o.id = ?""", (oid,), one=True)
    me = g.user["id"]
    if not o or me not in (o["user_id"], o["supplier_user"]):
        fail("Request not found", 404)
    if db.query("SELECT 1 FROM reports WHERE order_id = ? AND user_id = ? AND status = 'open'", (oid, me), one=True):
        fail("You have already reported this request. An admin will look into it", 409)
    rid = db.execute("INSERT INTO reports(order_id,user_id,by_role,category,message,ts) VALUES(?,?,?,?,?,?)",
                     (oid, me, "customer" if me == o["user_id"] else "supplier", category, message, int(time.time()))).lastrowid
    return jsonify(id=rid, status="open"), 201
