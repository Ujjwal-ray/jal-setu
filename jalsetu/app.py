"""JalSetu backend: Flask + SQLite. Run: python app.py  ->  http://localhost:5000"""
import math, os, secrets, sqlite3, time
from functools import wraps
from flask import Flask, g, jsonify, request, send_from_directory
from werkzeug.security import check_password_hash, generate_password_hash

BASE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("JALSETU_DB", os.path.join(BASE, "jalsetu.db"))
app = Flask(__name__, static_folder=os.path.join(BASE, "static"), static_url_path="")

SCHEMA = """
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, name TEXT NOT NULL, phone TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'user');
CREATE TABLE IF NOT EXISTS tokens(token TEXT PRIMARY KEY, user_id INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS suppliers(id INTEGER PRIMARY KEY, user_id INTEGER UNIQUE, business_name TEXT NOT NULL,
  lat REAL NOT NULL, lng REAL NOT NULL, address TEXT, service_area TEXT, contact TEXT, verified INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY, supplier_id INTEGER NOT NULL, jar_size TEXT DEFAULT '20 L',
  price REAL NOT NULL, delivery_charge REAL DEFAULT 0, availability INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, supplier_id INTEGER NOT NULL,
  qty INTEGER DEFAULT 1, address TEXT, note TEXT, status TEXT DEFAULT 'pending', ts INTEGER,
  phone TEXT, slot TEXT, email TEXT);
CREATE TABLE IF NOT EXISTS reviews(id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, supplier_id INTEGER NOT NULL,
  rating INTEGER NOT NULL, comment TEXT, ts INTEGER);
"""

def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(_):
    d = g.pop("db", None)
    if d: d.close()

def q(sql, args=(), one=False):
    cur = db().execute(sql, args)
    rows = [dict(r) for r in cur.fetchall()]
    return (rows[0] if rows else None) if one else rows

def run(sql, args=()):
    cur = db().execute(sql, args); db().commit(); return cur.lastrowid

def migrate(con):
    # databases created before the request form gained phone / preferred slot / e-mail fields
    cols = {r[1] for r in con.execute("PRAGMA table_info(orders)")}
    for c in ("phone", "slot", "email"):
        if c not in cols:
            con.execute(f"ALTER TABLE orders ADD COLUMN {c} TEXT")

def seed():
    con = sqlite3.connect(DB_PATH); con.executescript(SCHEMA); migrate(con)
    if con.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        h = generate_password_hash
        con.execute("INSERT INTO users(name,phone,password_hash,role) VALUES('Admin','admin',?,'admin')", (h("admin123"),))
        con.execute("INSERT INTO users(name,phone,password_hash,role) VALUES('Demo Student','9000000001',?,'user')", (h("demo123"),))
        demo = [  # name, lat, lng, address, area, contact, price, delivery, avail, verified
            ("Aqua Pure Suppliers", 22.5668, 88.3902, "Beliaghata Main Rd", "Beliaghata, Phoolbagan, Ultadanga", "9830011111", 40, 10, 1, 1),
            ("Shree Jal Distributors", 22.5602, 88.3987, "Canal South Rd", "Beliaghata, Tangra, Entally", "9830022222", 35, 20, 1, 1),
            ("Ganga Fresh Water", 22.5731, 88.3810, "Sealdah Area", "Sealdah, Maniktala, Entally", "9830033333", 45, 0, 0, 1),
            ("Blue Drop Agency", 22.5520, 88.4100, "Topsia", "Topsia, Tangra, Science City", "9830044444", 38, 15, 1, 1),
            ("New Local Supplier (pending)", 22.5700, 88.3950, "Phoolbagan", "Phoolbagan", "9830055555", 30, 0, 1, 0),
        ]
        for i, d in enumerate(demo):
            uid = con.execute("INSERT INTO users(name,phone,password_hash,role) VALUES(?,?,?,'supplier')",
                              (d[0], f"900000010{i}", h("supplier123"))).lastrowid
            sid = con.execute("INSERT INTO suppliers(user_id,business_name,lat,lng,address,service_area,contact,verified) VALUES(?,?,?,?,?,?,?,?)",
                              (uid, d[0], d[1], d[2], d[3], d[4], d[5], d[9])).lastrowid
            con.execute("INSERT INTO products(supplier_id,price,delivery_charge,availability) VALUES(?,?,?,?)", (sid, d[6], d[7], d[8]))
        con.execute("INSERT INTO reviews(user_id,supplier_id,rating,comment,ts) VALUES(2,1,5,'Quick delivery, clean jars',?)", (int(time.time()),))
        con.execute("INSERT INTO reviews(user_id,supplier_id,rating,comment,ts) VALUES(2,2,4,'Cheap but sometimes late',?)", (int(time.time()),))
        con.commit()
    con.close()

def km(a, b, c, d):
    p = math.pi / 180
    x = math.sin((c - a) * p / 2) ** 2 + math.cos(a * p) * math.cos(c * p) * math.sin((d - b) * p / 2) ** 2
    return 12742 * math.asin(math.sqrt(x))

def auth(roles=None, optional=False):
    def deco(f):
        @wraps(f)
        def w(*a, **k):
            t = request.headers.get("Authorization", "").replace("Bearer ", "")
            u = q("SELECT u.id,u.name,u.phone,u.role FROM tokens t JOIN users u ON u.id=t.user_id WHERE t.token=?", (t,), one=True) if t else None
            if not u and not optional: return jsonify(error="Sign in required"), 401
            if u and roles and u["role"] not in roles: return jsonify(error="Not allowed"), 403
            g.user = u
            return f(*a, **k)
        return w
    return deco

def new_token(uid):
    t = secrets.token_hex(16); run("INSERT INTO tokens(token,user_id) VALUES(?,?)", (t, uid)); return t

@app.post("/api/register")
def register():
    d = request.get_json(force=True)
    name, phone, pw = (d.get("name") or "").strip(), (d.get("phone") or "").strip(), d.get("password") or ""
    role = d.get("role") if d.get("role") in ("user", "supplier") else "user"
    if not name or not phone or len(pw) < 4: return jsonify(error="Name, phone and a password (4+ chars) are required"), 400
    if q("SELECT id FROM users WHERE phone=?", (phone,), one=True): return jsonify(error="Phone already registered"), 409
    uid = run("INSERT INTO users(name,phone,password_hash,role) VALUES(?,?,?,?)", (name, phone, generate_password_hash(pw), role))
    return jsonify(token=new_token(uid), user=dict(id=uid, name=name, phone=phone, role=role))

@app.post("/api/login")
def login():
    d = request.get_json(force=True)
    u = q("SELECT * FROM users WHERE phone=?", ((d.get("phone") or "").strip(),), one=True)
    if not u or not check_password_hash(u["password_hash"], d.get("password") or ""): return jsonify(error="Wrong phone or password"), 401
    return jsonify(token=new_token(u["id"]), user=dict(id=u["id"], name=u["name"], phone=u["phone"], role=u["role"]))

@app.get("/api/me")
@auth()
def me(): return jsonify(g.user)

SUP_SQL = """SELECT s.*, p.price, p.delivery_charge, p.availability, p.jar_size,
  (SELECT ROUND(AVG(rating),1) FROM reviews r WHERE r.supplier_id=s.id) rating,
  (SELECT COUNT(*) FROM reviews r WHERE r.supplier_id=s.id) review_count
  FROM suppliers s LEFT JOIN products p ON p.supplier_id=s.id"""

@app.get("/api/suppliers")
def suppliers():
    a = request.args
    rows = q(SUP_SQL + " WHERE s.verified=1")
    lat, lng = a.get("lat", type=float), a.get("lng", type=float)
    out = []
    for r in rows:
        r["distance_km"] = round(km(lat, lng, r["lat"], r["lng"]), 2) if lat is not None and lng is not None else None
        if a.get("max_km", type=float) and r["distance_km"] is not None and r["distance_km"] > a.get("max_km", type=float): continue
        if a.get("max_price", type=float) and (r["price"] or 0) > a.get("max_price", type=float): continue
        if a.get("min_price", type=float) and (r["price"] or 0) < a.get("min_price", type=float): continue
        if a.get("available") == "1" and not r["availability"]: continue
        t = (a.get("q") or "").lower().strip()
        if t and t not in (r["business_name"] + " " + (r["service_area"] or "") + " " + (r["address"] or "")).lower(): continue
        out.append(r)
    sort = a.get("sort", "distance")
    out.sort(key=lambda r: (r["price"] or 9e9) if sort == "price" else (r["distance_km"] if r["distance_km"] is not None else 9e9))
    return jsonify(out)

@app.get("/api/suppliers/<int:sid>")
def supplier(sid):
    s = q(SUP_SQL + " WHERE s.id=?", (sid,), one=True)
    if not s or not s["verified"]: return jsonify(error="Not found"), 404
    s["reviews"] = q("SELECT r.rating,r.comment,r.ts,u.name FROM reviews r JOIN users u ON u.id=r.user_id WHERE supplier_id=? ORDER BY r.id DESC", (sid,))
    return jsonify(s)

@app.post("/api/suppliers/<int:sid>/reviews")
@auth()
def add_review(sid):
    d = request.get_json(force=True); r = int(d.get("rating") or 0)
    if not 1 <= r <= 5: return jsonify(error="Rating must be 1-5"), 400
    if not q("SELECT id FROM orders WHERE user_id=? AND supplier_id=? AND status='delivered'", (g.user["id"], sid), one=True):
        return jsonify(error="You can review a supplier after a delivered order"), 403
    run("INSERT INTO reviews(user_id,supplier_id,rating,comment,ts) VALUES(?,?,?,?,?)", (g.user["id"], sid, r, d.get("comment", ""), int(time.time())))
    return jsonify(ok=True)

@app.get("/api/my-listing")
@auth(["supplier"])
def my_listing():
    return jsonify(q(SUP_SQL + " WHERE s.user_id=?", (g.user["id"],), one=True))

@app.put("/api/my-listing")
@auth(["supplier"])
def save_listing():
    d = request.get_json(force=True)
    try:
        lat, lng, price = float(d["lat"]), float(d["lng"]), float(d["price"])
    except (KeyError, TypeError, ValueError):
        return jsonify(error="Location and price are required"), 400
    if not (d.get("business_name") or "").strip(): return jsonify(error="Business name required"), 400
    s = q("SELECT id FROM suppliers WHERE user_id=?", (g.user["id"],), one=True)
    vals = (d["business_name"].strip(), lat, lng, d.get("address", ""), d.get("service_area", ""), d.get("contact", g.user["phone"]))
    if s:
        sid = s["id"]
        run("UPDATE suppliers SET business_name=?,lat=?,lng=?,address=?,service_area=?,contact=? WHERE id=?", vals + (sid,))
        run("UPDATE products SET price=?,delivery_charge=?,availability=? WHERE supplier_id=?",
            (price, float(d.get("delivery_charge") or 0), 1 if d.get("availability") else 0, sid))
    else:
        sid = run("INSERT INTO suppliers(business_name,lat,lng,address,service_area,contact,user_id,verified) VALUES(?,?,?,?,?,?,?,0)", vals + (g.user["id"],))
        run("INSERT INTO products(supplier_id,price,delivery_charge,availability) VALUES(?,?,?,?)",
            (sid, price, float(d.get("delivery_charge") or 0), 1 if d.get("availability") else 0))
    return jsonify(q(SUP_SQL + " WHERE s.id=?", (sid,), one=True))

@app.post("/api/orders")
@auth(["user", "supplier", "admin"])
def create_order():
    d = request.get_json(force=True)
    s = q("SELECT * FROM suppliers WHERE id=? AND verified=1", (d.get("supplier_id"),), one=True)
    if not s: return jsonify(error="Supplier not found"), 404
    qty = max(1, min(int(d.get("qty") or 1), 50))
    if not (d.get("address") or "").strip(): return jsonify(error="Delivery address required"), 400
    phone = "".join(ch for ch in str(d.get("phone") or "") if ch.isdigit())[-10:] or g.user["phone"]
    email = (d.get("email") or "").strip()[:120]
    if email and "@" not in email: return jsonify(error="That e-mail address doesn't look right"), 400
    oid = run("INSERT INTO orders(user_id,supplier_id,qty,address,note,status,ts,phone,slot,email) VALUES(?,?,?,?,?,'pending',?,?,?,?)",
              (g.user["id"], s["id"], qty, d["address"].strip(), d.get("note", ""), int(time.time()),
               phone, (d.get("slot") or "").strip()[:40], email))
    return jsonify(id=oid, status="pending")

ORD_SQL = """SELECT o.*, s.business_name, s.contact, u.name customer, u.phone customer_phone, p.price, p.delivery_charge
  FROM orders o JOIN suppliers s ON s.id=o.supplier_id JOIN users u ON u.id=o.user_id LEFT JOIN products p ON p.supplier_id=s.id"""

@app.get("/api/orders")
@auth()
def my_orders():
    rows = q(ORD_SQL + " WHERE o.user_id=? ORDER BY o.id DESC", (g.user["id"],))
    for r in rows: r["total"] = (r["price"] or 0) * r["qty"] + (r["delivery_charge"] or 0)
    return jsonify(rows)

@app.get("/api/supplier/orders")
@auth(["supplier"])
def supplier_orders():
    rows = q(ORD_SQL + " WHERE s.user_id=? ORDER BY o.id DESC", (g.user["id"],))
    for r in rows: r["total"] = (r["price"] or 0) * r["qty"] + (r["delivery_charge"] or 0)
    return jsonify(rows)

FLOW = {"pending": ["accepted", "rejected"], "accepted": ["out_for_delivery", "rejected"], "out_for_delivery": ["delivered"]}

@app.patch("/api/orders/<int:oid>")
@auth()
def update_order(oid):
    st = (request.get_json(force=True) or {}).get("status")
    o = q("SELECT o.*, s.user_id sup_user FROM orders o JOIN suppliers s ON s.id=o.supplier_id WHERE o.id=?", (oid,), one=True)
    if not o: return jsonify(error="Not found"), 404
    if st == "cancelled" and o["user_id"] == g.user["id"] and o["status"] == "pending": pass
    elif o["sup_user"] == g.user["id"] and st in FLOW.get(o["status"], []): pass
    else: return jsonify(error="Invalid status change"), 400
    run("UPDATE orders SET status=? WHERE id=?", (st, oid))
    return jsonify(id=oid, status=st)

@app.get("/api/admin/suppliers")
@auth(["admin"])
def admin_suppliers(): return jsonify(q(SUP_SQL + " ORDER BY s.verified, s.id DESC"))

@app.post("/api/admin/suppliers/<int:sid>/verify")
@auth(["admin"])
def verify(sid):
    v = 1 if (request.get_json(silent=True) or {}).get("verified", True) else 0
    run("UPDATE suppliers SET verified=? WHERE id=?", (v, sid)); return jsonify(ok=True, verified=v)

@app.get("/")
def index(): return send_from_directory(app.static_folder, "index.html")

seed()
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
