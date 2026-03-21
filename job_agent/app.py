from __future__ import annotations

import logging
import os
import threading
from functools import wraps
from flask import Flask, jsonify, render_template, request, Response, session, redirect, url_for

from job_agent.config import get_runtime_config_snapshot
from job_agent.database import (
    get_application,
    init_database,
    list_applications,
    save_application,
    update_application_notes,
)

app = Flask(__name__)
# Secret key for session management - use env var or fallback
app.secret_key = os.getenv("FLASK_SECRET_KEY", "job-tracker-secret-2024")

# Dashboard credentials - defaults allow login even without env vars set
# Accept both DASHBOARD_USERNAME (Render env group) and DASHBOARD_USER (legacy)
DASHBOARD_USER = os.getenv("DASHBOARD_USERNAME") or os.getenv("DASHBOARD_USER", "admin")
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "admin123")


def check_auth(username, password):
    """Check if a username/password combination is valid."""
    return username == DASHBOARD_USER and password == DASHBOARD_PASSWORD


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # Check session-based login first
        if session.get("logged_in"):
            return f(*args, **kwargs)
        # Fall back to HTTP Basic Auth for API clients
        auth = request.authorization
        if auth and check_auth(auth.username, auth.password):
            return f(*args, **kwargs)
        # Not authenticated - redirect to login page
        return redirect(url_for("login"))
    return decorated


# Initialize database once at startup, not on every request
init_database()


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if check_auth(username, password):
            session["logged_in"] = True
            session["username"] = username
            return redirect(url_for("dashboard"))
        else:
            error = "Invalid username or password. Please try again."
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@requires_auth
def dashboard():
    applications = list_applications()
    return render_template("dashboard.html", applications=applications)


@app.route("/api/config")
@requires_auth
def runtime_config():
    """Expose non-secret runtime configuration for verification."""
    return jsonify(get_runtime_config_snapshot())


@app.route("/api/application/<int:app_id>")
@requires_auth
def get_application_details(app_id: int):
    application = get_application(app_id)
    if application:
        return jsonify(application)
    return jsonify({"error": "Application not found"}), 404


@app.route("/api/application/<int:app_id>/notes", methods=["PUT"])
@requires_auth
def save_notes(app_id: int):
    payload = request.get_json(silent=True) or {}
    notes = payload.get("notes", "")
    updated = update_application_notes(app_id, notes)
    if not updated:
        return jsonify({"error": "Application not found"}), 404
    return jsonify({"ok": True})


@app.route("/api/applications", methods=["POST"])
@requires_auth
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


_automation_lock = threading.Lock()
_automation_status = {"running": False, "last_result": None}


@app.route("/api/run-automation", methods=["POST"])
@requires_auth
def run_automation():
    """Trigger the Naukri Gulf job search automation in a background thread."""
    if _automation_status["running"]:
        return jsonify({"error": "Automation is already running"}), 409

    payload = request.get_json(silent=True) or {}
    max_apps = min(int(payload.get("max_applications", 5)), 20)

    def _run():
        with _automation_lock:
            _automation_status["running"] = True
            try:
                from job_agent.naukri_runner import run_naukri_job_search
                result = run_naukri_job_search(max_applications=max_apps, headless=True)
                _automation_status["last_result"] = result
            except Exception as exc:
                logging.getLogger(__name__).error("Automation failed: %s", exc)
                _automation_status["last_result"] = {"error": str(exc)}
            finally:
                _automation_status["running"] = False

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"status": "started", "max_applications": max_apps}), 202


@app.route("/api/automation-status")
@requires_auth
def automation_status():
    """Check the current automation run status."""
    return jsonify(_automation_status)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(debug=False, host="0.0.0.0", port=port)
