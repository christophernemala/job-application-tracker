"""CLI entrypoint — all pipeline operations accessible from the terminal.

Commands
--------
  run           Full pipeline (ingest → filter → tailor → package)
  scrape        Ingest only
  shortlist     Filter + score only (uses cached / mock data)
  tailor        Re-tailor CVs for queued jobs
  queue         Print current application queue
  submit        Submit (or open browser for) queued packages
  status        Print tracker summary
  export        Export tracker to CSV
  scheduler     Start daily scheduler
"""
from __future__ import annotations
import json
import sys

try:
    import click
except ImportError:
    print("click not installed. Run: pip install click")
    sys.exit(1)

from pipeline.utils.logger import get_logger

log = get_logger("pipeline.cli")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _candidate_from_env() -> dict:
    """Build candidate profile from env vars or return placeholders."""
    import os
    return {
        "first_name": os.getenv("CANDIDATE_FIRST_NAME", "[FIRST_NAME]"),
        "last_name": os.getenv("CANDIDATE_LAST_NAME", "[LAST_NAME]"),
        "email": os.getenv("CANDIDATE_EMAIL", "[EMAIL]"),
        "phone": os.getenv("CANDIDATE_PHONE", "[PHONE]"),
        "location": os.getenv("CANDIDATE_LOCATION", "Dubai, UAE"),
        "nationality": os.getenv("CANDIDATE_NATIONALITY", "[NATIONALITY]"),
        "visa_status": os.getenv("CANDIDATE_VISA_STATUS", "[VISA_STATUS]"),
        "notice_period": os.getenv("CANDIDATE_NOTICE_PERIOD", "1 month"),
        "current_salary": os.getenv("CANDIDATE_CURRENT_SALARY", "[CURRENT_SALARY_AED]"),
        "years_experience": os.getenv("CANDIDATE_YEARS_EXP", "[YEARS]"),
        "linkedin_url": os.getenv("CANDIDATE_LINKEDIN", "[LINKEDIN_URL]"),
    }


# ---------------------------------------------------------------------------
# CLI definition
# ---------------------------------------------------------------------------

@click.group()
def cli():
    """Job Application Pipeline CLI."""


@cli.command()
@click.option("--auto-submit", is_flag=True, default=False,
              help="Trigger submission handlers automatically.")
def run(auto_submit: bool):
    """Full pipeline: scrape → filter → tailor → package [→ submit]."""
    from pipeline.main import run_pipeline
    summary = run_pipeline(candidate=_candidate_from_env(), auto_submit=auto_submit)
    click.echo(json.dumps(summary, indent=2))


@cli.command()
@click.option("--source", default=None, help="Specific source (linkedin/indeed/bayt/gulftaient).")
def scrape(source: str | None):
    """Ingest jobs from Apify (or mock) and print raw count."""
    from pipeline.ingestion.apify_client import fetch_jobs, fetch_all_jobs
    jobs = fetch_jobs(source) if source else fetch_all_jobs()
    click.echo(f"Fetched {len(jobs)} jobs.")
    click.echo(json.dumps(jobs[:3], indent=2, default=str))


@cli.command()
def shortlist():
    """Show current shortlisted jobs from tracker."""
    from pipeline.tracker.db import get_queue
    jobs = get_queue()
    if not jobs:
        click.echo("No shortlisted jobs in tracker.")
        return
    for j in jobs:
        click.echo(
            f"[{j['score']:3d}] {j['company'][:30]:30s}  {j['title'][:40]:40s}  {j['apply_mode']}"
        )


@cli.command()
def tailor():
    """Re-run CV tailoring for all shortlisted jobs."""
    from pipeline.tracker.db import get_queue
    from pipeline.tailoring.tailor import tailor_batch
    jobs = get_queue()
    if not jobs:
        click.echo("No jobs in queue.")
        return
    paths = tailor_batch(jobs)
    click.echo(f"Tailored {len(paths)} CVs.")


@cli.command()
def queue():
    """Print the full application queue with package paths."""
    from pipeline.tracker.db import get_queue
    from pipeline.config import QUEUE_DIR
    jobs = get_queue()
    if not jobs:
        click.echo("Queue is empty.")
        return
    click.echo(f"\n{'#'*70}\n  APPLICATION QUEUE ({len(jobs)} jobs)\n{'#'*70}")
    for j in jobs:
        pkg = QUEUE_DIR / j["id"]
        click.echo(
            f"\n  [{j['score']:3d}/100] {j['company']} — {j['title']}\n"
            f"  Mode:    {j['apply_mode']}\n"
            f"  URL:     {j['url']}\n"
            f"  Package: {pkg}\n"
        )


@cli.command()
@click.option("--job-id", default=None, help="Submit only this job ID.")
def submit(job_id: str | None):
    """Open browser / trigger submission for queued packages."""
    from pipeline.tracker.db import get_queue, get_jobs, init_db
    from pipeline.application.submitter import submit_job
    from pipeline.config import QUEUE_DIR

    init_db()
    if job_id:
        jobs = [j for j in get_jobs() if j["id"] == job_id]
    else:
        jobs = get_queue()

    if not jobs:
        click.echo("Nothing to submit.")
        return

    for job in jobs:
        pkg = QUEUE_DIR / job["id"]
        if not pkg.exists():
            click.echo(f"Package missing for {job['id']} — run `pipeline run` first.")
            continue
        status = submit_job(job, pkg)
        click.echo(f"  {job['id']} → {status}")


@cli.command()
def status():
    """Print tracker summary grouped by status."""
    from pipeline.tracker.db import get_jobs
    from collections import Counter
    jobs = get_jobs()
    counts = Counter(j["status"] for j in jobs)
    click.echo(f"\nTracker: {len(jobs)} total jobs")
    for st, cnt in sorted(counts.items()):
        click.echo(f"  {st:20s} {cnt}")


@cli.command()
@click.option("--out", default=None, help="Output CSV file path.")
def export(out: str | None):
    """Export tracker to CSV."""
    from pipeline.tracker.db import export_csv
    from pathlib import Path
    path = export_csv(Path(out) if out else None)
    click.echo(f"Exported → {path}")


@cli.command()
def scheduler():
    """Start the daily scheduler (blocking)."""
    from pipeline.scheduler.runner import start_scheduler
    start_scheduler()


if __name__ == "__main__":
    cli()
