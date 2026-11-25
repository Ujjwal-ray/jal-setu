"""Supplier search and details for customers, reviews, and a supplier's own listing."""
import sqlite3
import time

from flask import Blueprint, g, jsonify, request

from . import db
from .auth import auth
from .util import body, fail, km, normalize_phone, number, query_float, text

bp = Blueprint("suppliers", __name__)

SUPPLIER_SQL = """SELECT s.*, p.price, p.delivery_charge, p.availability, p.jar_size,
  (SELECT ROUND(AVG(rating), 1) FROM reviews r WHERE r.supplier_id = s.id) rating,
  (SELECT COUNT(*) FROM reviews r WHERE r.supplier_id = s.id) review_count
  FROM suppliers s LEFT JOIN products p ON p.supplier_id = s.id"""

NO_PRICE = float("inf")


@bp.get("/suppliers")
def search():
    """Verified suppliers. Query: lat, lng, max_km, min_price, max_price, available=1, q, sort=distance|price."""
    lat, lng = query_float("lat"), query_float("lng")
    max_km, min_price, max_price = query_float("max_km"), query_float("min_price"), query_float("max_price")
    term = (request.args.get("q") or "").lower().strip()
    in_stock_only = request.args.get("available") == "1"

    found = []
    for s in db.query(SUPPLIER_SQL + " WHERE s.verified = 1"):
        s["distance_km"] = round(km(lat, lng, s["lat"], s["lng"]), 2) if lat is not None and lng is not None else None
        price = s["price"] if s["price"] is not None else NO_PRICE
        # a limit of 0 (or none) means "any", matching the frontend filters
        if max_km and s["distance_km"] is not None and s["distance_km"] > max_km:
            continue
        if max_price and price > max_price:
            continue
        if min_price and price < min_price:
            continue
        if in_stock_only and not s["availability"]:
            continue
        if term and term not in " ".join(filter(None, (s["business_name"], s["service_area"], s["address"]))).lower():
            continue
        found.append(s)

    def by_distance(s):
        return s["distance_km"] if s["distance_km"] is not None else NO_PRICE

    def by_price(s):
        return s["price"] if s["price"] is not None else NO_PRICE

    keys = (by_price, by_distance) if request.args.get("sort") == "price" else (by_distance, by_price)
    found.sort(key=lambda s: (keys[0](s), keys[1](s), s["id"]))
    return jsonify(found)


@bp.get("/suppliers/<int:sid>")
def detail(sid):
    s = db.query(SUPPLIER_SQL + " WHERE s.id = ? AND s.verified = 1", (sid,), one=True)
    if not s:
        fail("Supplier not found", 404)
    s["reviews"] = db.query("""SELECT r.rating, r.comment, r.ts, u.name FROM reviews r JOIN users u ON u.id = r.user_id
                               WHERE r.supplier_id = ? ORDER BY r.id DESC LIMIT 50""", (sid,))
    return jsonify(s)


@bp.post("/suppliers/<int:sid>/reviews")
@auth()
def add_review(sid):
    d = body()
    rating = number(d, "rating", "Rating", lo=1, hi=5, integer=True)
    comment = text(d, "comment", 500)
    delivered = "SELECT o.id FROM orders o WHERE o.user_id = ? AND o.supplier_id = ? AND o.status = 'delivered'"
    args = (g.user["id"], sid)

    if d.get("order_id") is not None:
        order_id = number(d, "order_id", "Order", integer=True)
        order = db.query(delivered + " AND o.id = ?", args + (order_id,), one=True)
        if not order:
            fail("You can rate a supplier once they have delivered your order", 403)
    else:
        # clients that don't send order_id rate their latest delivered order that has no review yet
        order = db.query(delivered + " AND NOT EXISTS (SELECT 1 FROM reviews r WHERE r.order_id = o.id) ORDER BY o.id DESC",
                         args, one=True)
        if not order:
            if db.query(delivered, args, one=True):
                fail("You have already rated this delivery", 409)
            fail("You can rate a supplier once they have delivered your order", 403)

    # optional yes/no answers: was it on time, was the water good, were all the jars there
    checks = tuple(None if d.get(k) is None else (1 if d.get(k) else 0) for k in ("on_time", "quality_ok", "quantity_ok"))
    try:
        db.execute("""INSERT INTO reviews(user_id,supplier_id,order_id,rating,comment,ts,on_time,quality_ok,quantity_ok)
                      VALUES(?,?,?,?,?,?,?,?,?)""", (g.user["id"], sid, order["id"], rating, comment, int(time.time())) + checks)
    except sqlite3.IntegrityError:
        fail("You have already rated this delivery", 409)
    return jsonify(ok=True), 201


@bp.get("/my-listing")
@auth("supplier")
def my_listing():
    return jsonify(db.query(SUPPLIER_SQL + " WHERE s.user_id = ?", (g.user["id"],), one=True))


@bp.put("/my-listing")
@auth("supplier")
def save_listing():
    d = body()
    name = text(d, "business_name", 80)
    if not name:
        fail("Business name required")
    lat = number(d, "lat", "Map pin latitude", lo=-90, hi=90)
    lng = number(d, "lng", "Map pin longitude", lo=-180, hi=180)
    price = number(d, "price", "Jar price", lo=0, hi=10_000)
    delivery = number(d, "delivery_charge", "Delivery charge", default=0.0, lo=0, hi=10_000)
    in_stock = 1 if d.get("availability") else 0
    raw_contact = text(d, "contact", 20)
    contact = normalize_phone(raw_contact) if raw_contact else g.user["phone"]
    if not contact:
        fail("Enter a 10-digit contact number")
    shop = (name, lat, lng, text(d, "address", 200), text(d, "service_area", 300), contact)

    con = db.get()
    with con:  # supplier row and price row change together or not at all
        row = con.execute("SELECT id FROM suppliers WHERE user_id = ?", (g.user["id"],)).fetchone()
        if row:
            sid = row["id"]
            con.execute("UPDATE suppliers SET business_name=?, lat=?, lng=?, address=?, service_area=?, contact=? WHERE id=?",
                        shop + (sid,))
        else:
            sid = con.execute("""INSERT INTO suppliers(business_name,lat,lng,address,service_area,contact,user_id,verified)
                                 VALUES(?,?,?,?,?,?,?,0)""", shop + (g.user["id"],)).lastrowid
        updated = con.execute("UPDATE products SET price=?, delivery_charge=?, availability=? WHERE supplier_id=?",
                              (price, delivery, in_stock, sid)).rowcount
        if not updated:
            con.execute("INSERT INTO products(supplier_id,price,delivery_charge,availability) VALUES(?,?,?,?)",
                        (sid, price, delivery, in_stock))
    return jsonify(db.query(SUPPLIER_SQL + " WHERE s.id = ?", (sid,), one=True))
