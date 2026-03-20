"""Core pipeline orchestrator — one full run from scrape to submission queue."""
from __future__ import annotations
from datetime import datetime

from pipeline import config
from pipeline.ingestion.apify_client import fetch_all_jobs
from pipeline.filtering.rules import build_shortlist
from pipeline.tailoring.tailor import tailor_batch
from pipeline.tracker import db
from pipeline.application.detector import annotate_apply_modes
from pipeline.application.packager import build_batch
from pipeline.application.submitter import submit_batch
from pipeline.utils.logger import get_logger

log = get_logger("pipeline.main")


def run_pipeline(
    candidate: dict | None = None,
    auto_submit: bool = False,
) -> dict:
    """Execute the full pipeline.

    Parameters
    ----------
    candidate   Candidate profile dict (name, email, phone, etc.)
    auto_submit If True, trigger submission handlers automatically.
                If False (default), builds packages only — human reviews first.

    Returns a summary dict.
    """
    start = datetime.utcnow()
    log.info("=" * 60)
    log.info("Pipeline run started at %s  [MOCK_MODE=%s]", start.isoformat(), config.MOCK_MODE)
    log.info("=" * 60)

    # ------------------------------------------------------------------
    # 0. Init DB
    # ------------------------------------------------------------------
    db.init_db()
    seen_ids = db.get_seen_ids()
    log.info("Tracker has %d existing job IDs.", len(seen_ids))

    # ------------------------------------------------------------------
    # 1. Ingest
    # ------------------------------------------------------------------
    log.info("--- Step 1: Ingestion ---")
    raw_jobs = fetch_all_jobs()
    log.info("Total raw jobs fetched: %d", len(raw_jobs))

    # ------------------------------------------------------------------
    # 2. Filter + Score
    # ------------------------------------------------------------------
    log.info("--- Step 2: Filtering & Scoring ---")
    shortlisted, rejected = build_shortlist(raw_jobs, seen_ids)
    log.info("Shortlisted: %d | Rejected: %d", len(shortlisted), len(rejected))

    if not shortlisted:
        log.info("No new shortlisted jobs this run.")
        db.log_run(len(raw_jobs), 0, 0, 0, "no_new_shortlisted")
        return {"shortlisted": 0, "applied": 0, "packages": 0}

    # ------------------------------------------------------------------
    # 3. Apply-mode detection
    # ------------------------------------------------------------------
    log.info("--- Step 3: Apply Mode Detection ---")
    shortlisted = annotate_apply_modes(shortlisted)
    for job in shortlisted:
        log.info(
            "  [%s] %-50s %s/100  mode=%s",
            job["source"][:8],
            f"{job['company'][:25]} / {job['title'][:22]}",
            job["score"],
            job["apply_mode"],
        )

    # ------------------------------------------------------------------
    # 4. CV Tailoring
    # ------------------------------------------------------------------
    log.info("--- Step 4: CV Tailoring ---")
    cv_paths = tailor_batch(shortlisted)

    # Attach cv_file path to job dicts
    for job in shortlisted:
        if job["id"] in cv_paths:
            job["cv_file"] = str(cv_paths[job["id"]])

    # ------------------------------------------------------------------
    # 5. Save to Tracker
    # ------------------------------------------------------------------
    log.info("--- Step 5: Tracker ---")
    for job in shortlisted:
        db.upsert_job(job)
    log.info("Saved %d jobs to tracker.", len(shortlisted))

    # ------------------------------------------------------------------
    # 6. Build Application Packages
    # ------------------------------------------------------------------
    log.info("--- Step 6: Build Packages ---")
    pkg_dirs = build_batch(shortlisted, cv_paths, candidate)
    log.info("Packages built: %d", len(pkg_dirs))

    # ------------------------------------------------------------------
    # 7. Submit (or queue)
    # ------------------------------------------------------------------
    applied_count = 0
    if auto_submit:
        log.info("--- Step 7: Submission ---")
        results = submit_batch(shortlisted, pkg_dirs)
        applied_count = sum(1 for s in results.values() if "applied" in s)
        log.info("Submission results: %s", results)
    else:
        log.info("--- Step 7: Skipped (auto_submit=False) ---")
        log.info(
            "Review packages in: %s\nThen run: python -m pipeline.cli submit",
            config.QUEUE_DIR,
        )

    # ------------------------------------------------------------------
    # 8. Run log
    # ------------------------------------------------------------------
    db.log_run(
        jobs_found=len(raw_jobs),
        shortlisted=len(shortlisted),
        applied=applied_count,
    )

    elapsed = (datetime.utcnow() - start).total_seconds()
    summary = {
        "run_at": start.isoformat(),
        "elapsed_seconds": round(elapsed, 1),
        "raw_jobs": len(raw_jobs),
        "shortlisted": len(shortlisted),
        "packages_built": len(pkg_dirs),
        "applied": applied_count,
        "queue_dir": str(config.QUEUE_DIR),
    }
    log.info("Pipeline complete in %.1fs | %s", elapsed, summary)
    return summary
