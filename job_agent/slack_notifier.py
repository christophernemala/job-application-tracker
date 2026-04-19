"""Slack webhook notifications for the job application tracker."""

from __future__ import annotations

import json
import logging
import os
import urllib.request

logger = logging.getLogger(__name__)

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")


def _post(payload: dict) -> bool:
    if not SLACK_WEBHOOK_URL:
        logger.debug("SLACK_WEBHOOK_URL not set — skipping Slack notification")
        return False
    try:
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            SLACK_WEBHOOK_URL,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=10)
        return True
    except Exception as exc:
        logger.warning("Slack notification failed: %s", exc)
        return False


def notify_new_application(job_title: str, company: str, platform: str, status: str, match_score: int | None = None) -> None:
    score_text = f" | Match: *{match_score}%*" if match_score else ""
    _post({
        "text": (
            f":briefcase: *New Application*\n"
            f"*{job_title}* at *{company}*\n"
            f"Platform: {platform} | Status: `{status}`{score_text}"
        )
    })


def notify_status_change(job_title: str, company: str, old_status: str, new_status: str) -> None:
    emoji = {
        "interview": ":calendar:",
        "offer": ":tada:",
        "rejected": ":x:",
        "applied": ":white_check_mark:",
    }.get(new_status, ":bell:")
    _post({
        "text": (
            f"{emoji} *Status Update*\n"
            f"*{job_title}* at *{company}*\n"
            f"`{old_status}` → `{new_status}`"
        )
    })


def notify_pipeline_run(total: int, applied: int, skipped: int, errors: int) -> None:
    _post({
        "text": (
            f":robot_face: *Pipeline Run Complete*\n"
            f"Total: {total} | Applied: {applied} | Skipped: {skipped} | Errors: {errors}"
        )
    })
