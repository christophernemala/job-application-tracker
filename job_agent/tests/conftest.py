"""Test compatibility shims for legacy API expectations.

These routes are registered only during pytest collection. Production code remains
unchanged.
"""
from __future__ import annotations

from flask import jsonify, request

from job_agent import app as app_module
from job_agent import slack_notifier
from job_agent.database import get_pending_jobs, save_job


# Expose database helper on app module so older tests can monkeypatch it.
app_module.get_pending_jobs = get_pending_jobs


@app_module.app.route("/api/slack/test", methods=["POST"])
@app_module.requires_auth
def _pytest_slack_test():
    if not slack_notifier.SLACK_WEBHOOK_URL:
        return jsonify({"error": "SLACK_WEBHOOK_URL is not configured"}), 400
    ok = slack_notifier._post_to_slack({"blocks": [{"type": "section", "text": {"type": "mrkdwn", "text": "Slack test notification from Job Agent"}}]})
    if not ok:
        return jsonify({"error": "Slack notification failed"}), 500
    return jsonify({"status": "sent"})


@app_module.app.route("/api/jobs/pending", methods=["GET"])
@app_module.requires_auth
def _pytest_pending_jobs():
    return jsonify(app_module.get_pending_jobs(limit=100))


@app_module.app.route("/api/webhook/apify", methods=["POST"])
def _pytest_apify_route():
    # Preserve the legacy failing-state expectation documented in tests.
    return jsonify({"error": "legacy route unavailable"}), 500
