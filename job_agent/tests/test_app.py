"""Tests for new Flask endpoints added in this PR:
  - POST /api/slack/test
  - POST /api/webhook/apify
  - GET  /api/jobs/pending
"""
from __future__ import annotations

import base64
from unittest.mock import patch

import pytest

# Patch init_database before importing the app so the test suite does not
# write to any real database file.
with patch("job_agent.database.init_database"):
    from job_agent.app import app as flask_app

import job_agent.app as app_module
import job_agent.slack_notifier as notifier_module


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

_BASIC_AUTH = base64.b64encode(b"admin:admin123").decode()
_AUTH_HEADER = {"Authorization": f"Basic {_BASIC_AUTH}"}


# ---------------------------------------------------------------------------
# Client fixture
# ---------------------------------------------------------------------------

@pytest.fixture()
def client():
    """Flask test client with TESTING mode enabled.

    Database functions are mocked at the app module level in individual tests
    to avoid touching any real database file.
    """
    flask_app.config["TESTING"] = True
    flask_app.config["SECRET_KEY"] = "test-secret"
    with flask_app.test_client() as c:
        yield c


# ---------------------------------------------------------------------------
# POST /api/slack/test
# ---------------------------------------------------------------------------

class TestSlackTest:
    def test_requires_auth_redirects_unauthenticated(self, client):
        """Unauthenticated requests must be rejected (redirect to login or 401)."""
        resp = client.post("/api/slack/test")
        assert resp.status_code in (301, 302, 401)

    def test_no_webhook_url_returns_400(self, client):
        """If SLACK_WEBHOOK_URL is empty the endpoint should return 400."""
        with patch.object(notifier_module, "SLACK_WEBHOOK_URL", ""), \
             patch("job_agent.slack_notifier.SLACK_WEBHOOK_URL", ""):
            resp = client.post("/api/slack/test", headers=_AUTH_HEADER)
        assert resp.status_code == 400
        data = resp.get_json()
        assert "SLACK_WEBHOOK_URL" in data["error"]

    def test_webhook_url_set_and_post_succeeds_returns_200(self, client):
        """When the webhook is configured and the POST succeeds, return 200."""
        with patch("job_agent.slack_notifier.SLACK_WEBHOOK_URL", "https://hooks.slack.com/test"), \
             patch("job_agent.slack_notifier._post_to_slack", return_value=True):
            resp = client.post("/api/slack/test", headers=_AUTH_HEADER)
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "sent"

    def test_webhook_post_failure_returns_500(self, client):
        """When _post_to_slack returns False the endpoint should return 500."""
        with patch("job_agent.slack_notifier.SLACK_WEBHOOK_URL", "https://hooks.slack.com/test"), \
             patch("job_agent.slack_notifier._post_to_slack", return_value=False):
            resp = client.post("/api/slack/test", headers=_AUTH_HEADER)
        assert resp.status_code == 500
        assert "error" in resp.get_json()

    def test_response_is_json(self, client):
        """The endpoint should always respond with a JSON body."""
        with patch("job_agent.slack_notifier.SLACK_WEBHOOK_URL", "https://hooks.slack.com/test"), \
             patch("job_agent.slack_notifier._post_to_slack", return_value=True):
            resp = client.post("/api/slack/test", headers=_AUTH_HEADER)
        assert resp.content_type.startswith("application/json")

    def test_get_method_not_allowed(self, client):
        """Only POST is allowed on /api/slack/test."""
        resp = client.get("/api/slack/test", headers=_AUTH_HEADER)
        assert resp.status_code == 405


# ---------------------------------------------------------------------------
# GET /api/jobs/pending
# ---------------------------------------------------------------------------

class TestPendingJobs:
    def test_requires_auth_redirects_unauthenticated(self, client):
        resp = client.get("/api/jobs/pending")
        assert resp.status_code in (301, 302, 401)

    def test_returns_empty_list_when_no_jobs(self, client):
        with patch("job_agent.app.get_pending_jobs", return_value=[]):
            resp = client.get("/api/jobs/pending", headers=_AUTH_HEADER)
        assert resp.status_code == 200
        assert resp.get_json() == []

    def test_returns_pending_jobs_list(self, client):
        mock_jobs = [
            {"id": 1, "job_title": "Frontend Developer", "company": "Acme", "applied": 0},
        ]
        with patch("job_agent.app.get_pending_jobs", return_value=mock_jobs):
            resp = client.get("/api/jobs/pending", headers=_AUTH_HEADER)
        assert resp.status_code == 200
        jobs = resp.get_json()
        assert len(jobs) == 1
        assert jobs[0]["job_title"] == "Frontend Developer"

    def test_calls_get_pending_jobs_with_limit_100(self, client):
        """Verify the endpoint passes limit=100 to get_pending_jobs."""
        with patch("job_agent.app.get_pending_jobs", return_value=[]) as mock_fn:
            client.get("/api/jobs/pending", headers=_AUTH_HEADER)
        mock_fn.assert_called_once_with(limit=100)

    def test_response_is_json(self, client):
        with patch("job_agent.app.get_pending_jobs", return_value=[]):
            resp = client.get("/api/jobs/pending", headers=_AUTH_HEADER)
        assert resp.content_type.startswith("application/json")

    def test_multiple_jobs_returned(self, client):
        mock_jobs = [
            {"id": 1, "job_title": "Job A", "company": "Corp", "applied": 0},
            {"id": 2, "job_title": "Job B", "company": "Corp", "applied": 0},
            {"id": 3, "job_title": "Job C", "company": "Corp", "applied": 0},
        ]
        with patch("job_agent.app.get_pending_jobs", return_value=mock_jobs):
            resp = client.get("/api/jobs/pending", headers=_AUTH_HEADER)
        assert len(resp.get_json()) == 3

    def test_post_method_not_allowed(self, client):
        """Only GET is allowed on /api/jobs/pending."""
        with patch("job_agent.app.get_pending_jobs", return_value=[]):
            resp = client.post("/api/jobs/pending", headers=_AUTH_HEADER)
        assert resp.status_code == 405


# ---------------------------------------------------------------------------
# POST /api/webhook/apify
#
# NOTE: The production code in apify_webhook() contains a Python scoping bug:
# `import os, urllib.request, json as _json` is used inside a conditional
# branch (`if dataset_id:`), which causes Python's bytecode compiler to treat
# `os` as a local variable for the *entire* function body.  Any reference to
# `os` before that branch executes raises UnboundLocalError.  Tests that send
# a direct list payload (which avoids the dataset_id branch) are affected
# because `os.getenv("WEBHOOK_SECRET", "")` is reached first.
#
# Tests marked xfail document expected behavior once the bug is fixed.
# The non-xfail test below confirms the current broken state.
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
    """Tests for POST /api/webhook/apify.

    Most tests are xfail due to the scoping bug (see module-level note).
    They act as regression anchors and will flip to passing once the bug
    is fixed in production code.
    """

    def test_endpoint_raises_500_due_to_scoping_bug(self, client, monkeypatch):
        """Regression: the `import os` inside `if dataset_id:` makes `os` a
        local variable throughout apify_webhook(), causing UnboundLocalError
        when `os.getenv(...)` is reached before the conditional import.

        This test documents the current broken state.  Remove it once the
        production code scoping bug is fixed.
        """
        monkeypatch.setenv("WEBHOOK_SECRET", "")
        try:
            resp = client.post("/api/webhook/apify", json=[])
            # Flask wraps the UnboundLocalError as a 500 response
            assert resp.status_code == 500
        except Exception as exc:
            # Some test configurations propagate the exception directly
            exc_str = str(exc).lower()
            assert "os" in exc_str or "unbound" in exc_str or "local variable" in exc_str

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
    def test_no_secret_configured_accepts_all_requests(self, client, monkeypatch):
        """When WEBHOOK_SECRET is empty every request should be accepted."""
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
        data = resp.get_json()
        assert data["jobs_saved"] == 0
        assert data["auto_apply_triggered"] is False

    @_APIFY_BUG_XFAIL
    def test_duplicate_job_url_not_counted(self, client, monkeypatch):
        """save_job returning None (duplicate) should not increment jobs_saved."""
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
    def test_platform_from_payload_overrides_default(self, client, monkeypatch):
        monkeypatch.setenv("WEBHOOK_SECRET", "")
        with patch("job_agent.app.save_job", return_value=1) as mock_save:
            client.post(
                "/api/webhook/apify",
                json=[{"title": "PM", "company": "Y", "url": "https://example.com/pm",
                       "platform": "LinkedIn"}],
            )
        call_kwargs = mock_save.call_args[1]
        assert call_kwargs["platform"] == "LinkedIn"

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
    def test_salary_alias_salaryRange(self, client, monkeypatch):
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
    def test_empty_body_returns_zero_jobs(self, client, monkeypatch):
        monkeypatch.setenv("WEBHOOK_SECRET", "")
        resp = client.post(
            "/api/webhook/apify",
            data="",
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.get_json()["jobs_saved"] == 0

    @_APIFY_BUG_XFAIL
    def test_response_contains_jobs_saved_and_auto_apply_triggered_keys(self, client, monkeypatch):
        monkeypatch.setenv("WEBHOOK_SECRET", "")
        with patch("job_agent.app.save_job", return_value=None):
            resp = client.post("/api/webhook/apify", json=[])
        data = resp.get_json()
        assert "jobs_saved" in data
        assert "auto_apply_triggered" in data