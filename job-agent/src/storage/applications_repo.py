"""Repository for the applications table.

Tracks every application attempt with result, evidence,
and failure reasons for auditability.
"""

from typing import Optional

from src.storage.database import get_connection
from src.utils.logger import get_logger

logger = get_logger(__name__)


def insert_application(
    job_id: int,
    source: Optional[str] = None,
    resume_used: Optional[str] = None,
    result: str = "pending",
) -> int:
    """Record a new application attempt.

    Args:
        job_id: Foreign key to the jobs table.
        source: Source platform name.
        resume_used: Path/name of resume variant used.
        result: Initial result status.

    Returns:
        The application row ID.

    Raises:
        sqlite3.IntegrityError: If application for this job_id already exists.
    """
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO applications (job_id, source, resume_used, result)
            VALUES (?, ?, ?, ?)
            """,
            (job_id, source, resume_used, result),
        )
        app_id = cursor.lastrowid
        logger.info(
            "Recorded application id=%d for job_id=%d result=%s",
            app_id, job_id, result,
        )
        return app_id


def update_application_result(
    job_id: int,
    result: str,
    confirmation_text: Optional[str] = None,
    screenshot_path: Optional[str] = None,
    failure_reason: Optional[str] = None,
) -> None:
    """Update the result of an application.

    Args:
        job_id: The job ID this application belongs to.
        result: Outcome ('success', 'failure', 'partial', 'pending').
        confirmation_text: Any confirmation message captured.
        screenshot_path: Path to screenshot evidence.
        failure_reason: Reason for failure if applicable.
    """
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE applications
            SET result = ?,
                confirmation_text = COALESCE(?, confirmation_text),
                screenshot_path = COALESCE(?, screenshot_path),
                failure_reason = COALESCE(?, failure_reason)
            WHERE job_id = ?
            """,
            (result, confirmation_text, screenshot_path, failure_reason, job_id),
        )
        logger.info("Updated application for job_id=%d: result=%s", job_id, result)


def get_application_by_job_id(job_id: int) -> Optional[dict]:
    """Get the application record for a specific job.

    Args:
        job_id: Job ID to look up.

    Returns:
        Application dict or None.
    """
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM applications WHERE job_id = ?", (job_id,)
        ).fetchone()
        return dict(row) if row else None


def list_applications(
    result_filter: Optional[str] = None, limit: int = 100
) -> list[dict]:
    """List application records.

    Args:
        result_filter: Optional filter by result status.
        limit: Max results.

    Returns:
        List of application dicts with joined job info.
    """
    with get_connection() as conn:
        if result_filter:
            rows = conn.execute(
                """
                SELECT a.*, j.title, j.company, j.url as job_url
                FROM applications a
                JOIN jobs j ON a.job_id = j.id
                WHERE a.result = ?
                ORDER BY a.applied_at DESC
                LIMIT ?
                """,
                (result_filter, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT a.*, j.title, j.company, j.url as job_url
                FROM applications a
                JOIN jobs j ON a.job_id = j.id
                ORDER BY a.applied_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]


def has_applied(job_id: int) -> bool:
    """Check if an application has already been submitted for a job.

    Args:
        job_id: Job ID to check.

    Returns:
        True if an application record exists.
    """
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM applications WHERE job_id = ?", (job_id,)
        ).fetchone()
        return row is not None
