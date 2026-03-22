"""Slack notification helper.

Sends per-application status updates to a Slack channel via an
Incoming Webhook (set SLACK_WEBHOOK_URL in your .env).

NOTE: Apify → Slack scrape-summary notifications are handled by
Slack's native Apify app integration. This module only covers
application-level status updates posted by the job agent.

Usage:
    from job_agent.slack_notifier import notify_application_status
    notify_application_status("Accounts Receivable Specialist", "Acme Corp",
                               "LinkedIn", "applied", "https://...")
"""
from __future__ import annotations

import json
import logging
import os
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")

# Status → emoji map
_STATUS_ICON = {
    "applied": ":white_check_mark:",
    "failed": ":x:",
    "skipped": ":next_track_button:",
    "interview": ":calendar:",
    "offer": ":tada:",
    "rejected": ":no_entry_sign:",
}


def _post_to_slack(payload: dict) -> bool:
    """POST a JSON payload to the configured Slack webhook. Returns True on success."""
    if not SLACK_WEBHOOK_URL:
        logger.warning("SLACK_WEBHOOK_URL not set — Slack notification skipped.")
        return False

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        SLACK_WEBHOOK_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                return True
            logger.error("Slack webhook returned HTTP %s", resp.status)
            return False
    except Exception as exc:
        logger.error("Failed to send Slack notification: %s", exc)
        return False


def notify_application_status(
    job_title: str,
    company: str,
    platform: str,
    status: str,
    job_url: str = "",
) -> bool:
    """Post a single job-application status update to Slack.

    Args:
        job_title: Title of the role applied to
        company:   Employer name
        platform:  Source platform (e.g. "Naukri Gulf", "LinkedIn")
        status:    One of: applied, failed, skipped, interview, offer, rejected
        job_url:   Direct link to the job listing (optional)
    """
    icon = _STATUS_ICON.get(status.lower(), ":information_source:")
    label = status.capitalize()

    title_text = f"<{job_url}|{job_title}>" if job_url else job_title
    body = f"{icon} *{label}* — {title_text}\n*Company:* {company}   |   *Platform:* {platform}"

    payload = {
        "blocks": [
            {"type": "section", "text": {"type": "mrkdwn", "text": body}},
        ]
    }
    return _post_to_slack(payload)


def notify_run_summary(
    platform: str,
    attempted: int,
    successful: int,
    failed: int,
    errors: list[str] | None = None,
) -> bool:
    """Post an end-of-run summary block to Slack."""
    icon = ":white_check_mark:" if not errors else ":warning:"
    lines = [
        f"{icon} *{platform} run finished*",
        f"• Attempted: *{attempted}*   Successful: *{successful}*   Failed: *{failed}*",
    ]
    if errors:
        lines.append(f"• {len(errors)} error(s) — check logs")

    payload = {
        "blocks": [
            {"type": "section", "text": {"type": "mrkdwn", "text": "\n".join(lines)}},
            {"type": "context", "elements": [{"type": "mrkdwn", "text": "Job Application Tracker"}]},
        ]
    }
    return _post_to_slack(payload)


def notify_error(message: str, platform: str = "") -> bool:
    """Post a simple error alert to Slack."""
    header = f":x: Error{f' — {platform}' if platform else ''}"
    payload = {
        "blocks": [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*{header}*\n```{message}```"},
            }
        ]
    }
    return _post_to_slack(payload)
