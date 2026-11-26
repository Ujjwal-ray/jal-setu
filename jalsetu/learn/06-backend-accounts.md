# 06 — Backend: accounts and passwords (`auth.py`)

**In this lesson:** how JalSetu keeps passwords safe, how sign-in tokens work in code, the `@auth` guard that
protects every private endpoint, the limits that stop someone trying over and over, the 6-digit codes texted
to phones, signing up, and forgotten passwords. All of it is in [backend/auth.py](../backend/auth.py).

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
| **Passwords** and **texted codes** | `generate_password_hash` / `check_password_hash` (from Werkzeug) | Deliberately **slow**, and adds a random **salt** (extra random text mixed in) so two people with the same password get different hashes. People pick guessable passwords, so making each guess slow matters |
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

## 2. Lines 1–32: imports and settings

```python
import hashlib          # sha256 hashing (for tokens)
import ipaddress        # reads internet addresses, e.g. "is this one this same computer?" (section 6)
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
LIMITS = {  # kind of try: (how many are allowed, within how many seconds). Each try is a row in the attempts table.
    "wrong_password": (5, 5 * 60),        # wrong passwords for one account; then signing in to it pauses
    "wrong_password_ip": (20, 15 * 60),   # wrong passwords from one internet address, whichever accounts they're for
    "signup_ip": (10, 3600),              # sign-ups started from one internet address
    "reset_ip": (10, 3600),               # forgot-password texts asked for from one internet address
}
```

The limits on trying again and again, all in one place. `LIMITS` is a **dict**: each name on the left
leads to a pair of numbers on the right, "how many tries" and "within how many seconds". So
`"wrong_password": (5, 5 * 60)` reads "5 wrong passwords within 300 seconds (5 minutes)".

An **internet address** (or **IP address**) is the number that identifies the connection a request came from,
like the return address on an envelope. `203.0.113.5` is one. Everyone using the same home Wi-Fi usually shares
one. Section 6 shows how these limits are counted.

```python
SEEN_EVERY = 60            # refresh users.last_seen at most once a minute per account

CODE_TTL = 15 * 60         # a texted code (sign-up or password reset) works for 15 minutes ...
CODE_TRIES = 5             # ... and survives this many wrong guesses
CODES_PER_HOUR = 3         # codes one number can ask for per hour, for each purpose (codes from an admin don't count)

SMS_TEXT = "Your JalSetu code is {code}. It works for 15 minutes. Never share it with anyone."
TAKEN = "This phone number is already registered. Sign in instead"
EXPIRED = "This code has expired or was already used. Ask for a new one"
```

- More rules, collected at the top so they're easy to find and change. **TTL** means "time to live": how
  long something lasts before it expires.
- The last three are messages used in more than one place, so they're written once. `{code}` in `SMS_TEXT`
  is a gap to fill: `SMS_TEXT.format(code="482913")` gives the text with `482913` in the gap.

## 3. Lines 35–69: tokens and "who is this?"

### `_hash()`, lines 35–36

```python
def _hash(token):
    return hashlib.sha256(token.encode()).hexdigest()
```

`.encode()` turns text into bytes (what hash functions work on). `sha256(...)` hashes them. `.hexdigest()` gives
the result as 64 hex characters (`0-9a-f`).

### `_bearer()`, lines 39–41: read the token from the request

```python
def _bearer():
    header = request.headers.get("Authorization", "")
    return header[7:].strip() if header.startswith("Bearer ") else ""
```

The frontend sends the header `Authorization: Bearer mF3kQ…`. `"Bearer "` is 7 characters, so `header[7:]`
is everything after it: the token itself. No header (or a different kind) → `""`.

### `issue_token()`, lines 44–52: make a new sign-in

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

### `current_user()`, lines 55–65: who sent this request?

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

### `mark_seen()`, lines 68–69

```python
def mark_seen(user_id, now=None):
    db.execute("UPDATE users SET last_seen = ? WHERE id = ?", (now or int(time.time()), user_id))
```

Record "this account was active just now". The admin dashboard turns it into "online now" / "last seen 3 min ago".

## 4. Lines 72–85: the `@auth` guard

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

## 5. Lines 88–89: `_public()`

```python
def _public(user):
    return {k: user[k] for k in ("id", "name", "phone", "role")}
```

A **dict comprehension**: build a new dict with only these four keys. The user row from the database also has
`password_hash`, and this makes sure that's **never** sent to the browser.

## 6. Lines 92–133: limits on repeated tries

Someone who wants into an account they don't own can try password after password. Someone who wants to annoy
people, or run up JalSetu's SMS bill, can ask for code after code. These limits stop both.

Picture a guard with a **notebook**. Every try is written down with its time. Before anyone tries again, the
guard counts their lines from the last few minutes. Too many → "come back later" (**429 Too Many Requests**).

The notebook is the `attempts` table (lesson 04). It's in the database, not the server's memory, for two
reasons:

- Restarting the server wipes its memory. Someone could otherwise get a fresh set of guesses after every restart.
- A busy website runs **several copies** of the backend at once (called **processes**), and each has its own
  memory. They all share one database, so every copy sees the same counts.

### `_client_ip()`, lines 96–111: which internet address is this?

```python
def _client_ip():
    ip = request.remote_addr or ""
    try:
        if not ipaddress.ip_address(ip).is_loopback:
            return ip
    except ValueError:
        pass  # no address, or not a valid one
    ...
    return None
```

- `request.remote_addr`: the address the request came from, as text.
- `ipaddress.ip_address(ip)` reads that text as an address. `.is_loopback` is true for **this same computer**
  (`127.0.0.1`, or `::1` in IPv6, the newer kind of address).
- Any other address → return it.
- `try: … except ValueError:` catches the error `ip_address` raises when the text isn't an address at all.
  `pass` means "do nothing". Either way the code carries on to `return None`: "can't tell who this is".

**Why "this same computer" means "can't tell":** recall from lesson 03 that the browser never talks to Flask
directly. The Next.js server passes every `/api` call on (it's a **proxy**), and it doesn't say whom each call
came from. So on your computer *every* request reaches Flask from `127.0.0.1`. If the limits counted by
that address, every visitor would share one count, and one person's typos would lock everyone out. So the
per-address limits switch themselves off.

Lines 107–110 print a warning about this in the backend terminal, once:
`current_app.extensions` is a dict Flask provides for app-wide things, and `"jalsetu_ip_warned"` in it
remembers that the warning has been shown.

**On a real website**, a proxy such as nginx sits in front and writes the visitor's real address in a header
called `X-Forwarded-For`. Setting `JALSETU_PROXIES=1` tells Flask to read it (that code is in
[backend/__init__.py](../backend/__init__.py)). It's off unless set, because anyone can write that header
themselves. Without a proxy you trust, it could say anything.

### `_take()`, lines 114–128: count one try, or refuse

```python
def _take(kind, key, message):
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
```

`kind` is one of the names in `LIMITS`. `key` says **who** is trying: an account's login, or an address from
`_client_ip()`. `message` is what to say if they're over the limit.

1. No key (the address is unknown) → no limit, return straight away.
2. `most, window = LIMITS[kind]`: take the pair of numbers apart into two variables. For `"signup_ip"`,
   `most = 10` and `window = 3600`.
3. In one transaction:
   - **Tidy up**: delete rows older than the longest window (one hour). `max(w for _, w in LIMITS.values())`
     goes through every pair, ignores the first number (`_` is the usual name for "don't need this"), and
     picks the biggest second number: 3600.
   - **Count** this key's tries of this kind within the window.
   - Already at the limit → `fail(...)` with **429**. The error also cancels the transaction, so nothing is saved.
   - Otherwise **write down** this try and return its `id`, like a receipt. A try can be handed back later
     using it (see `login()`).

**Why one transaction?** Imagine 30 guesses sent at *exactly* the same moment. Without it, all 30 could count
"4 so far, fine" before any of them wrote its own line, and all 30 would get in. Inside a transaction, the
first request's `DELETE` takes the database's write lock. The others wait their turn, so each one counts
the lines the earlier ones wrote. When this was tested by sending 30 wrong passwords at once, exactly 5 got a
password check and the other 25 were refused.

### `_clear_wrong_passwords()`, lines 131–133

```python
def _clear_wrong_passwords(login, give_back=None):
    db.execute("DELETE FROM attempts WHERE (kind = 'wrong_password' AND key = ?) OR id = ?", (login, give_back))
```

- Wipe an account's wrong-password lines: its pause is lifted and it starts again from zero.
- `OR id = ?` also deletes one other line, the receipt passed as `give_back`. When there's none, `give_back`
  is `None`, which SQL calls `NULL`. Nothing is ever equal to `NULL` in SQL, so that part matches no rows.

## 7. Lines 136–177: codes texted to a phone

Signing up and "forgot password" both text a 6-digit code to prove the person holds that phone. The parts
they share are written once, here.

### `_new_code()`, lines 139–142

```python
def _new_code():
    code = f"{secrets.randbelow(1_000_000):06d}"
    return code, generate_password_hash(code)
```

- `secrets.randbelow(1_000_000)`: a random whole number from 0 to 999,999.
  `:06d` pads it to 6 digits with leading zeros: `4821` → `"004821"`.
- Return **two** things: the code (to text to the person) and its **hash** (to store). A 6-digit code is
  guessable, so it gets the same slow hashing as passwords.

### `_code_from()`, lines 145–149

```python
def _code_from(d):
    code = re.sub(r"\D", "", text(d, "code", 20))
    if len(code) != 6:
        fail("Enter the 6-digit code")
    return code
```

Take the `code` the person typed and keep the digits only. `\D` means "anything that isn't a digit", and
`re.sub` replaces each one with nothing. So `"482 913"` → `"482913"`. Not 6 digits → a clear message.

### `_check_code()`, lines 152–159: is this code right?

```python
def _check_code(table, row, code):
    if check_password_hash(row["code_hash"], code):
        return
    db.execute(f"UPDATE {table} SET attempts = attempts + 1, used = attempts + 1 >= ? WHERE id = ?", (CODE_TRIES, row["id"]))
    left = CODE_TRIES - row["attempts"] - 1
    fail(f"That code isn't right. {left} {'try' if left == 1 else 'tries'} left" if left > 0
         else "That code isn't right, and it has now stopped working. Ask for a new one")
```

`table` is `"signup_codes"` or `"password_resets"`, and `row` is the code's row from that table.

- Right code → `return`, and the caller carries on.
- Wrong code: add 1 to `attempts`. In the same statement, set `used` to the result of `attempts + 1 >= 5`.
  SQLite gives `1` (true) or `0` (false). Inside an `UPDATE`, the right side uses the row's **old** values, so
  on the 5th wrong guess (old attempts = 4) `used` becomes 1 and the code is dead.
- Tell them how many tries are left ("1 try" / "3 tries"), or that the code has stopped working.

**Why?** A 6-digit code has a million possibilities. With only 5 guesses, guessing it is hopeless.

> The table's name is put into the SQL text with an f-string, not a `?`. A `?` can only stand for a value,
> never a table name. That's safe here because `table` is always one of two names written in this file,
> never something a visitor typed.

### `_check_sms_budget()`, lines 162–171: a daily cap on texts

```python
def _check_sms_budget():
    since = int(time.time()) - 86400
    sent = db.query("""SELECT (SELECT COUNT(*) FROM signup_codes WHERE created > ?)
                            + (SELECT COUNT(*) FROM password_resets WHERE issued_by IS NULL AND created > ?) n""",
                    (since, since), one=True)["n"]
    if sent >= current_app.config["SMS_DAILY_LIMIT"]:
        current_app.logger.error("SMS daily limit reached: %s texts in 24 hours (JALSETU_SMS_DAILY_LIMIT)", sent)
        fail("We can't send more codes right now. Try again later, or call JalSetu support", 503)
```

- `86400` seconds = 24 hours.
- Count every text sent in that time: sign-up codes, plus reset codes people asked for themselves (codes an
  admin read out weren't texted). Two small counts are added together, and the total is named `n`.
- At the daily limit (200 unless `JALSETU_SMS_DAILY_LIMIT` says otherwise), write an error in the backend log
  and refuse with **503 Service Unavailable**. Each real SMS costs money, so this caps the bill.

### `_signed_in()`, lines 174–177

```python
def _signed_in(uid, name, phone, role, status=200):
    mark_seen(uid)
    return jsonify(token=issue_token(uid), user=dict(id=uid, name=name, phone=phone, role=role)), status
```

Every way into an account ends the same way: mark them online and reply with a new token and their public
details. `status=200` is a **default**: used unless the caller gives another number (sign-up gives 201).

## 8. Lines 180–283: sign up, sign in, sign out, me

### Signing up takes two steps

```
 New customer fills in name, phone, password → "Create account"
        │
        ▼  POST /api/register  {name, phone, password, role}
 Backend: details OK? this network under 10 sign-ups this hour? number not taken yet?
          → keeps the details in signup_codes (NOT in users yet)
          → texts a 6-digit code                          → 202 "now enter the code"
        │
        ▼  Customer reads the code and types it in
           POST /api/register/verify  {phone, code}
 Backend: newest unused, unexpired code for this phone?
          wrong → attempts + 1 (5th wrong guess kills the code)
          right → in ONE transaction: mark the code used, create the account in users
          → issue a token → signed in                    → 201 Created
```

**Why not create the account straight away?** Then anyone could sign up with *your* phone number. The code
proves the person really holds that phone.

### `register()`, lines 180–222: `POST /api/register`

```python
@bp.post("/register")
def register():
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
```

- Read the JSON body. Clean the name (max 80 chars) and the phone.
- Password must be text, otherwise treat it as empty.
- Role may only be `user` or `supplier`. **Nobody can sign themselves up as `admin`.** Anything else becomes `user`.
- Check each field, with a clear message for each problem.

```python
    _take("signup_ip", _client_ip(), "Too many sign-ups from this network in the last hour. Try again later")
    if db.query("SELECT 1 FROM users WHERE phone = ?", (phone,), one=True):
        fail(TAKEN, 409)
    password_hash = generate_password_hash(password)
```

- Count this sign-up against the internet address (at most 10 an hour, section 6).
- The number already has an account → **409 Conflict**, "Sign in instead".
- Hash the password now. Only the hash is ever kept, even while waiting for the code.

The count comes *before* the "already registered" check on purpose. That check tells anyone whether a number
has an account, so the limit also slows down someone testing number after number.

```python
    if not current_app.config["VERIFY_PHONES"]:
        try:
            uid = db.execute("INSERT INTO users(name,phone,password_hash,role) VALUES(?,?,?,?)",
                             (name, phone, password_hash, role)).lastrowid
        except sqlite3.IntegrityError:
            fail(TAKEN, 409)
        return _signed_in(uid, name, phone, role, 201)
```

A switch for running the site before an SMS company is connected: with `JALSETU_VERIFY_PHONES=0`, skip the
code and create the account at once. `.lastrowid` = the new user's `id`. If two people grab the same number at
the same moment, the UNIQUE rule on `phone` makes SQLite raise `IntegrityError` → 409.

```python
    now = int(time.time())
    asked = db.query("SELECT COUNT(*) n FROM signup_codes WHERE phone = ? AND created > ?", (phone, now - 3600), one=True)["n"]
    if asked >= CODES_PER_HOUR:
        fail("You've asked for 3 codes in the last hour. Wait a while, then try again", 429)
    _check_sms_budget()
    code, code_hash = _new_code()
```

- At most 3 codes per phone number per hour, so nobody can flood one person's phone with texts.
- Check the daily SMS cap.
- Make a code. `code, code_hash = …` catches the two things `_new_code()` returns in two variables.

```python
    con = db.get()
    with con:
        con.execute("DELETE FROM signup_codes WHERE created < ?", (now - 2 * 86400,))
        con.execute("UPDATE signup_codes SET used = 1 WHERE phone = ? AND used = 0", (phone,))
        con.execute("""INSERT INTO signup_codes(phone,name,role,password_hash,code_hash,created,expires)
                       VALUES(?,?,?,?,?,?,?)""", (phone, name, role, password_hash, code_hash, now, now + CODE_TTL))
    delivery = sms.send(phone, SMS_TEXT.format(code=code))
    return jsonify(ok=True, verify=True, delivery=delivery, expires=now + CODE_TTL), 202
```

In one transaction:

1. Tidy up: delete rows more than 2 days old. (The counts above look back a day at most.)
2. Cancel this number's older unused codes, so only the newest one works.
3. Save the waiting sign-up: details, password hash, code hash, and an expiry 15 minutes ahead.

Then text the code (lesson 05: for now it's printed in the backend terminal) and answer **202 Accepted**,
which means "received, but not finished yet". The reply has no sign-in token, and that's how the frontend
([AuthModal.tsx](../frontend/components/AuthModal.tsx)) knows to show the "enter your code" step. `delivery`
says how the code went out; `"console"` makes the frontend show a "test mode" note. The code itself is
**not** in the reply, or anyone could sign up with anyone's number.

### `register_verify()`, lines 225–248: `POST /api/register/verify`

```python
    phone = normalize_phone(d.get("phone"))
    if not phone:
        fail("Enter a 10-digit mobile number")
    code = _code_from(d)
    row = db.query("""SELECT id, name, role, password_hash, code_hash, attempts FROM signup_codes
                      WHERE phone = ? AND used = 0 AND expires > ? ORDER BY id DESC""", (phone, int(time.time())), one=True)
    if not row:
        fail(EXPIRED)
    _check_code("signup_codes", row, code)
```

- Clean the phone and the code.
- Find this phone's **newest** (`ORDER BY id DESC`) code that is unused and unexpired. None → "expired or used".
- `_check_code` (section 7): a wrong code stops here with "x tries left".

```python
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
```

Right code. In **one transaction**:

1. Mark the code used, but only `WHERE … used = 0`. If two requests raced with the same code, only the
   first changes a row (`rowcount` = 1). The second gets 0 → "expired", and the transaction rolls back. This
   is called guarding against a **race condition**. The waiting copy of the password hash is wiped too
   (`password_hash = ''`): it's about to move into `users`, and there's no reason to keep a second copy.
2. Create the account with the details that were waiting.

If the number got an account while the code was waiting, the UNIQUE rule refuses the new row → 409.
Otherwise, sign them in with **201 Created**.

### `login()`, lines 251–269: `POST /api/login`

```python
@bp.post("/login")
def login():
    d = body()
    raw = text(d, "phone", 40)
    login_name = normalize_phone(raw) or raw  # the admin account signs in as "admin", not a phone number
    password = d.get("password") if isinstance(d.get("password"), str) else ""
```

`normalize_phone(raw) or raw`: use the tidied phone number, or if it isn't one (like `admin`), use what was typed.

```python
    ip_try = _take("wrong_password_ip", _client_ip(),
                   "Too many wrong passwords from this network. Try again in a few minutes")
    _take("wrong_password", login_name, "Too many wrong passwords. Try again in a few minutes")
```

Before the password is even looked at, count this try as a wrong password twice: once for the internet
address (at most 20 in 15 minutes), once for the account (at most 5 in 5 minutes). Either limit reached →
**429**, even if the password would have been right. Keep the address's receipt in `ip_try`.

```python
    user = db.query("SELECT * FROM users WHERE phone = ?", (login_name,), one=True)
    if not user or not check_password_hash(user["password_hash"], password):
        fail("Wrong phone number or password", 401)
    _clear_wrong_passwords(login_name, give_back=ip_try)
    mark_seen(user["id"])
    return jsonify(token=issue_token(user["id"]), user=_public(user))
```

- Find the account. `check_password_hash` hashes the typed password the same way and compares.
- No account **or** wrong password → **401**, and both lines written above stay in the notebook. Notice it's
  the **same message** either way, so a guesser can't tell which part was wrong.
- Right password → wipe the account's wrong-password lines and hand back this try's line for the address.
  Then mark them online and return a new token and the public user details.

Three choices worth noticing:

- **Counted before checking.** Writing the line first, and handing it back if the password was right, means
  30 tries sent at the same moment can't all slip through before any was counted (section 6).
- **The address first.** Once an address is over its limit, `login()` stops at the first `_take`, so its tries
  no longer count against accounts. Someone blocked can't keep pushing other people's accounts into a pause.
- **Only this try is handed back to the address.** Its earlier wrong passwords stay. Otherwise someone could
  sign in to an account of their own between guesses to wipe their count.

### `logout()`, lines 272–277

```python
@bp.post("/logout")
def logout():
    token = _bearer()
    if token:
        db.execute("DELETE FROM tokens WHERE token_hash = ?", (_hash(token),))
    return jsonify(ok=True)
```

Delete **this** device's token. Other devices stay signed in. It always answers OK.

### `me()`, lines 280–283: `GET /api/me`

```python
@bp.get("/me")
@auth()
def me():
    return jsonify(g.user)
```

The guard does all the work. If you're signed in, it returns who you are. The frontend calls this on page load
(to check the saved token still works) and every 2 minutes (a "heartbeat" that keeps you "online").

## 9. Lines 286–350: forgotten passwords

The whole flow:

```
 Customer: "Forgot password?" → types phone
        │
        ▼  POST /api/password/forgot  {phone}
 Backend: this network under 10 asks this hour? account exists?
          this number asked < 3 times this hour? daily SMS cap not reached?
          → makes a random 6-digit code, saves its HASH (valid 15 min)
          → sms.send(...)  (for now: printed in the backend terminal)
        │
        ▼  Customer reads the code, types code + new password
           POST /api/password/reset  {phone, code, password}
 Backend: newest unused, unexpired code for this phone?
          wrong → attempts + 1 (5th wrong guess kills the code)
          right → in ONE transaction: mark code used, set new password hash,
                  delete ALL tokens (signed out everywhere)
          → lift any wrong-password pause, issue a fresh token → customer is signed in
```

Someone who can't receive the SMS can phone JalSetu support. An admin then makes a code for them on the
admin dashboard (lesson 08), using the same `issue_reset_code` function.

### `issue_reset_code()`, lines 290–299

```python
def issue_reset_code(user_id, issued_by=None):
    code, code_hash = _new_code()
    now = int(time.time())
    con = db.get()
    with con:
        con.execute("UPDATE password_resets SET used = 1 WHERE user_id = ? AND used = 0", (user_id,))
        con.execute("INSERT INTO password_resets(user_id,code_hash,created,expires,issued_by) VALUES(?,?,?,?,?)",
                    (user_id, code_hash, now, now + CODE_TTL, issued_by))
    return code, now + CODE_TTL
```

- Make a code and its hash (section 7).
- Cancel any older unused codes for this account (only the newest one works).
- Save the **hash** with a 15-minute expiry and who issued it (`None` = the person asked themselves).
- Return the code (to text or show to the admin) and its expiry time.

### `forgot_password()`, lines 302–320: `POST /api/password/forgot`

```python
    phone = normalize_phone(body().get("phone"))
    if not phone:
        fail("Enter the 10-digit mobile number you signed up with")
    _take("reset_ip", _client_ip(), "Too many codes asked for from this network. Try again later, or call JalSetu support")
    user = db.query("SELECT id FROM users WHERE phone = ?", (phone,), one=True)
    if not user:
        # /register already tells anyone whether a number is taken, so hiding it here would protect nothing
        fail("No JalSetu account uses this number. Check it, or create a new account", 404)
```

- Validate the phone.
- Count this ask against the internet address (at most 10 an hour). Like in `register()`, this comes before
  the "does this account exist?" answer.
- Find the account. The comment explains a deliberate choice: many sites hide whether an account exists, but
  here sign-up already reveals it, so a clear message is more helpful.

```python
    asked = db.query("SELECT COUNT(*) n FROM password_resets WHERE user_id = ? AND issued_by IS NULL AND created > ?",
                     (user["id"], int(time.time()) - 3600), one=True)["n"]
    if asked >= CODES_PER_HOUR:
        fail("You've asked for 3 codes in the last hour. Wait a while, or ask JalSetu support for a code", 429)
    _check_sms_budget()
```

Count codes this account requested **itself** (`issued_by IS NULL`) in the last hour (3600 seconds).
`COUNT(*) n` names the result column `n`. Three or more → **429**. Then check the daily SMS cap.

```python
    code, expires = issue_reset_code(user["id"])
    delivery = sms.send(phone, SMS_TEXT.format(code=code))
    return jsonify(ok=True, delivery=delivery, expires=expires)
```

Make the code, "send" it, and tell the frontend how it went (`"console"` → it shows the "test mode" note).
The code itself is **not** in the response, or anyone could reset anyone's password.

### `reset_password()`, lines 323–350: `POST /api/password/reset`

```python
    d = body()
    phone = normalize_phone(d.get("phone"))
    if not phone:
        fail("Enter the 10-digit mobile number you signed up with")
    code = _code_from(d)
    password = d.get("password") if isinstance(d.get("password"), str) else ""
    if len(password) < 6:
        fail("Password must be at least 6 characters")
```

Clean and check the inputs. `_code_from` keeps the digits of the code (section 7).

```python
    row = db.query("""SELECT r.id, r.code_hash, r.attempts, u.id user_id, u.name, u.phone, u.role
                      FROM password_resets r JOIN users u ON u.id = r.user_id
                      WHERE u.phone = ? AND r.used = 0 AND r.expires > ? ORDER BY r.id DESC""",
                   (phone, int(time.time())), one=True)
    if not row:
        fail(EXPIRED)
    _check_code("password_resets", row, code)
```

Find this phone's **newest** code that is unused and unexpired. None → "expired or used". Then check it with
the same `_check_code` that sign-up uses: 5 wrong guesses and it's dead.

```python
    con = db.get()
    with con:  # use up the code, change the password and end old sign-ins together, or not at all
        if not con.execute("UPDATE password_resets SET used = 1 WHERE id = ? AND used = 0", (row["id"],)).rowcount:
            fail(EXPIRED)  # another request used this code a moment ago
        con.execute("UPDATE users SET password_hash = ? WHERE id = ?", (generate_password_hash(password), row["user_id"]))
        con.execute("DELETE FROM tokens WHERE user_id = ?", (row["user_id"],))
    _clear_wrong_passwords(row["phone"])
    return _signed_in(row["user_id"], row["name"], row["phone"], row["role"])
```

Right code. In **one transaction**:

1. Mark the code used, with the same `used = 0` guard against two requests racing as in `register_verify()`.
2. Save the new password's hash.
3. Delete **all** the account's tokens: signed out on every device. If someone else had got in, they're now out.

Then lift any wrong-password pause on the account (they've just proved who they are), and sign them in on
**this** device.

---

## Quick check

1. If someone copies `jalsetu.db`, can they read users' passwords? Why or why not?
2. What's the difference between `@auth()` and `@auth("admin")`?
3. Why does login say "Wrong phone number or password" instead of "No such phone number"?
4. What happens to a texted code after 5 wrong guesses?
5. Why does a password reset delete every token for that account?
6. Why does sign-up wait for the texted code before creating the account?
7. Why are wrong passwords written in the database instead of kept in the server's memory?
8. On your own computer, why are the limits per internet address switched off?

<details><summary>Answers</summary>

1. No. Only slow, salted hashes are stored, and hashes can't be reversed.
2. `@auth()` lets any signed-in account in. `@auth("admin")` also requires the role to be `admin` (otherwise 403).
3. So a guesser can't find out which phone numbers have accounts from the login form.
4. `used` becomes 1, so it stops working, and the person has to ask for a new one.
5. To sign the account out everywhere, in case someone else had access. The person is then signed in again on this device only.
6. The code proves the person holds that phone. Otherwise anyone could sign up with someone else's number.
7. Restarting the server wipes its memory, which would give a guesser a fresh set of tries. And when several
   copies of the backend run at once, they each have their own memory but share one database.
8. Every request reaches Flask through the Next.js server, so they all seem to come from `127.0.0.1`. Counting
   by that address would lump every visitor together, and one person's mistakes would lock everyone out.

</details>

**Next:** [07 — Backend: suppliers and orders](07-backend-suppliers-and-orders.md)
