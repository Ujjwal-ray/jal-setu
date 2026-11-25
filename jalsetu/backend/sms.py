"""Text messages (password-reset codes).

No SMS provider is connected yet, so JALSETU_SMS defaults to "console": each message is written to the
server log, which is the terminal running `python app.py`. To text real phones, sign up with an SMS
provider (in India the sender and message template must also be DLT-registered), add it to send()
below, and set JALSETU_SMS to its name.
"""
from flask import current_app


def send(phone, message):
    """Send `message` to a 10-digit Indian mobile number. Returns how it went out: "sms" or "console"."""
    provider = current_app.config["SMS_PROVIDER"]
    if provider == "console":
        current_app.logger.warning("SMS to %s: %s", phone, message)
        return "console"
    raise RuntimeError(f"No SMS provider called {provider!r} is set up (JALSETU_SMS)")
