"""Accounts and sessions: register, sign in, sign out, current user, forgotten passwords, and the @auth guard."""
import hashlib
import ipaddress
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

LIMITS = {  # kind of try: (how many are allowed, within how many seconds). Each try is a row in the attempts table.
    "wrong_password": (5, 5 * 60),        # wrong passwords for one account; then signing in to it pauses
    "wrong_password_ip": (20, 15 * 60),   # wrong passwords from one internet address, whichever accounts they're for
    "signup_ip": (10, 3600),              # sign-ups started from one internet address
    "reset_ip": (10, 3600),               # forgot-password texts asked for from one internet address
}
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


# ---------------------------------------------------------------------------
# Limits on repeated tries (LIMITS above). The tries are rows in the attempts table, so a restart doesn't wipe
# them and every server process counts the same ones.

def _client_ip():
    """The visitor's internet address, or None when this server can't tell visitors apart."""
    ip = request.remote_addr or ""
    try:
        if not ipaddress.ip_address(ip).is_loopback:
            return ip
    except ValueError:
        pass  # no address, or not a valid one
    # The request came from this same computer. Through the Next.js server every request does, because it
    # forwards visitors' calls without saying who they're from. Limiting by address would then lump every
    # visitor together, so one person's wrong passwords would lock everyone out: per-address limits stay off.
    if not current_app.extensions.get("jalsetu_ip_warned"):
        current_app.extensions["jalsetu_ip_warned"] = True
        current_app.logger.warning("Limits per internet address are off: requests arrive from %s, not from the "
                                   "visitors. Behind a proxy that adds X-Forwarded-For, set JALSETU_PROXIES", ip or "?")
    return None


def _take(kind, key, message):
    """Count one try of LIMITS[kind] for `key` (an account, or an address from _client_ip), or fail with 429
    and `message` when the window already holds as many as allowed. Returns the try's id, so it can be given back."""
    if key is None:
        return None
    most, window = LIMITS[kind]
    now = int(time.time())
    con = db.get()
    with con:  # check and count in one transaction: requests sent at the same moment are counted one after another
        con.execute("DELETE FROM attempts WHERE ts <= ?", (now - max(w for _, w in LIMITS.values()),))
        used = con.execute("SELECT COUNT(*) FROM attempts WHERE kind = ? AND key = ? AND ts > ?",
                           (kind, key, now - window)).fetchone()[0]
        if used >= most:
            fail(message, 429)
        return con.execute("INSERT INTO attempts(kind,key,ts) VALUES(?,?,?)", (kind, key, now)).lastrowid


def _clear_wrong_passwords(login, give_back=None):
    """Lift a wrong-password pause on an account, and give back the try `give_back` if one is named."""
    db.execute("DELETE FROM attempts WHERE (kind = 'wrong_password' AND key = ?) OR id = ?", (login, give_back))


def confirm_password(password):
    """For an action that asks the signed-in person to type their password again (opening the shop, say): fail
    unless it's right. A wrong one counts toward the same pause as a wrong password at sign-in. The answer is
    403, not 401, so the frontend doesn't take it to mean "signed out"."""
    login = g.user["phone"]
    _take("wrong_password", login, "Too many wrong passwords. Try again in a few minutes")
    row = db.query("SELECT password_hash FROM users WHERE id = ?", (g.user["id"],), one=True)
    if not isinstance(password, str) or not check_password_hash(row["password_hash"], password):
        fail("That password isn't right", 403)
    _clear_wrong_passwords(login)


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


def texts_sent_today():
    """Codes texted in the last 24 hours: sign-up codes, and reset codes people asked for themselves."""
    since = int(time.time()) - 86400
    return db.query("""SELECT (SELECT COUNT(*) FROM signup_codes WHERE created > ?)
                            + (SELECT COUNT(*) FROM password_resets WHERE issued_by IS NULL AND created > ?) n""",
                    (since, since), one=True)["n"]


def _check_sms_budget():
    """Refuse once the last 24 hours have used SMS_DAILY_LIMIT texts: a cap on the SMS bill if someone floods
    the sign-up form with numbers."""
    sent = texts_sent_today()
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
    # counted before the "already registered" check too, which also limits how fast one address can test numbers
    _take("signup_ip", _client_ip(), "Too many sign-ups from this network in the last hour. Try again later")
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
    # Each try is counted as a wrong password before the password is checked, so a burst of tries sent at once
    # can't all slip in before any is counted; the right password gives the try back. The address is counted
    # first: once it is blocked, its tries stop counting against accounts, so it can't keep locking people out.
    ip_try = _take("wrong_password_ip", _client_ip(),
                   "Too many wrong passwords from this network. Try again in a few minutes")
    _take("wrong_password", login_name, "Too many wrong passwords. Try again in a few minutes")
    user = db.query("SELECT * FROM users WHERE phone = ?", (login_name,), one=True)
    if not user or not check_password_hash(user["password_hash"], password):
        fail("Wrong phone number or password", 401)
    # The address's earlier wrong passwords stay counted: signing in to an account of its own mustn't reset them.
    _clear_wrong_passwords(login_name, give_back=ip_try)
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
    _take("reset_ip", _client_ip(), "Too many codes asked for from this network. Try again later, or call JalSetu support")
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
    _clear_wrong_passwords(row["phone"])
    return _signed_in(row["user_id"], row["name"], row["phone"], row["role"])
