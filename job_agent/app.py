from __future__ import annotations

import os
from flask import Flask, jsonify, render_template, request

from job_agent.config import get_runtime_config_snapshot
from job_agent.database import (
    get_application,
    init_database,
    list_applications,
    save_application,
    update_application_notes,
)

app = Flask(__name__)

# Initialize database once at startup, not on every request
init_database()


@app.route("/")
def dashboard():
    applications = list_applications()
    return render_template("dashboard.html", applications=applications)




@app.route("/api/config")
def runtime_config():
    """Expose non-secret runtime configuration for verification."""
    return jsonify(get_runtime_config_snapshot())


@app.route("/api/application/<int:app_id>")
def get_application_details(app_id: int):
    application = get_application(app_id)
    if application:
        return jsonify(application)
    return jsonify({"error": "Application not found"}), 404


@app.route("/api/application/<int:app_id>/notes", methods=["PUT"])
def save_notes(app_id: int):
    payload = request.get_json(silent=True) or {}
    notes = payload.get("notes", "")
    updated = update_application_notes(app_id, notes)
    if not updated:
        return jsonify({"error": "Application not found"}), 404
    return jsonify({"ok": True})


@app.route("/api/applications", methods=["POST"])
def create_application():
    payload = request.get_json()
    app_id = save_application(
        job_title=payload["job_title"],
        company=payload["company"],
        platform=payload["platform"],
        job_url=payload.get("job_url", ""),
        status=payload.get("status", "applied"),
        match_score=payload.get("match_score"),
        cover_letter=payload.get("cover_letter"),
        resume_path=payload.get("resume_version"),
        screenshot_path=payload.get("screenshot_path"),
    )
    return jsonify({"id": app_id}), 201


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(debug=False, host="0.0.0.0", port=port)
