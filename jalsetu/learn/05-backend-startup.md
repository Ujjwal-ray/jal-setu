# 05 — Backend: starting up

**In this lesson:** what Flask is, and four files line by line:
[requirements.txt](../requirements.txt), [app.py](../app.py), [backend/\_\_init\_\_.py](../backend/__init__.py),
[backend/util.py](../backend/util.py) and [backend/sms.py](../backend/sms.py).

---

## 1. What is Flask?

Writing a web server from nothing means handling network connections and decoding HTTP by hand. **Flask** is a
Python **library** (ready-made code you can use) that does all that. You just say:

> "When a `GET` request for `/api/health` arrives, run this function, and send back what it returns."

```python
@app.get("/api/health")
def health():
    return jsonify(ok=True)
```

- `@app.get("/api/health")` is a **decorator** (the `@` line). It registers the function below as the
  handler for that method + path. That pairing is called a **route**.
- The function is called a **view**. Whatever it returns becomes the response.
- `jsonify(ok=True)` builds a JSON response: `{"ok": true}`.

## 2. `requirements.txt`

```
flask>=3.0
```

The list of Python packages the backend needs: Flask, version 3.0 or newer. `pip install -r requirements.txt`
downloads them. (`pip` is Python's package installer.) Flask brings its helpers along automatically, such as
**Werkzeug** (password hashing, HTTP errors) and **Click** (terminal commands).

## 3. `app.py`: the front door

```python
 1  """JalSetu backend entry point.
 2
 3      python app.py                        -> http://127.0.0.1:5000
 4      flask --app app create-admin LOGIN   -> add an admin account
 5      flask --app app reset-password LOGIN -> set a new password for any account (admins included)
 6
 7  Environment: JALSETU_DB (database file), JALSETU_SEED=0 (no demo data), HOST, PORT, JALSETU_DEBUG=1,
 8  JALSETU_SMS (how reset codes are texted; default "console" prints them here, see backend/sms.py).
 9  """
10  import os
11
12  from backend import create_app
13
14  app = create_app()
15
16  if __name__ == "__main__":
17      app.run(host=os.environ.get("HOST", "127.0.0.1"),
18              port=int(os.environ.get("PORT", 5000)),
19              debug=os.environ.get("JALSETU_DEBUG") == "1")
```

| Line | Meaning |
|------|---------|
| 1–9 | A docstring: how to use this file. The `->` arrows are just text in the note |
| 10 | `os` = Python's toolbox for the operating system: file paths, **environment variables** |
| 12 | Import the `create_app` function from the `backend` folder. (A folder with an `__init__.py` is a Python **package**; importing `backend` runs `backend/__init__.py`) |
| 14 | Build the app. Everything is set up inside `create_app()` (next section) |
| 16 | `__name__` is `"__main__"` only when *this* file is the one you ran (`python app.py`). If another program imports `app.py`, as the `flask` command does, this block is skipped |
| 17 | Start the server. `host` = which network address to listen on. `127.0.0.1` means "only this computer can connect" |
| 18 | `port` = 5000 unless the `PORT` environment variable says otherwise. `int(...)` converts text `"5000"` to the number `5000` |
| 19 | Debug mode (auto-restart on code changes, detailed error pages) only if `JALSETU_DEBUG` is `"1"`. `==` gives `True` or `False` |

**Environment variables** are settings you give a program from outside, without editing its code. In
PowerShell: `$env:PORT = "8000"; python app.py`. `os.environ.get("PORT", 5000)` reads one, with `5000` as the
fallback when it isn't set.

## 4. `backend/__init__.py`: assembling the app

### Lines 1–13: imports and constants

```python
"""JalSetu backend: the Flask + SQLite JSON API behind the Next.js frontend."""
import os

from flask import Flask, jsonify, send_from_directory
from werkzeug.exceptions import HTTPException

from . import admin, auth, db, orders, suppliers
from .util import ApiError

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MESSAGES = {400: "Bad request", 401: "Sign in required", 403: "Not allowed", 404: "Not found",
            405: "Method not allowed", 413: "Request too large", 500: "Something went wrong on the server"}
```

- `Flask`: the class that *is* the web app. `send_from_directory`: sends a file from a folder.
- `HTTPException`: Werkzeug's family of HTTP errors (404, 405, …).
- Line 7 imports the other backend files as **modules**, so this file can use `auth.bp`, `db.init_app`, etc.
- **Line 10** works out the project folder:
  - `__file__` = this file's path, e.g. `D:\…\jalsetu\backend\__init__.py`
  - `os.path.abspath(...)` makes sure it's a full path
  - `os.path.dirname(...)` once → `D:\…\jalsetu\backend`
  - `os.path.dirname(...)` again → `D:\…\jalsetu`. That's `ROOT`.
- **Line 12**: a dict from status code → friendly English message, used by the error handler below.

### Lines 16–25: `create_app()` and its settings

```python
def create_app(config=None):
    app = Flask(__name__, static_folder=os.path.join(ROOT, "static"), static_url_path="")
    app.config.update(
        DB_PATH=os.environ.get("JALSETU_DB", os.path.join(ROOT, "jalsetu.db")),
        SEED_DEMO=os.environ.get("JALSETU_SEED", "1") != "0",  # demo accounts + suppliers in an empty database
        TOKEN_TTL=30 * 24 * 3600,                               # sign-in lasts 30 days
        MAX_CONTENT_LENGTH=64 * 1024,
        SMS_PROVIDER=os.environ.get("JALSETU_SMS", "console"),  # see sms.py
    )
    app.config.update(config or {})
```

A function that *builds and returns* the app is called an **app factory**. Tests can call it with different
settings.

- **17** Make the Flask app. `static_folder` = where plain files (HTML, images) are served from: `jalsetu/static/`.
  `static_url_path=""` means those files appear at the top of the address, e.g. `/index.html`.
- **18–24** `app.config` is the app's settings dict:
  - `DB_PATH`: where the database file is. `os.path.join` glues folder and file names with the right slash.
  - `SEED_DEMO`: `True` unless `JALSETU_SEED` is `"0"`.
  - `TOKEN_TTL`: "time to live" of a sign-in: 30 days × 24 hours × 3600 seconds = 2,592,000 seconds.
  - `MAX_CONTENT_LENGTH`: refuse request bodies over 64 KB (64 × 1024 bytes), so nobody can send huge junk. Flask answers 413.
  - `SMS_PROVIDER`: how text messages are sent (see `sms.py`).
- **25** `config or {}`: if `config` was given, apply it on top. `or` picks the right side when the left is empty/`None`.

### Lines 27–31: plug everything in

```python
    db.init_app(app)
    for module in (auth, suppliers, orders, admin):
        app.register_blueprint(module.bp, url_prefix="/api")
    app.cli.add_command(admin.create_admin)
    app.cli.add_command(admin.reset_password)
```

- **27** Set up the database: run migrations, add demo data, close connections after each request (lesson 04).
- **28–29** Each of the four files has a **Blueprint** called `bp`: a bundle of routes defined in that file.
  Registering it adds all its routes to the app, with `/api` in front. So `@bp.post("/orders")` in
  `orders.py` becomes `POST /api/orders`.
  **Why blueprints?** Each feature stays in its own file, instead of one enormous file.
- **30–31** Add two **terminal commands** (lesson 08): `flask --app app create-admin LOGIN` and `flask --app app reset-password LOGIN`.

### Lines 33–39: two simple routes

```python
    @app.get("/api/health")
    def health():
        return jsonify(ok=True)

    @app.get("/")
    def index():  # the earlier single-file prototype UI
        return send_from_directory(app.static_folder, "index.html")
```

- `/api/health`: "are you alive?" Answers `{"ok": true}`.
- `/`: visiting `http://localhost:5000/` shows the old prototype page `static/index.html`. (The real site is the Next.js one on port 3000.)

These functions are defined *inside* `create_app`. That's allowed in Python, and it keeps them tied to this `app`.

### Lines 41–49: turning errors into JSON

```python
    @app.errorhandler(ApiError)
    def api_error(e):
        return jsonify(error=e.message), e.status

    @app.errorhandler(HTTPException)
    def http_error(e):  # 404s, 405s, and unhandled exceptions (as 500) all answer in JSON
        if e.code == 500:
            app.logger.error("Unhandled error", exc_info=getattr(e, "original_exception", None) or e)
        return jsonify(error=MESSAGES.get(e.code, e.name)), e.code

    return app
```

This is a really useful pattern, so read it slowly.

- Anywhere in the backend, code can call `fail("Enter the delivery address")`. That **raises** an `ApiError`
  (see `util.py`), which stops the view function immediately.
- `@app.errorhandler(ApiError)` says "whenever an `ApiError` escapes a view, run `api_error`". It returns
  `{"error": "Enter the delivery address"}` with the error's status (400 by default).
- Returning a **pair** `(body, status)` from a Flask function sets both the JSON and the status code.
- The second handler catches every *other* HTTP error (wrong address → 404, wrong method → 405, crash → 500)
  and also answers in JSON, using the friendly `MESSAGES`. `MESSAGES.get(e.code, e.name)` = the friendly text,
  or Werkzeug's own name for codes not in the dict.
- For a 500 (a bug), it also writes the full error to the terminal log, so a developer can fix it.
- **Why?** The frontend always gets the same shape back, `{"error": "..."}`, and can show the message as-is.
  You'll see that in `lib/api.ts` (lesson 10).

## 5. `backend/util.py`: helpers used everywhere

### Lines 8–17: `ApiError` and `fail()`

```python
class ApiError(Exception):
    """Raised anywhere in a request; turned into {"error": message} with the given HTTP status."""

    def __init__(self, message, status=400):
        super().__init__(message)
        self.message, self.status = message, status


def fail(message, status=400):
    raise ApiError(message, status)
```

- `class ApiError(Exception)`: a new kind of error that *is a kind of* Python `Exception`.
- `__init__` runs when one is made. It stores the message and the status (400 unless given).
- `self.message, self.status = message, status` sets two things in one line.
- `fail(...)` is a short way to write `raise ApiError(...)`. Example: `fail("Supplier not found", 404)`.

### Lines 20–23: `body()`, read the JSON the frontend sent

```python
def body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}
```

- `request` is Flask's object for the *current* incoming request.
- `get_json(silent=True)` reads the body as JSON. `silent=True` means "give `None` instead of crashing if it isn't valid JSON".
- `isinstance(data, dict)` checks it really is a dict (`{...}`). If someone sent a list or garbage, use an empty dict `{}`.
- **Why?** Code that uses `body()` can safely call `.get("phone")` without worrying about strange input.

### Lines 26–33: `text()`, a clean piece of text

```python
def text(data, key, limit):
    value = data.get(key)
    if value is None:
        return ""
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        fail(f"'{key}' must be text")
    return str(value).strip()[:limit]
```

- Get the field. Missing → empty text `""`.
- Refuse `true`/`false`, lists and objects. (Numbers are fine: a phone number sent as `9000000001` becomes text.)
- `str(value)` makes it text, `.strip()` removes spaces at the start and end, and `[:limit]` cuts it to at most `limit` characters.
  Example: `text(d, "address", 300)` gives the address, trimmed, max 300 characters.

### Lines 36–59: `number()`, a checked number

```python
_REQUIRED = object()


def number(data, key, label, default=_REQUIRED, lo=None, hi=None, integer=False):
```

- `_REQUIRED = object()` makes a unique marker value. If `default` is still this marker, the caller didn't
  give a default, so the field is **required**. (`None` couldn't be used as the marker, because a caller
  might genuinely want `None` as a default.)
- `label` is the human name for error messages ("Number of jars"). `lo`/`hi` = allowed range.
  `integer=True` = whole numbers only.

```python
    value = data.get(key)
    if value is None or value == "":
        if default is _REQUIRED:
            fail(f"{label} is required")
        return default
```
Missing or empty → error if required, otherwise the default.

```python
    try:
        if isinstance(value, bool):
            raise ValueError
        n = float(value)
    except (TypeError, ValueError):
        fail(f"{label} must be a number")
```
Try to turn it into a decimal number. `"40"` → `40.0` works. `"abc"` raises `ValueError` → nice error.
`true` is refused on purpose: Python would otherwise treat `True` as `1`.

```python
    if not math.isfinite(n) or (integer and n != int(n)):
        fail(f"{label} must be a whole number" if integer else f"{label} must be a number")
```
`isfinite` refuses "infinity" and "not a number" (yes, those are valid floats). `n != int(n)` catches `2.5` when a whole number is needed.

```python
    if lo is not None and hi is not None and not lo <= n <= hi:
        fail(f"{label} must be between {lo:g} and {hi:g}")
    if lo is not None and n < lo:
        fail(f"{label} must be at least {lo:g}")
    if hi is not None and n > hi:
        fail(f"{label} must be at most {hi:g}")
    return int(n) if integer else n
```
- Range checks. `lo <= n <= hi` is Python's "between" (a **chained comparison**).
- `{lo:g}` formats the number neatly: `1.0` prints as `1`.
- Finally return a whole number (`int`) or a decimal (`float`).

Example from `orders.py`: `number(d, "qty", "Number of jars", default=1, lo=1, hi=50, integer=True)` →
missing means 1; `"3"` → `3`; `0` → "Number of jars must be between 1 and 50"; `2.5` → "must be a whole number".

### Lines 62–69: `normalize_phone()`, tidy any Indian mobile number

```python
def normalize_phone(raw):
    """'+91 98300 11111' / '098300 11111' -> '9830011111'. None unless it is a 10-digit Indian mobile number."""
    digits = re.sub(r"\D", "", str(raw or ""))
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    return digits if re.fullmatch(r"[6-9]\d{9}", digits) else None
```

This uses **regular expressions** ("regex"), a mini-language for patterns in text. `re` is Python's regex library.

- `str(raw or "")`: if `raw` is `None`, use `""`.
- `re.sub(r"\D", "", ...)`: **sub**stitute every **non-digit** (`\D`) with nothing. So `+91 98300 11111` → `919830011111`.
- 12 digits starting with `91` (India's country code)? Drop the first 2: `digits[2:]` = from position 2 to the end.
- 11 digits starting with `0`? Drop the `0`.
- `re.fullmatch(r"[6-9]\d{9}", digits)`: the **whole** text must be one digit from 6 to 9, then exactly 9 more digits (`\d{9}`). Indian mobile numbers start with 6, 7, 8 or 9.
- Valid → the 10 digits. Otherwise → `None`.

**Why?** People type numbers in many ways. Storing one standard form means "+91 90000 00001" and "9000000001" are recognised as the same account.

### Lines 72–75: `query_float()`, a number from the URL

```python
def query_float(name):
    value = request.args.get(name, type=float)
    return value if value is not None and math.isfinite(value) else None
```

`request.args` holds the query string (`?lat=22.56&lng=88.39`). `type=float` converts it, giving `None` if it isn't a number.

### Lines 78–83: `km()`, distance between two map points

```python
def km(lat1, lng1, lat2, lng2):
    """Great-circle distance in kilometres."""
    p = math.pi / 180
    x = (math.sin((lat2 - lat1) * p / 2) ** 2
         + math.cos(lat1 * p) * math.cos(lat2 * p) * math.sin((lng2 - lng1) * p / 2) ** 2)
    return 12742 * math.asin(math.sqrt(x))
```

The Earth is a ball, so distance between two latitude/longitude points needs a special formula, the
**haversine formula**. You don't need to follow the maths:

- `p = π / 180` converts degrees to radians (the unit `sin` and `cos` expect).
- `x` combines the north-south and east-west differences, allowing for the Earth's curve.
- `12742` is the Earth's **diameter** in km (2 × 6371 km radius).

Result: distance in km "as the crow flies" (not by road).

## 6. `backend/sms.py`: sending text messages

```python
def send(phone, message):
    """Send `message` to a 10-digit Indian mobile number. Returns how it went out: "sms" or "console"."""
    provider = current_app.config["SMS_PROVIDER"]
    if provider == "console":
        current_app.logger.warning("SMS to %s: %s", phone, message)
        return "console"
    raise RuntimeError(f"No SMS provider called {provider!r} is set up (JALSETU_SMS)")
```

Real SMS costs money and needs an account with an SMS company (and, in India, DLT registration). So for now:

- With the setting `"console"` (the default), the "SMS" is just **printed in the backend's terminal** as a
  warning line, e.g. `SMS to 9000000001: Your JalSetu code is 482913. ...`. It returns `"console"`, and the
  frontend then shows "Test mode: … the code is printed in the terminal".
- Any other setting raises an error, because no real provider is written yet.
- `{provider!r}` prints the value with quotes, e.g. `'twilio'`.

To connect a real SMS service later, a developer adds a branch here. Nothing else would need to change.

## 7. What happens when you type `python app.py`

1. Python runs `app.py`, which imports `backend` → runs `backend/__init__.py`, which imports
   `admin.py`, `auth.py`, `db.py`, `orders.py`, `suppliers.py` and `util.py`. (Each file creates its Blueprint and its constants.)
2. `create_app()` runs:
   1. makes the Flask app and its settings,
   2. `db.init_app()` → opens `jalsetu.db` (creating it if needed), runs missing migrations, adds demo data if empty,
   3. registers the 4 blueprints under `/api`, the terminal commands, `/api/health`, `/` and the error handlers.
3. `app.run(...)` starts listening on `127.0.0.1:5000`. The terminal prints something like
   `Running on http://127.0.0.1:5000`. It now waits for requests, forever, until you press **Ctrl+C**.
4. For each request: Flask finds the matching route → runs its view → turns the result (or the error) into a
   JSON response → closes the database connection (`teardown`).

---

## Quick check

1. What does `@bp.get("/orders")` in `orders.py` become as a full address, and why?
2. What does `fail("Enter your name")` send back to the frontend?
3. `normalize_phone("+91 90000-00001")` returns what? And `normalize_phone("12345")`?
4. Why are SMS codes printed in the terminal at the moment?

<details><summary>Answers</summary>

1. `GET /api/orders`, because `orders.bp` is registered with `url_prefix="/api"` in `__init__.py`.
2. Status 400 and the JSON `{"error": "Enter your name"}` (via the `ApiError` error handler).
3. `"9000000001"`, and `None` (not a valid 10-digit Indian mobile number).
4. No SMS provider is connected. `SMS_PROVIDER` defaults to `"console"`, so `sms.send` writes the message to the log.

</details>

**Next:** [06 — Backend: accounts and passwords](06-backend-accounts.md)
