"""Job Agent – Main entry point.

Orchestrates the full job monitoring and application pipeline:
1. Load configuration
2. Initialize database
3. Collect jobs from enabled sources
4. Parse and normalize job data
5. Score jobs against target profile
6. Route jobs to appropriate action paths
7. Execute controlled applications for auto_apply jobs
8. Log results and generate reports
9. Send notifications

Usage:
    python main.py                  # Full pipeline run
    python main.py --collect-only   # Only collect and score, no applications
    python main.py --report-only    # Only generate reports from existing data
    python main.py --init-db        # Initialize database schema only
"""

import argparse
import sys
from datetime import datetime

from src.utils.logger import get_logger, create_run_log
from src.utils.config_loader import (
    load_profile,
    load_rules,
    load_answers,
    get_enabled_sources,
)
from src.storage.database import init_database
from src.storage.run_logs_repo import insert_run_log, update_run_log

logger = get_logger("main")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Job Agent – Automated job monitoring and application system"
    )
    parser.add_argument(
        "--collect-only",
        action="store_true",
        help="Only collect and score jobs, do not apply",
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Generate reports from existing data only",
    )
    parser.add_argument(
        "--init-db",
        action="store_true",
        help="Initialize database schema and exit",
    )
    parser.add_argument(
        "--source",
        type=str,
        default=None,
        help="Run only for a specific source (e.g., linkedin, naukrigulf)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate the pipeline without making any applications",
    )
    return parser.parse_args()


def run_pipeline(args: argparse.Namespace) -> None:
    """Execute the main job agent pipeline.

    Args:
        args: Parsed CLI arguments.
    """
    start_time = datetime.now()
    logger.info("=" * 60)
    logger.info("Job Agent pipeline started at %s", start_time.isoformat())
    logger.info("=" * 60)

    # Step 1: Load configuration
    logger.info("Loading configuration...")
    profile = load_profile()
    rules = load_rules()
    answers = load_answers()
    enabled_sources = get_enabled_sources()

    logger.info(
        "Profile: %s | Target titles: %d | Enabled sources: %d",
        profile.get("candidate_name", "Unknown"),
        len(profile.get("target_titles", [])),
        len(enabled_sources),
    )

    if args.source:
        enabled_sources = [s for s in enabled_sources if s["name"] == args.source]
        if not enabled_sources:
            logger.error("Source '%s' not found or not enabled", args.source)
            return

    # Step 2: Initialize database
    logger.info("Initializing database...")
    init_database()

    if args.init_db:
        logger.info("Database initialized. Exiting (--init-db mode).")
        return

    # Step 3: Report-only mode
    if args.report_only:
        logger.info("Running in report-only mode...")
        _generate_reports()
        return

    # Step 4: Process each source
    for source_config in enabled_sources:
        source_name = source_config["name"]
        logger.info("-" * 40)
        logger.info("Processing source: %s", source_name)

        run_log_path = create_run_log(source_name)
        run_id = insert_run_log(source_name)

        counters = {
            "total_found": 0,
            "total_new": 0,
            "total_scored": 0,
            "total_applied": 0,
            "total_failed": 0,
        }

        try:
            # Collect jobs
            logger.info("[%s] Collecting jobs...", source_name)
            collected = _collect_jobs(source_config)
            counters["total_found"] = len(collected)
            logger.info("[%s] Found %d job listings", source_name, len(collected))

            # Parse and store
            logger.info("[%s] Parsing and storing jobs...", source_name)
            new_jobs = _parse_and_store(collected, source_name)
            counters["total_new"] = len(new_jobs)
            logger.info("[%s] %d new jobs stored", source_name, len(new_jobs))

            # Score jobs
            logger.info("[%s] Scoring jobs...", source_name)
            scored = _score_jobs(new_jobs, rules, profile)
            counters["total_scored"] = len(scored)

            # Route jobs
            logger.info("[%s] Routing jobs...", source_name)
            routed = _route_jobs(scored, rules)

            if args.collect_only or args.dry_run:
                logger.info(
                    "[%s] Collect-only/dry-run mode – skipping applications",
                    source_name,
                )
            else:
                # Apply to auto_apply jobs
                logger.info("[%s] Applying to eligible jobs...", source_name)
                applied, failed = _apply_to_jobs(routed, answers, args.dry_run)
                counters["total_applied"] = applied
                counters["total_failed"] = failed

        except Exception as e:
            logger.error("[%s] Pipeline error: %s", source_name, str(e), exc_info=True)
            counters["total_failed"] += 1

        # Update run log
        update_run_log(run_id, **counters)

    # Step 5: Generate reports
    logger.info("-" * 40)
    _generate_reports()

    # Step 6: Send notifications
    _send_notifications()

    elapsed = (datetime.now() - start_time).total_seconds()
    logger.info("=" * 60)
    logger.info("Pipeline completed in %.1f seconds", elapsed)
    logger.info("=" * 60)


def _collect_jobs(source_config: dict) -> list:
    """Collect jobs from a source using the appropriate collector.

    Args:
        source_config: Source configuration dict.

    Returns:
        List of RawJob objects.
    """
    from src.collectors import get_collector

    collector = get_collector(source_config)
    return collector.collect()


def _parse_and_store(collected: list, source: str) -> list[dict]:
    """Parse raw jobs and store new ones in the database.

    Args:
        collected: List of RawJob objects from a collector.
        source: Source name.

    Returns:
        List of newly stored job dicts (excluding duplicates).
    """
    from src.parsers.job_parser import parse_raw_job
    from src.storage.jobs_repo import insert_job, is_duplicate_job, get_job_by_id

    new_jobs = []
    for raw_job in collected:
        parsed = parse_raw_job(raw_job)

        # Check for duplicates
        if is_duplicate_job(
            source=parsed["source"],
            url=parsed["url"],
            company=parsed.get("company"),
            title=parsed.get("title"),
        ):
            logger.debug("Skipping duplicate: %s", parsed["url"])
            continue

        job_id = insert_job(
            source=parsed["source"],
            title=parsed["title"],
            url=parsed["url"],
            company=parsed.get("company"),
            location=parsed.get("location"),
            salary_text=parsed.get("salary_text"),
            salary_min=parsed.get("salary_min"),
            salary_max=parsed.get("salary_max"),
            posted_date=parsed.get("posted_date"),
            description=parsed.get("description"),
            normalized_title=parsed.get("normalized_title"),
            apply_type=parsed.get("apply_type", "unknown"),
        )

        if job_id:
            job = get_job_by_id(job_id)
            if job:
                job["metadata"] = parsed.get("metadata", {})
                new_jobs.append(job)

    return new_jobs


def _score_jobs(jobs: list[dict], rules: dict, profile: dict) -> list[dict]:
    """Score jobs against the target profile.

    Args:
        jobs: List of job dicts.
        rules: Scoring rules.
        profile: Candidate profile.

    Returns:
        List of scored job dicts.
    """
    from src.scorers.scoring_engine import ScoringEngine
    from src.storage.jobs_repo import update_job_score

    engine = ScoringEngine(profile=profile, rules=rules)
    scored = []

    for job in jobs:
        score, reason = engine.score_job(job)
        job["score"] = score
        job["score_reason"] = reason

        # Persist score to database
        if "id" in job:
            update_job_score(job["id"], score, reason)

        scored.append(job)
        logger.debug(
            "Scored: %.1f | %s | %s", score, job.get("title", "?"), reason,
        )

    return scored


def _route_jobs(scored_jobs: list[dict], rules: dict) -> dict[str, list[dict]]:
    """Route scored jobs to appropriate action paths.

    Args:
        scored_jobs: List of scored job dicts.
        rules: Routing rules.

    Returns:
        Dict of route_status -> list of jobs.
    """
    from src.scorers.router import route_jobs
    from src.storage.jobs_repo import update_job_route

    routed = route_jobs(scored_jobs, rules)

    # Persist route status to database
    for status, jobs in routed.items():
        for job in jobs:
            if "id" in job:
                update_job_route(job["id"], status)

    return routed


def _apply_to_jobs(
    routed: dict[str, list[dict]], answers: dict, dry_run: bool = False
) -> tuple[int, int]:
    """Apply to eligible auto_apply jobs using browser automation.

    Args:
        routed: Dict of route_status -> list of jobs.
        answers: Pre-filled form answers.
        dry_run: If True, simulate without submitting.

    Returns:
        Tuple of (applied_count, failed_count).
    """
    from src.appliers.application_engine import apply_to_jobs

    return apply_to_jobs(routed, answers=answers, dry_run=dry_run)


def _generate_reports() -> None:
    """Generate terminal and HTML summary reports."""
    from src.reports.report_generator import (
        get_summary_stats,
        print_terminal_report,
        generate_html_report,
    )

    try:
        stats = get_summary_stats()
        print_terminal_report(stats)
        report_path = generate_html_report(stats)
        logger.info("HTML report saved: %s", report_path)
    except Exception as e:
        logger.error("Report generation failed: %s", str(e))


def _send_notifications() -> None:
    """Send run completion notifications."""
    from src.notifications.notifier import notify_run_summary
    from src.storage.run_logs_repo import get_latest_run_log

    try:
        latest = get_latest_run_log()
        if latest:
            notify_run_summary(
                source=latest.get("source", "unknown"),
                total_found=latest.get("total_found", 0),
                total_new=latest.get("total_new", 0),
                total_applied=latest.get("total_applied", 0),
                total_failed=latest.get("total_failed", 0),
            )
    except Exception as e:
        logger.error("Notification failed: %s", str(e))


def main() -> None:
    """Main entry point."""
    args = parse_args()

    try:
        run_pipeline(args)
    except KeyboardInterrupt:
        logger.warning("Pipeline interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.critical("Unhandled error: %s", str(e), exc_info=True)
        sys.exit(2)


if __name__ == "__main__":
    main()
