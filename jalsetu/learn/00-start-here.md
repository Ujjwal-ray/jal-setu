# Start here: learning JalSetu from zero

These notes teach you how the JalSetu project works, starting from zero. You don't need to know any code
before you begin. Every new word is explained the first time it appears, and there is a
[glossary](17-glossary.md) for when you forget one.

By the end you will be able to:

- say what every file in the project is for,
- read a line of Python or TypeScript and say what it does,
- follow one click ("Order") from the button on the screen, through the server, into the database and back,
- make small changes yourself and see them work.

---

## The reading order

Read the lessons in order. Each one builds on the one before.

| # | Lesson | What you learn |
|---|--------|----------------|
| 01 | [What is JalSetu?](01-what-is-jalsetu.md) | What the app does, its 3 kinds of users, frontend vs backend vs database, a map of every file |
| 02 | [Coding basics](02-coding-basics.md) | Values, variables, if/else, loops, functions, using real lines from this project, in both Python and TypeScript |
| 03 | [How the web works](03-how-the-web-works.md) | Browsers, servers, URLs, requests and responses, JSON, APIs, tokens. The list of every API "door" in JalSetu |
| 04 | [Databases and SQL](04-database-and-sql.md) | Tables, rows, SQL commands, every JalSetu table, and `backend/db.py` line by line |
| 05 | [Backend: starting up](05-backend-startup.md) | `app.py`, `backend/__init__.py`, `backend/util.py`, `backend/sms.py` line by line |
| 06 | [Backend: accounts and passwords](06-backend-accounts.md) | `backend/auth.py` line by line: sign up, sign in, tokens, the `@auth` guard, forgotten passwords |
| 07 | [Backend: suppliers and orders](07-backend-suppliers-and-orders.md) | `backend/suppliers.py` and `backend/orders.py` line by line: search, reviews, placing and moving orders |
| 08 | [Backend: the admin](08-backend-admin.md) | `backend/admin.py` line by line: dashboard numbers, verifying suppliers, reset codes, terminal commands |
| 09 | [Frontend basics](09-frontend-basics.md) | HTML, CSS, JavaScript, TypeScript, React (components, props, state, effects) and Next.js |
| 10 | [Frontend: the foundation](10-frontend-foundation.md) | Config files, page routes, `lib/` helpers and `AppProvider` (the app's shared memory) line by line |
| 11 | [Frontend: the home page](11-frontend-home-page.md) | Every component on the home page: the order form, the supplier slider, the map, the pop-ups |
| 12 | [Frontend: signing in](12-frontend-sign-in.md) | The sign-in pop-up and the "forgot password" screens |
| 13 | [Frontend: the dashboards](13-frontend-dashboards.md) | My requests, the supplier dashboard and the admin dashboard |
| 14 | [CSS: how it looks](14-css-styling.md) | How `globals.css` gives the app its colours, shapes and layout |
| 15 | [Follow an order end to end](15-follow-an-order.md) | Seven real journeys traced file by file, line by line. **This is where it all clicks.** |
| 16 | [Run it and practise](16-run-it-and-practice.md) | Run the project, use the browser's developer tools, and do practice exercises |
| 17 | [Glossary](17-glossary.md) | Every technical word in these notes, A to Z |

**Short on time?** Read 01, 03, then 15. That gives you the whole idea. Then come back for the details.

---

## How to read these notes

1. **Keep the code open next to the lesson.** In VS Code, open the lesson, then click the file link in it (for
   example [backend/auth.py](../backend/auth.py)). Drag that tab to the right so you see both at once.
2. **Line numbers match the real files.** When a lesson says "line 42", look at line 42 in the file.
3. **Don't try to memorise.** Programmers look things up all day. Aim to *recognise* what a line does.
4. **Run the app** (lesson 16) as early as you like. Seeing it work makes the code much easier to follow.
5. **Change something small** and see what happens. If you break it, undo the change (Ctrl+Z) or run
   `git checkout -- <file>` to get the original back.

### Symbols used in these notes

| You see | It means |
|---------|----------|
| `code like this` | Something typed exactly as shown: code, a file name, a command |
| `#` at the start of a line in Python | A comment: a note for humans. The computer skips it |
| `//` at the start of a line in TypeScript | Also a comment |
| → | "becomes" or "leads to" |
| **Why?** boxes | The reason the code was written this way. That's often the most useful part |
| `<details>` blocks (click "Answer") | Hidden answers to the quick-check questions |

---

## The project in one picture

```
   CUSTOMER / SUPPLIER / ADMIN
   using a web browser
            │
            ▼
 ┌──────────────────────────┐        ┌──────────────────────────┐        ┌───────────────┐
 │ FRONTEND  (frontend/)    │  asks  │ BACKEND  (backend/)      │  reads │ DATABASE      │
 │ Next.js + React          │ ─────► │ Python + Flask           │ ─────► │ jalsetu.db    │
 │ TypeScript (.tsx/.ts)    │ ◄───── │ checks rules, does work  │ ◄───── │ (SQLite)      │
 │ what you SEE and CLICK   │ answer │ the "brain"              │ writes │ the "memory"  │
 └──────────────────────────┘        └──────────────────────────┘        └───────────────┘
        port 3000                             port 5000                      one file
```

Lesson 01 explains this picture properly.

---

There's also [INTERVIEW_PREP.md](../INTERVIEW_PREP.md) in the project folder: interview questions and answers about
JalSetu. It will make much more sense after you've read these lessons.

**Next:** [01 — What is JalSetu?](01-what-is-jalsetu.md)
