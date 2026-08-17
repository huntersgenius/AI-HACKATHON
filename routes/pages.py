"""Jinja2 pages. Templates get ids and names only — data arrives over the API."""

import os

from flask import Blueprint, current_app, render_template, send_from_directory

from core.errors import NotFound
from repos import doctor_repo, patient_repo
from services import doctor_service

bp = Blueprint("pages", __name__)


@bp.get("/sw.js")
def service_worker():
    """Served from the root path (not /static/) so its scope covers the
    whole app — push notification clicks need to find/focus any open tab."""
    return send_from_directory(
        os.path.join(current_app.root_path, "static"), "sw.js",
        mimetype="application/javascript",
    )


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


@bp.get("/doctor/<int:did>/dashboard")
def doctor_dashboard(did):
    doctor = doctor_service.get_doctor(did)  # raises NotFound in Uzbek
    return render_template("doctor_dashboard.html", doctor=doctor)


@bp.get("/doctor/patient/<int:pid>")
def doctor_patient(pid):
    patient = patient_repo.get(pid)
    if patient is None:
        raise NotFound("Bemor topilmadi.")
    doctor = doctor_repo.get(patient["doctor_id"])
    return render_template("doctor_patient.html", patient=patient, doctor=doctor)
