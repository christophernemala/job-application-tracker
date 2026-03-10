"""Repository for the run_logs table.

Tracks each execution run with counters for found, scored,
applied, and failed jobs per source.
"""

from datetime import datetime
from typing import Optional

from src.storage.database import get_connection
from src.utils.logger import get_logger

logger = get_logger(__name__)


def insert_run_log(source: str, notes: Optional[str] = None) -> int:
    """Create a new run log entry at the start of a run.

    Args:
        source: Source being processed.
        notes: Optional notes about this run.

    Returns:
        The run log row ID.
    """
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO run_logs (source, notes)
            VALUES (?, ?)
            """,
            (source, notes),
        )
        run_id = cursor.lastrowid
        logger.info("Created run_log id=%d for source=%s", run_id, source)
        return run_id


def update_run_log(
    run_id: int,
    total_found: int = 0,
    total_new: int = 0,
    total_scored: int = 0,
    total_applied: int = 0,
    total_failed: int = 0,
    notes: Optional[str] = None,
) -> None:
    """Update a run log entry at the end of a run.

    Args:
        run_id: Run log ID to update.
        total_found: Total job listings found.
        total_new: New (non-duplicate) jobs added.
        total_scored: Jobs scored by the engine.
        total_applied: Successful applications.
        total_failed: Failed application attempts.
        notes: Additional notes.
    """
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE run_logs
            SET run_completed_at = datetime('now'),
                total_found = ?,
                total_new = ?,
                total_scored = ?,
                total_applied = ?,
                total_failed = ?,
                notes = COALESCE(?, notes)
            WHERE id = ?
            """,
            (total_found, total_new, total_scored, total_applied, total_failed, notes, run_id),
        )
        logger.info(
            "Updated run_log id=%d: found=%d new=%d scored=%d applied=%d failed=%d",
            run_id, total_found, total_new, total_scored, total_applied, total_failed,
        )


def get_latest_run_log(source: Optional[str] = None) -> Optional[dict]:
    """Get the most recent run log entry.

    Args:
        source: Optional filter by source.

    Returns:
        Run log dict or None.
    """
    with get_connection() as conn:
        if source:
            row = conn.execute(
                """
                SELECT * FROM run_logs
                WHERE source = ?
                ORDER BY run_started_at DESC
                LIMIT 1
                """,
                (source,),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT * FROM run_logs ORDER BY run_started_at DESC LIMIT 1"
            ).fetchone()
        return dict(row) if row else None


def list_run_logs(limit: int = 20) -> list[dict]:
    """List recent run logs.

    Args:
        limit: Max number of entries.

    Returns:
        List of run log dicts.
    """
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM run_logs ORDER BY run_started_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
