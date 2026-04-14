"""Tests for job_agent.slack_notifier (new in this PR)."""
from __future__ import annotations

import json
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

import job_agent.slack_notifier as notifier


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

class _FakeResponse:
    """Minimal stand-in for urllib.response.addinfourl."""

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
# _post_to_slack
# ---------------------------------------------------------------------------

def test_post_to_slack_returns_false_when_no_url(monkeypatch):
    monkeypatch.setattr(notifier, "SLACK_WEBHOOK_URL", "")
    assert notifier._post_to_slack({"text": "hello"}) is False


def test_post_to_slack_returns_true_on_200(monkeypatch):
    monkeypatch.setattr(notifier, "SLACK_WEBHOOK_URL", "https://hooks.slack.com/test")
    with patch("urllib.request.urlopen", side_effect=_urlopen_ok):
        result = notifier._post_to_slack({"text": "hello"})
    assert result is True


def test_post_to_slack_returns_false_on_non_200(monkeypatch):
    monkeypatch.setattr(notifier, "SLACK_WEBHOOK_URL", "https://hooks.slack.com/test")
    with patch("urllib.request.urlopen", side_effect=_urlopen_non_200):
        result = notifier._post_to_slack({"text": "hello"})
    assert result is False


def test_post_to_slack_returns_false_on_network_error(monkeypatch):
    monkeypatch.setattr(notifier, "SLACK_WEBHOOK_URL", "https://hooks.slack.com/test")
    with patch("urllib.request.urlopen", side_effect=_urlopen_raise):
        result = notifier._post_to_slack({"text": "hello"})
    assert result is False


def test_post_to_slack_sends_json_content_type(monkeypatch):
    monkeypatch.setattr(notifier, "SLACK_WEBHOOK_URL", "https://hooks.slack.com/test")
    captured = {}

    def _capture(req, timeout=10):
        captured["headers"] = req.headers
        captured["data"] = req.data
        return _FakeResponse(200)

    with patch("urllib.request.urlopen", side_effect=_capture):
        notifier._post_to_slack({"blocks": []})

    assert captured["headers"].get("Content-type") == "application/json"
    parsed = json.loads(captured["data"])
    assert "blocks" in parsed


# ---------------------------------------------------------------------------
# notify_application_status
# ---------------------------------------------------------------------------

def test_notify_application_status_applied_icon(monkeypatch):
    monkeypatch.setattr(notifier, "SLACK_WEBHOOK_URL", "https://hooks.slack.com/test")
    captured_payload = {}

    def _fake_post(payload):
        captured_payload.update(payload)
        return True

    monkeypatch.setattr(notifier, "_post_to_slack", _fake_post)
    notifier.notify_application_status("Dev", "Acme", "LinkedIn", "applied", "https://example.com")

    text = captured_payload["blocks"][0]["text"]["text"]
    assert ":white_check_mark:" in text
    assert "Applied" in text
    assert "Acme" in text
    assert "LinkedIn" in text


def test_notify_application_status_failed_icon(monkeypatch):
    monkeypatch.setattr(notifier, "SLACK_WEBHOOK_URL", "https://hooks.slack.com/test")
    captured_payload = {}

    def _fake_post(payload):
        captured_payload.update(payload)
        return True

    monkeypatch.setattr(notifier, "_post_to_slack", _fake_post)
    notifier.notify_application_status("Dev", "Acme", "Naukri Gulf", "failed")

    text = captured_payload["blocks"][0]["text"]["text"]
    assert ":x:" in text
    assert "Failed" in text


def test_notify_application_status_unknown_status_uses_info_icon(monkeypatch):
    captured_payload = {}

    def _fake_post(payload):
        captured_payload.update(payload)
        return True

    monkeypatch.setattr(notifier, "_post_to_slack", _fake_post)
    notifier.notify_application_status("Dev", "Acme", "LinkedIn", "custom_status")
    text = captured_payload["blocks"][0]["text"]["text"]
    assert ":information_source:" in text


def test_notify_application_status_with_url_makes_link(monkeypatch):
    captured_payload = {}

    def _fake_post(payload):
        captured_payload.update(payload)
        return True

    monkeypatch.setattr(notifier, "_post_to_slack", _fake_post)
    notifier.notify_application_status("Dev", "Acme", "LinkedIn", "applied", "https://jobs.example.com/123")
    text = captured_payload["blocks"][0]["text"]["text"]
    assert "<https://jobs.example.com/123|Dev>" in text


def test_notify_application_status_without_url_no_link(monkeypatch):
    captured_payload = {}

    def _fake_post(payload):
        captured_payload.update(payload)
        return True

    monkeypatch.setattr(notifier, "_post_to_slack", _fake_post)
    notifier.notify_application_status("Dev", "Acme", "LinkedIn", "applied")
    text = captured_payload["blocks"][0]["text"]["text"]
    # Plain title without hyperlink markup
    assert "<" not in text or "Dev" in text
    assert "<https://" not in text


def test_notify_application_status_returns_bool(monkeypatch):
    monkeypatch.setattr(notifier, "_post_to_slack", lambda p: True)
    result = notifier.notify_application_status("Dev", "Acme", "LinkedIn", "applied")
    assert result is True


def test_notify_application_status_all_known_statuses(monkeypatch):
    """All statuses in _STATUS_ICON should produce a known emoji."""
    icons = notifier._STATUS_ICON
    for status, expected_icon in icons.items():
        captured = {}

        def _fake_post(payload, _captured=captured):
            _captured.update(payload)
            return True

        monkeypatch.setattr(notifier, "_post_to_slack", _fake_post)
        notifier.notify_application_status("Job", "Co", "Platform", status)
        text = captured["blocks"][0]["text"]["text"]
        assert expected_icon in text, f"Expected icon {expected_icon!r} for status {status!r}"


# ---------------------------------------------------------------------------
# notify_run_summary
# ---------------------------------------------------------------------------

def test_notify_run_summary_no_errors_uses_checkmark(monkeypatch):
    captured_payload = {}

    def _fake_post(payload):
        captured_payload.update(payload)
        return True

    monkeypatch.setattr(notifier, "_post_to_slack", _fake_post)
    notifier.notify_run_summary("LinkedIn", attempted=10, successful=8, failed=2)

    text = captured_payload["blocks"][0]["text"]["text"]
    assert ":white_check_mark:" in text
    assert "LinkedIn" in text
    assert "10" in text
    assert "8" in text
    assert "2" in text


def test_notify_run_summary_with_errors_uses_warning(monkeypatch):
    captured_payload = {}

    def _fake_post(payload):
        captured_payload.update(payload)
        return True

    monkeypatch.setattr(notifier, "_post_to_slack", _fake_post)
    notifier.notify_run_summary("Naukri Gulf", attempted=5, successful=2, failed=3,
                                 errors=["err1", "err2"])

    text = captured_payload["blocks"][0]["text"]["text"]
    assert ":warning:" in text
    assert "2 error(s)" in text


def test_notify_run_summary_no_errors_line_when_none(monkeypatch):
    captured_payload = {}

    def _fake_post(payload):
        captured_payload.update(payload)
        return True

    monkeypatch.setattr(notifier, "_post_to_slack", _fake_post)
    notifier.notify_run_summary("LinkedIn", attempted=1, successful=1, failed=0, errors=None)

    text = captured_payload["blocks"][0]["text"]["text"]
    assert "error" not in text.lower()


def test_notify_run_summary_has_context_block(monkeypatch):
    captured_payload = {}

    def _fake_post(payload):
        captured_payload.update(payload)
        return True

    monkeypatch.setattr(notifier, "_post_to_slack", _fake_post)
    notifier.notify_run_summary("LinkedIn", attempted=0, successful=0, failed=0)

    block_types = [b["type"] for b in captured_payload["blocks"]]
    assert "context" in block_types


def test_notify_run_summary_returns_bool(monkeypatch):
    monkeypatch.setattr(notifier, "_post_to_slack", lambda p: False)
    result = notifier.notify_run_summary("LinkedIn", attempted=0, successful=0, failed=0)
    assert result is False


# ---------------------------------------------------------------------------
# notify_error
# ---------------------------------------------------------------------------

def test_notify_error_includes_message(monkeypatch):
    captured_payload = {}

    def _fake_post(payload):
        captured_payload.update(payload)
        return True

    monkeypatch.setattr(notifier, "_post_to_slack", _fake_post)
    notifier.notify_error("Something went wrong")

    text = captured_payload["blocks"][0]["text"]["text"]
    assert "Something went wrong" in text
    assert ":x:" in text


def test_notify_error_with_platform_includes_platform(monkeypatch):
    captured_payload = {}

    def _fake_post(payload):
        captured_payload.update(payload)
        return True

    monkeypatch.setattr(notifier, "_post_to_slack", _fake_post)
    notifier.notify_error("Timeout", platform="Naukri Gulf")

    text = captured_payload["blocks"][0]["text"]["text"]
    assert "Naukri Gulf" in text


def test_notify_error_without_platform_no_dash(monkeypatch):
    captured_payload = {}

    def _fake_post(payload):
        captured_payload.update(payload)
        return True

    monkeypatch.setattr(notifier, "_post_to_slack", _fake_post)
    notifier.notify_error("Timeout")

    text = captured_payload["blocks"][0]["text"]["text"]
    # Header should be ":x: Error" without a " — " suffix
    assert " — " not in text.split("\n")[0]


def test_notify_error_returns_bool(monkeypatch):
    monkeypatch.setattr(notifier, "_post_to_slack", lambda p: True)
    result = notifier.notify_error("boom")
    assert result is True