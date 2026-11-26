"""Is the server healthy? /api/health answers uptime monitors (services outside that check the site every few
minutes and alert someone when it stops answering). /api/admin/health gives the admin the details: the database,
disk space, recent crashes, the SMS budget and risky settings. record_error() remembers each crash for that page."""
import os
import shutil
import sqlite3
import time

from flask import Blueprint, current_app, jsonify, request
from werkzeug.security import check_password_hash

from . import db
from .auth import auth, texts_sent_today

bp = Blueprint("health", __name__)

ERRORS_KEPT_DAYS = 7
GB = 1024 ** 3


def _database_problem():
    """None when the database answers and its tables are up to date, otherwise what's wrong."""
    try:
        con = db.get()
        con.execute("SELECT 1 FROM users LIMIT 1").fetchall()
        version = con.execute("PRAGMA user_version").fetchone()[0]
    except sqlite3.Error as e:
        return f"The database can't be read: {e}"
    if version != db.SCHEMA_VERSION:
        return f"The database is at version {version}, but this code expects {db.SCHEMA_VERSION}. Restart the backend"
    return None


@bp.get("/health")
def health():
    """200 {"ok": true} when the server and its database work, 503 {"ok": false} when they don't.
    No details: anyone can open this address."""
    if _database_problem():
        return jsonify(ok=False), 503
    return jsonify(ok=True)


def record_error(error):
    """Remember a crashed request for the admin. It opens a connection of its own, because the request's
    connection may be what broke. If even that fails, the crash is still in the server's log."""
    try:
        con = db.connect(current_app.config["DB_PATH"])
        try:
            with con:
                now = int(time.time())
                con.execute("DELETE FROM server_errors WHERE ts < ?", (now - ERRORS_KEPT_DAYS * 86400,))
                con.execute("INSERT INTO server_errors(ts,method,path,error) VALUES(?,?,?,?)",
                            (now, request.method, request.path[:200], f"{type(error).__name__}: {error}"[:300]))
        finally:
            con.close()
    except Exception:  # any error at all: this runs while handling a crash, so it must never crash itself
        current_app.logger.exception("Couldn't record the crash for the admin's Server health page")


@bp.get("/admin/health")
@auth("admin")
def admin_health():
    """Every check with a level: "ok", "info" (fine on your own computer, matters once online), "warn" or "bad"."""
    cfg = current_app.config
    now = int(time.time())
    checks = []

    def add(level, title, detail):
        checks.append(dict(level=level, title=title, detail=detail))

    problem = _database_problem()
    if problem:
        add("bad", "Database", problem)
    else:
        size = os.path.getsize(cfg["DB_PATH"]) / 1024 ** 2
        add("ok", "Database", f"Answering, tables up to date (version {db.SCHEMA_VERSION}), file size {size:.1f} MB")

    free = shutil.disk_usage(os.path.dirname(os.path.abspath(cfg["DB_PATH"]))).free
    level = "bad" if free < GB / 2 else "warn" if free < 2 * GB else "ok"
    add(level, "Disk space", f"{free / GB:.1f} GB free where the database is kept"
        + ("" if level == "ok" else ". When it runs out, nothing new can be saved"))

    errors = db.query("SELECT ts, method, path, error FROM server_errors WHERE ts > ? ORDER BY id DESC LIMIT 20",
                      (now - ERRORS_KEPT_DAYS * 86400,))
    today = sum(e["ts"] > now - 86400 for e in errors)
    if today:
        add("bad" if today >= 10 else "warn", "Crashes",
            f"{today} {'request' if today == 1 else 'requests'} crashed in the last 24 hours. The latest is listed below")
    else:
        add("ok", "Crashes", "No request crashed in the last 24 hours")

    admin = db.query("SELECT password_hash FROM users WHERE phone = 'admin'", one=True)
    if admin and check_password_hash(admin["password_hash"], "admin123"):
        add("bad", "Admin password", "The demo password admin123 still works, and it's shown on the sign-in screen. "
            "Change it on the server: flask --app app reset-password admin")
    else:
        add("ok", "Admin password", "The demo admin password no longer works")

    if current_app.debug:
        add("bad", "Debug mode", "On (JALSETU_DEBUG=1). When something breaks it shows the code's inner workings to "
            "whoever is looking. Never use it on a public server")

    if cfg["SMS_PROVIDER"] == "console":
        add("warn", "Text messages", "No SMS service is connected: codes only appear in the server's terminal, "
            "so people don't receive them (backend/sms.py, JALSETU_SMS)")
    else:
        add("ok", "Text messages", f"Sent through {cfg['SMS_PROVIDER']}")

    sent = texts_sent_today()
    limit = cfg["SMS_DAILY_LIMIT"]
    level = "bad" if sent >= limit else "warn" if sent >= 0.8 * limit else "ok"
    add(level, "SMS budget", f"{sent} of {limit} texts used in the last 24 hours"
        + (". New codes are refused until older ones pass 24 hours" if level == "bad" else ""))

    if not cfg["VERIFY_PHONES"]:
        add("warn", "Phone check at sign-up", "Off (JALSETU_VERIFY_PHONES=0): people can sign up with any number")

    how = cfg["PAYMENTS"]
    if how == "off":
        add("info", "Online payment", "Off (JALSETU_PAYMENTS): customers pay the delivery person in cash")
    elif how == "demo":
        add("warn", "Online payment", "Pretend mode (JALSETU_PAYMENTS=demo): customers tap through a fake UPI payment "
            "and no money moves. Never use it on a public site")
    elif how == "razorpay":
        missing = [k for k in ("RAZORPAY_KEY_ID", "RAZORPAY_KEY_SECRET", "RAZORPAY_WEBHOOK_SECRET") if not cfg[k]]
        unpaid_out = db.query("""SELECT COUNT(*) n FROM suppliers s WHERE s.verified = 1
                                 AND NOT EXISTS (SELECT 1 FROM payout_accounts pa WHERE pa.supplier_id = s.id)""", one=True)["n"]
        if missing:
            add("bad", "Online payment", "Razorpay is chosen, but these settings are empty: " + ", ".join(missing))
        else:
            add("warn" if unpaid_out else "ok", "Online payment", "Through Razorpay"
                + (f". {unpaid_out} verified {'shop has' if unpaid_out == 1 else 'shops have'} no payout account yet, "
                   "so their customers can only pay cash (Payments tab)" if unpaid_out else ""))
    else:
        add("bad", "Online payment", f"JALSETU_PAYMENTS is {how!r}, which isn't off, demo or razorpay")
    twice = db.query("SELECT COUNT(*) n FROM payments WHERE status = 'duplicate'", one=True)["n"]
    if twice:
        add("bad", "Paid twice", f"{twice} {'payment' if twice == 1 else 'payments'} arrived for orders that were already "
            "paid. Refund them in the Razorpay Dashboard (listed on the Payments tab)")

    if not cfg["PROXIES"]:
        add("info", "Limits per internet address", "Off, because no proxy is set (JALSETU_PROXIES). Fine on your own "
            "computer; set it once the site runs behind nginx or similar")

    return jsonify(checks=checks, errors=errors, started=current_app.extensions.get("jalsetu_started"), now=now)
