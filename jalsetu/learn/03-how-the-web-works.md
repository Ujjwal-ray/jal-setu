# 03 — How the web works

**In this lesson:** what really happens when a web page "talks to a server": URLs, requests, responses, JSON,
APIs, sign-in tokens and live updates. At the end there's a table of **every API door in JalSetu**.

---

## 1. Clients and servers

- A **server** is a program that waits for messages and answers them. (The computer it runs on is also called a server.)
- A **client** is a program that sends messages to a server. Your **browser** is a client.

In JalSetu there are two servers:

| Server | Started with | Listens on | Its job |
|--------|--------------|-----------|---------|
| **Next.js** (frontend server) | `npm run dev` | port **3000** | Sends your browser the pages (HTML, JavaScript, CSS, images) and forwards `/api` messages to Flask |
| **Flask** (backend server) | `python app.py` | port **5000** | Answers `/api/...` messages: checks rules, reads and writes the database |

## 2. URLs: the address of everything

```
  http://localhost:3000/requests?tab=1
  └─┬─┘  └───┬───┘ └┬─┘└───┬───┘└─┬──┘
 scheme    host   port   path   query string
```

| Part | Meaning |
|------|---------|
| **scheme** `http` | The set of rules for talking. `https` is the encrypted version used on real websites |
| **host** `localhost` | Which computer. `localhost` (or `127.0.0.1`) always means "this same computer" |
| **port** `3000` | Which program on that computer. Think: building = host, flat number = port |
| **path** `/requests` | Which page or resource |
| **query string** `?lat=22.56&lng=88.39` | Extra settings, as `name=value` pairs joined by `&`. JalSetu's supplier search uses these |

## 3. Requests and responses

Talking to a server is always the same two-step dance:

1. The client sends a **request**.
2. The server sends back a **response**.

That's **HTTP** (HyperText Transfer Protocol). Here's a real JalSetu request, written out in full. This is what
the order form sends:

```
POST /api/orders HTTP/1.1                          ← METHOD, PATH
Host: localhost:3000
Content-Type: application/json                     ← HEADERS: extra information about the message
Authorization: Bearer mF3kQ...x9                   ←   (this one proves who you are, see section 7)

{"supplier_id": 1, "qty": 2, "address": "12 Lake Rd", "phone": "9000000001", "email": "", "slot": "2026-11-26 10:00"}
                                                   ↑ BODY: the data being sent, written as JSON
```

And the response:

```
HTTP/1.1 201 CREATED                               ← STATUS CODE: how it went
Content-Type: application/json

{"id": 7, "status": "pending"}                     ← BODY: the answer, as JSON
```

### Methods: what kind of request

| Method | Meaning | JalSetu example |
|--------|---------|-----------------|
| `GET` | "Give me…" (reading only, changes nothing) | `GET /api/suppliers`: list suppliers |
| `POST` | "Create this / do this action" | `POST /api/orders`: place an order |
| `PUT` | "Replace this whole thing with what I send" | `PUT /api/my-listing`: save a supplier's listing |
| `PATCH` | "Change part of this thing" | `PATCH /api/orders/7` with `{"status": "accepted"}` |

When you type a URL in the browser's address bar, the browser sends a `GET`.

### Status codes: how it went

The first digit tells you the family: **2xx** = success, **4xx** = *you* (the client) did something wrong,
**5xx** = the *server* broke.

| Code | Name | When JalSetu sends it |
|------|------|-----------------------|
| 200 | OK | Normal success |
| 201 | Created | Something new was made: an account, an order, a review, a report |
| 400 | Bad Request | Something you sent is wrong: "Enter the delivery address" |
| 401 | Unauthorized | You're not signed in, or the password is wrong |
| 403 | Forbidden | You're signed in but not allowed (a customer opening admin data) |
| 404 | Not Found | That supplier, order or page doesn't exist |
| 405 | Method Not Allowed | Wrong method for that path (e.g. `GET` on a `POST`-only door) |
| 409 | Conflict | It clashes with the current state: "already registered", "already rated", "this request was just updated" |
| 413 | Payload Too Large | The body is over 64 KB |
| 429 | Too Many Requests | Too many wrong passwords, or too many reset codes asked for |
| 500 | Internal Server Error | A bug in the backend |

## 4. JSON: the shared language

Python and TypeScript are different languages, so they need a shared way to write data down as text.
That's **JSON** (JavaScript Object Notation). It looks almost exactly like a Python dict or a TypeScript object:

```json
{
  "id": 1,
  "business_name": "Aqua Pure Suppliers",
  "lat": 22.5668,
  "lng": 88.3902,
  "price": 40.0,
  "delivery_charge": 10.0,
  "availability": 1,
  "verified": 1,
  "rating": 5.0,
  "review_count": 1,
  "distance_km": 0.56,
  "service_area": "Beliaghata, Phoolbagan, Ultadanga"
}
```

That's (part of) one supplier as `GET /api/suppliers` returns it.

- Backend → JSON: `jsonify(...)` in Flask turns a Python dict/list into JSON text.
- Frontend → JSON: `JSON.stringify(...)` turns an object into JSON text. `r.json()` reads JSON text back into an object.

## 5. APIs: the list of doors

An **API** (Application Programming Interface) is the set of requests a server agrees to answer: its "menu".
Each item is called an **endpoint** (a method + a path).

In Flask, each endpoint is a Python function with a line like `@bp.post("/orders")` above it. That line says
"when a `POST` to `/api/orders` arrives, run this function." (The `/api` part is added in `backend/__init__.py`.)

### Every endpoint in JalSetu

"Who" says who may use it. The backend checks this with the `@auth(...)` guard (lesson 06).

| Method | Path (after `/api`) | Who | File | What it does |
|--------|---------------------|-----|------|--------------|
| GET | `/health` | anyone | `__init__.py` | Answers `{"ok": true}`, just to check the server is up |
| POST | `/register` | anyone | `auth.py` | Create an account (customer or supplier), sign in |
| POST | `/login` | anyone | `auth.py` | Sign in with phone + password → get a token |
| POST | `/logout` | anyone | `auth.py` | Delete this sign-in's token |
| GET | `/me` | signed in | `auth.py` | "Who am I?", also marks you as online |
| POST | `/password/forgot` | anyone | `auth.py` | Text a 6-digit reset code to the account's phone |
| POST | `/password/reset` | anyone with a code | `auth.py` | Set a new password using that code |
| GET | `/suppliers` | anyone | `suppliers.py` | Search **verified** suppliers (filters in the query string) |
| GET | `/suppliers/<id>` | anyone | `suppliers.py` | One supplier + its latest reviews |
| POST | `/suppliers/<id>/reviews` | signed in | `suppliers.py` | Rate a supplier after a **delivered** order |
| GET | `/my-listing` | supplier | `suppliers.py` | The supplier's own listing |
| PUT | `/my-listing` | supplier | `suppliers.py` | Create or update the listing (name, price, stock, map pin…) |
| POST | `/orders` | signed in | `orders.py` | Place a delivery request |
| GET | `/orders` | signed in | `orders.py` | My requests (as a customer) |
| GET | `/supplier/orders` | supplier | `orders.py` | Requests sent to my shop |
| PATCH | `/orders/<id>` | the order's customer or supplier | `orders.py` | Change status: cancel, accept, reject, out for delivery, delivered |
| POST | `/orders/<id>/reports` | the order's customer or supplier | `orders.py` | Report a problem to the admin |
| GET | `/admin/overview` | admin | `admin.py` | The big numbers on the dashboard |
| GET | `/admin/suppliers` | admin | `admin.py` | Every supplier with orders, earnings, ratings, who's online |
| GET | `/admin/feedback` | admin | `admin.py` | Problem reports and latest reviews |
| PATCH | `/admin/reports/<id>` | admin | `admin.py` | Mark a report resolved / reopen it |
| POST | `/admin/suppliers/<id>/verify` | admin | `admin.py` | Verify or un-verify a supplier |
| POST | `/admin/reset-codes` | admin | `admin.py` | Make a reset code to read out to someone on the phone |

`<id>` means "a number goes here", e.g. `/orders/7`.

## 6. The proxy: why the browser only talks to port 3000

Browsers have a safety rule: a page from one **origin** (scheme + host + port) may not read answers from a
*different* origin unless that server says it's OK. `localhost:3000` and `localhost:5000` count as different
origins.

JalSetu avoids the problem neatly. The browser sends **everything** to port 3000. Next.js **forwards** any
path starting with `/api/` to Flask on port 5000 and passes the answer back. A middle-man like that is a
**proxy**. The setting is three lines in [frontend/next.config.ts](../frontend/next.config.ts):

```ts
async rewrites() {
  return [{ source: "/api/:path*", destination: `${BACKEND}/api/:path*` }];
},
```

"Any request to `/api/` + *anything* → send it to `http://127.0.0.1:5000/api/` + *the same anything*."

```
Browser ──GET /api/suppliers──► Next.js :3000 ──GET /api/suppliers──► Flask :5000
Browser ◄──────── JSON ───────── Next.js :3000 ◄──────── JSON ──────── Flask :5000
```

## 7. Signing in: tokens

HTTP has no memory. Every request arrives as if from a stranger. So how does the backend know request #2 is
from the same person who signed in with request #1?

**Analogy:** at a concert you show your ticket once at the gate and get a **wristband**. After that you show the
wristband, not the ticket.

1. You sign in (`POST /api/login` with phone + password). That's showing the ticket.
2. The backend makes a long random secret, the **token** (e.g. `mF3kQ…x9`, 43 characters). That's the wristband.
   It saves a *scrambled* copy ("hash") of it in the `tokens` table, and sends the real token back to you.
3. The frontend stores the token in the browser's **localStorage** (a small storage box each website gets in
   your browser, which survives closing the tab).
4. Every later request carries it in a **header**: `Authorization: Bearer mF3kQ…x9`.
5. The backend scrambles the token it receives the same way and looks for a match in `tokens`. Found and not
   expired → it knows who you are.
6. Signing out deletes the token on both sides.

Tokens last **30 days** (`TOKEN_TTL` in `backend/__init__.py`). Lesson 06 shows the code.

## 8. "Live" updates: polling

A server can't simply message your browser whenever it likes. The browser has to ask. So pages that need to
stay fresh **ask again on a timer**. That's called **polling**:

| Page | Asks every | Code |
|------|-----------|------|
| My requests | 15 seconds | `usePoll(..., POLL_MS)` in `components/pages/Requests.tsx` |
| Supplier dashboard | 15 seconds (even in a background tab) | `components/pages/SupplierDashboard.tsx` |
| Admin dashboard | 30 seconds | `setInterval(..., REFRESH_MS)` in `components/pages/Admin.tsx` |
| Any signed-in page | 2 minutes ("heartbeat" so admin sees you online) | `components/AppProvider.tsx` |

Each page compares the new answer with the previous one. If something changed (a new order, a new status), it
shows a pop-up message (a "toast") and, for suppliers, plays a chime.

## 9. Try it yourself

With the backend running (`python app.py`):

1. Open <http://localhost:5000/api/health> in your browser. You'll see `{"ok": true}`. You just sent a `GET`
   request and read the JSON response.
2. Open <http://localhost:5000/api/suppliers?lat=22.5645&lng=88.3951&sort=price>. That's the raw supplier list,
   cheapest first.
3. Change `sort=price` to `sort=distance`, or add `&max_price=38`. Watch the list change.
4. Open <http://localhost:5000/api/orders>. You'll get `{"error": "Sign in required"}` with status 401, because
   your address bar doesn't send a token.

With the frontend running too, open <http://localhost:3000>, press **F12** to open the browser's
**developer tools**, click the **Network** tab, and use the site. Every `/api/...` request appears there. Click
one to see its method, headers, request body and response. Lesson 16 shows more.

---

## Quick check

1. Which method would "delete my account" most likely use, and which does "show my orders" use?
2. A request comes back with status 403. Whose fault is it, and what does it mean?
3. Why does the frontend send `/api/...` requests to port 3000 instead of straight to 5000?
4. Where does the browser keep the token, and how does it send it?

<details><summary>Answers</summary>

1. "Show my orders" is `GET /api/orders`. Deleting would normally be `DELETE`, a method JalSetu doesn't use yet.
2. A 4xx is the client's side: you're signed in but not allowed to do this.
3. To keep one origin (no cross-origin rules to deal with). Next.js forwards `/api` to Flask (`next.config.ts`).
4. In localStorage (key `jstoken`). It's sent in the `Authorization: Bearer <token>` header on every request.

</details>

**Next:** [04 — Databases and SQL](04-database-and-sql.md)
