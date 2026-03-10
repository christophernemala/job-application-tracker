"""Tests for the storage module – database init, jobs, applications, run logs."""

import sqlite3
import tempfile
from pathlib import Path

import pytest

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class TestDatabaseInit:
    """Test database schema creation."""

    def test_init_creates_tables(self, tmp_path):
        """Database init creates all required tables."""
        db_path = tmp_path / "test.db"

        from src.storage.database import init_database
        init_database(db_path)

        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()

        assert "jobs" in tables
        assert "applications" in tables
        assert "run_logs" in tables
        assert "profile_rules" in tables

    def test_init_is_idempotent(self, tmp_path):
        """Calling init_database twice doesn't raise errors."""
        db_path = tmp_path / "test.db"

        from src.storage.database import init_database
        init_database(db_path)
        init_database(db_path)  # Should not raise

    def test_jobs_table_has_correct_columns(self, tmp_path):
        """Jobs table has all expected columns."""
        db_path = tmp_path / "test.db"

        from src.storage.database import init_database
        init_database(db_path)

        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute("PRAGMA table_info(jobs)")
        columns = {row[1] for row in cursor.fetchall()}
        conn.close()

        expected = {
            "id", "source", "title", "normalized_title", "company",
            "location", "salary_text", "salary_min", "salary_max",
            "posted_date", "url", "description", "apply_type",
            "score", "score_reason", "route_status",
            "created_at", "updated_at",
        }
        assert expected.issubset(columns)


class TestJobsRepo:
    """Test jobs repository operations."""

    def test_insert_job(self, temp_db):
        """Insert a job and retrieve it."""
        from src.storage.jobs_repo import insert_job, get_job_by_id

        job_id = insert_job(
            source="linkedin",
            title="Senior AR Analyst",
            url="https://linkedin.com/jobs/123",
            company="Test Corp",
            location="Dubai, UAE",
        )

        assert job_id is not None
        job = get_job_by_id(job_id)
        assert job["title"] == "Senior AR Analyst"
        assert job["company"] == "Test Corp"
        assert job["source"] == "linkedin"

    def test_duplicate_insert_returns_none(self, temp_db):
        """Inserting the same source+url returns None."""
        from src.storage.jobs_repo import insert_job

        job_id1 = insert_job(
            source="linkedin",
            title="Credit Controller",
            url="https://linkedin.com/jobs/456",
        )
        job_id2 = insert_job(
            source="linkedin",
            title="Credit Controller",
            url="https://linkedin.com/jobs/456",
        )

        assert job_id1 is not None
        assert job_id2 is None

    def test_upsert_job_creates_and_updates(self, temp_db):
        """Upsert creates a new job then updates it."""
        from src.storage.jobs_repo import upsert_job, get_job_by_id

        job_id = upsert_job(
            source="naukrigulf",
            title="Collections Specialist",
            url="https://naukrigulf.com/jobs/789",
            company="Finance Co",
        )
        assert job_id is not None

        # Upsert same URL - should return same ID
        job_id2 = upsert_job(
            source="naukrigulf",
            title="Collections Specialist",
            url="https://naukrigulf.com/jobs/789",
            company="Finance Co Updated",
        )
        assert job_id2 == job_id

    def test_update_score_and_route(self, temp_db):
        """Update job score and routing status."""
        from src.storage.jobs_repo import (
            insert_job, update_job_score, update_job_route, get_job_by_id,
        )

        job_id = insert_job(
            source="linkedin",
            title="O2C Analyst",
            url="https://linkedin.com/jobs/o2c",
        )

        update_job_score(job_id, 85.5, "Strong title match + keyword match")
        update_job_route(job_id, "auto_apply")

        job = get_job_by_id(job_id)
        assert job["score"] == 85.5
        assert job["route_status"] == "auto_apply"
        assert "Strong title" in job["score_reason"]

    def test_invalid_route_status_raises(self, temp_db):
        """Invalid route status raises ValueError."""
        from src.storage.jobs_repo import insert_job, update_job_route

        job_id = insert_job(
            source="test", title="Test", url="https://test.com/1",
        )

        with pytest.raises(ValueError, match="Invalid route_status"):
            update_job_route(job_id, "invalid_status")

    def test_is_duplicate_exact(self, temp_db):
        """Exact duplicate detection by source+url."""
        from src.storage.jobs_repo import insert_job, is_duplicate_job

        insert_job(source="linkedin", title="AR Lead", url="https://example.com/1")
        assert is_duplicate_job("linkedin", "https://example.com/1") is True
        assert is_duplicate_job("linkedin", "https://example.com/2") is False

    def test_get_jobs_by_status(self, temp_db):
        """Filter jobs by routing status."""
        from src.storage.jobs_repo import insert_job, update_job_route, get_jobs_by_status

        id1 = insert_job(source="test", title="Job A", url="https://test.com/a")
        id2 = insert_job(source="test", title="Job B", url="https://test.com/b")
        id3 = insert_job(source="test", title="Job C", url="https://test.com/c")

        update_job_route(id1, "auto_apply")
        update_job_route(id2, "auto_apply")
        update_job_route(id3, "reject")

        auto_jobs = get_jobs_by_status("auto_apply")
        assert len(auto_jobs) == 2

        reject_jobs = get_jobs_by_status("reject")
        assert len(reject_jobs) == 1


class TestApplicationsRepo:
    """Test applications repository operations."""

    def test_insert_and_retrieve_application(self, temp_db):
        """Insert an application and retrieve it."""
        from src.storage.jobs_repo import insert_job
        from src.storage.applications_repo import (
            insert_application, get_application_by_job_id,
        )

        job_id = insert_job(source="test", title="Test Job", url="https://test.com/1")

        app_id = insert_application(
            job_id=job_id, source="test", resume_used="ar_collections",
        )
        assert app_id is not None

        app = get_application_by_job_id(job_id)
        assert app is not None
        assert app["resume_used"] == "ar_collections"
        assert app["result"] == "pending"

    def test_update_application_result(self, temp_db):
        """Update application with result and evidence."""
        from src.storage.jobs_repo import insert_job
        from src.storage.applications_repo import (
            insert_application, update_application_result, get_application_by_job_id,
        )

        job_id = insert_job(source="test", title="Test Job", url="https://test.com/2")
        insert_application(job_id=job_id)

        update_application_result(
            job_id=job_id,
            result="success",
            confirmation_text="Application submitted successfully",
            screenshot_path="/logs/screenshots/confirm_123.png",
        )

        app = get_application_by_job_id(job_id)
        assert app["result"] == "success"
        assert "submitted successfully" in app["confirmation_text"]

    def test_has_applied(self, temp_db):
        """Check if already applied to a job."""
        from src.storage.jobs_repo import insert_job
        from src.storage.applications_repo import insert_application, has_applied

        job_id = insert_job(source="test", title="Test", url="https://test.com/3")
        assert has_applied(job_id) is False

        insert_application(job_id=job_id)
        assert has_applied(job_id) is True


class TestRunLogsRepo:
    """Test run logs repository operations."""

    def test_insert_and_update_run_log(self, temp_db):
        """Create and update a run log entry."""
        from src.storage.run_logs_repo import insert_run_log, update_run_log, get_latest_run_log

        run_id = insert_run_log("linkedin", notes="Test run")

        update_run_log(
            run_id,
            total_found=50,
            total_new=30,
            total_scored=30,
            total_applied=5,
            total_failed=1,
        )

        latest = get_latest_run_log("linkedin")
        assert latest is not None
        assert latest["total_found"] == 50
        assert latest["total_new"] == 30
        assert latest["total_applied"] == 5
        assert latest["run_completed_at"] is not None
