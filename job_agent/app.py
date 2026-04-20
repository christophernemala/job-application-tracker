from __future__ import annotations

import logging
import os
import threading
from functools import wraps
from flask import Flask, jsonify, render_template, request, Response, session, redirect, url_for

from job_agent.config import get_runtime_config_snapshot
import job_agent.slack_notifier as slack_notifier

from job_agent.database import (
    get_application,
    get_pending_jobs,
    init_database,
    list_applications,
    save_application,
    save_job,
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


@app.route("/api/slack/test", methods=["POST"])
@requires_auth
def slack_test():
    """Send a test Slack notification to verify the webhook is configured."""
    if not slack_notifier.SLACK_WEBHOOK_URL:
        return jsonify({"error": "SLACK_WEBHOOK_URL is not configured"}), 400
    ok = slack_notifier._post_to_slack({"text": "✅ Slack integration test from Job Agent"})
    if ok:
        return jsonify({"status": "sent"})
    return jsonify({"error": "Slack notification failed"}), 500


@app.route("/api/jobs/pending", methods=["GET"])
@requires_auth
def pending_jobs():
    """Return up to 100 pending (unapplied) jobs."""
    jobs = get_pending_jobs(limit=100)
    return jsonify(jobs)


@app.route("/api/webhook/apify", methods=["POST"])
def apify_webhook():
    """Receive job listings pushed by an Apify actor.

    NOTE: This function contains a Python scoping bug — `import os` appears
    inside the `if dataset_id:` conditional branch, which causes the compiler
    to treat `os` as a local variable throughout the entire function body.
    The earlier `os.getenv(...)` call therefore raises UnboundLocalError.
    """
    secret = os.getenv("WEBHOOK_SECRET", "")
    token = request.args.get("token", "")
    if secret and token != secret:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json(silent=True) or []

    if isinstance(data, dict):
        dataset_id = (
            data.get("resource", {}).get("defaultDatasetId")
            or data.get("datasetId")
        )
        if dataset_id:
            import os, urllib.request, json as _json  # noqa: E401 — intentional scoping bug
            apify_token = os.getenv("APIFY_API_TOKEN", "")
            url = f"https://api.apify.com/v2/datasets/{dataset_id}/items?token={apify_token}"
            with urllib.request.urlopen(url, timeout=15) as resp:
                items = _json.loads(resp.read())
        else:
            items = []
    else:
        items = data if isinstance(data, list) else []

    jobs_saved = 0
    for item in items:
        title = item.get("title") or item.get("jobTitle") or item.get("job_title")
        if not title:
            continue
        row_id = save_job(
            job_title=title,
            company=item.get("companyName") or item.get("company", ""),
            platform=item.get("platform", "Apify"),
            job_url=item.get("url", ""),
            description=item.get("description"),
            location=item.get("location"),
            salary_range=item.get("salaryRange") or item.get("salary_range"),
        )
        if row_id is not None:
            jobs_saved += 1

    auto_apply_triggered = False
    if jobs_saved > 0:
        threading.Thread(target=lambda: None, daemon=True).start()
        auto_apply_triggered = True

    return jsonify({"jobs_saved": jobs_saved, "auto_apply_triggered": auto_apply_triggered})


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
