"""SQLite database initialization and connection management.

Creates the schema on first run and provides a context-managed
connection factory for all repository modules.
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from src.utils.logger import get_logger
from src.utils.config_loader import get_db_path

logger = get_logger(__name__)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS jobs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source          TEXT NOT NULL,
    title           TEXT NOT NULL,
    normalized_title TEXT,
    company         TEXT,
    location        TEXT,
    salary_text     TEXT,
    salary_min      REAL,
    salary_max      REAL,
    posted_date     TEXT,
    url             TEXT NOT NULL,
    description     TEXT,
    apply_type      TEXT DEFAULT 'unknown',
    score           REAL DEFAULT 0,
    score_reason    TEXT,
    route_status    TEXT DEFAULT 'pending',
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_jobs_dedup
    ON jobs (source, url);

CREATE INDEX IF NOT EXISTS idx_jobs_route_status
    ON jobs (route_status);

CREATE INDEX IF NOT EXISTS idx_jobs_score
    ON jobs (score DESC);

CREATE TABLE IF NOT EXISTS applications (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id            INTEGER NOT NULL REFERENCES jobs(id),
    applied_at        TEXT NOT NULL DEFAULT (datetime('now')),
    source            TEXT,
    result            TEXT DEFAULT 'pending',
    confirmation_text TEXT,
    screenshot_path   TEXT,
    resume_used       TEXT,
    failure_reason    TEXT,
    UNIQUE(job_id)
);

CREATE INDEX IF NOT EXISTS idx_applications_result
    ON applications (result);

CREATE TABLE IF NOT EXISTS run_logs (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    run_started_at    TEXT NOT NULL DEFAULT (datetime('now')),
    run_completed_at  TEXT,
    source            TEXT,
    total_found       INTEGER DEFAULT 0,
    total_new         INTEGER DEFAULT 0,
    total_scored      INTEGER DEFAULT 0,
    total_applied     INTEGER DEFAULT 0,
    total_failed      INTEGER DEFAULT 0,
    notes             TEXT
);

CREATE TABLE IF NOT EXISTS profile_rules (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_type   TEXT NOT NULL,
    rule_key    TEXT NOT NULL,
    rule_value  TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(rule_type, rule_key)
);
"""


def init_database(db_path: Path | None = None) -> None:
    """Create database tables if they don't exist.

    Args:
        db_path: Optional override for database path. Uses default if None.
    """
    path = db_path or get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(str(path)) as conn:
        conn.executescript(SCHEMA_SQL)

    logger.info("Database initialized at %s", path)


@contextmanager
def get_connection(db_path: Path | None = None) -> Generator[sqlite3.Connection, None, None]:
    """Context manager for SQLite connections.

    Yields a connection with row_factory set to sqlite3.Row,
    auto-commits on clean exit, rolls back on exception.

    Args:
        db_path: Optional override for database path.

    Yields:
        sqlite3.Connection with Row factory.
    """
    path = db_path or get_db_path()
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
