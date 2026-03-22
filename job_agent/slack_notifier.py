"""Slack notification helper.

Posts job-scraping results from Apify to a Slack channel via an
Incoming Webhook URL (set SLACK_WEBHOOK_URL in your .env).

Usage:
    from job_agent.slack_notifier import notify_scrape_results
    notify_scrape_results(results)
"""
from __future__ import annotations

import json
import logging
import os
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")


def _post_to_slack(payload: dict) -> bool:
    """Send a JSON payload to the Slack webhook. Returns True on success."""
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
                logger.info("Slack notification sent successfully.")
                return True
            logger.error("Slack webhook returned HTTP %s", resp.status)
            return False
    except Exception as exc:
        logger.error("Failed to send Slack notification: %s", exc)
        return False


def notify_scrape_results(results: dict[str, Any]) -> bool:
    """Format Apify scrape results and post a summary to Slack.

    Handles both single-platform results and combined {"runs": [...]} results.
    """
    runs: list[dict] = results.get("runs", [results])

    blocks: list[dict] = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": ":briefcase: Job Scrape Complete", "emoji": True},
        }
    ]

    for run in runs:
        platform = run.get("platform", "Unknown platform")
        jobs_found = run.get("jobs_found", 0)
        jobs_saved = run.get("jobs_saved", 0)
        errors = run.get("errors", [])

        status_icon = ":white_check_mark:" if not errors else ":warning:"
        text_lines = [
            f"{status_icon} *{platform}*",
            f"• Found: *{jobs_found}* listings",
            f"• Saved: *{jobs_saved}* to database",
        ]
        if errors:
            text_lines.append(f"• Errors: {len(errors)} (see logs)")

        blocks.append(
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "\n".join(text_lines)},
            }
        )

    blocks.append({"type": "divider"})
    blocks.append(
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "Job Application Tracker • Apify Scraper",
                }
            ],
        }
    )

    payload = {"blocks": blocks}
    return _post_to_slack(payload)


def notify_error(message: str, platform: str = "") -> bool:
    """Post a simple error alert to Slack."""
    header = f":x: Scrape Failed{f' — {platform}' if platform else ''}"
    payload = {
        "blocks": [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*{header}*\n```{message}```"},
            }
        ]
    }
    return _post_to_slack(payload)
