"""JalSetu backend entry point.

    python app.py                        -> http://127.0.0.1:5000
    flask --app app create-admin LOGIN   -> add an admin account
    flask --app app reset-password LOGIN -> set a new password for any account (admins included)

Environment: JALSETU_DB (database file), JALSETU_SEED=0 (no demo data), HOST, PORT, JALSETU_DEBUG=1,
JALSETU_SMS (how reset codes are texted; default "console" prints them here, see backend/sms.py).
"""
import os

from backend import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"),
            port=int(os.environ.get("PORT", 5000)),
            debug=os.environ.get("JALSETU_DEBUG") == "1")
