"""Tests for Slack notifier helpers."""

import job_agent.slack_notifier as sn


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
