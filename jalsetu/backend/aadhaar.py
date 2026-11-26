"""Aadhaar checks: before a shop is verified, its owner sends a picture of a masked Aadhaar (only the last 4 digits
showing) and an admin looks at it. The picture is deleted as soon as the admin approves or rejects it; only the
name and the last 4 digits are kept. The full 12-digit number is never asked for or stored."""
import base64
import re
import time

from flask import Blueprint, g, jsonify, request
from werkzeug.exceptions import RequestEntityTooLarge

from . import db
from .auth import auth
from .util import body, fail, number, text

bp = Blueprint("aadhaar", __name__)

MAX_IMAGE_BYTES = 2 * 1024 * 1024  # the frontend shrinks photos to well under this before sending them
TOO_BIG = "That picture is too large. Use one under 2 MB"
STATUS = "SELECT status, name, last4, note, submitted, decided FROM aadhaar_checks WHERE supplier_id = ?"


def _image_type(data):
    """The picture's type, read from its first bytes (not from what the browser claims), or None if it isn't a
    JPEG, PNG or WebP picture."""
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def _shop_id():
    shop = db.query("SELECT id FROM suppliers WHERE user_id = ?", (g.user["id"],), one=True)
    return shop and shop["id"]


# ---------------------------------------------------------------------------
# The supplier's side

@bp.get("/my-aadhaar")
@auth("supplier")
def mine():
    """This supplier's check, without the picture: null if they haven't sent one."""
    sid = _shop_id()
    return jsonify(sid and db.query(STATUS, (sid,), one=True))


@bp.post("/my-aadhaar")
@auth("supplier")
def send():
    """Send a masked Aadhaar, or a new one in place of a rejected or still unchecked one.
    A form upload (multipart), not JSON: fields name, last4, consent=yes, and the picture as `image`."""
    request.max_content_length = MAX_IMAGE_BYTES + 64 * 1024  # this request may carry a picture; others stay small
    sid = _shop_id()
    if not sid:
        fail("Save your shop listing first", 409)
    try:  # the form is read here; a body over the limit stops right away
        form, upload = request.form, request.files.get("image")
    except RequestEntityTooLarge:
        fail(TOO_BIG, 413)
    name = text(form, "name", 80)
    last4 = re.sub(r"\D", "", text(form, "last4", 20))
    data = upload.read(MAX_IMAGE_BYTES + 1) if upload else b""
    if not name:
        fail("Enter the name exactly as it is on the Aadhaar")
    if len(last4) != 4:
        fail("Enter the last 4 digits of the Aadhaar number")
    if not data:
        fail("Choose a picture of the masked Aadhaar")
    if len(data) > MAX_IMAGE_BYTES:
        fail(TOO_BIG, 413)
    kind = _image_type(data)
    if not kind:
        fail("The picture must be a JPG, PNG or WebP image")
    if form.get("consent") != "yes":
        fail("Tick the box to agree to the Aadhaar check")

    # A new picture replaces the old row and waits for an admin again, unless the check was already approved.
    # One statement does both, so an admin approving at the same moment can't be overwritten.
    saved = db.execute("""INSERT INTO aadhaar_checks(supplier_id,name,last4,image,image_type,submitted) VALUES(?,?,?,?,?,?)
        ON CONFLICT(supplier_id) DO UPDATE SET name = excluded.name, last4 = excluded.last4, image = excluded.image,
            image_type = excluded.image_type, submitted = excluded.submitted,
            status = 'pending', note = '', decided = NULL, decided_by = NULL
        WHERE aadhaar_checks.status != 'approved'""", (sid, name, last4, data, kind, int(time.time()))).rowcount
    if not saved:
        fail("Your Aadhaar has already been checked", 409)
    return jsonify(db.query(STATUS, (sid,), one=True)), 201


# ---------------------------------------------------------------------------
# The admin's side

@bp.get("/admin/suppliers/<int:sid>/aadhaar")
@auth("admin")
def view(sid):
    """The check with its picture, as a data: URL that an <img> can show straight away."""
    row = db.query("""SELECT status, name, last4, note, submitted, decided, image, image_type
                      FROM aadhaar_checks WHERE supplier_id = ?""", (sid,), one=True)
    if not row:
        fail("This supplier hasn't sent an Aadhaar yet", 404)
    image, kind = row.pop("image"), row.pop("image_type")
    row["image"] = f"data:{kind};base64,{base64.b64encode(image).decode()}" if image else None
    reply = jsonify(row)
    reply.headers["Cache-Control"] = "no-store"  # the browser mustn't keep a copy of an ID document
    return reply


@bp.post("/admin/suppliers/<int:sid>/aadhaar")
@auth("admin")
def decide(sid):
    """Approve or reject the picture the admin looked at. Either way the picture is deleted."""
    d = body()
    decision = d.get("decision")
    note = text(d, "note", 300)
    if decision not in ("approved", "rejected"):
        fail("Choose approve or reject")
    if decision == "rejected" and not note:
        fail("Say what's wrong, so the supplier knows what to fix")
    seen = number(d, "submitted", "Picture", integer=True)  # which picture the admin was looking at
    row = db.query("SELECT status FROM aadhaar_checks WHERE supplier_id = ?", (sid,), one=True)
    if not row:
        fail("This supplier hasn't sent an Aadhaar yet", 404)
    # only a check still waiting, and only the picture the admin saw: if the supplier sent a new one meanwhile,
    # nothing changes and the admin is asked to look again
    if not db.execute("""UPDATE aadhaar_checks SET status = ?, note = ?, image = NULL, image_type = NULL,
                             decided = ?, decided_by = ?
                         WHERE supplier_id = ? AND status = 'pending' AND submitted = ?""",
                      (decision, note if decision == "rejected" else "", int(time.time()), g.user["id"], sid, seen)).rowcount:
        fail("This check has changed since you opened it. Open it again", 409)
    return jsonify(db.query(STATUS, (sid,), one=True))
