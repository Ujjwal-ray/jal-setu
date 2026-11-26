# JalSetu prototype

Flask + SQLite backend (`app.py`) with a Next.js frontend (`frontend/`).
The Next.js app proxies every `/api/*` call to Flask, so the browser only talks to one origin.

## Run it (two terminals)

    # 1 — backend (port 5000)
    pip install -r requirements.txt
    python app.py

    # 2 — frontend (port 3000)
    cd frontend
    npm install
    npm run dev          # open http://localhost:3000

Point the frontend at a backend somewhere else with `JALSETU_API=http://host:port npm run dev`.

Demo logins: customer 9000000001 / demo123 | supplier 9000000100 / supplier123 | admin / admin123
Delete `jalsetu.db` to reset seed data.

## Phone codes: sign-up and forgotten passwords

JalSetu texts a 6-digit code to prove a person holds their phone number. A code is valid for 15 minutes and allows 5 wrong tries, and each number can ask for 3 codes per hour. No SMS provider is connected yet, so codes are printed in the terminal running `python app.py`. To text real phones, add a provider in `backend/sms.py` and set `JALSETU_SMS`.

- **Sign-up:** *Create an account* texts a code; the account is created only once the code is entered. To let people sign up without a code (for example, when the site is online before an SMS provider is set up), set `JALSETU_VERIFY_PHONES=0`.
- **Forgotten password, self-service:** Sign in → *Forgot password?* texts a code.
- **Forgotten password, admin help:** someone who can't get the SMS calls JalSetu. After checking it's them, an admin opens *Password help* on `/admin`, creates a code and reads it out. They enter it under *Forgot password? → I already have a code*.
- **Admins:** `flask --app app reset-password LOGIN` on the server.

Setting a new password signs the account out on every other device. At most `JALSETU_SMS_DAILY_LIMIT` texts (default 200) go out in any 24 hours, which caps the SMS bill if someone floods the forms.

## Opening and closing the shop

Every day a supplier opens their shop from the dashboard when work starts and closes it when they finish. Both times they type their password again and say whether they have jars in stock. That answer becomes the stock customers see.

- Customers still see a closed shop, marked *Closed now*, but they can't send it a request (the server refuses too). Open shops are listed first.
- A shop that is still open at midnight (India time) closes by itself. The supplier is told the next morning, and the admin's *Suppliers* tab shows how many nights each shop was left open in the last week, next to today's opening and closing times.
- A wrong password here counts toward the same 5-tries pause as signing in.
- Only verified shops can open. During the day, a supplier who runs out can still change *Stock* in their listing.
- To try it locally, sign in as a demo supplier (for example `9000000100` / `supplier123`) and press *Open shop*. Until then, every demo shop shows as closed.

## Server health

- **`/api/health`** answers `{"ok": true}` when the backend and its database work, and `503 {"ok": false}` when they don't. Called through the website (`https://your-site/api/health`), it checks the Next.js server, Flask and the database in one go.
- **Admin → Server health** lists the database, disk space, crashed requests (kept 7 days, without request bodies), the SMS budget, and risky settings such as the demo admin password or debug mode. While the dashboard is open, a red bar appears if the server stops answering, and an orange bar if a check says *Fix now*.
- **Alerts when nobody is watching:** once the site is online, add an HTTP monitor in an uptime service (for example UptimeRobot or Better Stack) for `https://your-site/api/health`. Have it alert you by SMS or e-mail when the address doesn't answer 200. A stopped server can't send its own alert, so this has to come from outside.

## Supplier Aadhaar check

Before an admin can verify a shop, its owner sends a picture of a **masked Aadhaar** (the version from the myAadhaar website that shows only the last 4 digits) from the supplier dashboard. The admin checks it under *Verification → Check Aadhaar*, then approves or rejects it with a reason the supplier sees. The admin can verify the shop only after approving the Aadhaar.

- The full 12-digit Aadhaar number is never asked for or stored. The picture stays in the database only until the admin decides; after that, only the name and last 4 digits are kept.
- The supplier must tick a consent box before sending. The browser shrinks the photo to about 1600 pixels, which also removes hidden details such as where it was taken. The server accepts JPG, PNG or WebP up to 2 MB.
- Shops verified before this check existed stay visible. If an admin unverifies one, it needs an approved Aadhaar to be verified again.
- An admin compares the picture by eye; it isn't checked against UIDAI. Before going live, check the current UIDAI rules and the Digital Personal Data Protection Act for collecting Aadhaar details.

## Limits on repeated tries

These counts are kept in the database, so restarting the server doesn't reset them.

| What | Limit |
|------|-------|
| Wrong passwords for one account | 5 in 5 minutes, then signing in to it pauses |
| Wrong passwords from one internet address, for any accounts | 20 in 15 minutes |
| Sign-ups from one internet address | 10 per hour |
| Forgot-password texts from one internet address | 10 per hour |

The limits per internet address need the visitor's real address. Through the Next.js server every request reaches Flask from `127.0.0.1`, so in the local setup those three limits are off (the server logs a warning once). In production, put a proxy that adds an `X-Forwarded-For` header (nginx, Caddy, a load balancer) in front of the site, and set `JALSETU_PROXIES` to the number of such proxies, usually `1`. Don't set it without such a proxy: visitors could then write any address they like into that header.

## Pages

| Route        | Who        | What |
|--------------|------------|------|
| `/`          | everyone   | Hero, quick delivery request (underwater form), nearby-supplier slider + map with filters, how it works, delivery types, verification certificates |
| `/requests`  | signed in  | Your requests with a status tracker; cancel a pending one, rate after delivery |
| `/supplier`  | suppliers  | Edit listing (price, delivery charge, stock, map pin) and move incoming requests through accepted → out for delivery → delivered |
| `/admin`     | admin      | Verify or unverify suppliers (only verified ones are shown to customers), resolve problem reports, create password-reset codes |

## Artwork

Every background and illustration in `frontend/public/img/` is generated by scripts. No third-party images are used.

    python tools/make_art.py    # hero.jpg, snow.jpg, underwater.jpg, wave.png (procedural 3-D terrain, water)
    python tools/make_svg.py    # jar, water cooler, delivery van, six "how it works" scenes

Needs `numpy` and `Pillow` for `make_art.py`.

`static/index.html` is the earlier single-file prototype UI; Flask still serves it at http://localhost:5000.
