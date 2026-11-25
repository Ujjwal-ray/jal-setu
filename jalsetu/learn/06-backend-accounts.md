# 06 — Backend: accounts and passwords (`auth.py`)

**In this lesson:** how JalSetu keeps passwords safe, how sign-in tokens work in code, the `@auth` guard that
protects every private endpoint, and the "forgot password" system. All of it is in
[backend/auth.py](../backend/auth.py).

---

## 1. Three ideas you need first

### Hashing: a one-way blender

A **hash function** turns any text into a jumble of characters, **one way only**:

```
"demo123"  ──hash──►  "scrypt:32768:8:1$Xk2…$9f1c…"      (you can't turn it back)
```

- The same input always gives the same output, so you can **check** a password by hashing what was typed
  and comparing the results.
- You **cannot** get the password back from the hash.

So JalSetu never stores passwords, only hashes. If someone stole `jalsetu.db`, they still wouldn't have
anyone's password.

JalSetu uses two kinds of hashing:

| What | Function | Why this one |
|------|----------|-------------|
| **Passwords** and **reset codes** | `generate_password_hash` / `check_password_hash` (from Werkzeug) | Deliberately **slow**, and adds a random **salt** (extra random text mixed in) so two people with the same password get different hashes. People pick guessable passwords, so making each guess slow matters |
| **Sign-in tokens** | `hashlib.sha256` | Fast. Tokens are 43 random characters, so nobody can guess one anyway. Speed is fine here |

### Random secrets

Python's `secrets` module makes random values that are safe for security (unpredictable). It's used for tokens
and 6-digit codes. (The ordinary `random` module is predictable, so it's not used for these.)

### Decorators: wrapping a function

A **decorator** is a function that takes a function and gives back a new function that does something extra
**before or after** the original. You apply one with `@` above a function:

```python
@bp.get("/me")     # 2nd: register the (guarded) function as the handler for GET /api/me
@auth()            # 1st: wrap me() so it first checks the sign-in
def me():
    return jsonify(g.user)
```

Decorators apply **from the bottom up**. Think of `@auth()` as a **security guard at the door** of the
function: it checks your wristband before letting you in. Section 4 shows how the guard is built.

---

## 2. Lines 1–23: imports and settings

```python
import hashlib          # sha256 hashing (for tokens)
import re               # regular expressions (to keep only digits of a code)
import secrets          # secure random tokens and codes
import sqlite3          # to recognise sqlite3.IntegrityError ("that phone is already taken")
import time             # the current time
from functools import wraps   # helps build decorators (see section 4)

from flask import Blueprint, current_app, g, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash

from . import db, sms
from .util import body, fail, normalize_phone, text

bp = Blueprint("auth", __name__)
```

- `bp = Blueprint("auth", __name__)`: this file's bundle of routes, plugged into the app under `/api`.

```python
MAX_FAILED_LOGINS = 5      # wrong passwords per account ...
LOCKOUT_SECONDS = 5 * 60   # ... within this window lock sign-in for that account
SEEN_EVERY = 60            # refresh users.last_seen at most once a minute per account

RESET_TTL = 15 * 60        # a password-reset code works for 15 minutes ...
RESET_TRIES = 5            # ... and survives this many wrong guesses
RESETS_PER_HOUR = 3        # codes a number can ask for itself per hour (codes from an admin don't count)
```

Rules, collected at the top so they're easy to find and change. `5 * 60` = 300 seconds = 5 minutes.

## 3. Lines 26–60: tokens and "who is this?"

### `_hash()`, lines 26–27

```python
def _hash(token):
    return hashlib.sha256(token.encode()).hexdigest()
```

`.encode()` turns text into bytes (what hash functions work on). `sha256(...)` hashes them. `.hexdigest()` gives
the result as 64 hex characters (`0-9a-f`).

### `_bearer()`, lines 30–32: read the token from the request

```python
def _bearer():
    header = request.headers.get("Authorization", "")
    return header[7:].strip() if header.startswith("Bearer ") else ""
```

The frontend sends the header `Authorization: Bearer mF3kQ…`. `"Bearer "` is 7 characters, so `header[7:]`
is everything after it: the token itself. No header (or a different kind) → `""`.

### `issue_token()`, lines 35–43: make a new sign-in

```python
def issue_token(user_id):
    token = secrets.token_urlsafe(32)
    now = int(time.time())
    con = db.get()
    with con:
        con.execute("DELETE FROM tokens WHERE expires <= ?", (now,))
        con.execute("INSERT INTO tokens(token_hash,user_id,created,expires) VALUES(?,?,?,?)",
                    (_hash(token), user_id, now, now + current_app.config["TOKEN_TTL"]))
    return token
```

1. `token_urlsafe(32)`: 32 random bytes written as 43 URL-safe characters. That's the "wristband".
2. `int(time.time())`: now, in whole seconds.
3. In one transaction: delete **expired** tokens (cleaning up as it goes), then save the **hash** of the new
   token with an expiry 30 days ahead.
4. Return the **real** token. It goes to the browser once and is never stored on the server.

### `current_user()`, lines 46–56: who sent this request?

```python
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
```

1. No token → nobody (`None`).
2. Hash the token and find the matching row in `tokens` that **hasn't expired**. `JOIN users` pulls in that user's details in the same query.
3. If found: `user.pop("last_seen")` **removes** `last_seen` from the dict and gives its value (so it's not sent
   to the frontend). `or 0` handles "never seen" (`None`). If it was more than 60 seconds ago, update it.
   **Why only once a minute?** Writing to the database on *every* request would be wasteful.
4. Return the user dict (`id`, `name`, `phone`, `role`) or `None`.

### `mark_seen()`, lines 59–60

```python
def mark_seen(user_id, now=None):
    db.execute("UPDATE users SET last_seen = ? WHERE id = ?", (now or int(time.time()), user_id))
```

Record "this account was active just now". The admin dashboard turns it into "online now" / "last seen 3 min ago".

## 4. Lines 63–76: the `@auth` guard

```python
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
```

This is the most important security code in the project. It has **three layers** of functions. Read it from
the outside in:

| Layer | Runs when | Its job |
|-------|-----------|---------|
| `auth(*roles)` | Once, when Python reads `@auth("supplier")` at start-up | Remembers which roles are allowed. `*roles` collects any number of arguments into a tuple: `auth("supplier")` → `roles = ("supplier",)`; `auth()` → `roles = ()` (anyone signed in) |
| `decorate(view)` | Once, right after, with the function below the `@` (e.g. `my_listing`) | Builds and returns the guarded version, `wrapper` |
| `wrapper(*args, **kwargs)` | On **every request** to that endpoint | The actual guard |

What the guard does on each request:

1. `current_user()`: who is this?
2. Nobody → stop with **401 "Sign in required"**.
3. Roles were listed and this user's role isn't one of them → stop with **403 "Not allowed"**.
4. Put the user on `g.user`, so the endpoint can use `g.user["id"]` to know who's asking.
5. Run the real function, passing along any arguments (`*args, **kwargs` = "whatever was given"). For
   `/orders/<int:oid>`, Flask passes `oid`.

`@wraps(view)` copies the original function's name onto `wrapper`. Flask needs every route function to have a
different name, and without this they'd all be called "wrapper".

Usage across the backend:

| Written | Means |
|---------|-------|
| `@auth()` | Any signed-in account |
| `@auth("supplier")` | Supplier accounts only |
| `@auth("admin")` | Admins only |

> **Why the backend checks, not just the frontend:** the frontend hides the admin page from customers, but
> anyone can send requests by hand (lesson 03, "Try it yourself"). The `@auth` guard is the real lock.

## 5. Lines 79–90: two small helpers

```python
def _public(user):
    return {k: user[k] for k in ("id", "name", "phone", "role")}
```

A **dict comprehension**: build a new dict with only these four keys. The user row from the database also has
`password_hash`, and this makes sure that's **never** sent to the browser.

```python
# Failed sign-ins per login, kept in memory (per server process; resets on restart).
def _recent_failures(login, now):
    failures = current_app.extensions.setdefault("jalsetu_login_failures", {})
    if len(failures) > 10_000:
        failures.clear()
    recent = [t for t in failures.get(login, []) if t > now - LOCKOUT_SECONDS]
    failures[login] = recent
    return recent
```

Protection against someone guessing passwords over and over:

- `current_app.extensions` is a dict Flask provides for storing app-wide things. `setdefault(key, {})` gets the
  entry, creating an empty dict the first time. It maps each login → a list of times a wrong password was tried.
- If it gets huge (over 10,000 logins, maybe from an attack), wipe it so memory can't fill up.
- Keep only the failures from the **last 5 minutes** and return that list.
- It lives in memory, not the database, so restarting the server clears it. The comment says so honestly.

## 6. Lines 93–145: register, login, logout, me

### `register()`, lines 93–112: `POST /api/register`

```python
@bp.post("/register")
def register():
    d = body()
    name = text(d, "name", 80)
    phone = normalize_phone(d.get("phone"))
    password = d.get("password") if isinstance(d.get("password"), str) else ""
    role = d.get("role") if d.get("role") in ("user", "supplier") else "user"
```

- Read the JSON body. Clean the name (max 80 chars) and the phone.
- Password must be text, otherwise treat it as empty.
- Role may only be `user` or `supplier`. **Nobody can sign themselves up as `admin`.** Anything else becomes `user`.

```python
    if not name:
        fail("Enter your name")
    if not phone:
        fail("Enter a 10-digit mobile number")
    if len(password) < 6:
        fail("Password must be at least 6 characters")
```
Check each field, with a clear message for each problem.

```python
    try:
        uid = db.execute("INSERT INTO users(name,phone,password_hash,role) VALUES(?,?,?,?)",
                         (name, phone, generate_password_hash(password), role)).lastrowid
    except sqlite3.IntegrityError:
        fail("This phone number is already registered. Sign in instead", 409)
    mark_seen(uid)
    return jsonify(token=issue_token(uid), user=dict(id=uid, name=name, phone=phone, role=role)), 201
```

- Save the new user with the **hashed** password. `.lastrowid` = the new user's `id`.
- If the phone is taken, the UNIQUE rule makes SQLite raise `IntegrityError` → **409** with a helpful message.
- Mark them online, make a token, and send back `{token, user}` with **201 Created**. They're now signed in.

### `login()`, lines 115–131: `POST /api/login`

```python
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
```

- `normalize_phone(raw) or raw`: use the tidied phone number, or if it isn't one (like `admin`), use what was typed.
- Five wrong tries in 5 minutes → **429**, locked for a while.

```python
    user = db.query("SELECT * FROM users WHERE phone = ?", (login_name,), one=True)
    if not user or not check_password_hash(user["password_hash"], password):
        failures.append(now)
        fail("Wrong phone number or password", 401)
    failures.clear()
    mark_seen(user["id"])
    return jsonify(token=issue_token(user["id"]), user=_public(user))
```

- Find the account. `check_password_hash` hashes the typed password the same way and compares.
- No account **or** wrong password → record the failure, **401**. Notice it's the **same message** either way,
  so a guesser can't tell which part was wrong.
- Correct → clear the failure list, mark online, return a new token and the public user details.

### `logout()`, lines 134–139

```python
@bp.post("/logout")
def logout():
    token = _bearer()
    if token:
        db.execute("DELETE FROM tokens WHERE token_hash = ?", (_hash(token),))
    return jsonify(ok=True)
```

Delete **this** device's token. Other devices stay signed in. It always answers OK.

### `me()`, lines 142–145: `GET /api/me`

```python
@bp.get("/me")
@auth()
def me():
    return jsonify(g.user)
```

The guard does all the work. If you're signed in, it returns who you are. The frontend calls this on page load
(to check the saved token still works) and every 2 minutes (a "heartbeat" that keeps you "online").

## 7. Lines 148–221: forgotten passwords

The whole flow:

```
 Customer: "Forgot password?" → types phone
        │
        ▼  POST /api/password/forgot  {phone}
 Backend: account exists? asked < 3 times this hour?
          → makes a random 6-digit code, saves its HASH (valid 15 min)
          → sms.send(...)  (for now: printed in the backend terminal)
        │
        ▼  Customer reads the code, types code + new password
           POST /api/password/reset  {phone, code, password}
 Backend: newest unused, unexpired code for this phone?
          wrong → attempts + 1 (5th wrong guess kills the code)
          right → in ONE transaction: mark code used, set new password hash,
                  delete ALL tokens (signed out everywhere)
          → issue a fresh token → customer is signed in
```

Someone who can't receive the SMS can phone JalSetu support. An admin then makes a code for them on the
admin dashboard (lesson 08), using the same `issue_reset_code` function.

### `issue_reset_code()`, lines 152–161

```python
def issue_reset_code(user_id, issued_by=None):
    code = f"{secrets.randbelow(1_000_000):06d}"
    now = int(time.time())
    con = db.get()
    with con:
        con.execute("UPDATE password_resets SET used = 1 WHERE user_id = ? AND used = 0", (user_id,))
        con.execute("INSERT INTO password_resets(user_id,code_hash,created,expires,issued_by) VALUES(?,?,?,?,?)",
                    (user_id, generate_password_hash(code), now, now + RESET_TTL, issued_by))
    return code, now + RESET_TTL
```

- `secrets.randbelow(1_000_000)`: a random whole number from 0 to 999,999.
  `:06d` pads it to 6 digits with leading zeros: `4821` → `"004821"`.
- Cancel any older unused codes for this account (only the newest one works).
- Save the **hash** of the code (the same slow hashing as passwords, since a 6-digit code is guessable), with
  a 15-minute expiry and who issued it (`None` = the person asked themselves).
- Return the code (to text or show to the admin) and its expiry time. Python can return two values at once as a tuple.

### `forgot_password()`, lines 164–180: `POST /api/password/forgot`

```python
    phone = normalize_phone(body().get("phone"))
    if not phone:
        fail("Enter the 10-digit mobile number you signed up with")
    user = db.query("SELECT id FROM users WHERE phone = ?", (phone,), one=True)
    if not user:
        # /register already tells anyone whether a number is taken, so hiding it here would protect nothing
        fail("No JalSetu account uses this number. Check it, or create a new account", 404)
```

Validate the phone and find the account. The comment explains a deliberate choice: many sites hide whether an
account exists, but here sign-up already reveals it, so a clear message is more helpful.

```python
    asked = db.query("SELECT COUNT(*) n FROM password_resets WHERE user_id = ? AND issued_by IS NULL AND created > ?",
                     (user["id"], int(time.time()) - 3600), one=True)["n"]
    if asked >= RESETS_PER_HOUR:
        fail("You've asked for 3 codes in the last hour. Wait a while, or ask JalSetu support for a code", 429)
```

Count codes this account requested **itself** (`issued_by IS NULL`) in the last hour (3600 seconds).
`COUNT(*) n` names the result column `n`. Three or more → **429**. This stops someone spamming a person's
phone with texts (real SMS costs money too).

```python
    code, expires = issue_reset_code(user["id"])
    delivery = sms.send(phone, f"Your JalSetu code is {code}. It works for 15 minutes. Never share it with anyone.")
    return jsonify(ok=True, delivery=delivery, expires=expires)
```

Make the code, "send" it, and tell the frontend how it went (`"console"` → it shows the "test mode" note).
The code itself is **not** in the response, or anyone could reset anyone's password.

### `reset_password()`, lines 183–221: `POST /api/password/reset`

```python
    d = body()
    phone = normalize_phone(d.get("phone"))
    code = re.sub(r"\D", "", text(d, "code", 20))
    password = d.get("password") if isinstance(d.get("password"), str) else ""
    if not phone: fail(...)
    if len(code) != 6: fail("Enter the 6-digit code")
    if len(password) < 6: fail("Password must be at least 6 characters")
```

Clean the inputs. The code keeps digits only, so `"482 913"` → `"482913"`.

```python
    expired = "This code has expired or was already used. Ask for a new one"
    row = db.query("""SELECT r.id, r.code_hash, r.attempts, u.id user_id, u.name, u.phone, u.role
                      FROM password_resets r JOIN users u ON u.id = r.user_id
                      WHERE u.phone = ? AND r.used = 0 AND r.expires > ? ORDER BY r.id DESC""",
                   (phone, int(time.time())), one=True)
    if not row:
        fail(expired)
```

Find this phone's **newest** (`ORDER BY r.id DESC`) code that is unused and unexpired. None → "expired or used".

```python
    if not check_password_hash(row["code_hash"], code):
        db.execute("UPDATE password_resets SET attempts = attempts + 1, used = attempts + 1 >= ? WHERE id = ?",
                   (RESET_TRIES, row["id"]))
        left = RESET_TRIES - row["attempts"] - 1
        fail(f"That code isn't right. {left} {'try' if left == 1 else 'tries'} left" if left > 0
             else "That code isn't right, and it has now stopped working. Ask for a new one")
```

Wrong code:

- Add 1 to `attempts`. In the same statement set `used` to the result of `attempts + 1 >= 5`. SQLite gives
  `1` (true) or `0` (false). Inside an `UPDATE`, the right side uses the row's **old** values, so on the
  5th wrong guess (old attempts = 4) `used` becomes 1 and the code is dead.
- Tell them how many tries are left ("1 try" / "3 tries"), or that the code has stopped working.

**Why?** A 6-digit code has a million possibilities. With only 5 guesses, guessing it is hopeless.

```python
    con = db.get()
    with con:  # use up the code, change the password and end old sign-ins together, or not at all
        if not con.execute("UPDATE password_resets SET used = 1 WHERE id = ? AND used = 0", (row["id"],)).rowcount:
            fail(expired)  # another request used this code a moment ago
        con.execute("UPDATE users SET password_hash = ? WHERE id = ?", (generate_password_hash(password), row["user_id"]))
        con.execute("DELETE FROM tokens WHERE user_id = ?", (row["user_id"],))
```

Right code. In **one transaction**:

1. Mark the code used, but only `WHERE … used = 0`. If two requests raced with the same code, only the
   first changes a row (`rowcount` = 1). The second gets 0 → "expired", and the transaction rolls back. This
   is called guarding against a **race condition**.
2. Save the new password's hash.
3. Delete **all** the account's tokens: signed out on every device. If someone else had got in, they're now out.

```python
    current_app.extensions.get("jalsetu_login_failures", {}).pop(row["phone"], None)  # lift a wrong-password lockout
    mark_seen(row["user_id"])
    user = dict(id=row["user_id"], name=row["name"], phone=row["phone"], role=row["role"])
    return jsonify(token=issue_token(row["user_id"]), user=user)
```

Clear any wrong-password lockout, mark them online, and sign them in on **this** device with a fresh token.

---

## Quick check

1. If someone copies `jalsetu.db`, can they read users' passwords? Why or why not?
2. What's the difference between `@auth()` and `@auth("admin")`?
3. Why does login say "Wrong phone number or password" instead of "No such phone number"?
4. What happens to a reset code after 5 wrong guesses?
5. Why does a password reset delete every token for that account?

<details><summary>Answers</summary>

1. No. Only slow, salted hashes are stored, and hashes can't be reversed.
2. `@auth()` lets any signed-in account in. `@auth("admin")` also requires the role to be `admin` (otherwise 403).
3. So a guesser can't find out which phone numbers have accounts from the login form.
4. `used` becomes 1, so it stops working, and the person has to ask for a new one.
5. To sign the account out everywhere, in case someone else had access. The person is then signed in again on this device only.

</details>

**Next:** [07 — Backend: suppliers and orders](07-backend-suppliers-and-orders.md)
