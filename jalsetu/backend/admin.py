"""Admin: live overview, per-supplier performance, problem reports and reviews, supplier verification,
password-reset codes for people who call in, and CLI commands to create admins and reset any password."""
import time
from datetime import datetime

import click
from flask import Blueprint, current_app, g, jsonify
from flask.cli import with_appcontext
from werkzeug.security import generate_password_hash

from . import db
from .auth import auth, issue_reset_code
from .util import body, fail, normalize_phone, text

bp = Blueprint("admin", __name__)

ONLINE_SECONDS = 10 * 60  # "online" = signed in and used the site in the last 10 minutes
ACTIVE = "('pending', 'accepted', 'out_for_delivery')"
ORDER_TOTAL = "(COALESCE(o.price, 0) * o.qty + COALESCE(o.delivery_charge, 0))"


def _month_start():
    return int(datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0).timestamp())


def _pct(avg):
    return None if avg is None else round(avg * 100)


@bp.get("/admin/overview")
@auth("admin")
def overview():
    now = int(time.time())
    one = lambda sql, args=(): db.query(sql, args, one=True)  # noqa: E731

    customers = one(f"""SELECT
        (SELECT COUNT(*) FROM users WHERE role = 'user') total,
        (SELECT COUNT(DISTINCT user_id) FROM orders WHERE status = 'delivered') served,
        (SELECT COUNT(DISTINCT user_id) FROM orders WHERE status IN {ACTIVE}) ordering_now""")

    by_status = {r["status"]: r["n"] for r in db.query("SELECT status, COUNT(*) n FROM orders GROUP BY status")}
    orders = dict(total=sum(by_status.values()), by_status=by_status,
                  active=sum(by_status.get(s, 0) for s in ("pending", "accepted", "out_for_delivery")))

    money = one(f"""SELECT COALESCE(SUM({ORDER_TOTAL}), 0) earned,
        COALESCE(SUM(CASE WHEN COALESCE(o.delivered_at, o.ts) >= ? THEN {ORDER_TOTAL} END), 0) earned_this_month
        FROM orders o WHERE o.status = 'delivered'""", (_month_start(),))

    suppliers = one(f"""SELECT
        (SELECT COUNT(*) FROM users WHERE role = 'supplier') accounts,
        (SELECT COUNT(*) FROM suppliers) listed,
        (SELECT COUNT(*) FROM suppliers WHERE verified = 1) verified,
        (SELECT COUNT(*) FROM suppliers WHERE verified = 0) awaiting,
        (SELECT COUNT(*) FROM suppliers s JOIN products p ON p.supplier_id = s.id
            WHERE s.verified = 1 AND p.availability = 1) in_stock,
        (SELECT COUNT(DISTINCT supplier_id) FROM orders WHERE status = 'out_for_delivery') delivering_now,
        (SELECT COUNT(DISTINCT supplier_id) FROM orders WHERE status IN {ACTIVE}) busy,
        (SELECT COUNT(DISTINCT u.id) FROM users u JOIN tokens t ON t.user_id = u.id
            WHERE u.role = 'supplier' AND t.expires > :now) signed_in,
        (SELECT COUNT(DISTINCT u.id) FROM users u JOIN tokens t ON t.user_id = u.id
            WHERE u.role = 'supplier' AND t.expires > :now AND u.last_seen >= :since) online""",
                    {"now": now, "since": now - ONLINE_SECONDS})
    suppliers["signed_out"] = suppliers["accounts"] - suppliers["signed_in"]

    fb = one("""SELECT COUNT(*) reviews, ROUND(AVG(rating), 1) rating,
        AVG(on_time) on_time, AVG(quality_ok) quality, AVG(quantity_ok) quantity FROM reviews""")
    reports = one("""SELECT COUNT(*) total, COALESCE(SUM(status = 'open'), 0) open,
        COALESCE(SUM(status = 'open' AND by_role = 'customer'), 0) open_from_customers,
        COALESCE(SUM(status = 'open' AND by_role = 'supplier'), 0) open_from_suppliers FROM reports""")
    feedback = dict(reviews=fb["reviews"], rating=fb["rating"], on_time_pct=_pct(fb["on_time"]),
                    quality_pct=_pct(fb["quality"]), quantity_pct=_pct(fb["quantity"]), **{f"reports_{k}": v for k, v in reports.items()})

    return jsonify(customers=customers, orders=orders, money=money, suppliers=suppliers, feedback=feedback,
                   online_minutes=ONLINE_SECONDS // 60, generated_at=now)


@bp.get("/admin/suppliers")
@auth("admin")
def suppliers():
    """Every listing (unverified first) with its owner's sign-in status, orders, earnings, ratings and reports."""
    now = int(time.time())
    rows = db.query(f"""SELECT s.*, p.price, p.delivery_charge, p.availability, p.jar_size,
        u.name owner_name, u.phone owner_phone, u.last_seen,
        EXISTS (SELECT 1 FROM tokens t WHERE t.user_id = s.user_id AND t.expires > :now) signed_in,
        (SELECT ROUND(AVG(rating), 1) FROM reviews r WHERE r.supplier_id = s.id) rating,
        (SELECT COUNT(*) FROM reviews r WHERE r.supplier_id = s.id) review_count,
        (SELECT AVG(on_time) FROM reviews r WHERE r.supplier_id = s.id) on_time,
        (SELECT AVG(quality_ok) FROM reviews r WHERE r.supplier_id = s.id) quality,
        (SELECT AVG(quantity_ok) FROM reviews r WHERE r.supplier_id = s.id) quantity,
        (SELECT COUNT(*) FROM orders o WHERE o.supplier_id = s.id) orders_total,
        (SELECT COUNT(*) FROM orders o WHERE o.supplier_id = s.id AND o.status = 'delivered') delivered,
        (SELECT COUNT(*) FROM orders o WHERE o.supplier_id = s.id AND o.status IN {ACTIVE}) active,
        (SELECT COUNT(*) FROM orders o WHERE o.supplier_id = s.id AND o.status = 'out_for_delivery') on_the_way,
        (SELECT COALESCE(SUM({ORDER_TOTAL}), 0) FROM orders o WHERE o.supplier_id = s.id AND o.status = 'delivered') earned,
        (SELECT COUNT(*) FROM reports rp JOIN orders o ON o.id = rp.order_id
            WHERE o.supplier_id = s.id AND rp.status = 'open') open_reports
        FROM suppliers s LEFT JOIN products p ON p.supplier_id = s.id LEFT JOIN users u ON u.id = s.user_id
        ORDER BY s.verified, s.id DESC""", {"now": now})
    for r in rows:
        r["signed_in"] = bool(r["signed_in"])
        r["online"] = r["signed_in"] and (r["last_seen"] or 0) >= now - ONLINE_SECONDS
        for key, pct in (("on_time", "on_time_pct"), ("quality", "quality_pct"), ("quantity", "quantity_pct")):
            r[pct] = _pct(r.pop(key))
    return jsonify(rows)


@bp.get("/admin/feedback")
@auth("admin")
def feedback():
    """Problem reports (open first) and the latest reviews with their on-time / quality / quantity answers."""
    reports = db.query("""SELECT rp.id, rp.order_id, rp.by_role, rp.category, rp.message, rp.status, rp.ts, rp.resolved_ts,
        u.name reporter, u.phone reporter_phone, s.business_name, s.contact supplier_contact,
        cu.name customer, COALESCE(o.phone, cu.phone) customer_phone, o.status order_status, o.qty
        FROM reports rp JOIN orders o ON o.id = rp.order_id JOIN suppliers s ON s.id = o.supplier_id
        JOIN users u ON u.id = rp.user_id JOIN users cu ON cu.id = o.user_id
        ORDER BY rp.status = 'resolved', rp.id DESC LIMIT 200""")
    reviews = db.query("""SELECT r.id, r.order_id, r.rating, r.comment, r.ts, r.on_time, r.quality_ok, r.quantity_ok,
        u.name customer, s.business_name FROM reviews r JOIN users u ON u.id = r.user_id JOIN suppliers s ON s.id = r.supplier_id
        ORDER BY r.id DESC LIMIT 100""")
    return jsonify(reports=reports, reviews=reviews)


@bp.patch("/admin/reports/<int:rid>")
@auth("admin")
def set_report_status(rid):
    status = body().get("status")
    if status not in ("open", "resolved"):
        fail("Unknown status")
    resolved_ts = int(time.time()) if status == "resolved" else None
    if not db.execute("UPDATE reports SET status = ?, resolved_ts = ? WHERE id = ?", (status, resolved_ts, rid)).rowcount:
        fail("Report not found", 404)
    return jsonify(id=rid, status=status)


@bp.post("/admin/suppliers/<int:sid>/verify")
@auth("admin")
def verify(sid):
    verified = 1 if body().get("verified", True) else 0
    if not db.execute("UPDATE suppliers SET verified = ? WHERE id = ?", (verified, sid)).rowcount:
        fail("Supplier not found", 404)
    return jsonify(ok=True, verified=verified)


@bp.post("/admin/reset-codes")
@auth("admin")
def create_reset_code():
    """A reset code for someone who can't get the SMS. The admin reads it to them after checking who they are."""
    phone = normalize_phone(text(body(), "phone", 40))
    if not phone:
        fail("Enter the 10-digit mobile number of the account")
    user = db.query("SELECT id, name, phone, role FROM users WHERE phone = ?", (phone,), one=True)
    if not user:
        fail("No JalSetu account uses this number", 404)
    if user["role"] == "admin":
        fail("Admin passwords are changed on the server: flask --app app reset-password LOGIN", 403)
    code, expires = issue_reset_code(user["id"], issued_by=g.user["id"])
    return jsonify(code=code, expires=expires, name=user["name"], phone=user["phone"], role=user["role"]), 201


@click.command("create-admin")
@with_appcontext
@click.argument("login")
@click.option("--name", default="Admin", show_default=True)
@click.password_option()
def create_admin(login, name, password):
    """Create an admin account that signs in with LOGIN (e.g. a phone number) and the password you type."""
    if len(password) < 6:
        raise click.ClickException("Password must be at least 6 characters")
    con = db.connect(current_app.config["DB_PATH"])
    try:
        with con:
            if con.execute("SELECT 1 FROM users WHERE phone = ?", (login,)).fetchone():
                raise click.ClickException(f"An account already signs in as {login!r}")
            con.execute("INSERT INTO users(name,phone,password_hash,role) VALUES(?,?,?,'admin')",
                        (name, login, generate_password_hash(password)))
    finally:
        con.close()
    click.echo(f"Admin {name!r} created. Sign in with {login!r}.")


@click.command("reset-password")
@with_appcontext
@click.argument("login")
@click.password_option()
def reset_password(login, password):
    """Set a new password for any account, admins included, and sign it out everywhere."""
    if len(password) < 6:
        raise click.ClickException("Password must be at least 6 characters")
    con = db.connect(current_app.config["DB_PATH"])
    try:
        with con:
            user = con.execute("SELECT id, name FROM users WHERE phone = ?", (normalize_phone(login) or login,)).fetchone()
            if not user:
                raise click.ClickException(f"No account signs in as {login!r}")
            con.execute("UPDATE users SET password_hash = ? WHERE id = ?", (generate_password_hash(password), user["id"]))
            con.execute("DELETE FROM tokens WHERE user_id = ?", (user["id"],))
    finally:
        con.close()
    click.echo(f"New password set for {user['name']!r}. They have been signed out everywhere.")
