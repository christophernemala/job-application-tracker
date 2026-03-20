"""SQLite tracker — CRUD operations for the job pipeline."""
from __future__ import annotations
import json
import sqlite3
from datetime import datetime, date
from pathlib import Path

from pipeline.config import TRACKER_DB
from pipeline.utils.logger import get_logger

log = get_logger(__name__)

_SCHEMA = Path(__file__).parent / "schema.sql"


# ---------------------------------------------------------------------------
# Connection factory
# ---------------------------------------------------------------------------

def get_conn(db_path: Path = TRACKER_DB) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(db_path: Path = TRACKER_DB) -> None:
    """Create tables if they don't exist."""
    sql = _SCHEMA.read_text(encoding="utf-8")
    with get_conn(db_path) as conn:
        conn.executescript(sql)
    log.info("Tracker DB initialised at %s", db_path)


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------

def get_seen_ids(db_path: Path = TRACKER_DB) -> set[str]:
    """Return all job IDs already in the tracker (for dedup)."""
    try:
        with get_conn(db_path) as conn:
            rows = conn.execute("SELECT id FROM jobs").fetchall()
        return {r["id"] for r in rows}
    except sqlite3.OperationalError:
        return set()


def get_jobs(
    status: str | None = None,
    db_path: Path = TRACKER_DB,
) -> list[dict]:
    """Fetch all jobs, optionally filtered by status."""
    with get_conn(db_path) as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM jobs WHERE status=? ORDER BY score DESC", (status,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM jobs ORDER BY score DESC"
            ).fetchall()
    return [dict(r) for r in rows]


def get_queue(db_path: Path = TRACKER_DB) -> list[dict]:
    """Jobs that are shortlisted but not yet applied."""
    return get_jobs(status="shortlisted", db_path=db_path)


# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------

def _now() -> str:
    return datetime.utcnow().isoformat(timespec="seconds")


def upsert_job(job: dict, db_path: Path = TRACKER_DB) -> None:
    """Insert or update a job record."""
    missing_skills = json.dumps(job.get("missing_skills") or [])
    shortlist_reason = ", ".join(job.get("matched_titles") or [])

    with get_conn(db_path) as conn:
        conn.execute(
            """
            INSERT INTO jobs (
                id, date_captured, company, title, location,
                salary_text, salary_aed_min, source, url, score,
                shortlist_reason, missing_skills, cv_file,
                status, apply_mode, easy_apply_url, updated_at
            ) VALUES (
                :id, :date_captured, :company, :title, :location,
                :salary_text, :salary_aed_min, :source, :url, :score,
                :shortlist_reason, :missing_skills, :cv_file,
                :status, :apply_mode, :easy_apply_url, :updated_at
            )
            ON CONFLICT(id) DO UPDATE SET
                score           = excluded.score,
                cv_file         = excluded.cv_file,
                apply_mode      = excluded.apply_mode,
                status          = CASE
                    WHEN jobs.status IN ('applied','skipped') THEN jobs.status
                    ELSE excluded.status
                END,
                updated_at      = excluded.updated_at
            """,
            {
                "id": job["id"],
                "date_captured": str(date.today()),
                "company": job.get("company", ""),
                "title": job.get("title", ""),
                "location": job.get("location", ""),
                "salary_text": job.get("salary_text", ""),
                "salary_aed_min": job.get("salary_aed_min"),
                "source": job.get("source", ""),
                "url": job.get("url", ""),
                "score": job.get("score", 0),
                "shortlist_reason": shortlist_reason,
                "missing_skills": missing_skills,
                "cv_file": str(job.get("cv_file") or ""),
                "status": job.get("status", "shortlisted"),
                "apply_mode": job.get("apply_mode", ""),
                "easy_apply_url": job.get("easy_apply_url", ""),
                "updated_at": _now(),
            },
        )


def update_status(
    job_id: str,
    status: str,
    notes: str = "",
    applied_at: str | None = None,
    db_path: Path = TRACKER_DB,
) -> None:
    with get_conn(db_path) as conn:
        conn.execute(
            """
            UPDATE jobs SET status=?, notes=?, applied_at=?, updated_at=?
            WHERE id=?
            """,
            (status, notes, applied_at or "", _now(), job_id),
        )


def log_run(
    jobs_found: int,
    shortlisted: int,
    applied: int,
    errors: int = 0,
    notes: str = "",
    db_path: Path = TRACKER_DB,
) -> None:
    with get_conn(db_path) as conn:
        conn.execute(
            """
            INSERT INTO run_log (jobs_found, shortlisted, applied, errors, notes)
            VALUES (?,?,?,?,?)
            """,
            (jobs_found, shortlisted, applied, errors, notes),
        )


# ---------------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------------

def export_csv(out_path: Path | None = None, db_path: Path = TRACKER_DB) -> Path:
    import csv
    out = out_path or (TRACKER_DB.parent / "tracker_export.csv")
    jobs = get_jobs(db_path=db_path)
    if not jobs:
        log.warning("No jobs to export.")
        return out
    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=jobs[0].keys())
        writer.writeheader()
        writer.writerows(jobs)
    log.info("Exported %d jobs → %s", len(jobs), out)
    return out
