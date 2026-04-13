"""Tests for job_agent.slack_notifier (new module added in this PR)."""
from __future__ import annotations

import json
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

import job_agent.slack_notifier as sn


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_response(status: int = 200) -> MagicMock:
    """Return a mock context-manager response whose .status is ``status``."""
    resp = MagicMock()
    resp.status = status
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


# ---------------------------------------------------------------------------
# _post_to_slack
# ---------------------------------------------------------------------------

class TestPostToSlack:
    def test_returns_false_when_url_not_set(self, monkeypatch):
        monkeypatch.setattr(sn, "SLACK_WEBHOOK_URL", "")
        assert sn._post_to_slack({"text": "hello"}) is False

    def test_returns_true_on_http_200(self, monkeypatch):
        monkeypatch.setattr(sn, "SLACK_WEBHOOK_URL", "https://hooks.slack.com/test")
        with patch("urllib.request.urlopen", return_value=_make_response(200)):
            assert sn._post_to_slack({"text": "hello"}) is True

    def test_returns_false_on_non_200(self, monkeypatch):
        monkeypatch.setattr(sn, "SLACK_WEBHOOK_URL", "https://hooks.slack.com/test")
        with patch("urllib.request.urlopen", return_value=_make_response(500)):
            assert sn._post_to_slack({"text": "oops"}) is False

    def test_returns_false_on_network_exception(self, monkeypatch):
        monkeypatch.setattr(sn, "SLACK_WEBHOOK_URL", "https://hooks.slack.com/test")
        with patch("urllib.request.urlopen", side_effect=OSError("timeout")):
            assert sn._post_to_slack({"text": "boom"}) is False

    def test_sends_json_content_type(self, monkeypatch):
        monkeypatch.setattr(sn, "SLACK_WEBHOOK_URL", "https://hooks.slack.com/test")
        captured_req = {}

        def fake_urlopen(req, timeout=None):
            captured_req["headers"] = req.headers
            return _make_response(200)

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            sn._post_to_slack({"text": "check"})

        assert captured_req["headers"].get("Content-type") == "application/json"

    def test_payload_is_serialised_as_json(self, monkeypatch):
        monkeypatch.setattr(sn, "SLACK_WEBHOOK_URL", "https://hooks.slack.com/test")
        payload = {"blocks": [{"type": "section"}]}
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["data"] = json.loads(req.data)
            return _make_response(200)

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            sn._post_to_slack(payload)

        assert captured["data"] == payload


# ---------------------------------------------------------------------------
# notify_application_status
# ---------------------------------------------------------------------------

class TestNotifyApplicationStatus:
    def _call(self, monkeypatch, **kwargs):
        monkeypatch.setattr(sn, "SLACK_WEBHOOK_URL", "https://hooks.slack.com/test")
        captured = {}

        def fake_post(payload):
            captured["payload"] = payload
            return True

        monkeypatch.setattr(sn, "_post_to_slack", fake_post)
        defaults = dict(
            job_title="Software Engineer",
            company="Acme",
            platform="LinkedIn",
            status="applied",
            job_url="https://example.com/job",
        )
        defaults.update(kwargs)
        result = sn.notify_application_status(**defaults)
        return result, captured.get("payload", {})

    def test_returns_true_on_success(self, monkeypatch):
        result, _ = self._call(monkeypatch)
        assert result is True

    def test_applied_status_uses_check_mark_icon(self, monkeypatch):
        _, payload = self._call(monkeypatch, status="applied")
        text = payload["blocks"][0]["text"]["text"]
        assert ":white_check_mark:" in text

    def test_failed_status_uses_x_icon(self, monkeypatch):
        _, payload = self._call(monkeypatch, status="failed")
        text = payload["blocks"][0]["text"]["text"]
        assert ":x:" in text

    def test_skipped_status_icon(self, monkeypatch):
        _, payload = self._call(monkeypatch, status="skipped")
        text = payload["blocks"][0]["text"]["text"]
        assert ":next_track_button:" in text

    def test_unknown_status_uses_info_icon(self, monkeypatch):
        _, payload = self._call(monkeypatch, status="pending_review")
        text = payload["blocks"][0]["text"]["text"]
        assert ":information_source:" in text

    def test_status_is_capitalised(self, monkeypatch):
        _, payload = self._call(monkeypatch, status="applied")
        text = payload["blocks"][0]["text"]["text"]
        assert "Applied" in text

    def test_job_url_creates_slack_link(self, monkeypatch):
        _, payload = self._call(monkeypatch, job_url="https://example.com/j")
        text = payload["blocks"][0]["text"]["text"]
        assert "<https://example.com/j|Software Engineer>" in text

    def test_empty_job_url_shows_plain_title(self, monkeypatch):
        _, payload = self._call(monkeypatch, job_url="")
        text = payload["blocks"][0]["text"]["text"]
        assert "Software Engineer" in text
        assert "<" not in text

    def test_company_and_platform_in_body(self, monkeypatch):
        _, payload = self._call(monkeypatch, company="Megacorp", platform="Naukri Gulf")
        text = payload["blocks"][0]["text"]["text"]
        assert "Megacorp" in text
        assert "Naukri Gulf" in text

    def test_payload_has_blocks(self, monkeypatch):
        _, payload = self._call(monkeypatch)
        assert "blocks" in payload
        assert payload["blocks"][0]["type"] == "section"

    def test_status_case_insensitive(self, monkeypatch):
        """Status lookup should be case-insensitive."""
        _, payload = self._call(monkeypatch, status="APPLIED")
        text = payload["blocks"][0]["text"]["text"]
        assert ":white_check_mark:" in text

    def test_returns_false_when_webhook_not_set(self, monkeypatch):
        monkeypatch.setattr(sn, "SLACK_WEBHOOK_URL", "")
        result = sn.notify_application_status(
            job_title="X", company="Y", platform="Z", status="applied"
        )
        assert result is False


# ---------------------------------------------------------------------------
# notify_run_summary
# ---------------------------------------------------------------------------

class TestNotifyRunSummary:
    def _call(self, monkeypatch, **kwargs):
        monkeypatch.setattr(sn, "SLACK_WEBHOOK_URL", "https://hooks.slack.com/test")
        captured = {}

        def fake_post(payload):
            captured["payload"] = payload
            return True

        monkeypatch.setattr(sn, "_post_to_slack", fake_post)
        defaults = dict(platform="LinkedIn", attempted=10, successful=8, failed=2, errors=None)
        defaults.update(kwargs)
        result = sn.notify_run_summary(**defaults)
        return result, captured.get("payload", {})

    def test_returns_true_on_success(self, monkeypatch):
        result, _ = self._call(monkeypatch)
        assert result is True

    def test_platform_name_in_text(self, monkeypatch):
        _, payload = self._call(monkeypatch, platform="Naukri Gulf")
        text = payload["blocks"][0]["text"]["text"]
        assert "Naukri Gulf" in text

    def test_stats_in_text(self, monkeypatch):
        _, payload = self._call(monkeypatch, attempted=5, successful=3, failed=2)
        text = payload["blocks"][0]["text"]["text"]
        assert "5" in text
        assert "3" in text
        assert "2" in text

    def test_no_errors_uses_check_mark(self, monkeypatch):
        _, payload = self._call(monkeypatch, errors=None)
        text = payload["blocks"][0]["text"]["text"]
        assert ":white_check_mark:" in text

    def test_with_errors_uses_warning(self, monkeypatch):
        _, payload = self._call(monkeypatch, errors=["err1", "err2"])
        text = payload["blocks"][0]["text"]["text"]
        assert ":warning:" in text

    def test_error_count_appended_when_errors_present(self, monkeypatch):
        _, payload = self._call(monkeypatch, errors=["e1", "e2", "e3"])
        text = payload["blocks"][0]["text"]["text"]
        assert "3 error" in text

    def test_payload_has_context_block(self, monkeypatch):
        _, payload = self._call(monkeypatch)
        block_types = [b["type"] for b in payload["blocks"]]
        assert "context" in block_types

    def test_zero_attempted_is_valid(self, monkeypatch):
        result, payload = self._call(monkeypatch, attempted=0, successful=0, failed=0)
        assert result is True
        text = payload["blocks"][0]["text"]["text"]
        assert "0" in text


# ---------------------------------------------------------------------------
# notify_error
# ---------------------------------------------------------------------------

class TestNotifyError:
    def _call(self, monkeypatch, message="Something went wrong", platform=""):
        monkeypatch.setattr(sn, "SLACK_WEBHOOK_URL", "https://hooks.slack.com/test")
        captured = {}

        def fake_post(payload):
            captured["payload"] = payload
            return True

        monkeypatch.setattr(sn, "_post_to_slack", fake_post)
        result = sn.notify_error(message=message, platform=platform)
        return result, captured.get("payload", {})

    def test_returns_true_on_success(self, monkeypatch):
        result, _ = self._call(monkeypatch)
        assert result is True

    def test_message_in_payload(self, monkeypatch):
        _, payload = self._call(monkeypatch, message="DB connection failed")
        text = payload["blocks"][0]["text"]["text"]
        assert "DB connection failed" in text

    def test_platform_in_header_when_provided(self, monkeypatch):
        _, payload = self._call(monkeypatch, platform="Naukri Gulf")
        text = payload["blocks"][0]["text"]["text"]
        assert "Naukri Gulf" in text

    def test_no_platform_omits_dash(self, monkeypatch):
        _, payload = self._call(monkeypatch, platform="")
        text = payload["blocks"][0]["text"]["text"]
        # Header should be ":x: Error" without " — "
        assert " — " not in text.split("\n")[0]

    def test_error_icon_in_header(self, monkeypatch):
        _, payload = self._call(monkeypatch)
        text = payload["blocks"][0]["text"]["text"]
        assert ":x:" in text

    def test_message_wrapped_in_code_block(self, monkeypatch):
        _, payload = self._call(monkeypatch, message="trace here")
        text = payload["blocks"][0]["text"]["text"]
        assert "```" in text

    def test_returns_false_when_webhook_not_set(self, monkeypatch):
        monkeypatch.setattr(sn, "SLACK_WEBHOOK_URL", "")
        result = sn.notify_error("oops")
        assert result is False