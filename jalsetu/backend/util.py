"""Request parsing, validation and small shared helpers."""
import math
import re

from flask import request


class ApiError(Exception):
    """Raised anywhere in a request; turned into {"error": message} with the given HTTP status."""

    def __init__(self, message, status=400):
        super().__init__(message)
        self.message, self.status = message, status


def fail(message, status=400):
    raise ApiError(message, status)


def body():
    """The request's JSON object, or {} when the body is missing or isn't a JSON object."""
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def text(data, key, limit):
    """A trimmed string field, cut to `limit` characters ('' when absent)."""
    value = data.get(key)
    if value is None:
        return ""
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        fail(f"'{key}' must be text")
    return str(value).strip()[:limit]


_REQUIRED = object()


def number(data, key, label, default=_REQUIRED, lo=None, hi=None, integer=False):
    value = data.get(key)
    if value is None or value == "":
        if default is _REQUIRED:
            fail(f"{label} is required")
        return default
    try:
        if isinstance(value, bool):
            raise ValueError
        n = float(value)
    except (TypeError, ValueError):
        fail(f"{label} must be a number")
    if not math.isfinite(n) or (integer and n != int(n)):
        fail(f"{label} must be a whole number" if integer else f"{label} must be a number")
    if lo is not None and hi is not None and not lo <= n <= hi:
        fail(f"{label} must be between {lo:g} and {hi:g}")
    if lo is not None and n < lo:
        fail(f"{label} must be at least {lo:g}")
    if hi is not None and n > hi:
        fail(f"{label} must be at most {hi:g}")
    return int(n) if integer else n


def normalize_phone(raw):
    """'+91 98300 11111' / '098300 11111' -> '9830011111'. None unless it is a 10-digit Indian mobile number."""
    digits = re.sub(r"\D", "", str(raw or ""))
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    return digits if re.fullmatch(r"[6-9]\d{9}", digits) else None


def query_float(name):
    """A finite float from the query string, or None."""
    value = request.args.get(name, type=float)
    return value if value is not None and math.isfinite(value) else None


def km(lat1, lng1, lat2, lng2):
    """Great-circle distance in kilometres."""
    p = math.pi / 180
    x = (math.sin((lat2 - lat1) * p / 2) ** 2
         + math.cos(lat1 * p) * math.cos(lat2 * p) * math.sin((lng2 - lng1) * p / 2) ** 2)
    return 12742 * math.asin(math.sqrt(x))
