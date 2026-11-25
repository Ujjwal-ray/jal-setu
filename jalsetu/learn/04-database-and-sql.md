# 04 — Databases and SQL

**In this lesson:** what a database is, every table JalSetu keeps, the SQL commands the backend uses, and
[backend/db.py](../backend/db.py) line by line.

---

## 1. What a database is

Picture a **workbook of spreadsheets**:

- each **sheet** is a **table** (`users`, `orders`, …),
- each **column** is one kind of information (`name`, `phone`, …),
- each **row** is one thing (one user, one order).

JalSetu uses **SQLite**, a database that lives in **one ordinary file**: `jalsetu.db`. No separate database
program is needed, because Python has SQLite built in. If you delete the file, the backend makes a fresh one
with demo data the next time it starts.

You talk to a database in **SQL** (Structured Query Language). It reads almost like English:

```sql
SELECT name, phone FROM users WHERE role = 'supplier'
```

"Get the name and phone of every user whose role is supplier."

## 2. Every JalSetu table

Times are stored as **Unix timestamps**: the number of seconds since 1 January 1970. For example
`1795564800` is midnight (UTC) at the start of 25 Nov 2026. Computers like this because comparing and subtracting times becomes simple maths.
Yes/no values are stored as `1` (yes) and `0` (no).

### `users`: every account

| Column | Meaning |
|--------|---------|
| `id` | A unique number for each row, given automatically (1, 2, 3…). This is the **primary key** |
| `name` | Display name |
| `phone` | What you sign in with. **UNIQUE**: two accounts can't share it. (The admin's is just the word `admin`) |
| `password_hash` | A one-way scrambled version of the password, never the password itself (lesson 06) |
| `role` | `user` (customer), `supplier` or `admin` |
| `last_seen` | When this account last used the site, for "online now" on the admin dashboard |

### `tokens`: who is signed in

| Column | Meaning |
|--------|---------|
| `token_hash` | A scrambled copy of the sign-in token (the "wristband" from lesson 03) |
| `user_id` | Whose token it is → points to `users.id` |
| `created`, `expires` | When it was made and when it stops working (30 days later) |

### `suppliers`: each shop

| Column | Meaning |
|--------|---------|
| `id` | Shop number |
| `user_id` | The supplier account that owns it → `users.id` (UNIQUE: one shop per account) |
| `business_name`, `address`, `service_area`, `contact` | Shop details shown to customers |
| `lat`, `lng` | Latitude and longitude: where the pin goes on the map |
| `verified` | `1` once an admin has checked it. **Customers only ever see verified shops** |

### `products`: each shop's price list (one row per shop)

| Column | Meaning |
|--------|---------|
| `supplier_id` | Which shop → `suppliers.id` |
| `jar_size` | Defaults to `'20 L'` |
| `price` | Price of one jar in rupees |
| `delivery_charge` | Extra charge per order (0 = free delivery) |
| `availability` | `1` = in stock, `0` = out of stock |

### `orders`: every delivery request

| Column | Meaning |
|--------|---------|
| `id` | Request number (shown as "Request #7") |
| `user_id` | The customer → `users.id` |
| `supplier_id` | The shop → `suppliers.id` |
| `qty` | Number of jars |
| `address`, `phone`, `email`, `note`, `slot` | What the customer typed. `slot` is the wanted date/time like `2026-11-26 10:00` |
| `status` | `pending`, `accepted`, `out_for_delivery`, `delivered`, `rejected` or `cancelled` |
| `ts` | When it was placed |
| `price`, `delivery_charge` | **A copy** of the price at the moment of ordering (so a later price change doesn't rewrite old bills) |
| `delivered_at` | When it was marked delivered (for "earned this month") |

### `reviews`: star ratings

| Column | Meaning |
|--------|---------|
| `user_id`, `supplier_id`, `order_id` | Who rated, which shop, which delivered order (UNIQUE per order: one rating each) |
| `rating` | 1 to 5 stars |
| `comment` | Optional text |
| `on_time`, `quality_ok`, `quantity_ok` | Yes/no answers: `1`, `0`, or empty (`NULL`) if skipped |
| `ts` | When |

### `reports`: "report a problem"

| Column | Meaning |
|--------|---------|
| `order_id` | Which request it's about |
| `user_id`, `by_role` | Who reported, and whether they were the `customer` or the `supplier` |
| `category` | `quality`, `quantity`, `late`, `behaviour`, `payment`, `address` or `other` |
| `message` | Their words |
| `status`, `ts`, `resolved_ts` | `open` or `resolved`, and when each happened |

### `password_resets`: 6-digit "forgot password" codes

| Column | Meaning |
|--------|---------|
| `user_id` | Whose password |
| `code_hash` | Scrambled code (the real code is never stored) |
| `created`, `expires` | Valid for 15 minutes |
| `attempts` | Wrong guesses so far (5 allowed) |
| `used` | `1` once used up or cancelled |
| `issued_by` | Empty if the person asked by SMS, or the admin's user id if an admin made it |

### How the tables connect

A column that holds another table's `id` (like `orders.user_id`) is a **foreign key**. It's how rows point
at each other:

Read `A ──< B` as "one A has many B", and `A ──1 B` as "one A has one B".

```
users     ──< tokens            one account can be signed in on many devices
users     ──1 suppliers         a supplier account owns one shop      (suppliers.user_id)
suppliers ──1 products          one price row per shop                (products.supplier_id)
users     ──< orders            a customer places many orders         (orders.user_id)
suppliers ──< orders            a shop receives many orders           (orders.supplier_id)
orders    ──1 reviews           at most one review per delivered order (reviews.order_id)
orders    ──< reports           an order can have several problem reports (reports.order_id)
users     ──< reviews, reports, password_resets   who wrote / asked for each one
```

```
            ┌──────────┐ owns  ┌────────────┐  price  ┌──────────┐
            │  users   │──────►│ suppliers  │────────►│ products │
            └──────────┘       └────────────┘         └──────────┘
              │      │               │
     signs in │      │ places        │ receives
              ▼      ▼               ▼
        ┌────────┐  ┌──────────────────────┐
        │ tokens │  │        orders        │
        └────────┘  └──────────────────────┘
                         │             │
                  rated  │             │ problem
                         ▼             ▼
                    ┌─────────┐   ┌─────────┐
                    │ reviews │   │ reports │
                    └─────────┘   └─────────┘
```

## 3. SQL in 10 commands (with JalSetu examples)

**Create a table:**
```sql
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, name TEXT NOT NULL, phone TEXT UNIQUE NOT NULL, ...)
```
`INTEGER`, `TEXT`, `REAL` (decimal) are column types. `NOT NULL` = must have a value. `IF NOT EXISTS` = skip if it's already there.

**Add a row:**
```sql
INSERT INTO users(name, phone, password_hash, role) VALUES ('Asha', '9876543210', '...', 'user')
```

**Read rows:**
```sql
SELECT * FROM users WHERE phone = '9000000001'        -- * means "every column"
SELECT id, name FROM users ORDER BY id DESC LIMIT 5   -- newest 5 (DESC = biggest first)
```

**Change rows:**
```sql
UPDATE orders SET status = 'accepted' WHERE id = 7
```
⚠️ Without `WHERE`, `UPDATE` changes **every** row!

**Remove rows:**
```sql
DELETE FROM tokens WHERE expires <= 1795564800
```

**Join tables** (combine rows that point at each other):
```sql
SELECT o.id, o.qty, s.business_name
FROM orders o JOIN suppliers s ON s.id = o.supplier_id
```
`orders o` gives the table a short nickname `o`. For each order, find the supplier whose `id` equals the
order's `supplier_id`, and put both on one row. A **LEFT JOIN** keeps the left row even when there's no match
(the missing columns become `NULL`).

**Count and average:**
```sql
SELECT COUNT(*) FROM users WHERE role = 'user'                     -- how many customers
SELECT ROUND(AVG(rating), 1) FROM reviews WHERE supplier_id = 1    -- average stars, 1 decimal place
SELECT status, COUNT(*) n FROM orders GROUP BY status              -- how many orders in each status
```

**A query inside a query** ("subquery") and **EXISTS**:
```sql
SELECT s.*, (SELECT COUNT(*) FROM reviews r WHERE r.supplier_id = s.id) review_count FROM suppliers s
EXISTS (SELECT 1 FROM reviews r WHERE r.order_id = o.id)   -- 1 if at least one such row exists, else 0
```

**Handy functions:** `COALESCE(a, b)` gives `a` unless it's `NULL`, then `b`. `CASE WHEN … THEN … END` is SQL's if/else.

### The `?` placeholders, and why they matter

In the Python code you'll **never** see user input glued straight into SQL. Instead:

```python
db.query("SELECT * FROM users WHERE phone = ?", (login_name,), one=True)
```

The `?` is a slot. The value is sent **separately**, and SQLite treats it strictly as data. If someone typed
`' OR '1'='1` as their phone number, gluing it in would change the meaning of the SQL. That attack is called
**SQL injection**. With `?` it's just a strange phone number that matches nobody.

### Transactions: all or nothing

Sometimes several changes must happen **together or not at all**. (Changing a password *and* signing out
every device, for example.) A **transaction** groups them: if anything fails halfway, everything is undone
(**rolled back**). If all succeed, they're saved together (**committed**). In Python's sqlite3:

```python
with con:          # start a transaction
    con.execute(...)
    con.execute(...)
# leaving the "with" block → COMMIT if all went well, ROLLBACK if an error happened
```

### Indexes

An **index** is like the index at the back of a book. It lets the database find rows by a column quickly,
without reading the whole table. JalSetu adds indexes on columns it searches often, like `orders.user_id`.
A **UNIQUE index** also refuses duplicates. That's how "one review per order" is enforced.

## 4. Migrations: changing tables safely over time

The project grew in steps. New columns and tables were added later. But people already had a `jalsetu.db`
with the *old* layout (the **schema**). Deleting their data isn't acceptable, so the database is upgraded step
by step. Each step is a **migration**.

SQLite has a spare number stored inside every database file, `user_version`. JalSetu uses it to remember
**how many migrations have already run**. On start-up: "this file is at version 2, the code has 4 steps, so
run steps 3 and 4." The rule written in the code: *append new steps; never edit old ones.*

---

## 5. `backend/db.py` line by line

Open [backend/db.py](../backend/db.py) next to this.

### Lines 1–6: setup

```python
"""SQLite access, versioned schema migrations and demo data."""
import sqlite3
import time

from flask import current_app, g
from werkzeug.security import generate_password_hash
```

- Line 1: a docstring describing the file.
- `import sqlite3`: Python's built-in SQLite library.
- `import time`: for the current time (`time.time()` = seconds since 1970).
- `current_app`: Flask's handle on "the app that is handling this request" (to read settings like `DB_PATH`).
- `g`: Flask's **per-request scratchpad**. Anything put on `g` lasts for one request, then is thrown away.
- `generate_password_hash`: scrambles passwords for the demo accounts.

### Lines 9–12: `connect()`, open the database file

```python
def connect(path):
    con = sqlite3.connect(path, timeout=10)
    con.row_factory = sqlite3.Row
    return con
```

- Opens the file at `path` and gives back a **connection** (`con`), a live line to the database.
- `timeout=10`: if another request is writing at that moment, wait up to 10 seconds instead of failing at once.
- `row_factory = sqlite3.Row`: makes each result row act like a dict, so code can write `row["name"]` instead of `row[1]`.

### Lines 15–19: `get()`, one connection per request

```python
def get():
    """The request's connection (opened on first use, closed at teardown)."""
    if "db" not in g:
        g.db = connect(current_app.config["DB_PATH"])
    return g.db
```

- The first time any code asks for the database during a request, open a connection and keep it on `g`.
- Later calls in the same request reuse it. Opening is cheap, but there's no reason to do it twice.

### Lines 22–25: `close()`

```python
def close(_exc=None):
    con = g.pop("db", None)
    if con is not None:
        con.close()
```

- `g.pop("db", None)`: take the connection off `g` (or `None` if no one opened one).
- Close it. Line 188 tells Flask to call this automatically at the end of every request ("teardown").
- `_exc` is information about an error, if one happened. The leading `_` is a convention for "unused".

### Lines 28–30: `query()`, read rows

```python
def query(sql, args=(), one=False):
    rows = [dict(r) for r in get().execute(sql, args).fetchall()]
    return (rows[0] if rows else None) if one else rows
```

Used for every `SELECT` in the backend.

- `get().execute(sql, args)`: run the SQL with the `?` slots filled from `args`.
- `.fetchall()`: collect every result row.
- `[dict(r) for r in ...]`: turn each row into a plain dict (easy to edit and to send as JSON).
- Line 30 reads: if `one=True`, return just the first row (or `None` if there were none). Otherwise return the whole list.

### Lines 33–37: `execute()`, change rows

```python
def execute(sql, args=()):
    """Run one write statement and commit it. Returns the cursor (lastrowid, rowcount)."""
    con = get()
    with con:
        return con.execute(sql, args)
```

Used for single `INSERT` / `UPDATE` / `DELETE` statements. `with con:` commits it (saves it for good).
It returns the **cursor**, which carries two useful facts:

- `.lastrowid`: the `id` given to a row just inserted (e.g. the new order's number),
- `.rowcount`: how many rows were changed (0 means "nothing matched", which the code uses to detect "not found").

### Lines 44–45: `_columns()`, which columns exist?

```python
def _columns(con, table):
    return {r[1] for r in con.execute(f"PRAGMA table_info({table})")}
```

`PRAGMA table_info(orders)` asks SQLite to describe a table: one row per column, and item `[1]` of each is the
column's name. `{... for ...}` builds a **set** (a list with no duplicates that's fast to search). Migrations
use it to ask "does `orders` already have a `price` column?"

The `_` at the start of the name is a convention for "private: only for use inside this file".

### Lines 48–67: migration 1, the original tables

```python
def _v1_prototype(con):
    for stmt in """
    CREATE TABLE IF NOT EXISTS users(...);
    CREATE TABLE IF NOT EXISTS tokens(...);
    ...
    CREATE TABLE IF NOT EXISTS reviews(...)
    """.split(";"):
        con.execute(stmt)
    have = _columns(con, "orders")
    for col in ("phone", "slot", "email"):
        if col not in have:
            con.execute(f"ALTER TABLE orders ADD COLUMN {col} TEXT")
```

- One long text holds six `CREATE TABLE` commands separated by `;`. `.split(";")` cuts it into separate
  commands, and the loop runs each one.
- Then it adds the `phone`, `slot` and `email` columns to `orders`, but only if they're missing. (Very early
  databases didn't have them.) `ALTER TABLE … ADD COLUMN` adds a column to an existing table.

### Lines 70–95: migration 2, price snapshots, one review per order, safer sign-ins

```python
    for col in ("price", "delivery_charge"):
        if col not in have:
            con.execute(f"ALTER TABLE orders ADD COLUMN {col} REAL")
    con.execute("""UPDATE orders SET
        price = (SELECT p.price FROM products p WHERE p.supplier_id = orders.supplier_id), ...
      WHERE price IS NULL""")
```

- Adds `price` and `delivery_charge` to `orders`, so each order remembers what it cost when placed.
- For old orders that don't have them yet (`price IS NULL`), copy the supplier's *current* price in. That's the best guess available.

```python
    if "order_id" not in _columns(con, "reviews"):
        con.execute("ALTER TABLE reviews ADD COLUMN order_id INTEGER")
    con.execute("CREATE UNIQUE INDEX IF NOT EXISTS reviews_order ON reviews(order_id)")
```

- Each review now points at the delivered order it rates. The **unique index** makes a second review of the
  same order impossible; SQLite itself refuses it.

```python
    con.execute("DROP TABLE IF EXISTS tokens")
    con.execute("""CREATE TABLE tokens(token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL,
        created INTEGER NOT NULL, expires INTEGER NOT NULL)""")
```

- The old `tokens` table stored tokens as plain text (anyone who copied the database file could pretend to
  be anyone). It's deleted (`DROP TABLE`) and remade to store only a **hash** plus an expiry date. Side effect:
  everyone has to sign in once more.

Lines 92–95 add four **indexes** for the columns searched most.

### Lines 98–114: migration 3, activity and feedback

- `users.last_seen`: for "online now".
- `orders.delivered_at`: for "earned this month".
- `reviews.on_time`, `quality_ok`, `quantity_ok`: the three yes/no questions.
- A new `reports` table for "report a problem", plus an index on `order_id`.

### Lines 117–123: migration 4, password-reset codes

Creates the `password_resets` table (see section 2) and an index on `user_id`.

### Lines 126–127: the list of steps

```python
MIGRATIONS = [_v1_prototype, _v2_snapshots_reviews_sessions, _v3_activity_and_feedback, _v4_password_resets]
SCHEMA_VERSION = len(MIGRATIONS)
```

A list of the four **functions themselves** (no `()`, so they aren't run yet, just collected in order).
`len(...)` = how many items = 4.

### Lines 130–144: `migrate()`, run the missing steps

```python
def migrate(path):
    con = sqlite3.connect(path, isolation_level=None)  # manual BEGIN/COMMIT: each step is all-or-nothing
    try:
        version = con.execute("PRAGMA user_version").fetchone()[0]
        for number, step in enumerate(MIGRATIONS[version:], start=version + 1):
            con.execute("BEGIN IMMEDIATE")
            try:
                step(con)
                con.execute(f"PRAGMA user_version = {number}")
                con.execute("COMMIT")
            except BaseException:
                con.execute("ROLLBACK")
                raise
    finally:
        con.close()
```

Line by line:

- **131** Open the file with `isolation_level=None`, meaning "I'll start and finish transactions myself".
- **132** `try: … finally:` makes sure line 144 (`con.close()`) runs no matter what.
- **133** Read the stored version number. A brand-new file says `0`.
- **134** `MIGRATIONS[version:]` is the list **from position `version` to the end**, i.e. only the steps not yet
  run. `enumerate(..., start=version + 1)` pairs each with its step number. At version 2 you'd get `(3, _v3_…)`
  and `(4, _v4_…)`.
- **135** `BEGIN IMMEDIATE`: start a transaction and lock the database for writing right away.
- **137** Run the step, e.g. `_v3_activity_and_feedback(con)`.
- **138** Record the new version number *inside the same transaction*.
- **139** `COMMIT`: save it all.
- **140–142** If *anything* failed, `ROLLBACK` undoes this step completely, then `raise` passes the error on so
  the server stops with a clear message instead of running on a half-upgraded database.

**Why?** Because each step and its version number commit together, a crash can never leave the database
"half-migrated". Next start-up simply retries the step.

### Lines 149–155: the demo suppliers

```python
DEMO_SUPPLIERS = [  # name, lat, lng, address, service area, contact, price, delivery, in stock, verified
    ("Aqua Pure Suppliers", 22.5668, 88.3902, "Beliaghata Main Rd", "...", "9830011111", 40, 10, 1, 1),
    ...
    ("New Local Supplier (pending)", 22.5700, 88.3950, "Phoolbagan", "Phoolbagan", "9830055555", 30, 0, 1, 0),
]
```

A list of **tuples** (fixed little lists written with `( )`). The comment says what each position means.
Five shops in Kolkata. The last has `verified = 0`, so customers can't see it until an admin verifies it.
That's handy for demonstrating verification.

### Lines 158–181: `seed_demo()`, fill an empty database

```python
def seed_demo(path):
    con = connect(path)
    try:
        with con:
            if con.execute("SELECT COUNT(*) FROM users").fetchone()[0]:
                return
```

- Open the database and start a transaction.
- If there's **at least one user already**, stop (`return`). Never add demo data to a database in use.
  (In Python, `0` counts as false and any other number as true.)

```python
            h = generate_password_hash
            con.execute("INSERT INTO users(...) VALUES('Admin','admin',?,'admin')", (h("admin123"),))
            customer = con.execute("INSERT INTO users(...) VALUES('Demo Student','9000000001',?,'user')",
                                   (h("demo123"),)).lastrowid
```

- `h = generate_password_hash`: a short nickname for the function (to save typing).
- Make the admin (login `admin`) and the demo customer. Keep the customer's new `id` in `customer`.
- `(h("admin123"),)`: a tuple with **one** item. The trailing comma is what makes it a tuple.

```python
            supplier_pw = h("supplier123")
            for i, d in enumerate(DEMO_SUPPLIERS):
                uid = con.execute("INSERT INTO users(...) VALUES(?,?,?,'supplier')",
                                  (d[0], f"900000010{i}", supplier_pw)).lastrowid
                sid = con.execute("""INSERT INTO suppliers(...) VALUES(?,?,?,?,?,?,?,?)""",
                                  (uid, *d[:6], d[9])).lastrowid
                con.execute("INSERT INTO products(...) VALUES(?,?,?,?)", (sid, d[6], d[7], d[8]))
```

For each demo shop (`i` counts 0, 1, 2…):

1. Make a supplier **account**. Its login is `900000010` + `i`, so `9000000100`, `9000000101`, …
2. Make the **shop** row. `d[:6]` = items 0–5 of the tuple (name … contact). The `*` "spreads" them into
   separate values. `d[9]` = verified.
3. Make its **price** row: `d[6]` price, `d[7]` delivery charge, `d[8]` in stock.

Lines 177–179 add two sample reviews (5 stars for shop 1, 4 stars for shop 2) so ratings show from the start.

### Lines 184–188: `init_app()`, what runs at start-up

```python
def init_app(app):
    migrate(app.config["DB_PATH"])
    if app.config["SEED_DEMO"]:
        seed_demo(app.config["DB_PATH"])
    app.teardown_appcontext(close)
```

Called once by `create_app()` when the backend starts:

1. Bring the tables up to date.
2. Add demo data if that setting is on (it is unless you set `JALSETU_SEED=0`).
3. Register `close` to run after every request.

---

## Quick check

1. Why does an order store its own `price` when the `products` table already has one?
2. What would `UPDATE orders SET status = 'cancelled'` (with no `WHERE`) do?
3. Why use `?` instead of putting the phone number straight into the SQL text?
4. The database file is at version 3. What happens at the next start-up?
5. What stops a customer from rating the same delivery twice, even if the frontend has a bug?

<details><summary>Answers</summary>

1. So old bills keep the price the customer was quoted, even if the supplier changes the price later.
2. Cancel **every** order in the database.
3. To prevent SQL injection: the value is sent separately and treated only as data.
4. `migrate()` runs only `_v4_password_resets`, then sets `user_version = 4`, in one transaction.
5. The unique index `reviews_order` on `reviews(order_id)`: SQLite refuses a second row with the same `order_id`.

</details>

**Next:** [05 — Backend: starting up](05-backend-startup.md)
