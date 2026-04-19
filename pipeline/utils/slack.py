"""Slack webhook notifications for the pipeline."""

from __future__ import annotations

import json
import logging
import urllib.request
from datetime import datetime

from pipeline.config import SLACK_WEBHOOK_URL

logger = logging.getLogger(__name__)


def _post(text: str) -> None:
    if not SLACK_WEBHOOK_URL:
        return
    try:
        data = json.dumps({"text": text}).encode()
        req = urllib.request.Request(
            SLACK_WEBHOOK_URL,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception as exc:
        logger.warning("Slack notification failed: %s", exc)


def notify_application_submitted(job: dict, status: str) -> None:
    emoji = ":white_check_mark:" if "applied" in status else ":hourglass:"
    score = f" | Match: *{job['match_score']}%*" if job.get("match_score") else ""
    _post(
        f"{emoji} *Application Submitted*\n"
        f"*{job.get('title', 'Unknown')}* at *{job.get('company', 'Unknown')}*\n"
        f"Platform: {job.get('platform', 'n/a')} | Status: `{status}`{score}"
    )


def notify_pipeline_complete(total: int, applied: int, skipped: int, errors: int) -> None:
    _post(
        f":robot_face: *Pipeline Run Complete* — {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}\n"
        f"Total: {total} | Applied: {applied} | Skipped: {skipped} | Errors: {errors}"
    )
