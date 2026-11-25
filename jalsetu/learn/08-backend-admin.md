# 08 — Backend: the admin (`admin.py`)

**In this lesson:** [backend/admin.py](../backend/admin.py) line by line: the numbers on the admin dashboard,
the supplier table, problem reports, verifying suppliers, password-help codes, and two commands you type in
the terminal.

Every web endpoint here has `@auth("admin")`, so only admin accounts get in. Everyone else gets **403**.

---

## 1. Lines 1–27: setup

```python
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
```

- `datetime`: dates and times as calendar values (for "the start of this month").
- `click`: the library Flask uses for terminal commands (section 7).
- `ACTIVE` and `ORDER_TOTAL` are **pieces of SQL** kept as text, so several queries can reuse them:
  - `ACTIVE`: the statuses that count as "still in progress".
  - `ORDER_TOTAL`: an order's money total. `COALESCE(x, 0)` uses 0 if the value is missing.

```python
def _month_start():
    return int(datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0).timestamp())


def _pct(avg):
    return None if avg is None else round(avg * 100)
```

- `_month_start()`: take "now", set it to day 1 at 00:00:00, and turn it into a Unix timestamp. That's the
  first moment of this month.
- `_pct(avg)`: the yes/no answers are stored as 1/0, so their **average** is the fraction of "yes".
  0.83 → `83` (percent). No answers → `None`.

## 2. Lines 30–74: `overview()`, `GET /api/admin/overview`

All the big numbers on the admin's **Overview** tab come from this one endpoint.

```python
@bp.get("/admin/overview")
@auth("admin")
def overview():
    now = int(time.time())
    one = lambda sql, args=(): db.query(sql, args, one=True)  # noqa: E731
```

`one` is a small shortcut function: "run this query and give me the single row". (The `# noqa: E731`
comment tells a style-checking tool not to complain about using `lambda` this way.)

### Customers

```python
    customers = one(f"""SELECT
        (SELECT COUNT(*) FROM users WHERE role = 'user') total,
        (SELECT COUNT(DISTINCT user_id) FROM orders WHERE status = 'delivered') served,
        (SELECT COUNT(DISTINCT user_id) FROM orders WHERE status IN {ACTIVE}) ordering_now""")
```

One query that makes three numbers:
- `total`: customer accounts,
- `served`: how many **different** customers (`COUNT(DISTINCT …)`) have had at least one delivery,
- `ordering_now`: how many different customers have an order in progress. `{ACTIVE}` drops the status list into the SQL text.

### Orders

```python
    by_status = {r["status"]: r["n"] for r in db.query("SELECT status, COUNT(*) n FROM orders GROUP BY status")}
    orders = dict(total=sum(by_status.values()), by_status=by_status,
                  active=sum(by_status.get(s, 0) for s in ("pending", "accepted", "out_for_delivery")))
```

- `GROUP BY status` gives one row per status with its count. The dict comprehension turns that into e.g.
  `{"pending": 2, "delivered": 5, "cancelled": 1}`.
- `total` adds them all up. `active` adds up just the in-progress ones (`.get(s, 0)` = 0 if that status has no orders).

### Money

```python
    money = one(f"""SELECT COALESCE(SUM({ORDER_TOTAL}), 0) earned,
        COALESCE(SUM(CASE WHEN COALESCE(o.delivered_at, o.ts) >= ? THEN {ORDER_TOTAL} END), 0) earned_this_month
        FROM orders o WHERE o.status = 'delivered'""", (_month_start(),))
```

Across delivered orders only:
- `earned`: the sum of all totals.
- `earned_this_month`: `CASE WHEN … THEN … END` is SQL's if: count an order's total only if it was delivered
  this month (or placed this month, for old orders without `delivered_at`). Otherwise it's `NULL`, which `SUM` ignores.

### Suppliers

```python
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
```

Nine supplier numbers in one go. Two worth understanding:

- `signed_in`: supplier accounts that have at least one **unexpired token** (they're signed in somewhere).
- `online`: signed in **and** active in the last 10 minutes (`last_seen`, updated by the frontend's 2-minute heartbeat).

This query uses **named placeholders** `:now` and `:since` instead of `?`, filled from the dict
`{"now": …, "since": …}`. Handy when the same value appears more than once.

`signed_out` is worked out in Python: accounts − signed in.

### Feedback

```python
    fb = one("""SELECT COUNT(*) reviews, ROUND(AVG(rating), 1) rating,
        AVG(on_time) on_time, AVG(quality_ok) quality, AVG(quantity_ok) quantity FROM reviews""")
    reports = one("""SELECT COUNT(*) total, COALESCE(SUM(status = 'open'), 0) open,
        COALESCE(SUM(status = 'open' AND by_role = 'customer'), 0) open_from_customers,
        COALESCE(SUM(status = 'open' AND by_role = 'supplier'), 0) open_from_suppliers FROM reports""")
```

- Average stars, and the average of each yes/no question (`AVG` skips `NULL`s, the unanswered ones).
- A neat trick: `SUM(status = 'open')`. Each comparison is 1 or 0 in SQLite, so adding them up **counts** the matches.

```python
    feedback = dict(reviews=fb["reviews"], rating=fb["rating"], on_time_pct=_pct(fb["on_time"]),
                    quality_pct=_pct(fb["quality"]), quantity_pct=_pct(fb["quantity"]), **{f"reports_{k}": v for k, v in reports.items()})

    return jsonify(customers=customers, orders=orders, money=money, suppliers=suppliers, feedback=feedback,
                   online_minutes=ONLINE_SECONDS // 60, generated_at=now)
```

- Turn the averages into percentages.
- `**{f"reports_{k}": v for k, v in reports.items()}` renames every report number with a `reports_` prefix
  (`open` → `reports_open`) and **unpacks** them into the dict (`**` spreads a dict's items in, like `...` in TypeScript).
- Send it all. `//` is whole-number division: 600 // 60 = 10. `generated_at` lets the page show "Updated 3:41:07 pm".

The JSON shape matches the `AdminOverview` type in `frontend/lib/api.ts`.

## 3. Lines 77–104: `suppliers()`, `GET /api/admin/suppliers`

Every shop (**including unverified ones**) with performance numbers, for the **Suppliers** and **Verification** tabs.

```python
    rows = db.query(f"""SELECT s.*, p.price, p.delivery_charge, p.availability, p.jar_size,
        u.name owner_name, u.phone owner_phone, u.last_seen,
        EXISTS (SELECT 1 FROM tokens t WHERE t.user_id = s.user_id AND t.expires > :now) signed_in,
        (SELECT ROUND(AVG(rating), 1) FROM reviews r WHERE r.supplier_id = s.id) rating,
        ... review_count, on_time, quality, quantity,
        ... orders_total, delivered, active, on_the_way, earned, open_reports
        FROM suppliers s LEFT JOIN products p ON p.supplier_id = s.id LEFT JOIN users u ON u.id = s.user_id
        ORDER BY s.verified, s.id DESC""", {"now": now})
```

For each shop: its details, its owner's name/phone/last-seen, and a **subquery per number** (ratings, order
counts by status, money earned from delivered orders, open problem reports on its orders).

`ORDER BY s.verified, s.id DESC`: `verified` 0 comes before 1, so **shops awaiting verification are listed first**. Within each group, newest first.

```python
    for r in rows:
        r["signed_in"] = bool(r["signed_in"])
        r["online"] = r["signed_in"] and (r["last_seen"] or 0) >= now - ONLINE_SECONDS
        for key, pct in (("on_time", "on_time_pct"), ("quality", "quality_pct"), ("quantity", "quantity_pct")):
            r[pct] = _pct(r.pop(key))
    return jsonify(rows)
```

Tidy each row: true/false for `signed_in`, work out `online`, and swap the 0–1 averages for percentages under
new names (`r.pop(key)` removes the old one and hands back its value).

## 4. Lines 107–120: `feedback()`, `GET /api/admin/feedback`

```python
    reports = db.query("""SELECT rp.id, rp.order_id, ..., u.name reporter, u.phone reporter_phone, s.business_name,
        s.contact supplier_contact, cu.name customer, COALESCE(o.phone, cu.phone) customer_phone, o.status order_status, o.qty
        FROM reports rp JOIN orders o ON o.id = rp.order_id JOIN suppliers s ON s.id = o.supplier_id
        JOIN users u ON u.id = rp.user_id JOIN users cu ON cu.id = o.user_id
        ORDER BY rp.status = 'resolved', rp.id DESC LIMIT 200""")
```

Each report, joined with everything the admin needs to act on it: who reported it, the order, the shop and
its phone, and the customer and their phone. `users` is joined **twice** with two nicknames: `u` = the
reporter, `cu` = the order's customer (they may be different people, e.g. when the supplier reports).

`ORDER BY rp.status = 'resolved'` puts false (0, open) before true (1, resolved): **open reports first**.

The second query gets the latest 100 reviews with their yes/no answers, customer name and shop name.

## 5. Lines 123–141: changing things

### `set_report_status()`, `PATCH /api/admin/reports/<id>`

```python
    status = body().get("status")
    if status not in ("open", "resolved"):
        fail("Unknown status")
    resolved_ts = int(time.time()) if status == "resolved" else None
    if not db.execute("UPDATE reports SET status = ?, resolved_ts = ? WHERE id = ?", (status, resolved_ts, rid)).rowcount:
        fail("Report not found", 404)
    return jsonify(id=rid, status=status)
```

Mark a report resolved (recording when) or reopen it. `rowcount` 0 → no such report → 404.

### `verify()`, `POST /api/admin/suppliers/<id>/verify`

```python
    verified = 1 if body().get("verified", True) else 0
    if not db.execute("UPDATE suppliers SET verified = ? WHERE id = ?", (verified, sid)).rowcount:
        fail("Supplier not found", 404)
    return jsonify(ok=True, verified=verified)
```

**This one switch decides whether customers can see a shop.** `{"verified": true}` (or nothing) → 1;
`{"verified": false}` → 0 (hidden again).

## 6. Lines 144–157: `create_reset_code()`, `POST /api/admin/reset-codes`

For someone who forgot their password and can't receive the SMS. They phone support, the admin checks
it's really them, makes a code here and reads it out.

```python
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
```

- Find the account by phone.
- **Admins can't reset another admin's password this way.** That would let one compromised admin account
  take over the others. Admin passwords are reset on the server itself (next section).
- Reuse `issue_reset_code` from `auth.py`, recording **which admin** made it (`issued_by`).
- Unlike the SMS route, the code **is** returned, because the admin has to read it out.

## 7. Lines 160–199: terminal commands

These aren't web endpoints. They're commands you type in a terminal on the server:

```
flask --app app create-admin 9123456789 --name "Priya"
flask --app app reset-password admin
```

```python
@click.command("create-admin")
@with_appcontext
@click.argument("login")
@click.option("--name", default="Admin", show_default=True)
@click.password_option()
def create_admin(login, name, password):
```

Decorators from **Click** describe the command:

| Decorator | Meaning |
|-----------|---------|
| `@click.command("create-admin")` | The command's name |
| `@with_appcontext` | Run it "inside" the Flask app, so `current_app.config["DB_PATH"]` works |
| `@click.argument("login")` | One required word after the name, e.g. `9123456789`. Passed in as `login` |
| `@click.option("--name", default="Admin")` | An optional `--name "Priya"`. Defaults to `Admin` |
| `@click.password_option()` | Asks for the password **twice**, hidden as you type. Passed in as `password` |

```python
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
```

- `ClickException` prints a clean error and stops.
- There's no web request here, so `db.get()` (which uses `g`) isn't available. It opens its own connection with
  `db.connect` and closes it in `finally`.
- Refuse a login that's already taken, otherwise insert the admin with a hashed password.
- `click.echo` prints a message to the terminal.

`reset_password` (lines 181–199) works the same way: find the account (by tidied phone, or the raw login like
`admin`), set the new password hash, delete all its tokens, and print a confirmation.

**Why are these commands and not web pages?** Making admins is the most powerful action in the system. Only
someone with access to the server's terminal should be able to do it.

---

## Quick check

1. Which endpoint's numbers appear on the admin's Overview tab?
2. How does `SUM(status = 'open')` count open reports?
3. Why can't an admin create a reset code for another admin from the dashboard?
4. Where would you go to add a brand-new admin account?
5. In the admin supplier list, why do unverified shops come first?

<details><summary>Answers</summary>

1. `GET /api/admin/overview` (`overview()` in `admin.py`).
2. Each `status = 'open'` is 1 (true) or 0 (false), so adding them up counts the true ones.
3. So one compromised admin account can't take over other admin accounts. Admin passwords are changed only from the server terminal.
4. A terminal on the server: `flask --app app create-admin LOGIN`.
5. `ORDER BY s.verified` sorts 0 (unverified) before 1, so the admin sees what needs checking first.

</details>

**Next:** [09 — Frontend basics](09-frontend-basics.md)
