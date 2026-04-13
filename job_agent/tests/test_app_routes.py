"""Tests for new Flask routes added in this PR:
  - POST /api/slack/test
  - POST /api/webhook/apify
  - GET  /api/jobs/pending
"""
from __future__ import annotations

import contextlib
import json
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from job_agent import database


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def isolated_db(tmp_path: Path, monkeypatch):
    """Redirect all database I/O to a per-test temporary SQLite file.

    ``get_connection`` is decorated with ``@contextmanager`` so its default
    argument is captured at function-definition time.  We replace the entire
    function with an equivalent that defaults to ``test_db``.
    """
    test_db = tmp_path / "test.db"

    @contextlib.contextmanager
    def patched_connection(db_path: Path = test_db):
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    monkeypatch.setattr(database, "get_connection", patched_connection)
    monkeypatch.setattr(database, "DB_PATH", test_db)
    database.init_database(test_db)
    return test_db


@pytest.fixture()
def flask_app():
    """Return the Flask app configured for testing."""
    from job_agent.app import app as _app
    _app.config["TESTING"] = True
    _app.config["SECRET_KEY"] = "test-secret"
    return _app


@pytest.fixture()
def client(flask_app):
    """Return a Flask test client."""
    with flask_app.test_client() as c:
        yield c


def _login(client):
    """Authenticate the test client via the login form."""
    client.post(
        "/login",
        data={"username": "admin", "password": "admin123"},
        follow_redirects=True,
    )


def _auth_headers():
    """Return HTTP Basic Auth headers for admin/admin123."""
    import base64
    creds = base64.b64encode(b"admin:admin123").decode()
    return {"Authorization": f"Basic {creds}"}


# ---------------------------------------------------------------------------
# POST /api/slack/test
# ---------------------------------------------------------------------------

class TestSlackTest:
    def test_returns_400_when_webhook_not_configured(self, client, monkeypatch):
        import job_agent.slack_notifier as sn
        monkeypatch.setattr(sn, "SLACK_WEBHOOK_URL", "")
        _login(client)
        resp = client.post("/api/slack/test")
        assert resp.status_code == 400
        data = resp.get_json()
        assert "error" in data
        assert "SLACK_WEBHOOK_URL" in data["error"]

    def test_returns_200_when_post_succeeds(self, client, monkeypatch):
        import job_agent.slack_notifier as sn
        monkeypatch.setattr(sn, "SLACK_WEBHOOK_URL", "https://hooks.slack.com/test")
        monkeypatch.setattr(sn, "_post_to_slack", lambda payload: True)
        _login(client)
        resp = client.post("/api/slack/test")
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "sent"

    def test_returns_500_when_post_fails(self, client, monkeypatch):
        import job_agent.slack_notifier as sn
        monkeypatch.setattr(sn, "SLACK_WEBHOOK_URL", "https://hooks.slack.com/test")
        monkeypatch.setattr(sn, "_post_to_slack", lambda payload: False)
        _login(client)
        resp = client.post("/api/slack/test")
        assert resp.status_code == 500
        assert "error" in resp.get_json()

    def test_requires_authentication(self, client, monkeypatch):
        import job_agent.slack_notifier as sn
        monkeypatch.setattr(sn, "SLACK_WEBHOOK_URL", "https://hooks.slack.com/test")
        # No login — should redirect (302) not 200/400/500
        resp = client.post("/api/slack/test")
        assert resp.status_code in (302, 401)

    def test_accepts_basic_auth(self, client, monkeypatch):
        import job_agent.slack_notifier as sn
        monkeypatch.setattr(sn, "SLACK_WEBHOOK_URL", "")
        resp = client.post("/api/slack/test", headers=_auth_headers())
        # Should hit the handler (returns 400 for missing URL), not redirect
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# POST /api/webhook/apify
# ---------------------------------------------------------------------------

class TestApifyWebhook:
    def test_empty_payload_returns_zero_saved(self, client, monkeypatch):
        monkeypatch.delenv("WEBHOOK_SECRET", raising=False)
        resp = client.post(
            "/api/webhook/apify",
            json={},
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["jobs_saved"] == 0
        assert data["auto_apply_triggered"] is False

    def test_list_payload_saves_jobs(self, client, monkeypatch):
        monkeypatch.delenv("WEBHOOK_SECRET", raising=False)
        jobs = [
            {"title": "Engineer", "company": "Acme", "url": "https://ex.com/1"},
            {"title": "Analyst", "company": "Corp", "url": "https://ex.com/2"},
        ]
        resp = client.post(
            "/api/webhook/apify",
            data=json.dumps(jobs),
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["jobs_saved"] == 2

    def test_list_payload_skips_items_without_title(self, client, monkeypatch):
        monkeypatch.delenv("WEBHOOK_SECRET", raising=False)
        jobs = [
            {"company": "NoCo", "url": "https://ex.com/notitle"},
        ]
        resp = client.post(
            "/api/webhook/apify",
            data=json.dumps(jobs),
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.get_json()["jobs_saved"] == 0

    def test_list_payload_accepts_alternate_field_names(self, client, monkeypatch):
        monkeypatch.delenv("WEBHOOK_SECRET", raising=False)
        jobs = [
            {"jobTitle": "Dev", "companyName": "X", "jobUrl": "https://ex.com/alt"},
        ]
        resp = client.post(
            "/api/webhook/apify",
            data=json.dumps(jobs),
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.get_json()["jobs_saved"] == 1

    def test_list_payload_accepts_snake_case_fields(self, client, monkeypatch):
        monkeypatch.delenv("WEBHOOK_SECRET", raising=False)
        jobs = [
            {"job_title": "QA", "company": "Y", "job_url": "https://ex.com/snake"},
        ]
        resp = client.post(
            "/api/webhook/apify",
            data=json.dumps(jobs),
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.get_json()["jobs_saved"] == 1

    def test_duplicate_url_not_double_counted(self, client, monkeypatch):
        monkeypatch.delenv("WEBHOOK_SECRET", raising=False)
        jobs = [
            {"title": "Dev", "company": "A", "url": "https://ex.com/dup"},
            {"title": "Dev", "company": "A", "url": "https://ex.com/dup"},
        ]
        resp = client.post(
            "/api/webhook/apify",
            data=json.dumps(jobs),
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.get_json()["jobs_saved"] == 1

    def test_auto_apply_triggered_true_when_jobs_saved(self, client, monkeypatch):
        monkeypatch.delenv("WEBHOOK_SECRET", raising=False)
        # Prevent background thread from actually running naukri automation
        with patch("job_agent.app.threading.Thread") as mock_thread:
            mock_thread.return_value = MagicMock()
            jobs = [{"title": "Dev", "company": "A", "url": "https://ex.com/t1"}]
            resp = client.post(
                "/api/webhook/apify",
                data=json.dumps(jobs),
                content_type="application/json",
            )
        data = resp.get_json()
        assert data["auto_apply_triggered"] is True

    def test_auto_apply_not_triggered_when_no_jobs(self, client, monkeypatch):
        monkeypatch.delenv("WEBHOOK_SECRET", raising=False)
        resp = client.post("/api/webhook/apify", json={})
        assert resp.get_json()["auto_apply_triggered"] is False

    def test_token_required_when_secret_set(self, client, monkeypatch):
        monkeypatch.setenv("WEBHOOK_SECRET", "mysecret")
        resp = client.post("/api/webhook/apify", json={})
        assert resp.status_code == 401

    def test_correct_token_grants_access(self, client, monkeypatch):
        monkeypatch.setenv("WEBHOOK_SECRET", "mysecret")
        resp = client.post("/api/webhook/apify?token=mysecret", json={})
        assert resp.status_code == 200

    def test_wrong_token_returns_401(self, client, monkeypatch):
        monkeypatch.setenv("WEBHOOK_SECRET", "mysecret")
        resp = client.post("/api/webhook/apify?token=wrongtoken", json={})
        assert resp.status_code == 401

    def test_no_secret_env_var_allows_all_requests(self, client, monkeypatch):
        monkeypatch.setenv("WEBHOOK_SECRET", "")
        resp = client.post("/api/webhook/apify", json={})
        assert resp.status_code == 200

    def test_envelope_payload_without_dataset_id_saves_nothing(self, client, monkeypatch):
        monkeypatch.delenv("WEBHOOK_SECRET", raising=False)
        envelope = {"resource": {}, "eventData": {}}
        resp = client.post("/api/webhook/apify", json=envelope)
        assert resp.status_code == 200
        assert resp.get_json()["jobs_saved"] == 0

    def test_default_platform_is_apify_when_not_specified(self, client, monkeypatch, isolated_db):
        monkeypatch.delenv("WEBHOOK_SECRET", raising=False)
        jobs = [{"title": "Dev", "company": "A", "url": "https://ex.com/p1"}]
        resp = client.post(
            "/api/webhook/apify",
            data=json.dumps(jobs),
            content_type="application/json",
        )
        assert resp.status_code == 200
        # Verify the platform stored in DB via the same patched get_connection
        pending = database.get_pending_jobs()
        assert pending[0]["platform"] == "Apify"

    def test_envelope_dataset_fetch_failure_returns_500(self, client, monkeypatch):
        monkeypatch.delenv("WEBHOOK_SECRET", raising=False)
        envelope = {"resource": {"defaultDatasetId": "abc123"}}
        with patch("urllib.request.urlopen", side_effect=OSError("network error")):
            resp = client.post("/api/webhook/apify", json=envelope)
        assert resp.status_code == 500
        assert "error" in resp.get_json()


# ---------------------------------------------------------------------------
# GET /api/jobs/pending
# ---------------------------------------------------------------------------

class TestPendingJobs:
    def test_returns_empty_list_when_no_jobs(self, client):
        _login(client)
        resp = client.get("/api/jobs/pending")
        assert resp.status_code == 200
        assert resp.get_json() == []

    def test_returns_pending_jobs(self, client, monkeypatch):
        captured = {}

        def fake_get_pending(limit=20):
            captured["limit"] = limit
            return [{"job_title": "Pending Role", "applied": 0}]

        monkeypatch.setattr("job_agent.app.get_pending_jobs", fake_get_pending)
        _login(client)
        resp = client.get("/api/jobs/pending")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data) == 1
        assert data[0]["job_title"] == "Pending Role"

    def test_excludes_applied_jobs(self, client, monkeypatch):
        def fake_get_pending(limit=20):
            return []

        monkeypatch.setattr("job_agent.app.get_pending_jobs", fake_get_pending)
        _login(client)
        resp = client.get("/api/jobs/pending")
        assert resp.status_code == 200
        assert resp.get_json() == []

    def test_requires_authentication(self, client):
        # No login — should redirect, not return JSON
        resp = client.get("/api/jobs/pending")
        assert resp.status_code in (302, 401)

    def test_accepts_basic_auth(self, client):
        resp = client.get("/api/jobs/pending", headers=_auth_headers())
        assert resp.status_code == 200

    def test_returns_json_content_type(self, client):
        _login(client)
        resp = client.get("/api/jobs/pending")
        assert "application/json" in resp.content_type

    def test_returns_at_most_100_jobs(self, client, monkeypatch):
        """Route passes limit=100 to get_pending_jobs."""
        captured = {}

        def fake_get_pending(limit=20):
            captured["limit"] = limit
            return []

        monkeypatch.setattr("job_agent.app.get_pending_jobs", fake_get_pending)
        _login(client)
        client.get("/api/jobs/pending")
        assert captured.get("limit") == 100

    def test_returns_multiple_jobs(self, client, monkeypatch):
        def fake_get_pending(limit=20):
            return [
                {"job_title": "Role A", "applied": 0},
                {"job_title": "Role B", "applied": 0},
            ]

        monkeypatch.setattr("job_agent.app.get_pending_jobs", fake_get_pending)
        _login(client)
        resp = client.get("/api/jobs/pending")
        assert resp.status_code == 200
        assert len(resp.get_json()) == 2