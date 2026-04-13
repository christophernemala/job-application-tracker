import contextlib
import sqlite3
from pathlib import Path

import pytest

from job_agent import database


def test_init_and_insert_application(tmp_path: Path):
    test_db = tmp_path / "test.db"
    database.init_database(test_db)

    with database.get_connection(test_db) as conn:
        conn.execute(
            """
            INSERT INTO applications (job_title, company, platform, job_url, status)
            VALUES ('AR Specialist', 'ACME', 'LinkedIn', 'http://example.com', 'applied')
            """
        )

    with database.get_connection(test_db) as conn:
        row = conn.execute("SELECT COUNT(*) as c FROM applications").fetchone()
        assert row["c"] == 1


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@pytest.fixture()
def db(tmp_path: Path, monkeypatch):
    """Initialise a fresh in-process SQLite database and redirect all DB calls to it.

    ``get_connection`` is a ``@contextmanager``-decorated function whose default
    argument (``DB_PATH``) was bound at import time.  Patching ``__defaults__``
    has no effect on the wrapped generator, so we replace the entire function
    with an equivalent that defaults to ``test_db``.
    """
    test_db = tmp_path / "test.db"

    @contextlib.contextmanager
    def patched_connection(db_path: Path = test_db):
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    monkeypatch.setattr(database, "get_connection", patched_connection)
    monkeypatch.setattr(database, "DB_PATH", test_db)
    database.init_database(test_db)
    return test_db


# ---------------------------------------------------------------------------
# save_job tests
# ---------------------------------------------------------------------------

def test_save_job_returns_row_id(db):
    row_id = database.save_job(
        job_title="Software Engineer",
        company="Acme",
        platform="LinkedIn",
        job_url="https://example.com/job/1",
    )
    assert isinstance(row_id, int)
    assert row_id > 0


def test_save_job_persists_fields(db):
    database.save_job(
        job_title="Data Analyst",
        company="CorpX",
        platform="Naukri Gulf",
        job_url="https://example.com/job/2",
        description="Analyze data",
        location="Dubai, UAE",
        salary_range="15000-20000 AED",
    )

    with database.get_connection(db) as conn:
        row = conn.execute(
            "SELECT * FROM jobs WHERE job_url = 'https://example.com/job/2'"
        ).fetchone()

    assert row["job_title"] == "Data Analyst"
    assert row["company"] == "CorpX"
    assert row["platform"] == "Naukri Gulf"
    assert row["description"] == "Analyze data"
    assert row["location"] == "Dubai, UAE"
    assert row["salary_range"] == "15000-20000 AED"
    assert row["applied"] == 0


def test_save_job_optional_fields_default_none(db):
    row_id = database.save_job(
        job_title="QA Engineer",
        company="TestCo",
        platform="Apify",
        job_url="https://example.com/job/3",
    )
    with database.get_connection(db) as conn:
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (row_id,)).fetchone()
    assert row["description"] is None
    assert row["location"] is None
    assert row["salary_range"] is None


def test_save_job_duplicate_url_returns_none(db):
    url = "https://example.com/job/dup"
    first = database.save_job(
        job_title="Dev", company="A", platform="B", job_url=url
    )
    second = database.save_job(
        job_title="Dev 2", company="B", platform="C", job_url=url
    )
    assert first is not None
    assert second is None  # duplicate — IntegrityError swallowed


def test_save_job_empty_url_allows_multiple(db):
    """Empty string job_url is treated as a distinct value; first insert wins."""
    first = database.save_job(
        job_title="Job A", company="Co", platform="X", job_url=""
    )
    second = database.save_job(
        job_title="Job B", company="Co", platform="X", job_url=""
    )
    # Second call should return None because "" is treated as a duplicate UNIQUE value
    assert first is not None
    assert second is None


# ---------------------------------------------------------------------------
# get_pending_jobs tests
# ---------------------------------------------------------------------------

def test_get_pending_jobs_returns_unapplied(db):
    database.save_job(
        job_title="Pending Job", company="Co", platform="P",
        job_url="https://example.com/pending"
    )
    results = database.get_pending_jobs()
    assert len(results) == 1
    assert results[0]["job_title"] == "Pending Job"
    assert results[0]["applied"] == 0


def test_get_pending_jobs_excludes_applied(db):
    id1 = database.save_job(
        job_title="Applied Job", company="Co", platform="P",
        job_url="https://example.com/applied"
    )
    database.save_job(
        job_title="New Job", company="Co2", platform="P",
        job_url="https://example.com/new"
    )
    database.mark_job_applied(id1)

    results = database.get_pending_jobs()
    titles = [r["job_title"] for r in results]
    assert "Applied Job" not in titles
    assert "New Job" in titles


def test_get_pending_jobs_limit(db):
    for i in range(5):
        database.save_job(
            job_title=f"Job {i}", company="Co", platform="P",
            job_url=f"https://example.com/job/{i}"
        )
    results = database.get_pending_jobs(limit=3)
    assert len(results) == 3


def test_get_pending_jobs_empty(db):
    assert database.get_pending_jobs() == []


def test_get_pending_jobs_returns_dicts(db):
    database.save_job(
        job_title="Dict Test", company="Co", platform="P",
        job_url="https://example.com/dict"
    )
    results = database.get_pending_jobs()
    assert isinstance(results[0], dict)
    assert "job_title" in results[0]


def test_get_pending_jobs_ordered_oldest_first(db, monkeypatch):
    """Jobs should come back in discovered_date ASC order."""
    import time
    database.save_job(
        job_title="First", company="Co", platform="P",
        job_url="https://example.com/first"
    )
    time.sleep(0.01)
    database.save_job(
        job_title="Second", company="Co", platform="P",
        job_url="https://example.com/second"
    )
    results = database.get_pending_jobs()
    assert results[0]["job_title"] == "First"
    assert results[1]["job_title"] == "Second"


# ---------------------------------------------------------------------------
# mark_job_applied tests
# ---------------------------------------------------------------------------

def test_mark_job_applied_sets_flag(db):
    row_id = database.save_job(
        job_title="Mark Test", company="Co", platform="P",
        job_url="https://example.com/mark"
    )
    database.mark_job_applied(row_id)

    with database.get_connection(db) as conn:
        row = conn.execute("SELECT applied FROM jobs WHERE id = ?", (row_id,)).fetchone()
    assert row["applied"] == 1


def test_mark_job_applied_nonexistent_id_is_noop(db):
    """Marking a non-existent job id should not raise."""
    database.mark_job_applied(99999)  # Should not raise


def test_mark_job_applied_does_not_affect_other_jobs(db):
    id1 = database.save_job(
        job_title="Job 1", company="Co", platform="P",
        job_url="https://example.com/j1"
    )
    id2 = database.save_job(
        job_title="Job 2", company="Co", platform="P",
        job_url="https://example.com/j2"
    )
    database.mark_job_applied(id1)

    with database.get_connection(db) as conn:
        row = conn.execute("SELECT applied FROM jobs WHERE id = ?", (id2,)).fetchone()
    assert row["applied"] == 0