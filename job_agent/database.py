"""SQLite persistence layer for the AI Job Agent."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).resolve().parent / "job_agent.db"


@contextmanager
def get_connection(db_path: Path = DB_PATH):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_database(db_path: Path = DB_PATH) -> None:
    """Initialize SQLite database with schema for jobs, applications, and logs."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_title TEXT NOT NULL,
                company TEXT NOT NULL,
                platform TEXT NOT NULL,
                job_url TEXT,
                applied_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'applied',
                match_score INTEGER,
                cover_letter TEXT,
                resume_version TEXT,
                application_id TEXT,
                screenshot_path TEXT,
                response_received BOOLEAN DEFAULT 0,
                interview_date TIMESTAMP,
                notes TEXT
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_title TEXT NOT NULL,
                company TEXT NOT NULL,
                platform TEXT NOT NULL,
                job_url TEXT UNIQUE,
                discovered_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                description TEXT,
                salary_range TEXT,
                location TEXT,
                applied BOOLEAN DEFAULT 0,
                match_score INTEGER,
                skills_required TEXT
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                action TEXT,
                status TEXT,
                error_message TEXT,
                job_id INTEGER
            )
            """
        )


def save_application(
    *,
    job_title: str,
    company: str,
    platform: str,
    job_url: str,
    status: str,
    match_score: int | None,
    cover_letter: str | None,
    resume_path: str | None,
    screenshot_path: str | None = None,
) -> int:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO applications
            (job_title, company, platform, job_url, status, match_score, cover_letter, resume_version, screenshot_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job_title,
                company,
                platform,
                job_url,
                status,
                match_score,
                cover_letter,
                resume_path,
                screenshot_path,
            ),
        )
        return int(cursor.lastrowid)


def get_application(application_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT
                id, job_title, company, platform, job_url,
                applied_date, status, match_score, cover_letter,
                resume_version, screenshot_path, notes
            FROM applications
            WHERE id = ?
            """,
            (application_id,),
        ).fetchone()
        return dict(row) if row else None


def list_applications() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                id, job_title, company, platform, applied_date,
                status, match_score
            FROM applications
            ORDER BY applied_date DESC
            """
        ).fetchall()
        return [dict(r) for r in rows]


def update_application_notes(application_id: int, notes: str) -> bool:
    with get_connection() as conn:
        result = conn.execute(
            "UPDATE applications SET notes = ? WHERE id = ?",
            (notes, application_id),
        )
        return result.rowcount > 0


def log_event(action: str, status: str, error_message: str | None = None, job_id: int | None = None) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO logs (action, status, error_message, job_id)
            VALUES (?, ?, ?, ?)
            """,
            (action, status, error_message, job_id),
        )
