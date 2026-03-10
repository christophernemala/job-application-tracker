"""Notification abstraction.

Supports multiple notification backends:
- Console (always active)
- Log file (always active)
- Telegram (when configured)
- Email (when configured)

For now, Telegram and Email are stub implementations that
save payloads to log files for future integration.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.utils.logger import get_logger, LOGS_DIR

logger = get_logger(__name__)

NOTIFICATIONS_LOG = LOGS_DIR / "notifications.jsonl"


def notify(
    title: str,
    message: str,
    level: str = "info",
    job_url: Optional[str] = None,
    details: Optional[dict] = None,
) -> None:
    """Send a notification through all configured channels.

    Args:
        title: Short notification title.
        message: Notification body text.
        level: Severity level ('info', 'success', 'warning', 'error').
        job_url: Optional job URL for context.
        details: Optional extra details dict.
    """
    payload = {
        "timestamp": datetime.now().isoformat(),
        "title": title,
        "message": message,
        "level": level,
        "job_url": job_url,
        "details": details,
    }

    # Always: console
    _notify_console(payload)

    # Always: log file
    _notify_log_file(payload)

    # Optional: Telegram
    if os.environ.get("TELEGRAM_BOT_TOKEN") and os.environ.get("TELEGRAM_CHAT_ID"):
        _notify_telegram(payload)

    # Optional: Email
    if os.environ.get("SMTP_HOST") and os.environ.get("NOTIFICATION_EMAIL_TO"):
        _notify_email(payload)


def notify_application_result(
    job_title: str,
    company: str,
    success: bool,
    failure_reason: Optional[str] = None,
    job_url: Optional[str] = None,
) -> None:
    """Send a notification for an application result.

    Args:
        job_title: Job title applied to.
        company: Company name.
        success: Whether application was successful.
        failure_reason: Reason for failure if applicable.
        job_url: Job URL.
    """
    if success:
        notify(
            title="Application Submitted",
            message=f"Successfully applied to {job_title} at {company}",
            level="success",
            job_url=job_url,
        )
    else:
        notify(
            title="Application Failed",
            message=f"Failed to apply to {job_title} at {company}: {failure_reason}",
            level="error",
            job_url=job_url,
        )


def notify_manual_review(
    job_title: str,
    company: str,
    score: float,
    reason: str,
    job_url: Optional[str] = None,
) -> None:
    """Notify about a job routed to manual review.

    Args:
        job_title: Job title.
        company: Company name.
        score: Job score.
        reason: Reason for manual review.
        job_url: Job URL.
    """
    notify(
        title="Manual Review Required",
        message=f"{job_title} at {company} (score: {score:.0f}) – {reason}",
        level="warning",
        job_url=job_url,
    )


def notify_run_summary(
    source: str,
    total_found: int,
    total_new: int,
    total_applied: int,
    total_failed: int,
) -> None:
    """Notify with run summary stats.

    Args:
        source: Source name.
        total_found: Jobs found.
        total_new: New jobs.
        total_applied: Successful applications.
        total_failed: Failed applications.
    """
    notify(
        title="Run Complete",
        message=(
            f"[{source}] Found: {total_found} | New: {total_new} | "
            f"Applied: {total_applied} | Failed: {total_failed}"
        ),
        level="info",
        details={
            "source": source,
            "total_found": total_found,
            "total_new": total_new,
            "total_applied": total_applied,
            "total_failed": total_failed,
        },
    )


def _notify_console(payload: dict) -> None:
    """Print formatted notification to console."""
    level = payload["level"].upper()
    icons = {"INFO": "[i]", "SUCCESS": "[+]", "WARNING": "[!]", "ERROR": "[x]"}
    icon = icons.get(level, "[?]")

    print(f"\n  {icon} {payload['title']}")
    print(f"      {payload['message']}")
    if payload.get("job_url"):
        print(f"      URL: {payload['job_url']}")
    print()


def _notify_log_file(payload: dict) -> None:
    """Append notification payload to JSONL log file."""
    try:
        with open(NOTIFICATIONS_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload) + "\n")
    except Exception as e:
        logger.warning("Failed to write notification log: %s", str(e))


def _notify_telegram(payload: dict) -> None:
    """Send notification via Telegram bot.

    Stub implementation – saves payload for future integration.
    Requires TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID env vars.
    """
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")

    if not token or not chat_id:
        return

    # Format message for Telegram
    message = f"*{payload['title']}*\n{payload['message']}"
    if payload.get("job_url"):
        message += f"\n[View Job]({payload['job_url']})"

    # TODO: Implement actual Telegram API call
    # import urllib.request
    # url = f"https://api.telegram.org/bot{token}/sendMessage"
    # data = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}

    logger.debug("Telegram notification queued: %s", payload["title"])


def _notify_email(payload: dict) -> None:
    """Send notification via email.

    Stub implementation – saves payload for future integration.
    Requires SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD,
    NOTIFICATION_EMAIL_TO env vars.
    """
    # TODO: Implement actual email sending
    # import smtplib
    # from email.mime.text import MIMEText

    logger.debug("Email notification queued: %s", payload["title"])
