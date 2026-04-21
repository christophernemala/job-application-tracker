"""Slack notification helpers for the Job Agent.

Sends rich Slack messages via an Incoming Webhook.  All functions return True
on success and False on failure (including when no webhook URL is configured).
They never raise exceptions so callers do not need try/except guards.

Configure by setting the SLACK_WEBHOOK_URL environment variable (or adding it
to job_agent/.env).  When the variable is absent every call is a silent no-op.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.request

logger = logging.getLogger(__name__)

SLACK_WEBHOOK_URL: str = os.getenv("SLACK_WEBHOOK_URL", "")

_STATUS_ICONS: dict[str, str] = {
    "applied": ":white_check_mark:",
    "failed": ":x:",
    "skipped": ":next_track_button:",
    "interview": ":calendar:",
    "offer": ":tada:",
    "rejected": ":no_entry_sign:",
}
_DEFAULT_ICON = ":information_source:"


def _post_to_slack(payload: dict) -> bool:
    """POST *payload* as JSON to the configured Slack webhook.

    Returns True on HTTP 200, False in all other cases (missing URL, non-200
    response, or any network/serialisation error).  Never raises.
    """
    if not SLACK_WEBHOOK_URL:
        return False

    try:
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            SLACK_WEBHOOK_URL,
            data=data,
            headers={"Content-type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception as exc:
        logger.warning("Slack notification failed: %s", exc)
        return False


def notify_application_status(
    job_title: str,
    company: str,
    platform: str,
    status: str,
    job_url: str | None = None,
) -> bool:
    """Send a Slack message for a single job application status update.

    Args:
        job_title: Title of the job position.
        company: Company name.
        platform: Job platform (e.g. "LinkedIn", "Naukri Gulf").
        status: Application status (e.g. "applied", "failed", "offer").
        job_url: Optional URL to link the job title.

    Returns:
        True if the Slack message was delivered, False otherwise.
    """
    icon = _STATUS_ICONS.get(status.lower(), _DEFAULT_ICON)
    title = f"<{job_url}|{job_title}>" if job_url else job_title
    status_label = status.capitalize()

    text = (
        f"{icon} *{status_label}* — {title}\n"
        f"*Company:* {company}\n"
        f"*Platform:* {platform}"
    )

    payload: dict = {
        "blocks": [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": text},
            }
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
    """Send a Slack summary block after a job-search run.

    Args:
        platform: Job platform name.
        attempted: Total number of applications attempted.
        successful: Number of successful applications.
        failed: Number of failed applications.
        errors: Optional list of error strings encountered during the run.

    Returns:
        True if the Slack message was delivered, False otherwise.
    """
    has_errors = bool(errors)
    icon = ":warning:" if has_errors else ":white_check_mark:"

    lines = [
        f"{icon} *Run Summary — {platform}*",
        f"Attempted: *{attempted}*  |  Successful: *{successful}*  |  Failed: *{failed}*",
    ]
    if has_errors:
        lines.append(f"{len(errors)} error(s)")

    text = "\n".join(lines)

    payload: dict = {
        "blocks": [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": text},
            },
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": f"Platform: {platform}"},
                ],
            },
        ]
    }
    return _post_to_slack(payload)


def notify_error(message: str, platform: str | None = None) -> bool:
    """Send a Slack alert for an unexpected error.

    Args:
        message: Error message or stack trace to report.
        platform: Optional platform name to include in the header.

    Returns:
        True if the Slack message was delivered, False otherwise.
    """
    if platform:
        header = f":rotating_light: *Error — {platform}*"
    else:
        header = ":rotating_light: *Error*"

    text = f"{header}\n```{message}```"

    payload: dict = {
        "blocks": [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": text},
            }
        ]
    }
    return _post_to_slack(payload)
