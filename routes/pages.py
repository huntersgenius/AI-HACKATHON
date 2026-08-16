"""Jinja2 pages. Templates get ids and names only — data arrives over the API."""

from flask import Blueprint, render_template

from core.errors import NotFound
from repos import doctor_repo, patient_repo

bp = Blueprint("pages", __name__)


@bp.get("/")
def landing():
    """Role selection — standing in for a login screen."""
    return render_template(
        "landing.html",
        patients=patient_repo.list_all(),
        doctors=doctor_repo.list_all(),
    )


@bp.get("/patient/<int:pid>/chat")
def patient_chat(pid):
    patient = patient_repo.get(pid)
    if patient is None:
        raise NotFound("Bemor topilmadi.")
    return render_template("patient_chat.html", patient=patient)
