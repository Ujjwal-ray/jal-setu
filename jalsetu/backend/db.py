"""SQLite access, versioned schema migrations and demo data."""
import sqlite3
import time

from flask import current_app, g
from werkzeug.security import generate_password_hash


def connect(path):
    con = sqlite3.connect(path, timeout=10)
    con.row_factory = sqlite3.Row
    return con


def get():
    """The request's connection (opened on first use, closed at teardown)."""
    if "db" not in g:
        g.db = connect(current_app.config["DB_PATH"])
    return g.db


def close(_exc=None):
    con = g.pop("db", None)
    if con is not None:
        con.close()


def query(sql, args=(), one=False):
    rows = [dict(r) for r in get().execute(sql, args).fetchall()]
    return (rows[0] if rows else None) if one else rows


def execute(sql, args=()):
    """Run one write statement and commit it. Returns the cursor (lastrowid, rowcount)."""
    con = get()
    with con:
        return con.execute(sql, args)


# ---------------------------------------------------------------------------
# Migrations. PRAGMA user_version records how many have run, so an existing
# jalsetu.db is upgraded in place. Append new steps; never edit old ones.

def _columns(con, table):
    return {r[1] for r in con.execute(f"PRAGMA table_info({table})")}


def _v1_prototype(con):
    """The original prototype schema, including the phone / slot / e-mail order fields."""
    for stmt in """
    CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, name TEXT NOT NULL, phone TEXT UNIQUE NOT NULL,
      password_hash TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'user');
    CREATE TABLE IF NOT EXISTS tokens(token TEXT PRIMARY KEY, user_id INTEGER NOT NULL);
    CREATE TABLE IF NOT EXISTS suppliers(id INTEGER PRIMARY KEY, user_id INTEGER UNIQUE, business_name TEXT NOT NULL,
      lat REAL NOT NULL, lng REAL NOT NULL, address TEXT, service_area TEXT, contact TEXT, verified INTEGER DEFAULT 0);
    CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY, supplier_id INTEGER NOT NULL, jar_size TEXT DEFAULT '20 L',
      price REAL NOT NULL, delivery_charge REAL DEFAULT 0, availability INTEGER DEFAULT 1);
    CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, supplier_id INTEGER NOT NULL,
      qty INTEGER DEFAULT 1, address TEXT, note TEXT, status TEXT DEFAULT 'pending', ts INTEGER);
    CREATE TABLE IF NOT EXISTS reviews(id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, supplier_id INTEGER NOT NULL,
      rating INTEGER NOT NULL, comment TEXT, ts INTEGER)
    """.split(";"):
        con.execute(stmt)
    have = _columns(con, "orders")
    for col in ("phone", "slot", "email"):
        if col not in have:
            con.execute(f"ALTER TABLE orders ADD COLUMN {col} TEXT")


def _v2_snapshots_reviews_sessions(con):
    # Each order keeps the price it was placed at, so a later price edit doesn't rewrite old totals.
    have = _columns(con, "orders")
    for col in ("price", "delivery_charge"):
        if col not in have:
            con.execute(f"ALTER TABLE orders ADD COLUMN {col} REAL")
    con.execute("""UPDATE orders SET
        price = (SELECT p.price FROM products p WHERE p.supplier_id = orders.supplier_id),
        delivery_charge = (SELECT p.delivery_charge FROM products p WHERE p.supplier_id = orders.supplier_id)
      WHERE price IS NULL""")

    # A review rates one delivered order: at most one review per order.
    if "order_id" not in _columns(con, "reviews"):
        con.execute("ALTER TABLE reviews ADD COLUMN order_id INTEGER")
    con.execute("CREATE UNIQUE INDEX IF NOT EXISTS reviews_order ON reviews(order_id)")

    # Sessions: only a hash of each token is stored, and tokens expire.
    # Old plain-text tokens are dropped, so everyone signs in once more.
    con.execute("DROP TABLE IF EXISTS tokens")
    con.execute("""CREATE TABLE tokens(token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL,
        created INTEGER NOT NULL, expires INTEGER NOT NULL)""")

    con.execute("CREATE INDEX IF NOT EXISTS tokens_user ON tokens(user_id)")
    con.execute("CREATE INDEX IF NOT EXISTS orders_user ON orders(user_id)")
    con.execute("CREATE INDEX IF NOT EXISTS orders_supplier ON orders(supplier_id)")
    con.execute("CREATE INDEX IF NOT EXISTS products_supplier ON products(supplier_id)")


def _v3_activity_and_feedback(con):
    # when each account last used the site: drives "online now" on the admin dashboard
    if "last_seen" not in _columns(con, "users"):
        con.execute("ALTER TABLE users ADD COLUMN last_seen INTEGER")
    # when an order was delivered, for earnings by month
    if "delivered_at" not in _columns(con, "orders"):
        con.execute("ALTER TABLE orders ADD COLUMN delivered_at INTEGER")
    # three quick checks a customer answers when rating a delivery: 1 yes, 0 no, NULL not answered
    have = _columns(con, "reviews")
    for col in ("on_time", "quality_ok", "quantity_ok"):
        if col not in have:
            con.execute(f"ALTER TABLE reviews ADD COLUMN {col} INTEGER")
    # a problem raised on an order by its customer or its supplier; an admin resolves it
    con.execute("""CREATE TABLE IF NOT EXISTS reports(id INTEGER PRIMARY KEY, order_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL, by_role TEXT NOT NULL, category TEXT NOT NULL, message TEXT NOT NULL DEFAULT '',
        status TEXT NOT NULL DEFAULT 'open', ts INTEGER NOT NULL, resolved_ts INTEGER)""")
    con.execute("CREATE INDEX IF NOT EXISTS reports_order ON reports(order_id)")


def _v4_password_resets(con):
    # one-time codes for "forgot password": texted to the account's phone, or read out by an admin
    # (issued_by = that admin's user id). Only a hash of each code is kept.
    con.execute("""CREATE TABLE IF NOT EXISTS password_resets(id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL,
        code_hash TEXT NOT NULL, created INTEGER NOT NULL, expires INTEGER NOT NULL,
        attempts INTEGER NOT NULL DEFAULT 0, used INTEGER NOT NULL DEFAULT 0, issued_by INTEGER)""")
    con.execute("CREATE INDEX IF NOT EXISTS password_resets_user ON password_resets(user_id)")


def _v5_signup_codes(con):
    # sign-ups waiting for the code texted to their phone: the account is only created in users once the
    # number is proven. Holds the chosen name, role and password hash until then.
    con.execute("""CREATE TABLE IF NOT EXISTS signup_codes(id INTEGER PRIMARY KEY, phone TEXT NOT NULL,
        name TEXT NOT NULL, role TEXT NOT NULL, password_hash TEXT NOT NULL, code_hash TEXT NOT NULL,
        created INTEGER NOT NULL, expires INTEGER NOT NULL,
        attempts INTEGER NOT NULL DEFAULT 0, used INTEGER NOT NULL DEFAULT 0)""")
    con.execute("CREATE INDEX IF NOT EXISTS signup_codes_phone ON signup_codes(phone)")


def _v6_attempts(con):
    # one row per try that counts toward a limit in auth.py LIMITS: a wrong password (per account and per internet
    # address), a sign-up or a reset text (per address). Kept here rather than in the server's memory, so a restart
    # doesn't wipe the counts and every server process sees the same ones. Rows older than an hour are deleted.
    con.execute("""CREATE TABLE IF NOT EXISTS attempts(id INTEGER PRIMARY KEY, kind TEXT NOT NULL, key TEXT NOT NULL,
        ts INTEGER NOT NULL)""")
    con.execute("CREATE INDEX IF NOT EXISTS attempts_kind_key ON attempts(kind, key, ts)")


def _v7_aadhaar_checks(con):
    # who runs each shop: the owner sends a picture of a masked Aadhaar (only the last 4 digits showing) and an
    # admin checks it (status pending -> approved or rejected). The picture is deleted once the admin decides;
    # the name and last 4 digits stay. The full 12-digit number is never stored. One row per shop.
    # A table of its own, not columns on suppliers: the public supplier search sends every suppliers column.
    con.execute("""CREATE TABLE IF NOT EXISTS aadhaar_checks(supplier_id INTEGER PRIMARY KEY, name TEXT NOT NULL,
        last4 TEXT NOT NULL, image BLOB, image_type TEXT, status TEXT NOT NULL DEFAULT 'pending',
        note TEXT NOT NULL DEFAULT '', submitted INTEGER NOT NULL, decided INTEGER, decided_by INTEGER)""")


def _v8_server_errors(con):
    # requests that crashed (answered 500), for the admin's "Server health" tab: when, which address, and what
    # went wrong. Never the request's body, which could hold a password. Rows older than 7 days are deleted.
    con.execute("""CREATE TABLE IF NOT EXISTS server_errors(id INTEGER PRIMARY KEY, ts INTEGER NOT NULL,
        method TEXT NOT NULL, path TEXT NOT NULL, error TEXT NOT NULL)""")


def _v9_shop_hours(con):
    # each time a supplier opens their shop, and closes it again (shop_hours.py). The stock they reported at
    # each moment (1 in stock, 0 out of stock). closed_by: 'owner', or 'auto' when it was left open and closed
    # itself at midnight. A row with closed empty is a shop that is open right now.
    con.execute("""CREATE TABLE IF NOT EXISTS shop_hours(id INTEGER PRIMARY KEY, supplier_id INTEGER NOT NULL,
        opened INTEGER NOT NULL, open_stock INTEGER NOT NULL, closed INTEGER, close_stock INTEGER, closed_by TEXT)""")
    con.execute("CREATE INDEX IF NOT EXISTS shop_hours_supplier ON shop_hours(supplier_id, opened)")


def _v10_payments(con):
    # paying for orders (payments.py). Each order keeps JalSetu's fee as it was when ordered, when the customer
    # confirmed they received the jars, and how it was paid. Orders from before this step keep payment_status
    # empty: nobody knows how those were paid, so they are left out of payments and fees.
    have = _columns(con, "orders")
    for col, kind in (("service_fee", "REAL"), ("received_at", "INTEGER"), ("payment_status", "TEXT"),
                      ("payment_method", "TEXT"), ("paid_at", "INTEGER")):
        if col not in have:
            con.execute(f"ALTER TABLE orders ADD COLUMN {col} {kind}")
    # each try at paying an order online. supplier_amount: what Razorpay sends on to the supplier's bank;
    # fee_recovered: JalSetu fees from earlier cash orders kept back from this payment. status: created, paid,
    # or duplicate (paid although the order was already paid: the admin refunds it in Razorpay)
    con.execute("""CREATE TABLE IF NOT EXISTS payments(id INTEGER PRIMARY KEY, order_id INTEGER NOT NULL,
        provider TEXT NOT NULL, provider_order_id TEXT NOT NULL UNIQUE, amount REAL NOT NULL,
        supplier_amount REAL NOT NULL, fee_recovered REAL NOT NULL DEFAULT 0, status TEXT NOT NULL DEFAULT 'created',
        created INTEGER NOT NULL, paid_at INTEGER, provider_payment_id TEXT)""")
    con.execute("CREATE INDEX IF NOT EXISTS payments_order ON payments(order_id)")
    # each supplier's Razorpay "linked account": where Razorpay sends their share. Its own table, because the
    # public supplier search sends every suppliers column.
    con.execute("""CREATE TABLE IF NOT EXISTS payout_accounts(supplier_id INTEGER PRIMARY KEY,
        razorpay_account TEXT NOT NULL, updated INTEGER NOT NULL, updated_by INTEGER)""")
    # fees a supplier owed from cash orders and paid to JalSetu directly, as recorded by an admin
    con.execute("""CREATE TABLE IF NOT EXISTS fee_settlements(id INTEGER PRIMARY KEY, supplier_id INTEGER NOT NULL,
        amount REAL NOT NULL, note TEXT NOT NULL DEFAULT '', ts INTEGER NOT NULL, by_admin INTEGER NOT NULL)""")


MIGRATIONS = [_v1_prototype, _v2_snapshots_reviews_sessions, _v3_activity_and_feedback, _v4_password_resets,
              _v5_signup_codes, _v6_attempts, _v7_aadhaar_checks, _v8_server_errors, _v9_shop_hours,
              _v10_payments]
SCHEMA_VERSION = len(MIGRATIONS)


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


# ---------------------------------------------------------------------------

DEMO_SUPPLIERS = [  # name, lat, lng, address, service area, contact, price, delivery, in stock, verified
    ("Aqua Pure Suppliers", 22.5668, 88.3902, "Beliaghata Main Rd", "Beliaghata, Phoolbagan, Ultadanga", "9830011111", 40, 10, 1, 1),
    ("Shree Jal Distributors", 22.5602, 88.3987, "Canal South Rd", "Beliaghata, Tangra, Entally", "9830022222", 35, 20, 1, 1),
    ("Ganga Fresh Water", 22.5731, 88.3810, "Sealdah Area", "Sealdah, Maniktala, Entally", "9830033333", 45, 0, 0, 1),
    ("Blue Drop Agency", 22.5520, 88.4100, "Topsia", "Topsia, Tangra, Science City", "9830044444", 38, 15, 1, 1),
    ("New Local Supplier (pending)", 22.5700, 88.3950, "Phoolbagan", "Phoolbagan", "9830055555", 30, 0, 1, 0),
]


def seed_demo(path):
    """Fill an empty database with the demo accounts and Kolkata suppliers (see README for logins)."""
    con = connect(path)
    try:
        with con:
            if con.execute("SELECT COUNT(*) FROM users").fetchone()[0]:
                return
            h = generate_password_hash
            con.execute("INSERT INTO users(name,phone,password_hash,role) VALUES('Admin','admin',?,'admin')", (h("admin123"),))
            customer = con.execute("INSERT INTO users(name,phone,password_hash,role) VALUES('Demo Student','9000000001',?,'user')",
                                   (h("demo123"),)).lastrowid
            supplier_pw = h("supplier123")
            for i, d in enumerate(DEMO_SUPPLIERS):
                uid = con.execute("INSERT INTO users(name,phone,password_hash,role) VALUES(?,?,?,'supplier')",
                                  (d[0], f"900000010{i}", supplier_pw)).lastrowid
                sid = con.execute("""INSERT INTO suppliers(user_id,business_name,lat,lng,address,service_area,contact,verified)
                                     VALUES(?,?,?,?,?,?,?,?)""", (uid, *d[:6], d[9])).lastrowid
                con.execute("INSERT INTO products(supplier_id,price,delivery_charge,availability) VALUES(?,?,?,?)",
                            (sid, d[6], d[7], d[8]))
            now = int(time.time())
            con.execute("INSERT INTO reviews(user_id,supplier_id,rating,comment,ts) VALUES(?,1,5,'Quick delivery, clean jars',?)", (customer, now))
            con.execute("INSERT INTO reviews(user_id,supplier_id,rating,comment,ts) VALUES(?,2,4,'Cheap but sometimes late',?)", (customer, now))
    finally:
        con.close()


def init_app(app):
    migrate(app.config["DB_PATH"])
    if app.config["SEED_DEMO"]:
        seed_demo(app.config["DB_PATH"])
    app.teardown_appcontext(close)
