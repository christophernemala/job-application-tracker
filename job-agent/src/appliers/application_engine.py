"""Application orchestrator.

Manages the full application workflow:
1. Select jobs eligible for application
2. Launch browser with appropriate session
3. Apply to each job with rate limiting
4. Record results in the database
5. Respect daily/run application limits
"""

import os
from pathlib import Path
from typing import Optional

from src.appliers.base_applier import ApplicationResult
from src.appliers.linkedin_applier import LinkedInApplier
from src.appliers.naukrigulf_applier import NaukriGulfApplier
from src.storage.applications_repo import (
    insert_application,
    update_application_result,
    has_applied,
)
from src.utils.config_loader import load_rules, load_answers, get_resume_path
from src.utils.logger import get_logger, log_action

logger = get_logger(__name__)

_APPLIER_MAP = {
    "linkedin": LinkedInApplier,
    "naukrigulf": NaukriGulfApplier,
}


def select_resume(job: dict) -> Optional[str]:
    """Select the best resume variant for a job based on its metadata.

    Args:
        job: Job dict with title, metadata, etc.

    Returns:
        Path to resume file as string, or None.
    """
    title_lower = (job.get("normalized_title") or job.get("title", "")).lower()
    metadata = job.get("metadata", {})
    keywords = set(metadata.get("keywords", []))

    # Match resume variant to job type
    if "credit" in title_lower or "credit_control" in keywords:
        variant = "credit_control"
    elif "o2c" in title_lower or "order_to_cash" in keywords:
        variant = "o2c"
    elif "receivable" in title_lower or "accounts_receivable" in keywords or "ar" in title_lower:
        variant = "ar_collections"
    else:
        variant = "general_finance"

    try:
        path = get_resume_path(variant)
        if path.exists():
            logger.debug("Selected resume variant '%s' for: %s", variant, job.get("title"))
            return str(path)
        else:
            logger.warning("Resume file not found: %s", path)
            # Try fallback
            for fallback in ["ar_collections", "general_finance"]:
                try:
                    fp = get_resume_path(fallback)
                    if fp.exists():
                        return str(fp)
                except KeyError:
                    continue
    except KeyError:
        logger.warning("Resume variant '%s' not configured", variant)

    return None


def apply_to_jobs(
    routed_jobs: dict[str, list[dict]],
    answers: Optional[dict] = None,
    rules: Optional[dict] = None,
    dry_run: bool = False,
) -> tuple[int, int]:
    """Apply to jobs that have been routed to auto_apply.

    Args:
        routed_jobs: Dict with route_status -> list of jobs.
        answers: Pre-filled answers. Loaded from config if None.
        rules: Rules config. Loaded from config if None.
        dry_run: If True, simulate without actually submitting.

    Returns:
        Tuple of (applied_count, failed_count).
    """
    if answers is None:
        answers = load_answers()
    if rules is None:
        rules = load_rules()

    auto_jobs = routed_jobs.get("auto_apply", [])
    if not auto_jobs:
        logger.info("No jobs routed to auto_apply")
        return 0, 0

    max_per_run = rules.get("max_applications_per_run", 10)
    jobs_to_apply = auto_jobs[:max_per_run]

    logger.info(
        "Attempting to apply to %d jobs (max %d per run)",
        len(jobs_to_apply), max_per_run,
    )

    if dry_run:
        logger.info("DRY RUN: Would apply to %d jobs", len(jobs_to_apply))
        for job in jobs_to_apply:
            logger.info("  [DRY] %s at %s (score=%.1f)",
                        job.get("title"), job.get("company"), job.get("score", 0))
        return 0, 0

    applied = 0
    failed = 0

    # Group jobs by source for efficient browser session management
    by_source: dict[str, list[dict]] = {}
    for job in jobs_to_apply:
        source = job.get("source", "unknown")
        by_source.setdefault(source, []).append(job)

    for source, source_jobs in by_source.items():
        source_applied, source_failed = _apply_source_batch(
            source, source_jobs, answers
        )
        applied += source_applied
        failed += source_failed

    logger.info(
        "Application run complete: applied=%d failed=%d", applied, failed
    )
    return applied, failed


def _apply_source_batch(
    source: str,
    jobs: list[dict],
    answers: dict,
) -> tuple[int, int]:
    """Apply to a batch of jobs from a single source.

    Opens one browser session per source for efficiency.

    Args:
        source: Source name (e.g., 'linkedin', 'naukrigulf').
        jobs: List of jobs to apply to.
        answers: Pre-filled answers.

    Returns:
        Tuple of (applied_count, failed_count).
    """
    applier_class = _APPLIER_MAP.get(source)
    if not applier_class:
        logger.warning("No applier available for source: %s", source)
        return 0, len(jobs)

    applied = 0
    failed = 0

    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1280, "height": 800},
            )
            page = context.new_page()

            # Login
            _login_for_source(page, source)

            applier = applier_class(answers)

            for job in jobs:
                job_id = job.get("id", 0)

                # Skip if already applied
                if has_applied(job_id):
                    logger.info("Skipping already-applied job id=%d", job_id)
                    continue

                # Select resume
                resume_path = select_resume(job)

                # Record application attempt
                insert_application(
                    job_id=job_id,
                    source=source,
                    resume_used=resume_path,
                    result="in_progress",
                )

                # Attempt application
                result: ApplicationResult = applier.apply(
                    job, page, resume_path=resume_path
                )

                # Update database
                update_application_result(
                    job_id=job_id,
                    result="success" if result.success else "failure",
                    confirmation_text=result.confirmation_text,
                    screenshot_path=result.screenshot_path,
                    failure_reason=result.failure_reason,
                )

                # Log action
                log_action(
                    logger,
                    action="apply",
                    status="success" if result.success else "failure",
                    details=f"{job.get('title')} at {job.get('company')}",
                    job_url=job.get("url"),
                    error=result.failure_reason,
                )

                if result.success:
                    applied += 1
                else:
                    failed += 1

                # Rate limiting between applications
                page.wait_for_timeout(3000)

            browser.close()

    except ImportError:
        logger.error("Playwright not installed. Run: pip install playwright && playwright install")
        return 0, len(jobs)
    except Exception as e:
        logger.error("Browser session error for %s: %s", source, str(e))
        failed += len(jobs) - applied - failed
        return applied, failed

    return applied, failed


def _login_for_source(page, source: str) -> bool:
    """Login to a source platform.

    Args:
        page: Playwright page.
        source: Source name.

    Returns:
        True if login succeeded.
    """
    if source == "linkedin":
        email = os.environ.get("LINKEDIN_EMAIL", "")
        password = os.environ.get("LINKEDIN_PASSWORD", "")
        if not email or not password:
            logger.warning("LinkedIn credentials not configured")
            return False

        page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(2000)

        if "feed" in page.url:
            return True

        page.fill("#username", email)
        page.fill("#password", password)
        page.click("button[type='submit']")
        page.wait_for_timeout(5000)
        return "feed" in page.url or "mynetwork" in page.url

    elif source == "naukrigulf":
        email = os.environ.get("NAUKRIGULF_EMAIL", "")
        password = os.environ.get("NAUKRIGULF_PASSWORD", "")
        if not email or not password:
            logger.warning("NaukriGulf credentials not configured")
            return False

        page.goto("https://www.naukrigulf.com/login", wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(2000)

        page.fill("input[type='email'], #usernameField", email)
        page.fill("input[type='password'], #passwordField", password)
        page.click("button[type='submit']")
        page.wait_for_timeout(5000)
        return True

    logger.warning("No login handler for source: %s", source)
    return False
