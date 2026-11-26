"""Accounts and sessions: register, sign in, sign out, current user, forgotten passwords, and the @auth guard."""
import hashlib
import re
import secrets
import sqlite3
import time
from functools import wraps

from flask import Blueprint, current_app, g, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash

from . import db, sms
from .util import body, fail, normalize_phone, text

bp = Blueprint("auth", __name__)

MAX_FAILED_LOGINS = 5      # wrong passwords per account ...
LOCKOUT_SECONDS = 5 * 60   # ... within this window lock sign-in for that account
SEEN_EVERY = 60            # refresh users.last_seen at most once a minute per account

CODE_TTL = 15 * 60         # a texted code (sign-up or password reset) works for 15 minutes ...
CODE_TRIES = 5             # ... and survives this many wrong guesses
CODES_PER_HOUR = 3         # codes one number can ask for per hour, for each purpose (codes from an admin don't count)

SMS_TEXT = "Your JalSetu code is {code}. It works for 15 minutes. Never share it with anyone."
TAKEN = "This phone number is already registered. Sign in instead"
EXPIRED = "This code has expired or was already used. Ask for a new one"


def _hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def _bearer():
    header = request.headers.get("Authorization", "")
    return header[7:].strip() if header.startswith("Bearer ") else ""


def issue_token(user_id):
    token = secrets.token_urlsafe(32)
    now = int(time.time())
    con = db.get()
    with con:
        con.execute("DELETE FROM tokens WHERE expires <= ?", (now,))
        con.execute("INSERT INTO tokens(token_hash,user_id,created,expires) VALUES(?,?,?,?)",
                    (_hash(token), user_id, now, now + current_app.config["TOKEN_TTL"]))
    return token


def current_user():
    token = _bearer()
    if not token:
        return None
    now = int(time.time())
    user = db.query("""SELECT u.id, u.name, u.phone, u.role, u.last_seen FROM tokens t JOIN users u ON u.id = t.user_id
                       WHERE t.token_hash = ? AND t.expires > ?""", (_hash(token), now), one=True)
    if user:
        if (user.pop("last_seen") or 0) < now - SEEN_EVERY:
            mark_seen(user["id"], now)
    return user


def mark_seen(user_id, now=None):
    db.execute("UPDATE users SET last_seen = ? WHERE id = ?", (now or int(time.time()), user_id))


def auth(*roles):
    """Require a signed-in user (optionally with one of `roles`); the user is put in g.user."""
    def decorate(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            user = current_user()
            if not user:
                fail("Sign in required", 401)
            if roles and user["role"] not in roles:
                fail("Not allowed", 403)
            g.user = user
            return view(*args, **kwargs)
        return wrapper
    return decorate


def _public(user):
    return {k: user[k] for k in ("id", "name", "phone", "role")}


# Failed sign-ins per login, kept in memory (per server process; resets on restart).
def _recent_failures(login, now):
    failures = current_app.extensions.setdefault("jalsetu_login_failures", {})
    if len(failures) > 10_000:
        failures.clear()
    recent = [t for t in failures.get(login, []) if t > now - LOCKOUT_SECONDS]
    failures[login] = recent
    return recent


# ---------------------------------------------------------------------------
# Codes texted to a phone: they prove the person holds the number, for signing up and for a forgotten password.

def _new_code():
    """A random 6-digit code, and the hash that is stored instead of it."""
    code = f"{secrets.randbelow(1_000_000):06d}"
    return code, generate_password_hash(code)


def _code_from(d):
    code = re.sub(r"\D", "", text(d, "code", 20))
    if len(code) != 6:
        fail("Enter the 6-digit code")
    return code


def _check_code(table, row, code):
    """Fail unless `code` matches the row's code. Wrong guesses are counted; the last one allowed ends the code."""
    if check_password_hash(row["code_hash"], code):
        return
    db.execute(f"UPDATE {table} SET attempts = attempts + 1, used = attempts + 1 >= ? WHERE id = ?", (CODE_TRIES, row["id"]))
    left = CODE_TRIES - row["attempts"] - 1
    fail(f"That code isn't right. {left} {'try' if left == 1 else 'tries'} left" if left > 0
         else "That code isn't right, and it has now stopped working. Ask for a new one")


def _check_sms_budget():
    """Refuse once the last 24 hours have used SMS_DAILY_LIMIT texts: a cap on the SMS bill if someone floods
    the sign-up form with numbers."""
    since = int(time.time()) - 86400
    sent = db.query("""SELECT (SELECT COUNT(*) FROM signup_codes WHERE created > ?)
                            + (SELECT COUNT(*) FROM password_resets WHERE issued_by IS NULL AND created > ?) n""",
                    (since, since), one=True)["n"]
    if sent >= current_app.config["SMS_DAILY_LIMIT"]:
        current_app.logger.error("SMS daily limit reached: %s texts in 24 hours (JALSETU_SMS_DAILY_LIMIT)", sent)
        fail("We can't send more codes right now. Try again later, or call JalSetu support", 503)


def _signed_in(uid, name, phone, role, status=200):
    """Sign the account in: the token + user reply that every way into an account ends with."""
    mark_seen(uid)
    return jsonify(token=issue_token(uid), user=dict(id=uid, name=name, phone=phone, role=role)), status


@bp.post("/register")
def register():
    """Sign-up, step 1: check the details, then text a code to the phone. Nothing is saved in users yet.
    With JALSETU_VERIFY_PHONES=0 (no SMS service yet) the account is created straight away instead."""
    d = body()
    name = text(d, "name", 80)
    phone = normalize_phone(d.get("phone"))
    password = d.get("password") if isinstance(d.get("password"), str) else ""
    role = d.get("role") if d.get("role") in ("user", "supplier") else "user"
    if not name:
        fail("Enter your name")
    if not phone:
        fail("Enter a 10-digit mobile number")
    if len(password) < 6:
        fail("Password must be at least 6 characters")
    if db.query("SELECT 1 FROM users WHERE phone = ?", (phone,), one=True):
        fail(TAKEN, 409)
    password_hash = generate_password_hash(password)

    if not current_app.config["VERIFY_PHONES"]:
        try:
            uid = db.execute("INSERT INTO users(name,phone,password_hash,role) VALUES(?,?,?,?)",
                             (name, phone, password_hash, role)).lastrowid
        except sqlite3.IntegrityError:
            fail(TAKEN, 409)
        return _signed_in(uid, name, phone, role, 201)

    now = int(time.time())
    asked = db.query("SELECT COUNT(*) n FROM signup_codes WHERE phone = ? AND created > ?", (phone, now - 3600), one=True)["n"]
    if asked >= CODES_PER_HOUR:
        fail("You've asked for 3 codes in the last hour. Wait a while, then try again", 429)
    _check_sms_budget()
    code, code_hash = _new_code()
    con = db.get()
    with con:
        con.execute("DELETE FROM signup_codes WHERE created < ?", (now - 2 * 86400,))  # old ones: rate limits look back a day
        con.execute("UPDATE signup_codes SET used = 1 WHERE phone = ? AND used = 0", (phone,))  # a new code replaces the last
        con.execute("""INSERT INTO signup_codes(phone,name,role,password_hash,code_hash,created,expires)
                       VALUES(?,?,?,?,?,?,?)""", (phone, name, role, password_hash, code_hash, now, now + CODE_TTL))
    delivery = sms.send(phone, SMS_TEXT.format(code=code))
    return jsonify(ok=True, verify=True, delivery=delivery, expires=now + CODE_TTL), 202


@bp.post("/register/verify")
def register_verify():
    """Sign-up, step 2: the code from the SMS creates the account and signs the person in."""
    d = body()
    phone = normalize_phone(d.get("phone"))
    if not phone:
        fail("Enter a 10-digit mobile number")
    code = _code_from(d)
    row = db.query("""SELECT id, name, role, password_hash, code_hash, attempts FROM signup_codes
                      WHERE phone = ? AND used = 0 AND expires > ? ORDER BY id DESC""", (phone, int(time.time())), one=True)
    if not row:
        fail(EXPIRED)
    _check_code("signup_codes", row, code)
    con = db.get()
    try:
        with con:  # use up the code and create the account together, or not at all
            if not con.execute("UPDATE signup_codes SET used = 1, password_hash = '' WHERE id = ? AND used = 0",
                               (row["id"],)).rowcount:
                fail(EXPIRED)  # another request used this code a moment ago
            uid = con.execute("INSERT INTO users(name,phone,password_hash,role) VALUES(?,?,?,?)",
                              (row["name"], phone, row["password_hash"], row["role"])).lastrowid
    except sqlite3.IntegrityError:
        fail(TAKEN, 409)  # the number was registered while this code was waiting
    return _signed_in(uid, row["name"], phone, row["role"], 201)


@bp.post("/login")
def login():
    d = body()
    raw = text(d, "phone", 40)
    login_name = normalize_phone(raw) or raw  # the admin account signs in as "admin", not a phone number
    password = d.get("password") if isinstance(d.get("password"), str) else ""
    now = time.time()
    failures = _recent_failures(login_name, now)
    if len(failures) >= MAX_FAILED_LOGINS:
        fail("Too many wrong passwords. Try again in a few minutes", 429)
    user = db.query("SELECT * FROM users WHERE phone = ?", (login_name,), one=True)
    if not user or not check_password_hash(user["password_hash"], password):
        failures.append(now)
        fail("Wrong phone number or password", 401)
    failures.clear()
    mark_seen(user["id"])
    return jsonify(token=issue_token(user["id"]), user=_public(user))


@bp.post("/logout")
def logout():
    token = _bearer()
    if token:
        db.execute("DELETE FROM tokens WHERE token_hash = ?", (_hash(token),))
    return jsonify(ok=True)


@bp.get("/me")
@auth()
def me():
    return jsonify(g.user)


# ---------------------------------------------------------------------------
# Forgotten passwords: a one-time 6-digit code, texted to the account's phone (sms.py) or read out by an
# admin (admin.py), proves the person owns the account. The code then sets a new password.

def issue_reset_code(user_id, issued_by=None):
    """A new reset code for the account. Any older unused code for it stops working."""
    code, code_hash = _new_code()
    now = int(time.time())
    con = db.get()
    with con:
        con.execute("UPDATE password_resets SET used = 1 WHERE user_id = ? AND used = 0", (user_id,))
        con.execute("INSERT INTO password_resets(user_id,code_hash,created,expires,issued_by) VALUES(?,?,?,?,?)",
                    (user_id, code_hash, now, now + CODE_TTL, issued_by))
    return code, now + CODE_TTL


@bp.post("/password/forgot")
def forgot_password():
    """Text a reset code to the account's phone."""
    phone = normalize_phone(body().get("phone"))
    if not phone:
        fail("Enter the 10-digit mobile number you signed up with")
    user = db.query("SELECT id FROM users WHERE phone = ?", (phone,), one=True)
    if not user:
        # /register already tells anyone whether a number is taken, so hiding it here would protect nothing
        fail("No JalSetu account uses this number. Check it, or create a new account", 404)
    asked = db.query("SELECT COUNT(*) n FROM password_resets WHERE user_id = ? AND issued_by IS NULL AND created > ?",
                     (user["id"], int(time.time()) - 3600), one=True)["n"]
    if asked >= CODES_PER_HOUR:
        fail("You've asked for 3 codes in the last hour. Wait a while, or ask JalSetu support for a code", 429)
    _check_sms_budget()
    code, expires = issue_reset_code(user["id"])
    delivery = sms.send(phone, SMS_TEXT.format(code=code))
    return jsonify(ok=True, delivery=delivery, expires=expires)


@bp.post("/password/reset")
def reset_password():
    """Set a new password with a reset code. Ends every other sign-in, then signs the person in here."""
    d = body()
    phone = normalize_phone(d.get("phone"))
    if not phone:
        fail("Enter the 10-digit mobile number you signed up with")
    code = _code_from(d)
    password = d.get("password") if isinstance(d.get("password"), str) else ""
    if len(password) < 6:
        fail("Password must be at least 6 characters")

    row = db.query("""SELECT r.id, r.code_hash, r.attempts, u.id user_id, u.name, u.phone, u.role
                      FROM password_resets r JOIN users u ON u.id = r.user_id
                      WHERE u.phone = ? AND r.used = 0 AND r.expires > ? ORDER BY r.id DESC""",
                   (phone, int(time.time())), one=True)
    if not row:
        fail(EXPIRED)
    _check_code("password_resets", row, code)

    con = db.get()
    with con:  # use up the code, change the password and end old sign-ins together, or not at all
        if not con.execute("UPDATE password_resets SET used = 1 WHERE id = ? AND used = 0", (row["id"],)).rowcount:
            fail(EXPIRED)  # another request used this code a moment ago
        con.execute("UPDATE users SET password_hash = ? WHERE id = ?", (generate_password_hash(password), row["user_id"]))
        con.execute("DELETE FROM tokens WHERE user_id = ?", (row["user_id"],))
    current_app.extensions.get("jalsetu_login_failures", {}).pop(row["phone"], None)  # lift a wrong-password lockout
    return _signed_in(row["user_id"], row["name"], row["phone"], row["role"])
