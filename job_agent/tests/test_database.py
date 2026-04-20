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
# Helpers / fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def tmp_db(tmp_path, monkeypatch):
    """Initialise a fresh temporary database and redirect all no-arg DB calls to it.

    save_job, get_pending_jobs, and mark_job_applied call get_connection()
    without arguments, which uses the default DB_PATH captured at definition
    time.  We patch both the module attribute and the inner function's default
    so that all no-arg calls land on the temporary file.
    """
    test_db = tmp_path / "test.db"
    database.init_database(test_db)

    monkeypatch.setattr(database, "DB_PATH", test_db)

    # @contextmanager uses @wraps internally, which sets __wrapped__ to the
    # original generator function.  Patching its __defaults__ redirects
    # no-argument calls to our temporary file.
    inner_fn = database.get_connection.__wrapped__
    monkeypatch.setattr(inner_fn, "__defaults__", (test_db,))

    return test_db


# ---------------------------------------------------------------------------
# save_job
# ---------------------------------------------------------------------------

def test_save_job_returns_positive_integer_row_id(tmp_db):
    row_id = database.save_job(
        job_title="Software Engineer",
        company="Acme Corp",
        platform="Apify",
        job_url="https://example.com/jobs/1",
    )
    assert isinstance(row_id, int)
    assert row_id > 0


def test_save_job_persists_required_fields(tmp_db):
    database.save_job(
        job_title="Backend Developer",
        company="TechCo",
        platform="LinkedIn",
        job_url="https://example.com/jobs/backend",
    )
    with database.get_connection(tmp_db) as conn:
        row = conn.execute(
            "SELECT * FROM jobs WHERE job_url = ?",
            ("https://example.com/jobs/backend",),
        ).fetchone()
    assert row is not None
    assert row["job_title"] == "Backend Developer"
    assert row["company"] == "TechCo"
    assert row["platform"] == "LinkedIn"
    assert row["applied"] == 0  # default is unapplied


def test_save_job_persists_all_optional_fields(tmp_db):
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
        row = conn.execute(
            "SELECT * FROM jobs WHERE job_url = ?",
            ("https://example.com/jobs/2",),
        ).fetchone()
    assert row["description"] == "Analyse data"
    assert row["location"] == "Dubai, UAE"
    assert row["salary_range"] == "15000-20000 AED"


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


def test_save_job_duplicate_url_does_not_raise(tmp_db):
    """Duplicate insert should silently return None, not propagate an exception."""
    database.save_job(
        job_title="Role A",
        company="Corp",
        platform="Apify",
        job_url="https://example.com/jobs/silent-dup",
    )
    try:
        database.save_job(
            job_title="Role A",
            company="Corp",
            platform="Apify",
            job_url="https://example.com/jobs/silent-dup",
        )
    except Exception as exc:
        pytest.fail(f"save_job raised on duplicate URL: {exc}")


def test_save_job_multiple_unique_urls_each_get_distinct_ids(tmp_db):
    id1 = database.save_job(
        job_title="Job X",
        company="Co",
        platform="Apify",
        job_url="https://example.com/x",
    )
    id2 = database.save_job(
        job_title="Job Y",
        company="Co",
        platform="Apify",
        job_url="https://example.com/y",
    )
    assert id1 != id2
    assert isinstance(id1, int) and isinstance(id2, int)


def test_save_job_empty_url_stored_without_uniqueness_collision(tmp_db):
    """Empty string job_url is treated as a value; first insert succeeds."""
    row_id = database.save_job(
        job_title="Mystery Role",
        company="Unknown",
        platform="Naukri",
        job_url="",
    )
    assert row_id is not None


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


def test_get_pending_jobs_excludes_applied_jobs(tmp_db):
    row_id = database.save_job(
        job_title="Applied Job",
        company="Zeta",
        platform="Apify",
        job_url="https://example.com/jobs/applied",
    )
    database.mark_job_applied(row_id)
    jobs = database.get_pending_jobs()
    assert jobs == []


def test_get_pending_jobs_empty_when_no_jobs(tmp_db):
    assert database.get_pending_jobs() == []


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


def test_get_pending_jobs_returns_all_when_under_limit(tmp_db):
    for i in range(3):
        database.save_job(
            job_title=f"Job {i}",
            company="Company",
            platform="Apify",
            job_url=f"https://example.com/jobs/under/{i}",
        )
    jobs = database.get_pending_jobs(limit=10)
    assert len(jobs) == 3


def test_get_pending_jobs_oldest_first(tmp_db):
    """Jobs should be returned in ascending discovered_date / insertion order."""
    for i in range(4):
        database.save_job(
            job_title=f"Job {i}",
            company="Company",
            platform="Apify",
            job_url=f"https://example.com/jobs/order/{i}",
        )
    jobs = database.get_pending_jobs()
    ids = [j["id"] for j in jobs]
    assert ids == sorted(ids)


def test_get_pending_jobs_returns_list_of_dicts(tmp_db):
    database.save_job(
        job_title="Dict Job",
        company="Company",
        platform="Apify",
        job_url="https://example.com/jobs/dict",
    )
    jobs = database.get_pending_jobs()
    assert isinstance(jobs, list)
    assert isinstance(jobs[0], dict)


def test_get_pending_jobs_only_returns_pending_not_applied(tmp_db):
    """Mixed set: only pending jobs should be returned."""
    pending_id = database.save_job(
        job_title="Still Pending",
        company="A",
        platform="Apify",
        job_url="https://example.com/jobs/still-pending",
    )
    applied_id = database.save_job(
        job_title="Already Applied",
        company="B",
        platform="Apify",
        job_url="https://example.com/jobs/already-applied",
    )
    database.mark_job_applied(applied_id)

    jobs = database.get_pending_jobs()
    titles = [j["job_title"] for j in jobs]
    assert "Still Pending" in titles
    assert "Already Applied" not in titles


def test_get_pending_jobs_default_limit_is_twenty(tmp_db):
    """Without specifying a limit the default of 20 is applied."""
    for i in range(25):
        database.save_job(
            job_title=f"Bulk Job {i}",
            company="BulkCo",
            platform="Apify",
            job_url=f"https://example.com/jobs/bulk/{i}",
        )
    jobs = database.get_pending_jobs()
    assert len(jobs) == 20


# ---------------------------------------------------------------------------
# mark_job_applied
# ---------------------------------------------------------------------------

def test_mark_job_applied_sets_applied_flag(tmp_db):
    row_id = database.save_job(
        job_title="To Apply",
        company="Eta Corp",
        platform="Apify",
        job_url="https://example.com/jobs/eta",
    )
    database.mark_job_applied(row_id)
    with database.get_connection(tmp_db) as conn:
        row = conn.execute(
            "SELECT applied FROM jobs WHERE id = ?", (row_id,)
        ).fetchone()
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
        row2 = conn.execute(
            "SELECT applied FROM jobs WHERE id = ?", (id2,)
        ).fetchone()
    assert row2["applied"] == 0


def test_mark_job_applied_nonexistent_id_is_noop(tmp_db):
    """mark_job_applied with a non-existent id should not raise."""
    database.mark_job_applied(99999)  # must not raise


def test_mark_job_applied_idempotent(tmp_db):
    """Calling mark_job_applied twice should leave the job in the applied state."""
    row_id = database.save_job(
        job_title="Double Apply",
        company="Corp",
        platform="Apify",
        job_url="https://example.com/jobs/double",
    )
    database.mark_job_applied(row_id)
    database.mark_job_applied(row_id)  # second call must not raise

    with database.get_connection(tmp_db) as conn:
        row = conn.execute(
            "SELECT applied FROM jobs WHERE id = ?", (row_id,)
        ).fetchone()
    assert row["applied"] == 1