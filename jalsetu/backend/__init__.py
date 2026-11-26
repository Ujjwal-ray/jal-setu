"""JalSetu backend: the Flask + SQLite JSON API behind the Next.js frontend."""
import os

from flask import Flask, jsonify, send_from_directory
from werkzeug.exceptions import HTTPException

from . import admin, auth, db, orders, suppliers
from .util import ApiError

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MESSAGES = {400: "Bad request", 401: "Sign in required", 403: "Not allowed", 404: "Not found",
            405: "Method not allowed", 413: "Request too large", 500: "Something went wrong on the server"}


def create_app(config=None):
    app = Flask(__name__, static_folder=os.path.join(ROOT, "static"), static_url_path="")
    app.config.update(
        DB_PATH=os.environ.get("JALSETU_DB", os.path.join(ROOT, "jalsetu.db")),
        SEED_DEMO=os.environ.get("JALSETU_SEED", "1") != "0",  # demo accounts + suppliers in an empty database
        TOKEN_TTL=30 * 24 * 3600,                               # sign-in lasts 30 days
        MAX_CONTENT_LENGTH=64 * 1024,
        SMS_PROVIDER=os.environ.get("JALSETU_SMS", "console"),  # see sms.py
        VERIFY_PHONES=os.environ.get("JALSETU_VERIFY_PHONES", "1") != "0",  # sign-up needs the code texted to the phone
        SMS_DAILY_LIMIT=int(os.environ.get("JALSETU_SMS_DAILY_LIMIT", "200")),  # texts per 24 hours, a cap on the SMS bill
    )
    app.config.update(config or {})

    db.init_app(app)
    for module in (auth, suppliers, orders, admin):
        app.register_blueprint(module.bp, url_prefix="/api")
    app.cli.add_command(admin.create_admin)
    app.cli.add_command(admin.reset_password)

    @app.get("/api/health")
    def health():
        return jsonify(ok=True)

    @app.get("/")
    def index():  # the earlier single-file prototype UI
        return send_from_directory(app.static_folder, "index.html")

    @app.errorhandler(ApiError)
    def api_error(e):
        return jsonify(error=e.message), e.status

    @app.errorhandler(HTTPException)
    def http_error(e):  # 404s, 405s, and unhandled exceptions (as 500) all answer in JSON
        if e.code == 500:
            app.logger.error("Unhandled error", exc_info=getattr(e, "original_exception", None) or e)
        return jsonify(error=MESSAGES.get(e.code, e.name)), e.code

    return app
