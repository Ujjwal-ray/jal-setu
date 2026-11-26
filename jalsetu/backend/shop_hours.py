"""Opening and closing the shop each day. A verified supplier opens their shop in the morning and closes it at night,
typing their password each time and saying whether they have jars in stock. Customers see every verified shop, but
can only order from one that is open. A shop left open closes by itself at midnight, India time, and the admin
sees that it wasn't closed properly."""
import time
from datetime import datetime, timedelta, timezone

from flask import Blueprint, g, jsonify

from . import db
from .auth import auth, confirm_password
from .util import body, fail

bp = Blueprint("shop_hours", __name__)

IST_OFFSET = 5 * 3600 + 30 * 60  # India Standard Time is UTC + 5:30 all year (no daylight saving)
IST = timezone(timedelta(seconds=IST_OFFSET), "IST")

# a shop is open right now when it has a row opened today that isn't closed yet
OPEN_NOW = "closed IS NULL AND opened >= ?"


def day_start(ts=None):
    """When the day began (midnight, India time), as a Unix time. Today, unless `ts` names another moment."""
    moment = datetime.fromtimestamp(time.time() if ts is None else ts, IST)
    return int(moment.replace(hour=0, minute=0, second=0, microsecond=0).timestamp())


def is_open(sid):
    return bool(db.query(f"SELECT 1 FROM shop_hours WHERE supplier_id = ? AND {OPEN_NOW}", (sid, day_start()), one=True))


def close_forgotten():
    """Close every shop still open from an earlier day, at the midnight that ended that day ('auto').
    (opened + offset) % 86400 is how many seconds after midnight, India time, the shop opened."""
    db.execute("""UPDATE shop_hours SET closed = opened - (opened + ?) % 86400 + 86400, closed_by = 'auto'
                  WHERE closed IS NULL AND opened < ?""", (IST_OFFSET, day_start()))


def _my_shop():
    shop = db.query("SELECT id, verified FROM suppliers WHERE user_id = ?", (g.user["id"],), one=True)
    if not shop:
        fail("Save your shop listing first", 409)
    return shop


def _stock(d):
    in_stock = d.get("in_stock")
    if not isinstance(in_stock, bool):
        fail("Say whether you have jars in stock")
    return int(in_stock)


def _status(sid):
    """Whether the shop is open, each opening and closing today, and whether it was left open last night."""
    close_forgotten()
    start = day_start()
    today = db.query("""SELECT opened, open_stock, closed, close_stock, closed_by FROM shop_hours
                        WHERE supplier_id = ? AND opened >= ? ORDER BY id""", (sid, start))
    left_open = db.query("SELECT 1 FROM shop_hours WHERE supplier_id = ? AND closed_by = 'auto' AND closed = ?",
                         (sid, start), one=True)
    return dict(open=bool(today) and today[-1]["closed"] is None, today=today, left_open_last_night=bool(left_open))


@bp.get("/my-shop")
@auth("supplier")
def my_shop():
    """Today's openings and closings for this supplier's shop (null before the listing is saved)."""
    shop = db.query("SELECT id FROM suppliers WHERE user_id = ?", (g.user["id"],), one=True)
    return jsonify(shop and _status(shop["id"]))


@bp.post("/my-shop/open")
@auth("supplier")
def open_shop():
    """Open the shop: {password, in_stock: true/false}. Sets the stock customers see."""
    d = body()
    shop = _my_shop()
    if not shop["verified"]:
        fail("Your shop can open once an admin has verified it", 409)
    in_stock = _stock(d)
    confirm_password(d.get("password"))
    close_forgotten()
    con = db.get()
    with con:  # open (only if it isn't open already) and set the stock, together
        if not con.execute("""INSERT INTO shop_hours(supplier_id, opened, open_stock) SELECT ?, ?, ?
                              WHERE NOT EXISTS (SELECT 1 FROM shop_hours WHERE supplier_id = ? AND closed IS NULL)""",
                           (shop["id"], int(time.time()), in_stock, shop["id"])).rowcount:
            fail("Your shop is already open", 409)
        con.execute("UPDATE products SET availability = ? WHERE supplier_id = ?", (in_stock, shop["id"]))
    return jsonify(_status(shop["id"]))


@bp.post("/my-shop/close")
@auth("supplier")
def close_shop():
    """Close the shop: {password, in_stock: true/false}, the stock left at closing time."""
    d = body()
    shop = _my_shop()
    in_stock = _stock(d)
    confirm_password(d.get("password"))
    close_forgotten()
    con = db.get()
    with con:
        if not con.execute("""UPDATE shop_hours SET closed = ?, close_stock = ?, closed_by = 'owner'
                              WHERE supplier_id = ? AND closed IS NULL""",
                           (int(time.time()), in_stock, shop["id"])).rowcount:
            fail("Your shop isn't open", 409)
        con.execute("UPDATE products SET availability = ? WHERE supplier_id = ?", (in_stock, shop["id"]))
    return jsonify(_status(shop["id"]))
