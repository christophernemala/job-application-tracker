from __future__ import annotations

import os
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
from job_agent.telegram_bot import handle_update, set_webhook
import job_agent.telegram_bot as _tgbot
from job_agent.slack_notifier import notify_new_application

import secrets
import logging

_log = logging.getLogger(__name__)

app = Flask(__name__)

_secret = os.getenv("FLASK_SECRET_KEY")
if not _secret:
    _secret = secrets.token_hex(32)
    _log.warning("FLASK_SECRET_KEY not set — using a random key (sessions won't survive restarts)")
app.secret_key = _secret

DASHBOARD_USER = os.getenv("DASHBOARD_USERNAME") or os.getenv("DASHBOARD_USER", "admin")
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "")
if not DASHBOARD_PASSWORD:
    _log.error(
        "DASHBOARD_PASSWORD is not set. Set this environment variable before deploying. "
        "Login is disabled until a password is configured."
    )


def check_auth(username, password):
    if not DASHBOARD_PASSWORD:
        return False
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


# Initialize database and Telegram webhook once at startup
init_database()
set_webhook()


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
    job_title = payload["job_title"]
    company = payload["company"]
    platform = payload["platform"]
    status = payload.get("status", "applied")
    match_score = payload.get("match_score")
    app_id = save_application(
        job_title=job_title,
        company=company,
        platform=platform,
        job_url=payload.get("job_url", ""),
        status=status,
        match_score=match_score,
        cover_letter=payload.get("cover_letter"),
        resume_path=payload.get("resume_version"),
        screenshot_path=payload.get("screenshot_path"),
    )
    notify_new_application(job_title, company, platform, status, match_score)
    return jsonify({"id": app_id}), 201


@app.route("/webhook/telegram/<token>", methods=["POST"])
def telegram_webhook(token: str):
    """Receive updates from Telegram. Token in path authenticates the caller."""
    if token != _tgbot.TELEGRAM_BOT_TOKEN:
        return "", 403
    update = request.get_json(silent=True) or {}
    handle_update(update)
    return "OK", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(debug=False, host="0.0.0.0", port=port)
