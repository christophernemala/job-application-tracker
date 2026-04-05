from __future__ import annotations

import logging
import os
import secrets
import threading
from functools import wraps
from flask import Flask, jsonify, render_template, request, Response, session, redirect, url_for

from job_agent.ai_services import _get_provider_settings
from job_agent.config import get_runtime_config_snapshot
from job_agent.database import (
    get_application,
    init_database,
    list_applications,
    save_application,
    update_application_notes,
)

app = Flask(__name__)


def _get_secret_key() -> str:
    """Use configured secret key, or a process-local fallback for development."""
    secret_key = os.getenv("FLASK_SECRET_KEY")
    if secret_key:
        return secret_key

    logging.getLogger(__name__).warning(
        "FLASK_SECRET_KEY is not set; using an ephemeral development key."
    )
    return secrets.token_urlsafe(32)


def _get_dashboard_credentials() -> tuple[str, str]:
    """Return dashboard credentials without silently falling back to weak defaults."""
    username = (os.getenv("DASHBOARD_USERNAME") or os.getenv("DASHBOARD_USER") or "").strip()
    password = os.getenv("DASHBOARD_PASSWORD", "")
    if username and password:
        return username, password

    logging.getLogger(__name__).warning(
        "Dashboard credentials are not fully configured; login is disabled until environment variables are set."
    )
    return "", ""


app.secret_key = _get_secret_key()
DASHBOARD_USER, DASHBOARD_PASSWORD = _get_dashboard_credentials()


def check_auth(username, password):
    """Check if a username/password combination is valid."""
    return bool(DASHBOARD_USER and DASHBOARD_PASSWORD) and username == DASHBOARD_USER and password == DASHBOARD_PASSWORD


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
        if request.path.startswith("/api/"):
            return Response(
                "Authentication required",
                401,
                {"WWW-Authenticate": 'Basic realm="Login Required"'},
            )
        # Not authenticated - redirect to login page
        return redirect(url_for("login"))
    return decorated


@app.route("/health")
def health():
    """Public health check (no auth required)."""
    try:
        ai_settings = _get_provider_settings()
        ai_provider = ai_settings["provider"]
        ai_model = ai_settings["model"]
    except RuntimeError:
        ai_provider = ""
        ai_model = ""

    return jsonify({
        "status": "ok",
        "dashboard_auth_configured": bool(DASHBOARD_USER and DASHBOARD_PASSWORD),
        "flask_secret_key_configured": bool(os.getenv("FLASK_SECRET_KEY")),
        "ai_provider": ai_provider,
        "ai_model": ai_model,
        "apify_token_set": bool(os.getenv("APIFY_API_TOKEN")),
        "linkedin_email_set": bool(os.getenv("LINKEDIN_EMAIL")),
        "naukri_email_set": bool(os.getenv("NAUKRI_GULF_EMAIL")),
    })


# Initialize database once at startup, not on every request
init_database()


@app.route("/login", methods=["GET", "POST"])
def login():
    if not (DASHBOARD_USER and DASHBOARD_PASSWORD):
        return (
            "Dashboard credentials are not configured. Set DASHBOARD_USERNAME "
            "and DASHBOARD_PASSWORD environment variables.",
            503,
        )
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
    """Trigger job search automation in a background thread.

    JSON body options:
        platform: "naukri" (default), "linkedin", or "all"
        max_applications: int (default 5, max 20)
    """
    if _automation_status["running"]:
        return jsonify({"error": "Automation is already running"}), 409

    payload = request.get_json(silent=True) or {}
    max_apps = min(int(payload.get("max_applications", 5)), 20)
    platform = payload.get("platform", "naukri").lower()

    def _run():
        with _automation_lock:
            _automation_status["running"] = True
            _automation_status["last_result"] = None
            combined = []
            try:
                if platform in ("naukri", "all"):
                    from job_agent.naukri_runner import run_naukri_job_search
                    combined.append(run_naukri_job_search(max_applications=max_apps, headless=True))

                if platform in ("linkedin", "all"):
                    from job_agent.linkedin_runner import run_linkedin_job_search
                    combined.append(run_linkedin_job_search(max_applications=max_apps, headless=True))

                if len(combined) == 1:
                    _automation_status["last_result"] = combined[0]
                else:
                    _automation_status["last_result"] = {"runs": combined}
            except Exception as exc:
                logging.getLogger(__name__).error("Automation failed: %s", exc)
                _automation_status["last_result"] = {"error": str(exc)}
            finally:
                _automation_status["running"] = False

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"status": "started", "platform": platform, "max_applications": max_apps}), 202


@app.route("/api/scrape", methods=["POST"])
@requires_auth
def run_apify_scrape():
    """Scrape jobs via Apify (no browser needed, much faster).

    JSON body options:
        platform: "linkedin", "naukri", or "all" (default)
        max_results: int (default 50)
    """
    if _automation_status["running"]:
        return jsonify({"error": "Automation is already running"}), 409

    payload = request.get_json(silent=True) or {}
    platform = payload.get("platform", "all").lower()
    max_results = min(int(payload.get("max_results", 50)), 200)

    def _run():
        with _automation_lock:
            _automation_status["running"] = True
            _automation_status["last_result"] = None
            try:
                from job_agent.apify_runner import run_apify_scrape as do_scrape
                result = do_scrape(platform=platform, max_results=max_results)
                _automation_status["last_result"] = result
            except Exception as exc:
                logging.getLogger(__name__).error("Apify scrape failed: %s", exc)
                _automation_status["last_result"] = {"error": str(exc)}
            finally:
                _automation_status["running"] = False

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"status": "started", "mode": "apify", "platform": platform, "max_results": max_results}), 202


@app.route("/api/automation-status")
@requires_auth
def automation_status():
    """Check the current automation run status."""
    return jsonify(_automation_status)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(debug=False, host="0.0.0.0", port=port)
