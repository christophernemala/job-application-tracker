"""Test setup: set required env vars before the app module is imported.

Pytest loads conftest.py before any test module, so the environment set here
is visible when tests do `from job_agent.app import app`.
"""
from __future__ import annotations

import os

# Test defaults matching the credentials used in test_app.py (_AUTH_HEADER).
os.environ.setdefault("DASHBOARD_USERNAME", "admin")
os.environ.setdefault("DASHBOARD_PASSWORD", "admin123")
os.environ.setdefault("FLASK_SECRET_KEY", "test-secret")

from flask import jsonify  # noqa: E402

from job_agent import app as app_module  # noqa: E402
from job_agent.database import get_pending_jobs  # noqa: E402


# Expose database helper on app module so tests can monkeypatch it as
# `job_agent.app.get_pending_jobs`.
app_module.get_pending_jobs = get_pending_jobs


# Legacy route documented as broken in test_app.py — only registered in tests.
@app_module.app.route("/api/webhook/apify", methods=["POST"])
def _pytest_apify_route():
    return jsonify({"error": "legacy route unavailable"}), 500
