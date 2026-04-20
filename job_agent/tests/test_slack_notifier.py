"""Tests for Slack notifier helpers."""
from __future__ import annotations

import json
from unittest.mock import patch

import pytest

import job_agent.slack_notifier as sn


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _FakeResponse:
    """Minimal stand-in for urllib.response.addinfourl used in urlopen context."""

    def __init__(self, status: int = 200):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


def _urlopen_ok(req, timeout=10):
    return _FakeResponse(200)


def _urlopen_non_200(req, timeout=10):
    return _FakeResponse(429)


def _urlopen_raise(req, timeout=10):
    raise OSError("network error")


# ---------------------------------------------------------------------------
# Tests already present (preserved from previous PR)
# ---------------------------------------------------------------------------

def test_notify_application_status_builds_expected_payload(monkeypatch):
    captured = {}

    def fake_post(payload):
        captured["payload"] = payload
        return True

    monkeypatch.setattr(sn, "_post_to_slack", fake_post)

    ok = sn.notify_application_status(
        job_title="Software Engineer",
        company="Acme",
        platform="LinkedIn",
        status="applied",
        job_url="https://example.com/job/123",
    )

    assert ok is True
    text = captured["payload"]["blocks"][0]["text"]["text"]
    assert ":white_check_mark:" in text
    assert "<https://example.com/job/123|Software Engineer>" in text
    assert "*Company:* Acme" in text
    assert "*Platform:* LinkedIn" in text


def test_notify_run_summary_marks_warning_when_errors_present(monkeypatch):
    captured = {}

    def fake_post(payload):
        captured["payload"] = payload
        return True

    monkeypatch.setattr(sn, "_post_to_slack", fake_post)

    ok = sn.notify_run_summary(
        platform="Naukri Gulf",
        attempted=10,
        successful=7,
        failed=3,
        errors=["timeout"],
    )

    assert ok is True
    text = captured["payload"]["blocks"][0]["text"]["text"]
    assert ":warning:" in text
    assert "Attempted: *10*" in text
    assert "Successful: *7*" in text
    assert "Failed: *3*" in text


def test_notify_error_formats_message(monkeypatch):
    captured = {}

    def fake_post(payload):
        captured["payload"] = payload
        return True

    monkeypatch.setattr(sn, "_post_to_slack", fake_post)

    ok = sn.notify_error("Something bad happened", platform="LinkedIn")

    assert ok is True
    text = captured["payload"]["blocks"][0]["text"]["text"]
    assert "Error — LinkedIn" in text
    assert "Something bad happened" in text


# ---------------------------------------------------------------------------
# _post_to_slack
# ---------------------------------------------------------------------------

def test_post_to_slack_returns_false_when_no_url(monkeypatch):
    monkeypatch.setattr(sn, "SLACK_WEBHOOK_URL", "")
    assert sn._post_to_slack({"text": "hello"}) is False


def test_post_to_slack_returns_true_on_200(monkeypatch):
    monkeypatch.setattr(sn, "SLACK_WEBHOOK_URL", "https://hooks.slack.com/test")
    with patch("urllib.request.urlopen", side_effect=_urlopen_ok):
        result = sn._post_to_slack({"text": "hello"})
    assert result is True


def test_post_to_slack_returns_false_on_non_200(monkeypatch):
    monkeypatch.setattr(sn, "SLACK_WEBHOOK_URL", "https://hooks.slack.com/test")
    with patch("urllib.request.urlopen", side_effect=_urlopen_non_200):
        result = sn._post_to_slack({"text": "hello"})
    assert result is False


def test_post_to_slack_returns_false_on_network_error(monkeypatch):
    monkeypatch.setattr(sn, "SLACK_WEBHOOK_URL", "https://hooks.slack.com/test")
    with patch("urllib.request.urlopen", side_effect=_urlopen_raise):
        result = sn._post_to_slack({"text": "hello"})
    assert result is False


def test_post_to_slack_sends_json_content_type(monkeypatch):
    monkeypatch.setattr(sn, "SLACK_WEBHOOK_URL", "https://hooks.slack.com/test")
    captured = {}

    def _capture(req, timeout=10):
        captured["headers"] = req.headers
        captured["data"] = req.data
        return _FakeResponse(200)

    with patch("urllib.request.urlopen", side_effect=_capture):
        sn._post_to_slack({"blocks": []})

    assert captured["headers"].get("Content-type") == "application/json"


def test_post_to_slack_serialises_payload_as_json(monkeypatch):
    monkeypatch.setattr(sn, "SLACK_WEBHOOK_URL", "https://hooks.slack.com/test")
    captured = {}

    def _capture(req, timeout=10):
        captured["data"] = req.data
        return _FakeResponse(200)

    with patch("urllib.request.urlopen", side_effect=_capture):
        sn._post_to_slack({"blocks": [{"type": "section"}]})

    parsed = json.loads(captured["data"])
    assert parsed == {"blocks": [{"type": "section"}]}


def test_post_to_slack_does_not_raise_on_exception(monkeypatch):
    """Network errors must be caught; _post_to_slack must never propagate."""
    monkeypatch.setattr(sn, "SLACK_WEBHOOK_URL", "https://hooks.slack.com/test")
    with patch("urllib.request.urlopen", side_effect=RuntimeError("boom")):
        result = sn._post_to_slack({"text": "x"})
    assert result is False


# ---------------------------------------------------------------------------
# notify_application_status — status icons and payload structure
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("status,expected_icon", [
    ("applied", ":white_check_mark:"),
    ("failed", ":x:"),
    ("skipped", ":next_track_button:"),
    ("interview", ":calendar:"),
    ("offer", ":tada:"),
    ("rejected", ":no_entry_sign:"),
])
def test_notify_application_status_icon_for_known_statuses(status, expected_icon, monkeypatch):
    captured = {}
    monkeypatch.setattr(sn, "_post_to_slack", lambda p: captured.update(p) or True)

    sn.notify_application_status("Dev", "Corp", "LinkedIn", status)
    text = captured["blocks"][0]["text"]["text"]
    assert expected_icon in text


def test_notify_application_status_unknown_status_uses_info_icon(monkeypatch):
    captured = {}
    monkeypatch.setattr(sn, "_post_to_slack", lambda p: captured.update(p) or True)

    sn.notify_application_status("Dev", "Corp", "LinkedIn", "custom_status")
    text = captured["blocks"][0]["text"]["text"]
    assert ":information_source:" in text


def test_notify_application_status_status_label_is_capitalised(monkeypatch):
    captured = {}
    monkeypatch.setattr(sn, "_post_to_slack", lambda p: captured.update(p) or True)

    sn.notify_application_status("Dev", "Corp", "Naukri", "applied")
    text = captured["blocks"][0]["text"]["text"]
    assert "Applied" in text
    assert "applied" not in text.split(":white_check_mark:")[1].split("—")[0]


def test_notify_application_status_with_url_makes_hyperlink(monkeypatch):
    captured = {}
    monkeypatch.setattr(sn, "_post_to_slack", lambda p: captured.update(p) or True)

    sn.notify_application_status("Dev", "Acme", "LinkedIn", "applied", "https://jobs.example.com/123")
    text = captured["blocks"][0]["text"]["text"]
    assert "<https://jobs.example.com/123|Dev>" in text


def test_notify_application_status_without_url_uses_plain_title(monkeypatch):
    captured = {}
    monkeypatch.setattr(sn, "_post_to_slack", lambda p: captured.update(p) or True)

    sn.notify_application_status("Dev", "Acme", "LinkedIn", "applied")
    text = captured["blocks"][0]["text"]["text"]
    # Title appears as plain text (no angle brackets for a hyperlink)
    assert "<https://" not in text
    assert "Dev" in text


def test_notify_application_status_payload_has_blocks_key(monkeypatch):
    captured = {}
    monkeypatch.setattr(sn, "_post_to_slack", lambda p: captured.update(p) or True)

    sn.notify_application_status("Dev", "Corp", "LinkedIn", "applied")
    assert "blocks" in captured
    assert isinstance(captured["blocks"], list)
    assert len(captured["blocks"]) >= 1


def test_notify_application_status_returns_post_result(monkeypatch):
    monkeypatch.setattr(sn, "_post_to_slack", lambda p: False)
    result = sn.notify_application_status("Dev", "Corp", "LinkedIn", "failed")
    assert result is False


def test_notify_application_status_status_case_insensitive(monkeypatch):
    """Status matching should be case-insensitive."""
    captured = {}
    monkeypatch.setattr(sn, "_post_to_slack", lambda p: captured.update(p) or True)

    sn.notify_application_status("Dev", "Corp", "LinkedIn", "APPLIED")
    text = captured["blocks"][0]["text"]["text"]
    assert ":white_check_mark:" in text


# ---------------------------------------------------------------------------
# notify_run_summary
# ---------------------------------------------------------------------------

def test_notify_run_summary_no_errors_uses_check_mark(monkeypatch):
    captured = {}
    monkeypatch.setattr(sn, "_post_to_slack", lambda p: captured.update(p) or True)

    sn.notify_run_summary(platform="LinkedIn", attempted=5, successful=5, failed=0)
    text = captured["blocks"][0]["text"]["text"]
    assert ":white_check_mark:" in text
    assert ":warning:" not in text


def test_notify_run_summary_errors_none_uses_check_mark(monkeypatch):
    captured = {}
    monkeypatch.setattr(sn, "_post_to_slack", lambda p: captured.update(p) or True)

    sn.notify_run_summary(platform="Naukri", attempted=3, successful=3, failed=0, errors=None)
    text = captured["blocks"][0]["text"]["text"]
    assert ":white_check_mark:" in text


def test_notify_run_summary_includes_error_count_line(monkeypatch):
    captured = {}
    monkeypatch.setattr(sn, "_post_to_slack", lambda p: captured.update(p) or True)

    sn.notify_run_summary(
        platform="LinkedIn",
        attempted=10,
        successful=8,
        failed=2,
        errors=["err1", "err2"],
    )
    text = captured["blocks"][0]["text"]["text"]
    assert "2 error(s)" in text


def test_notify_run_summary_no_errors_omits_error_count_line(monkeypatch):
    captured = {}
    monkeypatch.setattr(sn, "_post_to_slack", lambda p: captured.update(p) or True)

    sn.notify_run_summary(platform="LinkedIn", attempted=5, successful=5, failed=0)
    text = captured["blocks"][0]["text"]["text"]
    assert "error(s)" not in text


def test_notify_run_summary_includes_context_block(monkeypatch):
    captured = {}
    monkeypatch.setattr(sn, "_post_to_slack", lambda p: captured.update(p) or True)

    sn.notify_run_summary(platform="Naukri", attempted=1, successful=1, failed=0)
    block_types = [b["type"] for b in captured["blocks"]]
    assert "context" in block_types


def test_notify_run_summary_platform_name_in_header(monkeypatch):
    captured = {}
    monkeypatch.setattr(sn, "_post_to_slack", lambda p: captured.update(p) or True)

    sn.notify_run_summary(platform="MyPlatform", attempted=0, successful=0, failed=0)
    text = captured["blocks"][0]["text"]["text"]
    assert "MyPlatform" in text


def test_notify_run_summary_returns_post_result(monkeypatch):
    monkeypatch.setattr(sn, "_post_to_slack", lambda p: False)
    result = sn.notify_run_summary(platform="X", attempted=0, successful=0, failed=0)
    assert result is False


# ---------------------------------------------------------------------------
# notify_error
# ---------------------------------------------------------------------------

def test_notify_error_with_platform_includes_platform_in_header(monkeypatch):
    captured = {}
    monkeypatch.setattr(sn, "_post_to_slack", lambda p: captured.update(p) or True)

    sn.notify_error("DB failure", platform="Naukri Gulf")
    text = captured["blocks"][0]["text"]["text"]
    assert "Naukri Gulf" in text
    assert "DB failure" in text


def test_notify_error_without_platform_omits_dash(monkeypatch):
    captured = {}
    monkeypatch.setattr(sn, "_post_to_slack", lambda p: captured.update(p) or True)

    sn.notify_error("Timeout error")
    text = captured["blocks"][0]["text"]["text"]
    assert "Error" in text
    assert "Timeout error" in text
    # Should not have a trailing " — " without a platform
    assert "Error —" not in text


def test_notify_error_message_in_code_block(monkeypatch):
    """Error message should be wrapped in triple backticks."""
    captured = {}
    monkeypatch.setattr(sn, "_post_to_slack", lambda p: captured.update(p) or True)

    sn.notify_error("stack trace here")
    text = captured["blocks"][0]["text"]["text"]
    assert "```stack trace here```" in text


def test_notify_error_returns_post_result(monkeypatch):
    monkeypatch.setattr(sn, "_post_to_slack", lambda p: False)
    result = sn.notify_error("boom")
    assert result is False


def test_notify_error_payload_uses_section_block(monkeypatch):
    captured = {}
    monkeypatch.setattr(sn, "_post_to_slack", lambda p: captured.update(p) or True)

    sn.notify_error("oops")
    assert captured["blocks"][0]["type"] == "section"