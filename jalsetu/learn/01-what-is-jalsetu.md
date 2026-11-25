# 01 — What is JalSetu?

**In this lesson:** what the app does, who uses it, the three big parts of any web app, and a map of every file.

---

## 1. The problem it solves

In many Indian neighbourhoods people buy 20-litre drinking-water jars by phoning a supplier they happen to know.
You can't easily compare prices, see who is nearby, or know whether a supplier is reliable.

**JalSetu** ("water bridge") is a website that:

- shows **verified** water-jar suppliers on a **map**, with price, delivery charge, distance, stock and ratings,
- lets a customer **send a delivery request** in one step,
- lets the customer **track** the request: Requested → Accepted → On the way → Delivered,
- lets the supplier **manage** their shop and move each request along,
- lets an **admin** check (verify) suppliers and watch everything on a dashboard.

## 2. The three kinds of users ("roles")

Every account has a **role**. The role decides what that person may see and do.

| Role | In the code it's called | What they do | Their page |
|------|------------------------|--------------|------------|
| Customer | `"user"` | Search suppliers, order jars, track, cancel, rate, report a problem | `/` (home) and `/requests` |
| Supplier | `"supplier"` | Edit their listing (price, stock, map pin), accept/reject requests, mark them delivered | `/supplier` |
| Admin | `"admin"` | Verify suppliers, see live numbers, resolve problem reports, help people reset passwords | `/admin` |

Demo accounts (they exist after the first run):

| Role | Phone / login | Password |
|------|---------------|----------|
| Customer | `9000000001` | `demo123` |
| Supplier | `9000000100` | `supplier123` |
| Admin | `admin` | `admin123` |

## 3. The three big parts of a web app

Think of a **restaurant**.

| Restaurant | Web app | In JalSetu |
|------------|---------|-----------|
| The dining room: menu, tables, the waiter who takes your order | **Frontend**: everything you see and click in the browser | The `frontend/` folder (Next.js + React, written in TypeScript) |
| The kitchen: checks the order makes sense, cooks it | **Backend**: a program on a server that checks rules and does the work | The `backend/` folder + `app.py` (Python + Flask) |
| The pantry and the order book: where everything is stored | **Database**: where data is kept permanently | The file `jalsetu.db` (SQLite) |
| The order slip passed between waiter and kitchen | **API request / response**: a message between frontend and backend | Messages to addresses like `/api/orders` |
| The language written on the slip | **JSON**: a simple text format for data | `{"supplier_id": 1, "qty": 2}` |

**Why split it up?** The frontend runs on *your* device, so anyone could change it. It can't be trusted to
enforce rules like "only the supplier may mark an order delivered". The backend runs on a computer *we*
control, so all the real rules live there. The database is separate so data survives when programs restart.

### How the parts talk

```
 ┌───────────── Your computer ─────────────┐
 │                                          │
 │  Browser (Chrome, Edge…)                 │
 │  shows http://localhost:3000             │
 │        │  ▲                              │
 │        │  │ pages, and answers to /api   │
 │        ▼  │                              │
 │  Next.js dev server   ── port 3000 ──    │  ← "npm run dev" in terminal 2
 │        │  ▲                              │
 │        │  │  it forwards every /api/...  │
 │        ▼  │  request (a "proxy")         │
 │  Flask server         ── port 5000 ──    │  ← "python app.py" in terminal 1
 │        │  ▲                              │
 │        ▼  │  SQL commands                │
 │  jalsetu.db (a file on disk)             │
 └──────────────────────────────────────────┘
```

During development **both servers run on your own computer**. That's why you need **two terminals**: one for
the backend (`python app.py`) and one for the frontend (`npm run dev`). On a real public website they would run
on rented computers in a data centre, but the code would be the same.

### One click, start to finish (short version)

You press **Order** on the home page:

1. **Frontend** (`RequestForm.tsx`) collects what you typed: supplier, phone, address, how many jars.
2. It sends a message: `POST /api/orders` with that data written as JSON, plus your sign-in "token".
3. **Next.js** forwards it to **Flask** on port 5000.
4. **Backend** (`backend/orders.py`) checks: are you signed in? Is the supplier verified? In stock? Is the address filled in?
5. It **saves** a new row in the `orders` table of the **database**.
6. It answers: `{"id": 7, "status": "pending"}`.
7. The frontend shows "Request sent!".
8. On the supplier's dashboard, a timer asks the backend for new requests every 15 seconds, so the new one appears there with a chime.

Lesson 15 follows this journey line by line.

## 4. The languages in this project

| Language | Files | Used for |
|----------|-------|----------|
| **Python** | `.py` | The backend: all the rules and data handling |
| **SQL** | inside the `.py` files as text | Talking to the database ("give me all verified suppliers") |
| **TypeScript** | `.ts`, `.tsx` | The frontend. `.tsx` files mix TypeScript with HTML-like tags (that mix is called JSX) |
| **CSS** | `.css` | How things look: colours, sizes, positions, animation |
| **HTML** | `.html`, and inside `.tsx` | The structure of a web page: headings, buttons, forms |
| **JSON** | `.json`, and every API message | Writing data as text. Settings files like `package.json` use it too |
| **Markdown** | `.md` | Documents like this one |

## 5. Map of every file

The project lives in `jalsetu/` (inside the git folder). `◆` marks the files you'll spend most time on.

```
jalsetu/
├── app.py ◆                  Starts the backend. Run: python app.py
├── requirements.txt          The Python packages the backend needs (just Flask)
├── README.md                 How to run the project, demo logins, page list
├── INTERVIEW_PREP.md         Interview questions about the project
├── jalsetu.db                The database file. Made on the first run (not in git)
├── learn/                    ← these lessons
│
├── backend/                  THE BACKEND (Python + Flask)
│   ├── __init__.py ◆         Builds the Flask app, plugs in all the parts, turns errors into JSON
│   ├── db.py ◆               Opens the database, creates/updates the tables, adds demo data
│   ├── util.py               Small helpers: read the request, check numbers, clean phone numbers, distance
│   ├── sms.py                Sends text messages (for now, prints them in the terminal)
│   ├── auth.py ◆             Accounts: register, sign in, sign out, tokens, forgot password, the @auth guard
│   ├── suppliers.py ◆        Supplier search for customers, supplier details, reviews, a supplier's own listing
│   ├── orders.py ◆           Place, list, cancel and move delivery requests; report a problem
│   └── admin.py              Admin dashboard numbers, verify suppliers, reset codes, terminal commands
│
├── frontend/                 THE FRONTEND (Next.js + React + TypeScript)
│   ├── package.json          Lists the JavaScript packages and the commands (npm run dev…)
│   ├── package-lock.json     Exact versions of every package (written by npm; don't edit)
│   ├── next.config.ts        Next.js settings: forward /api/* to the Flask backend
│   ├── tsconfig.json         TypeScript settings
│   ├── AGENTS.md             Notes for AI coding tools (written by Next.js)
│   │
│   ├── app/                  PAGES. Each folder with a page.tsx is one web address
│   │   ├── layout.tsx ◆      The frame around every page: <html>, font, global CSS, AppProvider
│   │   ├── globals.css ◆     ALL the styling for the whole site (about 2,500 lines)
│   │   ├── page.tsx          "/"          → the home page (shows <Landing />)
│   │   ├── requests/page.tsx "/requests"  → My requests (shows <Requests />)
│   │   ├── supplier/page.tsx "/supplier"  → Supplier dashboard
│   │   └── admin/page.tsx    "/admin"     → Admin dashboard
│   │
│   ├── components/           BUILDING BLOCKS of the pages
│   │   ├── AppProvider.tsx ◆ Shared memory for the whole app: who is signed in, pop-up messages
│   │   ├── Landing.tsx ◆     The home page: puts all the sections together, loads suppliers
│   │   ├── TopBar.tsx        Logo, the navy ribbon, the account menu
│   │   ├── Hero.tsx          The big first screen: "Water jar delivery"
│   │   ├── RequestForm.tsx ◆ The order form on the home page
│   │   ├── SupplierShowcase.tsx  Filters + the one-supplier-at-a-time slider + the map
│   │   ├── SupplierMap.tsx   The interactive map (Leaflet + OpenStreetMap), and the shop-pin picker
│   │   ├── SupplierModal.tsx Pop-up with one supplier's details and reviews
│   │   ├── HowItWorks.tsx    The 6-step picture reel
│   │   ├── WeDeliver.tsx     The van and the "Homes, Offices…" icons
│   │   ├── Verified.tsx      The row of verification certificates
│   │   ├── Certificate.tsx   One certificate drawing
│   │   ├── CallFab.tsx       The round floating phone button
│   │   ├── Footer.tsx        The bottom of every page
│   │   ├── AuthModal.tsx ◆   The sign-in / create-account pop-up
│   │   ├── ForgotPassword.tsx  The "forgot password?" screens inside that pop-up
│   │   ├── Modal.tsx         A general pop-up window (used by all the pop-ups)
│   │   ├── RoundButton.tsx   The big round navy button
│   │   ├── PageShell.tsx     The frame for signed-in pages, and the "please sign in" gate
│   │   ├── StatusTrack.tsx   The Requested → Accepted → On the way → Delivered tracker
│   │   ├── LiveNote.tsx      The "Live · this page updates by itself" line
│   │   ├── ReportModal.tsx   "Report a problem" pop-up
│   │   ├── Icons.tsx         All the little drawings (phone, star, pin…) and the logo
│   │   └── pages/
│   │       ├── Requests.tsx ◆          My requests page (+ the rating pop-up)
│   │       ├── SupplierDashboard.tsx ◆ Supplier dashboard
│   │       └── Admin.tsx ◆             Admin dashboard
│   │
│   ├── lib/                  HELPERS (no drawing on screen, just useful functions)
│   │   ├── api.ts ◆          How the frontend talks to the backend, and the shapes of the data
│   │   ├── format.ts         Turns data into nice text: ₹40, 1.2 km, "On the way", "3 min ago"
│   │   ├── usePoll.ts        "Run this every N seconds" (live updates)
│   │   └── chime.ts          Plays a two-note sound for new requests
│   │
│   └── public/img/           Pictures: jar, cooler, van, backgrounds (made by the tools/ scripts)
│
├── static/index.html         An older one-file version of the site. Flask still shows it at localhost:5000
└── tools/
    ├── make_art.py           Generates the background pictures with maths (mountains, water)
    └── make_svg.py           Generates the jar, cooler, van and "how it works" drawings
```

Files you should **never edit by hand**: `package-lock.json`, anything in `node_modules/` or `.next/` (made by
npm / Next.js), `__pycache__/` (made by Python), and `jalsetu.db` (use the app or delete it to reset).

The `.gitignore` file (one folder up) lists files git should *not* save: the database, `node_modules/`,
`.next/`, `.env` files (private local settings), and Python's cache files. They're either generated
automatically or private to your machine.

## 6. The life of a delivery request

Every order has a **status**. Only certain moves are allowed, and the backend enforces them
(lesson 07). This diagram is a "state machine":

```
                    customer cancels
          ┌──────────────────────────────► cancelled
          │
      pending ──supplier accepts──► accepted ──supplier──► out_for_delivery ──supplier──► delivered
     (Requested)                   (Accepted)              (On the way)                    (Delivered)
          │                            │                                                       │
          └──supplier rejects──┐       └──supplier rejects──┐                       customer can now RATE
                               ▼                            ▼
                            rejected                     rejected
```

The words in brackets are what the screen shows (from `STATUS_LABEL` in `frontend/lib/format.ts`).

---

## Quick check

1. Which folder holds the rules that decide whether an order is allowed?
2. Why can't the frontend be trusted to enforce rules?
3. What is `jalsetu.db`?
4. You want to change the words on the home page's big heading. Which folder would you look in?

<details><summary>Answers</summary>

1. `backend/`, in `orders.py`.
2. It runs on the user's own device, so they could change it. The backend runs on a computer we control.
3. The database file: a SQLite file holding all users, suppliers, orders and reviews.
4. `frontend/components/`, in `Hero.tsx` (line 17: `Water jar delivery`).

</details>

**Next:** [02 — Coding basics](02-coding-basics.md)
