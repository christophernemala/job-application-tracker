"""Submission strategy layer.

Strategy per apply_mode
-----------------------
easy_apply      → attempt API/form submission; mark applied on success
external_form   → open browser to ATS URL + pre-fill where possible
browser_assist  → open browser to job URL for human one-click submit
manual          → add to manual queue, log for human action

No platform is fully abandoned — the pipeline always produces an action.
"""
from __future__ import annotations
import json
import subprocess
import sys
import webbrowser
from datetime import datetime
from pathlib import Path

from pipeline.config import ZAPIER_WEBHOOK, MOCK_MODE
from pipeline.tracker import db
from pipeline.utils.logger import get_logger

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Mode handlers
# ---------------------------------------------------------------------------

def _submit_easy_apply(job: dict, pkg_dir: Path) -> str:
    """
    LinkedIn / Indeed Easy Apply.

    In MOCK_MODE: simulate success.
    In live mode: would use a Playwright/Selenium script to fill the
    built-in apply flow. Stub kept here — extend with browser automation.
    """
    if MOCK_MODE:
        log.info("[MOCK] Easy-apply simulated for %s", job.get("id"))
        return "applied_mock"

    # Placeholder for live Playwright automation
    url = job.get("easy_apply_url") or job.get("url", "")
    answers_path = pkg_dir / "answers.json"
    cv_path = pkg_dir / "cv_tailored.md"

    log.info(
        "Easy apply not yet automated — opening browser for %s", url
    )
    webbrowser.open(url)
    return "browser_opened"


def _submit_external_form(job: dict, pkg_dir: Path) -> str:
    """Open ATS URL in default browser with package directory logged."""
    url = job.get("url", "")
    answers_path = pkg_dir / "answers.json"
    log.info(
        "External ATS form — opening %s | answers at %s", url, answers_path
    )
    if not MOCK_MODE:
        webbrowser.open(url)
    return "browser_opened"


def _submit_browser_assist(job: dict, pkg_dir: Path) -> str:
    """Open job URL in browser — human completes the last step."""
    url = job.get("url", "")
    log.info("Browser-assist — opening %s", url)
    if not MOCK_MODE:
        webbrowser.open(url)
    return "browser_opened"


def _submit_manual(job: dict, pkg_dir: Path) -> str:
    """Log to manual queue — no automated action taken."""
    log.info(
        "Manual apply required for %s @ %s — package at %s",
        job.get("title"), job.get("company"), pkg_dir,
    )
    return "queued_manual"


_HANDLERS = {
    "easy_apply": _submit_easy_apply,
    "external_form": _submit_external_form,
    "browser_assist": _submit_browser_assist,
    "manual": _submit_manual,
}


# ---------------------------------------------------------------------------
# Zapier / webhook notification
# ---------------------------------------------------------------------------

def _notify_zapier(job: dict, status: str) -> None:
    if not ZAPIER_WEBHOOK:
        return
    try:
        import urllib.request
        payload = json.dumps({
            "job_id": job.get("id"),
            "company": job.get("company"),
            "title": job.get("title"),
            "url": job.get("url"),
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
        }).encode()
        req = urllib.request.Request(
            ZAPIER_WEBHOOK,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=10)
        log.info("Zapier notified for %s.", job.get("id"))
    except Exception as exc:  # pylint: disable=broad-except
        log.warning("Zapier notification failed: %s", exc)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def submit_job(job: dict, pkg_dir: Path) -> str:
    """Run the appropriate submission handler and update tracker status."""
    mode = job.get("apply_mode", "manual")
    handler = _HANDLERS.get(mode, _submit_manual)

    try:
        result_status = handler(job, pkg_dir)
    except Exception as exc:  # pylint: disable=broad-except
        log.error("Submission failed for %s: %s", job.get("id"), exc)
        result_status = "error"

    # Map handler result to tracker status
    tracker_status = {
        "applied_mock": "applied",
        "browser_opened": "in_progress",
        "queued_manual": "queued_manual",
        "error": "error",
    }.get(result_status, result_status)

    applied_at = datetime.utcnow().isoformat(timespec="seconds") if "applied" in tracker_status else None

    db.update_status(
        job["id"],
        status=tracker_status,
        notes=f"apply_mode={mode}; result={result_status}",
        applied_at=applied_at,
    )
    _notify_zapier(job, tracker_status)
    log.info("Job %s → status=%s", job.get("id"), tracker_status)
    return tracker_status


def submit_batch(
    jobs: list[dict],
    pkg_dirs: dict[str, Path],
) -> dict[str, str]:
    """Submit all jobs in the queue. Returns {job_id: status}."""
    results: dict[str, str] = {}
    for job in jobs:
        pkg = pkg_dirs.get(job["id"])
        if not pkg:
            log.warning("No package found for %s — skipping submission.", job.get("id"))
            continue
        results[job["id"]] = submit_job(job, pkg)
    return results
