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


def _collect_jobs(source_config: dict) -> list[dict]:
    """Collect jobs from a source. Placeholder for Stage 2."""
    # Will be implemented in Stage 2 with source-specific collectors
    logger.info("Collector not yet implemented for: %s", source_config["name"])
    return []


def _parse_and_store(collected: list[dict], source: str) -> list[dict]:
    """Parse and store collected jobs. Placeholder for Stage 2."""
    logger.info("Parser not yet implemented")
    return []


def _score_jobs(jobs: list[dict], rules: dict, profile: dict) -> list[dict]:
    """Score jobs against profile. Placeholder for Stage 2."""
    logger.info("Scorer not yet implemented")
    return []


def _route_jobs(scored_jobs: list[dict], rules: dict) -> dict[str, list[dict]]:
    """Route scored jobs. Placeholder for Stage 2."""
    logger.info("Router not yet implemented")
    return {"auto_apply": [], "semi_auto": [], "manual_review": [], "reject": []}


def _apply_to_jobs(
    routed: dict[str, list[dict]], answers: dict, dry_run: bool = False
) -> tuple[int, int]:
    """Apply to eligible jobs. Placeholder for Stage 3."""
    logger.info("Applier not yet implemented")
    return 0, 0


def _generate_reports() -> None:
    """Generate summary reports. Placeholder for Stage 4."""
    logger.info("Reporter not yet implemented")


def _send_notifications() -> None:
    """Send notifications. Placeholder for Stage 4."""
    logger.info("Notifier not yet implemented")


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
