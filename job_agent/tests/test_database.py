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
def tmp_db(tmp_path, monkeypatch):
    """Initialise a fresh temporary database and redirect all DB access to it.

    The new functions (save_job, get_pending_jobs, mark_job_applied) call
    get_connection() with no arguments, so they use the default DB_PATH value
    that was captured at function-definition time.  Monkeypatching the module
    attribute alone is not enough; we must also patch the inner function's
    __defaults__ (the @contextmanager wrapper preserves the original via
    __wrapped__).
    """
    test_db = tmp_path / "test.db"
    database.init_database(test_db)

    # Update the module-level attribute so explicit callers (e.g. test helpers)
    # also land on the temp file.
    monkeypatch.setattr(database, "DB_PATH", test_db)

    # Patch the default argument of the original (un-wrapped) function so that
    # no-arg calls to get_connection() go to the temp file.
    inner_fn = database.get_connection.__wrapped__
    monkeypatch.setattr(inner_fn, "__defaults__", (test_db,))

    return test_db


# ---------------------------------------------------------------------------
# save_job
# ---------------------------------------------------------------------------

def test_save_job_returns_row_id(tmp_db):
    row_id = database.save_job(
        job_title="Software Engineer",
        company="Acme Corp",
        platform="Apify",
        job_url="https://example.com/jobs/1",
    )
    assert isinstance(row_id, int)
    assert row_id > 0


def test_save_job_persists_all_fields(tmp_db):
    database.save_job(
        job_title="Data Analyst",
        company="Beta Ltd",
        platform="LinkedIn",
        job_url="https://example.com/jobs/2",
        description="Analyse data",
        location="Dubai, UAE",
        salary_range="15000-20000 AED",
    )
    with database.get_connection(tmp_db) as conn:
        row = conn.execute("SELECT * FROM jobs WHERE job_url = ?", ("https://example.com/jobs/2",)).fetchone()
    assert row is not None
    assert row["job_title"] == "Data Analyst"
    assert row["company"] == "Beta Ltd"
    assert row["platform"] == "LinkedIn"
    assert row["description"] == "Analyse data"
    assert row["location"] == "Dubai, UAE"
    assert row["salary_range"] == "15000-20000 AED"
    assert row["applied"] == 0  # default is unapplied


def test_save_job_duplicate_url_returns_none(tmp_db):
    database.save_job(
        job_title="DevOps Engineer",
        company="Gamma Inc",
        platform="Apify",
        job_url="https://example.com/jobs/dup",
    )
    result = database.save_job(
        job_title="DevOps Engineer",
        company="Gamma Inc",
        platform="Apify",
        job_url="https://example.com/jobs/dup",
    )
    assert result is None


def test_save_job_optional_fields_default_to_none(tmp_db):
    row_id = database.save_job(
        job_title="QA Engineer",
        company="Delta Co",
        platform="Naukri",
        job_url="https://example.com/jobs/qa",
    )
    with database.get_connection(tmp_db) as conn:
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (row_id,)).fetchone()
    assert row["description"] is None
    assert row["location"] is None
    assert row["salary_range"] is None


# ---------------------------------------------------------------------------
# get_pending_jobs
# ---------------------------------------------------------------------------

def test_get_pending_jobs_returns_unapplied(tmp_db):
    database.save_job(
        job_title="Pending Job",
        company="Epsilon",
        platform="Apify",
        job_url="https://example.com/jobs/pending",
    )
    jobs = database.get_pending_jobs()
    assert len(jobs) == 1
    assert jobs[0]["job_title"] == "Pending Job"
    assert jobs[0]["applied"] == 0


def test_get_pending_jobs_excludes_applied(tmp_db):
    row_id = database.save_job(
        job_title="Applied Job",
        company="Zeta",
        platform="Apify",
        job_url="https://example.com/jobs/applied",
    )
    database.mark_job_applied(row_id)
    jobs = database.get_pending_jobs()
    assert jobs == []


def test_get_pending_jobs_respects_limit(tmp_db):
    for i in range(5):
        database.save_job(
            job_title=f"Job {i}",
            company="Company",
            platform="Apify",
            job_url=f"https://example.com/jobs/{i}",
        )
    jobs = database.get_pending_jobs(limit=3)
    assert len(jobs) == 3


def test_get_pending_jobs_oldest_first(tmp_db):
    """Jobs should be returned in ascending discovered_date order."""
    for i in range(3):
        database.save_job(
            job_title=f"Job {i}",
            company="Company",
            platform="Apify",
            job_url=f"https://example.com/jobs/order/{i}",
        )
    jobs = database.get_pending_jobs()
    ids = [j["id"] for j in jobs]
    assert ids == sorted(ids)


def test_get_pending_jobs_returns_dicts(tmp_db):
    database.save_job(
        job_title="Dict Job",
        company="Company",
        platform="Apify",
        job_url="https://example.com/jobs/dict",
    )
    jobs = database.get_pending_jobs()
    assert isinstance(jobs[0], dict)


def test_get_pending_jobs_empty_when_no_jobs(tmp_db):
    assert database.get_pending_jobs() == []


# ---------------------------------------------------------------------------
# mark_job_applied
# ---------------------------------------------------------------------------

def test_mark_job_applied_sets_flag(tmp_db):
    row_id = database.save_job(
        job_title="To Apply",
        company="Eta Corp",
        platform="Apify",
        job_url="https://example.com/jobs/eta",
    )
    database.mark_job_applied(row_id)
    with database.get_connection(tmp_db) as conn:
        row = conn.execute("SELECT applied FROM jobs WHERE id = ?", (row_id,)).fetchone()
    assert row["applied"] == 1


def test_mark_job_applied_does_not_affect_other_jobs(tmp_db):
    id1 = database.save_job(
        job_title="Job A",
        company="A",
        platform="Apify",
        job_url="https://example.com/jobs/a",
    )
    id2 = database.save_job(
        job_title="Job B",
        company="B",
        platform="Apify",
        job_url="https://example.com/jobs/b",
    )
    database.mark_job_applied(id1)
    with database.get_connection(tmp_db) as conn:
        row2 = conn.execute("SELECT applied FROM jobs WHERE id = ?", (id2,)).fetchone()
    assert row2["applied"] == 0


def test_mark_job_applied_nonexistent_id_is_noop(tmp_db):
    """mark_job_applied on a non-existent id should not raise."""
    database.mark_job_applied(99999)  # should not raise