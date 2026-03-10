"""Repository for the jobs table.

Provides insert, upsert, query, and deduplication helpers
for job postings collected from various sources.
"""

from datetime import datetime, timedelta
from typing import Optional

from src.storage.database import get_connection
from src.utils.logger import get_logger

logger = get_logger(__name__)


def insert_job(
    source: str,
    title: str,
    url: str,
    company: Optional[str] = None,
    location: Optional[str] = None,
    salary_text: Optional[str] = None,
    salary_min: Optional[float] = None,
    salary_max: Optional[float] = None,
    posted_date: Optional[str] = None,
    description: Optional[str] = None,
    normalized_title: Optional[str] = None,
    apply_type: str = "unknown",
) -> Optional[int]:
    """Insert a new job if it doesn't already exist.

    Args:
        source: Source name (e.g., 'linkedin', 'naukrigulf').
        title: Raw job title.
        url: Job posting URL.
        company: Company name.
        location: Job location.
        salary_text: Raw salary text.
        salary_min: Parsed minimum salary.
        salary_max: Parsed maximum salary.
        posted_date: Posted date string.
        description: Job description text.
        normalized_title: Cleaned/normalized title.
        apply_type: Application type classification.

    Returns:
        The inserted row ID, or None if duplicate.
    """
    with get_connection() as conn:
        try:
            cursor = conn.execute(
                """
                INSERT INTO jobs (
                    source, title, normalized_title, company, location,
                    salary_text, salary_min, salary_max, posted_date, url,
                    description, apply_type
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    source, title, normalized_title, company, location,
                    salary_text, salary_min, salary_max, posted_date, url,
                    description, apply_type,
                ),
            )
            job_id = cursor.lastrowid
            logger.info("Inserted job id=%d source=%s title=%s", job_id, source, title)
            return job_id
        except Exception as e:
            if "UNIQUE constraint" in str(e):
                logger.debug("Duplicate job skipped: source=%s url=%s", source, url)
                return None
            raise


def upsert_job(
    source: str,
    title: str,
    url: str,
    **kwargs,
) -> int:
    """Insert or update a job by source + url.

    Args:
        source: Source name.
        title: Job title.
        url: Job URL.
        **kwargs: Additional fields to insert/update.

    Returns:
        The job row ID.
    """
    with get_connection() as conn:
        # Check if exists
        row = conn.execute(
            "SELECT id FROM jobs WHERE source = ? AND url = ?",
            (source, url),
        ).fetchone()

        if row:
            # Update existing
            update_fields = []
            update_values = []
            for key, value in kwargs.items():
                if value is not None:
                    update_fields.append(f"{key} = ?")
                    update_values.append(value)

            if update_fields:
                update_fields.append("updated_at = datetime('now')")
                update_values.append(row["id"])
                conn.execute(
                    f"UPDATE jobs SET {', '.join(update_fields)} WHERE id = ?",
                    update_values,
                )
                logger.debug("Updated job id=%d", row["id"])
            return row["id"]
        else:
            # Insert new
            cursor = conn.execute(
                """
                INSERT INTO jobs (
                    source, title, normalized_title, company, location,
                    salary_text, salary_min, salary_max, posted_date, url,
                    description, apply_type
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    source,
                    title,
                    kwargs.get("normalized_title"),
                    kwargs.get("company"),
                    kwargs.get("location"),
                    kwargs.get("salary_text"),
                    kwargs.get("salary_min"),
                    kwargs.get("salary_max"),
                    kwargs.get("posted_date"),
                    url,
                    kwargs.get("description"),
                    kwargs.get("apply_type", "unknown"),
                ),
            )
            logger.info("Inserted job id=%d via upsert", cursor.lastrowid)
            return cursor.lastrowid


def get_job_by_id(job_id: int) -> Optional[dict]:
    """Fetch a single job by its ID.

    Returns:
        Job dict or None if not found.
    """
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return dict(row) if row else None


def get_jobs_by_status(route_status: str, limit: int = 100) -> list[dict]:
    """Fetch jobs by their routing status.

    Args:
        route_status: One of 'auto_apply', 'semi_auto', 'manual_review', 'reject', 'pending'.
        limit: Max results.

    Returns:
        List of job dicts.
    """
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM jobs WHERE route_status = ? ORDER BY score DESC LIMIT ?",
            (route_status, limit),
        ).fetchall()
        return [dict(r) for r in rows]


def update_job_score(job_id: int, score: float, score_reason: str) -> None:
    """Update the score and reason for a job.

    Args:
        job_id: Job ID to update.
        score: Calculated relevance score (0-100).
        score_reason: Human-readable scoring breakdown.
    """
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE jobs
            SET score = ?, score_reason = ?, updated_at = datetime('now')
            WHERE id = ?
            """,
            (score, score_reason, job_id),
        )
        logger.debug("Updated score for job id=%d: score=%.1f", job_id, score)


def update_job_route(job_id: int, route_status: str) -> None:
    """Update the routing status for a job.

    Args:
        job_id: Job ID.
        route_status: One of 'auto_apply', 'semi_auto', 'manual_review', 'reject'.
    """
    valid_statuses = {"auto_apply", "semi_auto", "manual_review", "reject", "pending"}
    if route_status not in valid_statuses:
        raise ValueError(f"Invalid route_status '{route_status}'. Must be one of {valid_statuses}")

    with get_connection() as conn:
        conn.execute(
            """
            UPDATE jobs
            SET route_status = ?, updated_at = datetime('now')
            WHERE id = ?
            """,
            (route_status, job_id),
        )
        logger.info("Routed job id=%d to %s", job_id, route_status)


def is_duplicate_job(
    source: str,
    url: str,
    company: Optional[str] = None,
    title: Optional[str] = None,
    window_days: int = 30,
) -> bool:
    """Check if a job is a duplicate within the deduplication window.

    Checks by source + url (primary), and optionally by company + title
    within the time window.

    Args:
        source: Source name.
        url: Job URL.
        company: Company name for fuzzy dedup.
        title: Job title for fuzzy dedup.
        window_days: Days to look back for duplicates.

    Returns:
        True if duplicate found.
    """
    with get_connection() as conn:
        # Exact match by source + url
        row = conn.execute(
            "SELECT id FROM jobs WHERE source = ? AND url = ?",
            (source, url),
        ).fetchone()
        if row:
            return True

        # Fuzzy match by company + title within window
        if company and title:
            cutoff = (datetime.now() - timedelta(days=window_days)).isoformat()
            row = conn.execute(
                """
                SELECT id FROM jobs
                WHERE company = ? AND title = ? AND created_at >= ?
                """,
                (company, title, cutoff),
            ).fetchone()
            if row:
                logger.debug(
                    "Fuzzy duplicate found: company=%s title=%s", company, title
                )
                return True

        return False


def list_recent_jobs(limit: int = 50, source: Optional[str] = None) -> list[dict]:
    """List recently collected jobs.

    Args:
        limit: Max number of jobs.
        source: Optional filter by source.

    Returns:
        List of job dicts ordered by creation date descending.
    """
    with get_connection() as conn:
        if source:
            rows = conn.execute(
                "SELECT * FROM jobs WHERE source = ? ORDER BY created_at DESC LIMIT ?",
                (source, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]
