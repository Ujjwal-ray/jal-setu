# 02 — Coding basics (Python and TypeScript side by side)

**In this lesson:** the handful of ideas that *all* code is built from. Each idea is shown in **Python** (the
backend's language) and **TypeScript** (the frontend's language), using real lines from JalSetu where possible.

Once you know these ~15 ideas, you can read most of the project.

---

## 1. What a program is

A program is a **list of instructions** the computer follows **from top to bottom**, one line at a time.
Some instructions make it jump: "do this part only if…", "repeat this for every…", "go and run that function".

Code is plain text. A `.py` file is read by **Python**. A `.ts`/`.tsx` file is turned into **JavaScript** and run
by your **browser** (or by **Node.js**, a program that runs JavaScript outside the browser).

## 2. Comments: notes for humans

The computer skips comments. They explain *why* the code does something.

```python
# Python: everything after # on a line is a comment
TOKEN_TTL = 30 * 24 * 3600   # sign-in lasts 30 days

"""Text in triple quotes at the top of a file or function is a "docstring":
a comment that describes it."""
```

```ts
// TypeScript: everything after // on a line is a comment
/* or a block comment
   across several lines */
/** A comment starting with /** describes the thing below it (editors show it when you hover). */
```

## 3. Values and their types

A **value** is a piece of data. Every value has a **type**: what kind of thing it is.

| Kind | Python | TypeScript | Example in JalSetu |
|------|--------|-----------|-------------------|
| Text ("string") | `"Aqua Pure"` or `'Aqua Pure'` | `"Aqua Pure"` or `'Aqua Pure'` | a business name |
| Whole number ("integer") | `40` | `40` | jar price, quantity |
| Decimal number ("float") | `22.5668` | `22.5668` | a map latitude |
| Yes / no ("boolean") | `True` / `False` | `true` / `false` | is it in stock? |
| Nothing | `None` | `null` or `undefined` | a supplier with no rating yet |
| A list | `[1, 2, 3]` | `[1, 2, 3]` (called an "array") | all suppliers |
| Named fields | `{"name": "Asha", "role": "user"}` (a "dictionary" or "dict") | `{ name: "Asha", role: "user" }` (an "object") | one user |

> In TypeScript, `null` means "deliberately empty", `undefined` means "never set". Python has just `None`.

## 4. Variables: giving a value a name

A **variable** is a labelled box that holds a value. `=` means "put this value in this box". It does **not** mean "equals".

```python
# Python                                  (backend/auth.py, line 17)
MAX_FAILED_LOGINS = 5
```

```ts
// TypeScript                             (frontend/components/pages/Requests.tsx, line 17)
const POLL_MS = 15_000;
```

- In TypeScript, `const` makes a box you can't put a new value in later. `let` makes one you can change.
- The `;` at the end of a TypeScript line just means "end of instruction". Python doesn't use it.
- `15_000` is just `15000`. The `_` makes big numbers easier to read. Python allows that too (`10_000`).
- Names in ALL_CAPS are a habit for values that never change ("constants").

## 5. Doing things with values: operators

| Operator | Meaning | Example |
|----------|---------|---------|
| `+ - * /` | add, subtract, multiply, divide | `price * qty + delivery_charge` |
| `**` (Python) | to the power of | `x ** 2` is x squared |
| `%` | remainder after dividing | `7 % 3` is `1`. Used to "wrap around" a slider |
| `==` (Python), `===` (TS) | is equal to? (gives true/false) | `user.role === "admin"` |
| `!=` (Python), `!==` (TS) | is NOT equal to? | |
| `< > <= >=` | less / greater than (or equal) | `len(password) < 6` |
| `and or not` (Python) | combine yes/no answers | `if not phone:` |
| `&& \|\| !` (TS) | same, in TypeScript | `!user` means "there is no user" |
| `in` (Python) | is it inside this list/text? | `if new not in LABEL:` |

> TypeScript has `==` too, but it does loose, surprising conversions. Programmers use `===`.

## 6. Text with values inside it

Both languages let you build text with values dropped in:

```python
# Python "f-string": put f before the quotes, values go in { }      (backend/util.py, line 43)
fail(f"{label} is required")          # label = "Rating"  →  "Rating is required"
```

```ts
// TypeScript "template literal": use backticks ` `, values go in ${ }   (Landing.tsx, line 98)
`${all.length} verified suppliers`    // all.length = 4  →  "4 verified suppliers"
```

## 7. Making decisions: if / else

```python
# Python                                   (backend/auth.py, lines 100-105)
if not name:
    fail("Enter your name")
if not phone:
    fail("Enter a 10-digit mobile number")
if len(password) < 6:
    fail("Password must be at least 6 characters")
```

**Python uses indentation (spaces at the start of the line) to show what belongs inside the `if`.** The
lines indented under `if` run only when the condition is true. That indentation matters to Python.

```ts
// TypeScript uses { curly braces } instead       (RequestForm.tsx, lines 74-76)
if (digits.length !== 10) return setErr("Enter a 10-digit phone number");
if (!address.trim()) return setErr("Enter the delivery address");
```

A one-line `if` in TypeScript can skip the braces, as above.

There's also a short **"one-line if" that picks a value**:

```python
# Python: A if condition else B
role = d.get("role") if d.get("role") in ("user", "supplier") else "user"     # auth.py line 99
```

```ts
// TypeScript: condition ? A : B         ("if condition then A otherwise B")
{busy ? "Sending…" : "Order"}            // RequestForm.tsx line 154: button text while sending
```

## 8. Lists and repeating things (loops)

```python
# Python "for" loop: run the indented lines once for each item       (backend/__init__.py, line 28)
for module in (auth, suppliers, orders, admin):
    app.register_blueprint(module.bp, url_prefix="/api")
```

Python also has a compact way to **build a new list from an old one** (a "list comprehension"):

```python
rows = [dict(r) for r in cursor.fetchall()]     # db.py line 29: "a dict of r, for every r in the results"
```

TypeScript code mostly uses **array methods** instead of loops:

```ts
suppliers.filter((s) => s.availability)        // keep only the items where the test is true
open.map((s) => s.price)                       // make a new list by changing each item
list.findIndex((s) => s.id === activeId)       // the position of the first match (-1 if none)
rs.some((s) => s.id === cur)                   // true if ANY item passes the test
orders.reduce((sum, o) => sum + o.total, 0)    // boil a whole list down to one value (a total)
```

Positions in a list start at **0**: in `["a", "b", "c"]`, `"a"` is item 0.

## 9. Dictionaries / objects: data with named fields

```python
# Python dict
user = {"id": 2, "name": "Demo Student", "role": "user"}
user["name"]            # → "Demo Student"
user.get("email")       # → None (no error if the key is missing)
```

```ts
// TypeScript object
const user = { id: 2, name: "Demo Student", role: "user" };
user.name               // → "Demo Student"
user?.role              // "?." means: if user is null/undefined, stop and give undefined instead of crashing
```

**Spreading** copies all fields into a new object, then overrides some:

```ts
setFilters({ ...filters, ...p });   // SupplierShowcase.tsx line 44: "all the old filters, but with p's changes"
```

## 10. Functions: named, reusable recipes

A **function** is a set of instructions with a name. You **call** it (run it) by writing its name and `( )`.
Values you pass in are **arguments** (or **parameters**). The function can **return** a value.

```python
# Python: "def" defines a function                         (backend/db.py, lines 9-12)
def connect(path):                          # takes one input, called path
    con = sqlite3.connect(path, timeout=10) # open the database file
    con.row_factory = sqlite3.Row           # (a setting, see lesson 04)
    return con                              # hand the connection back to whoever called

con = connect("jalsetu.db")                 # calling it
```

```ts
// TypeScript: three ways to write the same idea
function rupee1(n: number) { return "₹" + n; }      // a normal function
const rupee2 = (n: number) => "₹" + n;              // an "arrow function": (inputs) => result
// format.ts line 3 really is:
export const rupee = (n: number | null | undefined) => "₹" + (n ?? 0).toLocaleString("en-IN");
```

**Default values** are used when an argument is left out:

```python
def fail(message, status=400):   # util.py line 16: fail("Oops") uses 400; fail("Oops", 404) uses 404
```

**Functions can be passed around like values.** This is used everywhere in the frontend:
`onClick={() => setOpen(false)}` hands the button a small function to run *later*, when it's clicked.

## 11. Using code from other files: import / export

```python
# Python                                         (backend/auth.py, lines 12-13)
from . import db, sms                            # "." means "this same folder (backend/)"
from .util import body, fail, normalize_phone, text
```

```ts
// TypeScript                                    (Landing.tsx, lines 5-6)
import { api, supplierQuery, type Supplier } from "@/lib/api";   // "@/" means "the frontend/ folder"
import { useApp } from "./AppProvider";                          // "./" means "this same folder"
```

In TypeScript, a file must **`export`** something before another file can import it.
`export default` marks the file's main thing; you import that without `{ }`:
`import Hero from "./Hero";`.

## 12. Classes and objects (just enough)

A **class** is a template for making objects that hold data *and* have their own functions. JalSetu uses only a few.

```python
# backend/util.py, lines 8-13
class ApiError(Exception):                  # a new kind of error, based on Python's built-in Exception
    def __init__(self, message, status=400):  # __init__ runs when one is created
        super().__init__(message)           # let the parent (Exception) set itself up too
        self.message, self.status = message, status   # remember both on the object ("self" = this object)
```

## 13. Errors: raise / throw, and catching them

When something goes wrong, code can **raise** (Python) or **throw** (TypeScript) an error. That stops the
current work and jumps out until something **catches** it.

```python
# Python                                    (backend/auth.py, lines 106-110)
try:
    uid = db.execute("INSERT INTO users ...")       # try this
except sqlite3.IntegrityError:                      # if THIS kind of error happens...
    fail("This phone number is already registered. Sign in instead", 409)   # ...do this instead
```

```ts
// TypeScript                               (RequestForm.tsx, lines 55-67)
try {
  const r = await api("/orders", { ... });   // try to send the order
  setDone(...);
} catch (e) {                                // if anything went wrong...
  setErr((e as Error).message);              // ...show the error message on the form
} finally {                                  // and whatever happened...
  setBusy(false);                            // ...the button stops saying "Sending…"
}
```

## 14. Waiting for slow things: async / await (TypeScript)

Asking the server takes time (milliseconds to seconds). The page shouldn't freeze meanwhile. So:

- `api(...)` returns a **Promise**: an IOU saying "I'll have the answer later".
- `await` means "pause *this function* here until the answer arrives". The rest of the page keeps working.
- Only functions marked `async` may use `await`.

```ts
async function send() {
  const r = await api<{ id: number }>("/orders", { method: "POST", body: {...} });
  // this line runs only after the server has answered
}
```

The other way to wait is `.then(...)`, used in many places:

```ts
api<User>("/me").then(setUser).catch(...)   // "when the answer comes, give it to setUser; if it fails, ..."
```

## 15. Types (TypeScript only)

TypeScript = JavaScript + **types**. You label what kind of value each thing holds, and the editor warns you
*before* you run the code if you mix them up (like writing `user.nmae`).

```ts
// frontend/lib/api.ts, lines 3-4
export type Role = "user" | "supplier" | "admin";      // "|" means OR: a Role is one of these three texts
export type User = { id: number; name: string; phone: string; role: Role };

let price: number | null = null;     // a number, or nothing
type Props = { distance?: number };  // "?" = this field is optional (may be missing)
api<Supplier[]>("/suppliers")        // <...> fills in a type: "this call returns a list of Supplier"
```

Types **disappear** when the code runs. They exist only to catch mistakes while you write.

Python in this project doesn't use type labels. It checks values by hand instead (see `backend/util.py`).

## 16. Small symbols cheat sheet

| Symbol | Language | Meaning | Example |
|--------|----------|---------|---------|
| `?.` | TS | "if the thing on the left is empty, stop here" | `user?.role` |
| `??` | TS | "use the right side if the left is null/undefined" | `n ?? 0` |
| `??=` | TS | "set it only if it's currently empty" | `ctx ??= new AudioContext()` |
| `!!x` | TS | turn anything into true/false | `!!user` → is someone signed in? |
| `...` | TS | spread: copy everything out of a list/object | `{ ...f, ...p }` |
| `...` / `*args` | TS / Python | "and all the rest" | `const { size, ...rest } = props` |
| `=>` | TS | arrow function | `(s) => s.price` |
| `@something` | Python | a "decorator": wraps the function below in extra behaviour | `@auth("admin")` (lesson 06) |
| `<Thing />` | TSX | use a React component | `<Hero count={4} />` (lesson 09) |
| `{ }` inside TSX | TSX | "the next bit is code, not text" | `<b>{user.name}</b>` |
| `[a, b] = ...` | both | "unpacking": put the parts into separate boxes | `const [open, setOpen] = useState(false)` |
| `r"..."` | Python | raw text (backslashes kept as typed; used for regex) | `r"\D"` |
| `\d`, `\D`, `{9}` | regex | a digit, a non-digit, exactly 9 times | see lesson 05 |

---

## Quick check

1. In `const POLL_MS = 15_000;`, what is the variable's name and what's its value?
2. What's the difference between `=` and `===`?
3. What does `suppliers.filter((s) => s.availability)` give back?
4. What does `await` do?
5. In Python, how does the computer know which lines are inside an `if`?

<details><summary>Answers</summary>

1. Name `POLL_MS`, value 15000 (milliseconds, so 15 seconds).
2. `=` puts a value into a variable. `===` asks "are these equal?" and gives true or false.
3. A new list with only the suppliers whose `availability` is truthy (in stock).
4. It pauses that function until a slow task (like a server request) finishes, without freezing the page.
5. By the indentation: lines indented under the `if` belong to it.

</details>

**Next:** [03 — How the web works](03-how-the-web-works.md)
