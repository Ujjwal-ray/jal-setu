"""JalSetu backend: the Flask + SQLite JSON API behind the Next.js frontend."""
import os
import time

from flask import Flask, jsonify, send_from_directory
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.proxy_fix import ProxyFix

from . import aadhaar, admin, auth, db, health, orders, payments, shop_hours, suppliers
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
        PROXIES=int(os.environ.get("JALSETU_PROXIES", "0")),  # proxies in front that add X-Forwarded-For (see below)
        # paying for orders (payments.py): "off" = cash only, "demo" = pretend UPI for trying the app, "razorpay"
        PAYMENTS=os.environ.get("JALSETU_PAYMENTS", "off"),
        SERVICE_FEE=float(os.environ.get("JALSETU_SERVICE_FEE", "5")),  # JalSetu's fee in rupees, added to each order
        RAZORPAY_KEY_ID=os.environ.get("RAZORPAY_KEY_ID", ""),
        RAZORPAY_KEY_SECRET=os.environ.get("RAZORPAY_KEY_SECRET", ""),
        RAZORPAY_WEBHOOK_SECRET=os.environ.get("RAZORPAY_WEBHOOK_SECRET", ""),
    )
    app.config.update(config or {})

    # Behind a proxy (nginx, a load balancer) every request arrives from the proxy, which names the visitor in
    # an X-Forwarded-For header. Trust only the last PROXIES entries: a visitor can write anything in front of them.
    # The Next.js server doesn't count: it passes the header on without adding to it.
    if app.config["PROXIES"]:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=app.config["PROXIES"])

    db.init_app(app)
    for module in (auth, suppliers, orders, admin, aadhaar, health, shop_hours, payments):
        app.register_blueprint(module.bp, url_prefix="/api")
    app.cli.add_command(admin.create_admin)
    app.cli.add_command(admin.reset_password)
    app.extensions["jalsetu_started"] = int(time.time())  # "running since …" on the admin's Server health tab

    @app.get("/")
    def index():  # the earlier single-file prototype UI
        return send_from_directory(app.static_folder, "index.html")

    @app.errorhandler(ApiError)
    def api_error(e):
        return jsonify(error=e.message), e.status

    @app.errorhandler(HTTPException)
    def http_error(e):  # 404s, 405s, and unhandled exceptions (as 500) all answer in JSON
        if e.code == 500:
            crash = getattr(e, "original_exception", None) or e
            app.logger.error("Unhandled error", exc_info=crash)
            health.record_error(crash)  # so the admin sees it on the Server health tab
        return jsonify(error=MESSAGES.get(e.code, e.name)), e.code

    return app
