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
import job_agent.ats_optimizer as ats

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


@app.route("/api/ats/provider", methods=["GET"])
def ats_provider():
    """Return which AI provider is currently active."""
    provider = ats.active_provider()
    models = {"anthropic": "claude-opus-4-6", "openai": "gpt-4o", "groq": "llama-3.3-70b-versatile"}
    return jsonify({
        "provider": provider,
        "model": models.get(provider, "unknown"),
        "configured": provider != "none",
    })


# ---------------------------------------------------------------------------
# ATS Optimizer API endpoints
# ---------------------------------------------------------------------------

def _ats_route(func_name: str, payload: dict) -> tuple:
    """Shared error wrapper for ATS endpoints."""
    try:
        fn = getattr(ats, func_name)
        result = fn(**payload)
        return jsonify({"ok": True, "result": result}), 200
    except RuntimeError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"ok": False, "error": f"ATS error: {str(e)}"}), 500


@app.route("/api/ats/parse-jd", methods=["POST"])
def ats_parse_jd():
    """Parse a job description and extract structured requirements."""
    body = request.get_json(silent=True) or {}
    jd = body.get("jd_text", "").strip()
    if not jd:
        return jsonify({"ok": False, "error": "jd_text is required"}), 400
    return _ats_route("parse_job_description", {"jd_text": jd})


@app.route("/api/ats/score", methods=["POST"])
def ats_score():
    """Score resume-to-JD alignment."""
    body = request.get_json(silent=True) or {}
    resume = body.get("resume_text", "").strip()
    jd = body.get("jd_text", "").strip()
    if not resume or not jd:
        return jsonify({"ok": False, "error": "resume_text and jd_text are required"}), 400
    return _ats_route("score_alignment", {"resume_text": resume, "jd_text": jd})


@app.route("/api/ats/gaps", methods=["POST"])
def ats_gaps():
    """Analyze skill gaps and suggest learning paths."""
    body = request.get_json(silent=True) or {}
    resume = body.get("resume_text", "").strip()
    jd = body.get("jd_text", "").strip()
    if not resume or not jd:
        return jsonify({"ok": False, "error": "resume_text and jd_text are required"}), 400
    return _ats_route("analyze_skill_gaps", {"resume_text": resume, "jd_text": jd})


@app.route("/api/ats/rewrite-bullets", methods=["POST"])
def ats_rewrite_bullets():
    """Rewrite resume bullet points for a specific role."""
    body = request.get_json(silent=True) or {}
    bullets = body.get("bullets", [])
    jd_context = body.get("jd_context", "").strip()
    candidate_context = body.get("candidate_context", "")
    if not bullets or not jd_context:
        return jsonify({"ok": False, "error": "bullets and jd_context are required"}), 400
    return _ats_route("rewrite_bullets", {
        "bullets": bullets,
        "jd_context": jd_context,
        "candidate_context": candidate_context,
    })


@app.route("/api/ats/resume", methods=["POST"])
def ats_resume():
    """Generate a full ATS-optimized resume in plain text."""
    body = request.get_json(silent=True) or {}
    resume_data = body.get("resume_data", {})
    jd = body.get("jd_text", "").strip()
    target_role = body.get("target_role", "").strip()
    if not resume_data or not jd or not target_role:
        return jsonify({"ok": False, "error": "resume_data, jd_text, and target_role are required"}), 400
    return _ats_route("generate_ats_resume", {
        "resume_data": resume_data,
        "jd_text": jd,
        "target_role": target_role,
        "target_company": body.get("target_company", ""),
    })


@app.route("/api/ats/cover-letter", methods=["POST"])
def ats_cover_letter():
    """Generate a targeted cover letter from real experience."""
    body = request.get_json(silent=True) or {}
    resume_text = body.get("resume_text", "").strip()
    jd = body.get("jd_text", "").strip()
    company = body.get("company_name", "").strip()
    role = body.get("role_title", "").strip()
    if not resume_text or not jd or not company or not role:
        return jsonify({"ok": False, "error": "resume_text, jd_text, company_name, and role_title are required"}), 400
    return _ats_route("generate_cover_letter", {
        "resume_text": resume_text,
        "jd_text": jd,
        "company_name": company,
        "role_title": role,
        "candidate_name": body.get("candidate_name", ""),
        "hiring_manager": body.get("hiring_manager", ""),
    })


@app.route("/api/ats/linkedin", methods=["POST"])
def ats_linkedin():
    """Generate optimized LinkedIn sections."""
    body = request.get_json(silent=True) or {}
    profile_data = body.get("profile_data", {})
    target_role = body.get("target_role", "").strip()
    if not profile_data or not target_role:
        return jsonify({"ok": False, "error": "profile_data and target_role are required"}), 400
    return _ats_route("optimize_linkedin", {
        "profile_data": profile_data,
        "target_role": target_role,
        "target_industry": body.get("target_industry", ""),
    })


@app.route("/api/ats/resume-variant", methods=["POST"])
def ats_resume_variant():
    """Generate role-family-specific resume variant guidance."""
    body = request.get_json(silent=True) or {}
    resume_data = body.get("resume_data", {})
    jd = body.get("jd_text", "").strip()
    job_family = body.get("job_family", "").strip()
    if not resume_data or not jd or not job_family:
        return jsonify({"ok": False, "error": "resume_data, jd_text, and job_family are required"}), 400
    return _ats_route("generate_resume_variant", {
        "resume_data": resume_data,
        "jd_text": jd,
        "job_family": job_family,
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(debug=False, host="0.0.0.0", port=port)
