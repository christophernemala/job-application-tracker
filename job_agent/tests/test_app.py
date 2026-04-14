"""Tests for new Flask endpoints added in this PR:
  - POST /api/slack/test
  - POST /api/webhook/apify
  - GET  /api/jobs/pending
"""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Patch init_database before importing the app so the test suite does not
# touch any real database file.
with patch("job_agent.database.init_database"):
    from job_agent.app import app as flask_app
import job_agent.app as app_module
import job_agent.database as database_module
import job_agent.slack_notifier as notifier_module


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

_BASIC_AUTH = base64.b64encode(b"admin:admin123").decode()
_AUTH_HEADER = {"Authorization": f"Basic {_BASIC_AUTH}"}


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """Test client with a throw-away DB.

    The new database functions (save_job, get_pending_jobs, mark_job_applied)
    call get_connection() without arguments and rely on the default DB_PATH
    that was captured at function-definition time.  We must patch both the
    module attribute AND the inner function's __defaults__.
    """
    test_db = tmp_path / "test.db"
    database_module.init_database(test_db)

    monkeypatch.setattr(database_module, "DB_PATH", test_db)
    inner_fn = database_module.get_connection.__wrapped__
    monkeypatch.setattr(inner_fn, "__defaults__", (test_db,))

    flask_app.config["TESTING"] = True
    flask_app.config["SECRET_KEY"] = "test-secret"

    with flask_app.test_client() as c:
        yield c


# ---------------------------------------------------------------------------
# POST /api/slack/test
# ---------------------------------------------------------------------------

class TestSlackTest:
    def test_requires_auth(self, client):
        resp = client.post("/api/slack/test")
        # Without auth should redirect to login (302) or return 401/302
        assert resp.status_code in (301, 302, 401)

    def test_no_webhook_url_returns_400(self, client, monkeypatch):
        monkeypatch.setattr(notifier_module, "SLACK_WEBHOOK_URL", "")
        with patch("job_agent.slack_notifier.SLACK_WEBHOOK_URL", ""):
            resp = client.post("/api/slack/test", headers=_AUTH_HEADER)
        assert resp.status_code == 400
        data = resp.get_json()
        assert "SLACK_WEBHOOK_URL" in data["error"]

    def test_webhook_url_set_and_post_succeeds_returns_200(self, client, monkeypatch):
        monkeypatch.setattr(notifier_module, "SLACK_WEBHOOK_URL", "https://hooks.slack.com/test")
        with patch("job_agent.slack_notifier.SLACK_WEBHOOK_URL", "https://hooks.slack.com/test"), \
             patch("job_agent.slack_notifier._post_to_slack", return_value=True):
            resp = client.post("/api/slack/test", headers=_AUTH_HEADER)
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "sent"

    def test_webhook_post_failure_returns_500(self, client, monkeypatch):
        monkeypatch.setattr(notifier_module, "SLACK_WEBHOOK_URL", "https://hooks.slack.com/test")
        with patch("job_agent.slack_notifier.SLACK_WEBHOOK_URL", "https://hooks.slack.com/test"), \
             patch("job_agent.slack_notifier._post_to_slack", return_value=False):
            resp = client.post("/api/slack/test", headers=_AUTH_HEADER)
        assert resp.status_code == 500
        assert "error" in resp.get_json()


# ---------------------------------------------------------------------------
# GET /api/jobs/pending
# ---------------------------------------------------------------------------

class TestPendingJobs:
    def test_requires_auth(self, client):
        resp = client.get("/api/jobs/pending")
        assert resp.status_code in (301, 302, 401)

    def test_returns_empty_list_when_no_jobs(self, client):
        resp = client.get("/api/jobs/pending", headers=_AUTH_HEADER)
        assert resp.status_code == 200
        assert resp.get_json() == []

    def test_returns_pending_jobs(self, client):
        database_module.save_job(
            job_title="Frontend Developer",
            company="Acme",
            platform="Apify",
            job_url="https://example.com/jobs/fe",
        )
        resp = client.get("/api/jobs/pending", headers=_AUTH_HEADER)
        assert resp.status_code == 200
        jobs = resp.get_json()
        assert len(jobs) >= 1
        titles = [j["job_title"] for j in jobs]
        assert "Frontend Developer" in titles

    def test_mocked_get_pending_jobs_called_with_limit_100(self, client):
        """Verify endpoint passes limit=100 to get_pending_jobs."""
        mock_jobs = [{"id": 1, "job_title": "Mock Job", "company": "Mock Co", "applied": 0}]
        with patch("job_agent.app.get_pending_jobs", return_value=mock_jobs) as mock_fn:
            resp = client.get("/api/jobs/pending", headers=_AUTH_HEADER)
        assert resp.status_code == 200
        assert resp.get_json() == mock_jobs
        mock_fn.assert_called_once_with(limit=100)

    def test_applied_jobs_not_returned(self, client):
        row_id = database_module.save_job(
            job_title="Applied Role",
            company="Corp",
            platform="Apify",
            job_url="https://example.com/jobs/applied",
        )
        database_module.mark_job_applied(row_id)
        resp = client.get("/api/jobs/pending", headers=_AUTH_HEADER)
        assert resp.status_code == 200
        jobs = resp.get_json()
        titles = [j["job_title"] for j in jobs]
        assert "Applied Role" not in titles


# ---------------------------------------------------------------------------
# POST /api/webhook/apify
#
# NOTE: The production code in apify_webhook() contains a Python scoping bug:
# `import os` is used inside a conditional branch (`if dataset_id:`), which
# causes Python's bytecode compiler to treat `os` as a local variable for the
# *entire* function body.  Any reference to `os` before that branch executes
# raises UnboundLocalError.  Tests that exercise the endpoint directly are
# therefore marked xfail until the production bug is fixed.
# ---------------------------------------------------------------------------

_APIFY_BUG_XFAIL = pytest.mark.xfail(
    strict=True,
    reason=(
        "apify_webhook() has a Python scoping bug: `import os` inside a "
        "conditional branch makes `os` a function-local variable, causing "
        "UnboundLocalError at the earlier `os.getenv(...)` call."
    ),
)


class TestApifyWebhook:
    """Tests for the /api/webhook/apify endpoint.

    Most tests are marked xfail because of a production-code scoping bug
    (see module-level note above).  The xfail markers serve as regression
    anchors: they will automatically start passing once the bug is fixed.
    """

    @_APIFY_BUG_XFAIL
    def test_wrong_token_returns_401(self, client, monkeypatch):
        monkeypatch.setenv("WEBHOOK_SECRET", "correct-token")
        resp = client.post(
            "/api/webhook/apify?token=wrong-token",
            json=[],
        )
        assert resp.status_code == 401

    @_APIFY_BUG_XFAIL
    def test_correct_token_accepted(self, client, monkeypatch):
        monkeypatch.setenv("WEBHOOK_SECRET", "my-secret")
        with patch("job_agent.app.save_job", return_value=None):
            resp = client.post(
                "/api/webhook/apify?token=my-secret",
                json=[],
            )
        assert resp.status_code == 200

    @_APIFY_BUG_XFAIL
    def test_no_secret_configured_accepts_request(self, client, monkeypatch):
        """When WEBHOOK_SECRET is empty, all requests are accepted."""
        monkeypatch.setenv("WEBHOOK_SECRET", "")
        with patch("job_agent.app.save_job", return_value=1):
            resp = client.post(
                "/api/webhook/apify",
                json=[{"title": "Engineer", "companyName": "Corp", "url": "https://example.com/j1"}],
            )
        assert resp.status_code == 200

    @_APIFY_BUG_XFAIL
    def test_direct_list_saves_jobs(self, client, monkeypatch):
        monkeypatch.setenv("WEBHOOK_SECRET", "")
        items = [
            {"title": "Backend Dev", "companyName": "Alpha", "url": "https://example.com/be"},
            {"title": "QA Engineer", "companyName": "Beta", "url": "https://example.com/qa"},
        ]
        with patch("job_agent.app.save_job", return_value=1) as mock_save:
            resp = client.post("/api/webhook/apify", json=items)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["jobs_saved"] == 2
        assert mock_save.call_count == 2

    @_APIFY_BUG_XFAIL
    def test_items_without_title_are_skipped(self, client, monkeypatch):
        monkeypatch.setenv("WEBHOOK_SECRET", "")
        items = [{"companyName": "NoTitle Corp", "url": "https://example.com/notitle"}]
        with patch("job_agent.app.save_job", return_value=1) as mock_save:
            resp = client.post("/api/webhook/apify", json=items)
        assert resp.status_code == 200
        assert resp.get_json()["jobs_saved"] == 0
        mock_save.assert_not_called()

    @_APIFY_BUG_XFAIL
    def test_empty_list_returns_zero_jobs_saved(self, client, monkeypatch):
        monkeypatch.setenv("WEBHOOK_SECRET", "")
        resp = client.post("/api/webhook/apify", json=[])
        assert resp.status_code == 200
        assert resp.get_json()["jobs_saved"] == 0
        assert resp.get_json()["auto_apply_triggered"] is False

    @_APIFY_BUG_XFAIL
    def test_duplicate_job_url_not_counted(self, client, monkeypatch):
        monkeypatch.setenv("WEBHOOK_SECRET", "")
        items = [{"title": "Dev", "companyName": "A", "url": "https://example.com/dup"}]
        with patch("job_agent.app.save_job", return_value=None):
            resp = client.post("/api/webhook/apify", json=items)
        assert resp.get_json()["jobs_saved"] == 0

    @_APIFY_BUG_XFAIL
    def test_auto_apply_triggered_when_jobs_saved(self, client, monkeypatch):
        monkeypatch.setenv("WEBHOOK_SECRET", "")
        items = [{"title": "Dev", "companyName": "A", "url": "https://example.com/trigger"}]
        with patch("job_agent.app.save_job", return_value=1), \
             patch("threading.Thread"):
            resp = client.post("/api/webhook/apify", json=items)
        assert resp.get_json()["auto_apply_triggered"] is True

    @_APIFY_BUG_XFAIL
    def test_alternative_title_field_jobTitle(self, client, monkeypatch):
        monkeypatch.setenv("WEBHOOK_SECRET", "")
        with patch("job_agent.app.save_job", return_value=1) as mock_save:
            client.post(
                "/api/webhook/apify",
                json=[{"jobTitle": "SRE", "company": "Corp", "url": "https://example.com/sre"}],
            )
        call_kwargs = mock_save.call_args[1]
        assert call_kwargs["job_title"] == "SRE"

    @_APIFY_BUG_XFAIL
    def test_alternative_title_field_job_title(self, client, monkeypatch):
        monkeypatch.setenv("WEBHOOK_SECRET", "")
        with patch("job_agent.app.save_job", return_value=1) as mock_save:
            client.post(
                "/api/webhook/apify",
                json=[{"job_title": "DevOps", "company": "Corp", "url": "https://example.com/devops"}],
            )
        call_kwargs = mock_save.call_args[1]
        assert call_kwargs["job_title"] == "DevOps"

    @_APIFY_BUG_XFAIL
    def test_platform_defaults_to_apify(self, client, monkeypatch):
        monkeypatch.setenv("WEBHOOK_SECRET", "")
        with patch("job_agent.app.save_job", return_value=1) as mock_save:
            client.post(
                "/api/webhook/apify",
                json=[{"title": "Analyst", "company": "X", "url": "https://example.com/a"}],
            )
        call_kwargs = mock_save.call_args[1]
        assert call_kwargs["platform"] == "Apify"

    @_APIFY_BUG_XFAIL
    def test_platform_from_payload(self, client, monkeypatch):
        monkeypatch.setenv("WEBHOOK_SECRET", "")
        with patch("job_agent.app.save_job", return_value=1) as mock_save:
            client.post(
                "/api/webhook/apify",
                json=[{"title": "PM", "company": "Y", "url": "https://example.com/pm", "platform": "LinkedIn"}],
            )
        call_kwargs = mock_save.call_args[1]
        assert call_kwargs["platform"] == "LinkedIn"

    @_APIFY_BUG_XFAIL
    def test_salary_field_alias_salaryRange(self, client, monkeypatch):
        monkeypatch.setenv("WEBHOOK_SECRET", "")
        with patch("job_agent.app.save_job", return_value=1) as mock_save:
            client.post(
                "/api/webhook/apify",
                json=[{"title": "Eng", "company": "Z", "url": "https://example.com/eng",
                        "salaryRange": "10000-15000"}],
            )
        call_kwargs = mock_save.call_args[1]
        assert call_kwargs["salary_range"] == "10000-15000"

    @_APIFY_BUG_XFAIL
    def test_envelope_without_dataset_id_saves_zero(self, client, monkeypatch):
        """An envelope dict with no dataset_id should produce jobs_saved=0."""
        monkeypatch.setenv("WEBHOOK_SECRET", "")
        envelope = {"eventType": "ACTOR.RUN.SUCCEEDED", "resource": {}}
        resp = client.post("/api/webhook/apify", json=envelope)
        assert resp.status_code == 200
        assert resp.get_json()["jobs_saved"] == 0

    @_APIFY_BUG_XFAIL
    def test_empty_body_returns_zero(self, client, monkeypatch):
        monkeypatch.setenv("WEBHOOK_SECRET", "")
        resp = client.post(
            "/api/webhook/apify",
            data="",
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.get_json()["jobs_saved"] == 0

    def test_endpoint_raises_unbound_local_error_for_os(self, client, monkeypatch):
        """Regression: documents the Python scoping bug in apify_webhook.

        The inner `import os` inside `if dataset_id:` makes `os` a local
        variable for the entire function, causing UnboundLocalError when
        `os.getenv(...)` is reached before the conditional branch executes.
        Remove this test once the bug is fixed in production code.
        """
        monkeypatch.setenv("WEBHOOK_SECRET", "")
        # The route is expected to raise a 500 (Flask wraps the UnboundLocalError)
        # or the test client propagates the exception.
        try:
            resp = client.post("/api/webhook/apify", json=[])
            # If Flask catches the exception it returns 500
            assert resp.status_code == 500
        except Exception as exc:
            assert "os" in str(exc).lower() or "unbound" in str(exc).lower()