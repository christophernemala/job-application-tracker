from __future__ import annotations

import os
import threading
from functools import wraps

from flask import Flask, jsonify, render_template, request, session, redirect, url_for

from job_agent.config import get_runtime_config_snapshot
from job_agent.database import (
    get_application,
    init_database,
    list_applications,
    save_application,
    update_application_notes,
)

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "job-tracker-secret-2024")

DASHBOARD_USER = os.getenv("DASHBOARD_USERNAME") or os.getenv("DASHBOARD_USER", "admin")
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "admin123")

# Shared state for the background agent run
_agent_state: dict = {"running": False, "last_result": None}


def check_auth(username, password):
    return username == DASHBOARD_USER and password == DASHBOARD_PASSWORD


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get("logged_in"):
            return f(*args, **kwargs)
        auth = request.authorization
        if auth and check_auth(auth.username, auth.password):
            return f(*args, **kwargs)
        return redirect(url_for("login"))
    return decorated


# Initialize database once at startup
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
    payload = request.get_json(silent=True)
    if not payload:
        return jsonify({"error": "Request body must be JSON"}), 400

    # Validate required fields
    required = ["job_title", "company", "platform"]
    missing = [f for f in required if not str(payload.get(f, "")).strip()]
    if missing:
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400

    app_id = save_application(
        job_title=payload["job_title"].strip(),
        company=payload["company"].strip(),
        platform=payload["platform"].strip(),
        job_url=payload.get("job_url", ""),
        status=payload.get("status", "applied"),
        match_score=payload.get("match_score"),
        cover_letter=payload.get("cover_letter"),
        resume_path=payload.get("resume_version"),
        screenshot_path=payload.get("screenshot_path"),
    )
    return jsonify({"id": app_id}), 201


# ── Agent Run Endpoints ────────────────────────────────────────────────────────

def _run_agent_background(max_applications: int) -> None:
    """Run the Naukri job search in a background thread."""
    from job_agent.naukri_runner import run_naukri_job_search
    try:
        result = run_naukri_job_search(max_applications=max_applications, headless=True)
        _agent_state["last_result"] = result
    except Exception as exc:
        _agent_state["last_result"] = {"errors": [str(exc)]}
    finally:
        _agent_state["running"] = False


@app.route("/api/run-agent", methods=["POST"])
@requires_auth
def run_agent():
    """Start the Naukri Gulf auto-apply agent in a background thread."""
    if _agent_state["running"]:
        return jsonify({"error": "Agent is already running"}), 409

    payload = request.get_json(silent=True) or {}
    max_applications = int(payload.get("max_applications", 5))
    if not 1 <= max_applications <= 20:
        return jsonify({"error": "max_applications must be between 1 and 20"}), 400

    _agent_state["running"] = True
    _agent_state["last_result"] = None
    thread = threading.Thread(
        target=_run_agent_background,
        args=(max_applications,),
        daemon=True,
    )
    thread.start()
    return jsonify({
        "ok": True,
        "message": f"Agent started — will attempt up to {max_applications} applications",
    })


@app.route("/api/agent-status")
@requires_auth
def agent_status():
    """Poll agent run status and last result."""
    return jsonify({
        "running": _agent_state["running"],
        "last_result": _agent_state["last_result"],
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(debug=False, host="0.0.0.0", port=port)
