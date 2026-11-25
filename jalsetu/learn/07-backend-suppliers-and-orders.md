# 07 — Backend: suppliers and orders

**In this lesson:** the two files that do JalSetu's main job:
[backend/suppliers.py](../backend/suppliers.py) (search, details, reviews, a supplier's own listing) and
[backend/orders.py](../backend/orders.py) (placing, listing and moving delivery requests, and reporting problems).

Both files follow the same pattern for every endpoint:

```
1. @bp.<method>("<path>")   which request this handles
2. @auth(...)               who may use it (if anyone needs to be signed in)
3. read the input           body() / request.args, cleaned with text(), number(), normalize_phone()
4. check the rules          fail("message", status) as soon as something is wrong
5. read/write the database  db.query(...) / db.execute(...)
6. return jsonify(...)      the answer, plus 201 if something was created
```

Once you see this pattern, every endpoint reads the same way.

---

## Part A: `backend/suppliers.py`

### Lines 1–18: setup and the shared supplier query

```python
bp = Blueprint("suppliers", __name__)

SUPPLIER_SQL = """SELECT s.*, p.price, p.delivery_charge, p.availability, p.jar_size,
  (SELECT ROUND(AVG(rating), 1) FROM reviews r WHERE r.supplier_id = s.id) rating,
  (SELECT COUNT(*) FROM reviews r WHERE r.supplier_id = s.id) review_count
  FROM suppliers s LEFT JOIN products p ON p.supplier_id = s.id"""

NO_PRICE = float("inf")
```

`SUPPLIER_SQL` is the start of a query that four endpoints reuse, each adding its own `WHERE …`. For every shop it gives:

- `s.*`: every column of `suppliers` (name, map position, address, verified…),
- the price columns from `products` (`p` is its nickname),
- `rating`: the average of its reviews, rounded to 1 decimal (a subquery),
- `review_count`: how many reviews.

`LEFT JOIN` keeps a shop in the results even if it has no `products` row yet (the price columns are then `NULL`).

`NO_PRICE = float("inf")` is infinity. When sorting by price, a shop with no price is treated as infinitely
expensive, so it goes **last**.

### Lines 21–54: `search()`, `GET /api/suppliers`

This is what fills the home page's slider and map. No `@auth`: anyone can search.

```python
@bp.get("/suppliers")
def search():
    """Verified suppliers. Query: lat, lng, max_km, min_price, max_price, available=1, q, sort=distance|price."""
    lat, lng = query_float("lat"), query_float("lng")
    max_km, min_price, max_price = query_float("max_km"), query_float("min_price"), query_float("max_price")
    term = (request.args.get("q") or "").lower().strip()
    in_stock_only = request.args.get("available") == "1"
```

Read the filters from the **query string**, e.g. `/api/suppliers?lat=22.56&lng=88.39&max_km=3&q=tangra`.
Missing numbers become `None`. The search word is lower-cased so "Tangra" matches "tangra".

```python
    found = []
    for s in db.query(SUPPLIER_SQL + " WHERE s.verified = 1"):
        s["distance_km"] = round(km(lat, lng, s["lat"], s["lng"]), 2) if lat is not None and lng is not None else None
        price = s["price"] if s["price"] is not None else NO_PRICE
```

- Get **only verified** shops (`s.verified = 1`). This is the line that hides unverified suppliers from customers.
- For each, work out its distance from the customer (2 decimal places), if the customer's position was given.

```python
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
```

Each `if` throws the shop out if it fails a filter. `continue` means "skip the rest of the loop body and move
on to the next shop". Shops that survive every test are added to `found`.

- `if max_km and …`: `None` and `0` both count as false in Python, so "no limit" and "0" both mean "any distance".
- The text search glues name + service area + address into one string and checks the term appears anywhere in it.
  `filter(None, (...))` drops any parts that are `None` first.

```python
    def by_distance(s):
        return s["distance_km"] if s["distance_km"] is not None else NO_PRICE

    def by_price(s):
        return s["price"] if s["price"] is not None else NO_PRICE

    keys = (by_price, by_distance) if request.args.get("sort") == "price" else (by_distance, by_price)
    found.sort(key=lambda s: (keys[0](s), keys[1](s), s["id"]))
    return jsonify(found)
```

Sorting:

- Two small functions say what to sort by. Missing values count as infinity, so they go last.
- `keys` picks the order: `sort=price` → cheapest first, ties broken by distance. Otherwise nearest first, ties broken by price.
- `found.sort(key=…)` sorts the list using a value computed for each item. `lambda s: (…)` is a tiny
  unnamed function. It returns a **tuple** of (main key, second key, id). Python compares tuples item by item,
  so this sorts by the first, then the second, then the id (so the order is always the same).
- Return the list as JSON.

**Why filter in Python instead of SQL?** Distance is calculated in Python (`km()`), so the distance filter has
to happen here. With a few hundred shops that's instant. A huge national app would use a database with
built-in map features instead.

### Lines 57–64: `detail()`, `GET /api/suppliers/<id>`

```python
@bp.get("/suppliers/<int:sid>")
def detail(sid):
    s = db.query(SUPPLIER_SQL + " WHERE s.id = ? AND s.verified = 1", (sid,), one=True)
    if not s:
        fail("Supplier not found", 404)
    s["reviews"] = db.query("""SELECT r.rating, r.comment, r.ts, u.name FROM reviews r JOIN users u ON u.id = r.user_id
                               WHERE r.supplier_id = ? ORDER BY r.id DESC LIMIT 50""", (sid,))
    return jsonify(s)
```

- `<int:sid>` in the path is a **variable part**: for `/suppliers/3`, Flask passes `sid = 3`. `int:` means it
  must be a whole number (otherwise 404).
- One verified shop, or 404.
- Add its latest 50 reviews, each with the reviewer's name (from `users`).
- Used by the "Details & reviews" pop-up.

### Lines 67–97: `add_review()`, `POST /api/suppliers/<id>/reviews`

```python
@bp.post("/suppliers/<int:sid>/reviews")
@auth()
def add_review(sid):
    d = body()
    rating = number(d, "rating", "Rating", lo=1, hi=5, integer=True)
    comment = text(d, "comment", 500)
    delivered = "SELECT o.id FROM orders o WHERE o.user_id = ? AND o.supplier_id = ? AND o.status = 'delivered'"
    args = (g.user["id"], sid)
```

- Must be signed in. Rating must be a whole number 1–5, and the comment is at most 500 characters.
- `delivered` is the start of a query: "this user's **delivered** orders from this shop". **Only real customers who
  got a delivery may rate.** That keeps ratings honest.

```python
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
```

Find which order is being rated:

- The frontend sends `order_id`, so it must be **this user's delivered order from this shop**, otherwise 403.
- For older clients that don't send one, pick their newest delivered order that has **no review yet**. If
  every delivered order is already rated → 409. If they have none → 403.
- `args + (order_id,)` joins two tuples: `(user_id, sid)` + `(order_id,)` → `(user_id, sid, order_id)`, filling the three `?`.

```python
    checks = tuple(None if d.get(k) is None else (1 if d.get(k) else 0) for k in ("on_time", "quality_ok", "quantity_ok"))
    try:
        db.execute("""INSERT INTO reviews(user_id,supplier_id,order_id,rating,comment,ts,on_time,quality_ok,quantity_ok)
                      VALUES(?,?,?,?,?,?,?,?,?)""", (g.user["id"], sid, order["id"], rating, comment, int(time.time())) + checks)
    except sqlite3.IntegrityError:
        fail("You have already rated this delivery", 409)
    return jsonify(ok=True), 201
```

- The three yes/no questions: not answered → `None`; yes → `1`; no → `0`.
- Save the review. If the same order is rated twice at the same moment, the unique index on `order_id`
  (lesson 04) makes SQLite refuse, and that becomes 409.

### Lines 100–103: `my_listing()`, `GET /api/my-listing`

```python
@bp.get("/my-listing")
@auth("supplier")
def my_listing():
    return jsonify(db.query(SUPPLIER_SQL + " WHERE s.user_id = ?", (g.user["id"],), one=True))
```

Suppliers only. Returns **their own** shop, verified or not, or `null` if they haven't made one yet.

### Lines 106–139: `save_listing()`, `PUT /api/my-listing`

```python
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
```

Validate everything the supplier dashboard form sends. Latitudes run from -90 to 90 and longitudes from -180
to 180 on Earth. Prices are kept between 0 and 10,000. If no contact number is typed, use the account's phone.
`shop` collects the six shop fields in order.

```python
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
```

In one transaction:

1. Does this supplier already have a shop? **Yes** → update it. **No** → create it with `verified = 0`
   (so a **new shop stays hidden until an admin verifies it**).
2. Update the price row. If no row was changed (`rowcount` is 0), there wasn't one yet, so insert it.
   (Doing "update, or insert if missing" like this is sometimes called an **upsert**.)
3. Send back the saved listing, freshly read, so the screen shows exactly what's stored.

---

## Part B: `backend/orders.py`

### Lines 13–29: the shared query and the rules

```python
ORDER_SQL = """SELECT o.*, s.business_name, s.contact, u.name customer, u.phone customer_phone,
  EXISTS (SELECT 1 FROM reviews r WHERE r.order_id = o.id) rated,
  EXISTS (SELECT 1 FROM reports rp WHERE rp.order_id = o.id AND rp.user_id = ? AND rp.status = 'open') reported
  FROM orders o JOIN suppliers s ON s.id = o.supplier_id JOIN users u ON u.id = o.user_id"""
```

For each order: all its columns, plus the shop's name and phone, plus the customer's name and phone
(`u.name customer` renames the column to `customer`), plus two yes/no flags:

- `rated`: does a review exist for this order?
- `reported`: does **the person viewing** have an open problem report on it? The `?` here is filled with the
  viewer's id, so a customer and a supplier looking at the same order each see their *own* report status.

```python
REPORT_CATEGORIES = ("quality", "quantity", "late", "behaviour", "payment", "address", "other")

LABEL = {"pending": "pending", "accepted": "accepted", "out_for_delivery": "out for delivery",
         "delivered": "delivered", "rejected": "rejected", "cancelled": "cancelled"}
# what a supplier may do next from each status; a customer may only cancel a pending request
SUPPLIER_NEXT = {"pending": ("accepted", "rejected"), "accepted": ("out_for_delivery", "rejected"),
                 "out_for_delivery": ("delivered",)}

EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
```

- `LABEL`: every valid status, with words for error messages.
- `SUPPLIER_NEXT` **is the order state machine** from lesson 01, written as data. From `pending` a supplier may
  go to `accepted` or `rejected`, and so on. `delivered`, `rejected` and `cancelled` aren't keys, so nothing
  can follow them: they're final.
- `EMAIL`: a regex for "looks like an e-mail": some characters that aren't `@` or spaces (`[^@\s]+`), an `@`,
  more of them, a dot, more of them. `re.compile` prepares it once so it's fast to reuse.

```
            ┌──── customer: cancelled  (only from pending)
            │
  pending ──┼──► accepted ──► out_for_delivery ──► delivered
            │       │
            └───────┴──► rejected   (supplier, from pending or accepted)
```

### Lines 32–37: `_orders()`, a list of orders with totals

```python
def _orders(where, args):
    rows = db.query(f"{ORDER_SQL} WHERE {where} ORDER BY o.id DESC", (g.user["id"],) + args)
    for r in rows:
        r["rated"], r["reported"] = bool(r["rated"]), bool(r["reported"])
        r["total"] = (r["price"] or 0) * r["qty"] + (r["delivery_charge"] or 0)
    return rows
```

- Glue on the `WHERE` part (written by the programmer, never by a user, so it's safe to put in the text).
  Newest first.
- The arguments are `(viewer id,)` for the `reported` `?`, then the caller's own arguments.
- SQLite gives `EXISTS` as `1`/`0`. `bool(...)` turns that into `True`/`False` for clean JSON.
- `total` = jar price × quantity + delivery charge, using the prices saved **in the order**.

### Lines 40–71: `create_order()`, `POST /api/orders`

```python
@bp.post("/orders")
@auth()
def create_order():
    d = body()
    sid = number(d, "supplier_id", "Supplier", integer=True)
    s = db.query("""SELECT s.id, s.user_id, p.price, p.delivery_charge, p.availability
                    FROM suppliers s JOIN products p ON p.supplier_id = s.id WHERE s.id = ? AND s.verified = 1""",
                 (sid,), one=True)
    if not s:
        fail("Supplier not found", 404)
    if s["user_id"] == g.user["id"]:
        fail("You can't order from your own listing")
    if not s["availability"]:
        fail("This supplier is out of stock right now. Pick another one", 409)
```

Signed in → which shop? It must exist **and be verified**. You can't order from your own shop. It must be in stock.

```python
    qty = number(d, "qty", "Number of jars", default=1, lo=1, hi=50, integer=True)
    address = text(d, "address", 300)
    if not address:
        fail("Enter the delivery address")
    raw_phone = text(d, "phone", 20)
    phone = normalize_phone(raw_phone) if raw_phone else normalize_phone(g.user["phone"])
    if raw_phone and not phone:
        fail("Enter a 10-digit phone number")
    email = text(d, "email", 120)
    if email and not EMAIL.fullmatch(email):
        fail("That e-mail address doesn't look right")
```

Check the rest: 1–50 jars (1 if not given), an address is required, the phone is optional (the account's phone
is used if blank), and the e-mail is optional but must look valid if given.

```python
    oid = db.execute("""INSERT INTO orders(user_id,supplier_id,qty,address,note,status,ts,phone,slot,email,price,delivery_charge)
                        VALUES(?,?,?,?,?,'pending',?,?,?,?,?,?)""",
                     (g.user["id"], sid, qty, address, text(d, "note", 300), int(time.time()),
                      phone, text(d, "slot", 40), email, s["price"], s["delivery_charge"] or 0)).lastrowid
    return jsonify(id=oid, status="pending"), 201
```

Save the order as `pending`, stamped with the current time, and **copy the shop's current price** into it.
Return the new order number with **201 Created**.

### Lines 74–83: listing orders

```python
@bp.get("/orders")
@auth()
def my_orders():
    return jsonify(_orders("o.user_id = ?", (g.user["id"],)))


@bp.get("/supplier/orders")
@auth("supplier")
def supplier_orders():
    return jsonify(_orders("s.user_id = ?", (g.user["id"],)))
```

- `/orders`: orders **I placed** (I'm the customer).
- `/supplier/orders`: orders sent to **the shop I own** (`s.user_id` is the shop owner's account).

Each person only ever gets their own orders, because the `WHERE` uses `g.user["id"]`, which comes from the
token and can't be faked.

### Lines 86–108: `update_order()`, `PATCH /api/orders/<id>`

The most rule-heavy endpoint: changing an order's status.

```python
@bp.patch("/orders/<int:oid>")
@auth()
def update_order(oid):
    new = body().get("status")
    if new not in LABEL:
        fail("Unknown status")
    o = db.query("""SELECT o.user_id, o.status, s.user_id supplier_user FROM orders o
                    JOIN suppliers s ON s.id = o.supplier_id WHERE o.id = ?""", (oid,), one=True)
    me = g.user["id"]
    if not o or me not in (o["user_id"], o["supplier_user"]):
        fail("Request not found", 404)
```

- The new status must be a real one.
- Load the order: its customer, its current status, and its shop's owner.
- If it doesn't exist, **or you're neither its customer nor its supplier** → 404. (404 rather than 403, so
  strangers can't even learn that order #7 exists.)

```python
    customer_cancels = new == "cancelled" and me == o["user_id"] and o["status"] == "pending"
    supplier_moves = me == o["supplier_user"] and new in SUPPLIER_NEXT.get(o["status"], ())
    if not (customer_cancels or supplier_moves):
        fail(f"A request that is {LABEL[o['status']]} can't be marked {LABEL[new]}", 409)
```

Two allowed moves, each a true/false value:

- `customer_cancels`: you're the customer, you're cancelling, and it's still `pending`.
- `supplier_moves`: you're the supplier, and the new status is in the allowed list for the current one.
  `SUPPLIER_NEXT.get(status, ())` gives `()` (empty) for final statuses, so nothing is allowed after them.

Neither → 409, e.g. "A request that is delivered can't be marked accepted".

```python
    # only succeeds if nobody changed the status since we read it
    delivered_at = int(time.time()) if new == "delivered" else None
    if not db.execute("UPDATE orders SET status = ?, delivered_at = COALESCE(?, delivered_at) WHERE id = ? AND status = ?",
                      (new, delivered_at, oid, o["status"])).rowcount:
        fail("This request was just updated. Refresh and try again", 409)
    return jsonify(id=oid, status=new)
```

- `delivered_at`: now if delivering, otherwise `None`. `COALESCE(?, delivered_at)` keeps the old value when the new one is `None`.
- `WHERE id = ? AND status = ?` with the status **we read a moment ago**. Picture this: the customer presses
  Cancel at the same second the supplier presses Accept. Both read "pending". The first update wins. The
  second finds the status is no longer "pending", changes 0 rows, and gets 409 "This request was just updated".
  Without that check, an order could end up "accepted" after being cancelled.

### Lines 111–131: `report_problem()`, `POST /api/orders/<id>/reports`

```python
    category = d.get("category")
    if category not in REPORT_CATEGORIES:
        fail("Pick what went wrong")
    message = text(d, "message", 1000)
    if category == "other" and not message:
        fail("Tell us what went wrong")
```
The category must be in the list. "Something else" needs a description.

```python
    o = db.query("""SELECT o.user_id, s.user_id supplier_user FROM orders o
                    JOIN suppliers s ON s.id = o.supplier_id WHERE o.id = ?""", (oid,), one=True)
    me = g.user["id"]
    if not o or me not in (o["user_id"], o["supplier_user"]):
        fail("Request not found", 404)
    if db.query("SELECT 1 FROM reports WHERE order_id = ? AND user_id = ? AND status = 'open'", (oid, me), one=True):
        fail("You have already reported this request. An admin will look into it", 409)
    rid = db.execute("INSERT INTO reports(order_id,user_id,by_role,category,message,ts) VALUES(?,?,?,?,?,?)",
                     (oid, me, "customer" if me == o["user_id"] else "supplier", category, message, int(time.time()))).lastrowid
    return jsonify(id=rid, status="open"), 201
```

- Only the order's customer or supplier may report it.
- Only one **open** report per person per order (no spamming the admin).
- Save it with `by_role` set to `customer` or `supplier`, depending on who you are on this order. The admin sees it (lesson 08).

---

## Quick check

1. Where exactly is it decided that customers never see unverified suppliers?
2. A supplier tries to change a `delivered` order to `accepted`. What happens, and which line decides?
3. Why does the order store `price` and `delivery_charge` copied from `products`?
4. What does `WHERE id = ? AND status = ?` in `update_order` protect against?
5. Can a customer rate a supplier they never ordered from? Why not?

<details><summary>Answers</summary>

1. `suppliers.py` line 30 (`WHERE s.verified = 1` in `search`), plus line 59 in `detail` and line 46 in `orders.py` (you can't order from one either).
2. 409 "A request that is delivered can't be marked accepted". `SUPPLIER_NEXT` has no entry for `delivered` (line 99, checked at line 100).
3. So the bill stays what the customer was quoted, even if the supplier changes their price later.
4. Two people changing the same order at the same moment (a race condition). The second change fails instead of overwriting the first.
5. No. `add_review` only accepts a delivered order of theirs from that supplier. Otherwise it's 403.

</details>

**Next:** [08 — Backend: the admin](08-backend-admin.md)
