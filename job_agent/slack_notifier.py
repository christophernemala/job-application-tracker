"""Slack notification helpers for the job application tracker.

The functions in this module are intentionally small and dependency-free so they
work both locally and inside GitHub Actions.
"""
from __future__ import annotations

import json
import os
import urllib.request
from datetime import datetime, timezone
from typing import Any


SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "").strip()

_STATUS_ICONS = {
    "applied": ":white_check_mark:",
    "failed": ":x:",
    "skipped": ":next_track_button:",
    "interview": ":calendar:",
    "offer": ":tada:",
    "rejected": ":no_entry_sign:",
}


def _post_to_slack(payload: dict[str, Any]) -> bool:
    """Post a JSON payload to Slack.

    Returns False instead of raising when the webhook is missing, Slack returns a
    non-200 response, or a network error occurs.
    """
    if not SLACK_WEBHOOK_URL:
        return False

    try:
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            SLACK_WEBHOOK_URL,
            data=data,
            headers={"Content-type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            return int(getattr(response, "status", 0)) == 200
    except Exception:
        return False


def notify_application_status(
    job_title: str,
    company: str,
    platform: str,
    status: str,
    job_url: str | None = None,
) -> bool:
    """Send one job application status update to Slack."""
    status_key = (status or "").lower()
    icon = _STATUS_ICONS.get(status_key, ":information_source:")
    status_label = status_key.replace("_", " ").title() if status_key else "Update"
    title = f"<{job_url}|{job_title}>" if job_url else job_title

    text = (
        f"{icon} *{status_label}* — {title}\n"
        f"*Company:* {company}\n"
        f"*Platform:* {platform}"
    )
    payload = {"blocks": [{"type": "section", "text": {"type": "mrkdwn", "text": text}}]}
    return _post_to_slack(payload)


def notify_run_summary(
    platform: str,
    attempted: int,
    successful: int,
    failed: int,
    errors: list[str] | None = None,
) -> bool:
    """Send a run summary to Slack."""
    has_errors = bool(errors) or failed > 0
    icon = ":warning:" if has_errors else ":white_check_mark:"
    text = (
        f"{icon} *{platform} Job Agent Run Summary*\n"
        f"Attempted: *{attempted}*\n"
        f"Successful: *{successful}*\n"
        f"Failed: *{failed}*"
    )
    if errors:
        text += f"\n{len(errors)} error(s): " + ", ".join(str(error) for error in errors[:5])

    payload = {
        "blocks": [
            {"type": "section", "text": {"type": "mrkdwn", "text": text}},
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"Generated {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
                    }
                ],
            },
        ]
    }
    return _post_to_slack(payload)


def notify_error(message: str, platform: str | None = None) -> bool:
    """Send an error notification to Slack."""
    header = f"Error — {platform}" if platform else "Error"
    text = f":x: *{header}*\n```{message}```"
    payload = {"blocks": [{"type": "section", "text": {"type": "mrkdwn", "text": text}}]}
    return _post_to_slack(payload)
