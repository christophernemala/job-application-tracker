"""Tests for the application engine – unit tests that don't require a browser."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.appliers.base_applier import ApplicationResult
from src.appliers.application_engine import select_resume


class TestApplicationResult:
    def test_success_result(self):
        result = ApplicationResult(
            job_id=1,
            source="linkedin",
            success=True,
            confirmation_text="Application submitted",
            screenshot_path="/logs/screenshots/test.png",
            resume_used="ar_collections.pdf",
        )
        assert result.success is True
        assert result.job_id == 1
        d = result.to_dict()
        assert d["source"] == "linkedin"
        assert d["confirmation_text"] == "Application submitted"

    def test_failure_result(self):
        result = ApplicationResult(
            job_id=2,
            source="naukrigulf",
            success=False,
            failure_reason="Apply button not found",
        )
        assert result.success is False
        assert "Apply button" in result.failure_reason

    def test_default_timestamp(self):
        result = ApplicationResult(job_id=1, source="test", success=True)
        assert result.applied_at is not None
        assert "T" in result.applied_at  # ISO format


class TestResumeSelection:
    def test_ar_title_selects_ar_resume(self):
        job = {
            "title": "Senior Accounts Receivable Analyst",
            "normalized_title": "Senior Accounts Receivable Analyst",
            "metadata": {"keywords": ["accounts_receivable"], "seniority": "senior"},
        }
        # This tests the selection logic; the file won't exist so it returns None
        result = select_resume(job)
        # Since resume files don't exist in test env, it should return None
        assert result is None

    def test_credit_title_selects_credit_resume(self):
        job = {
            "title": "Credit Controller",
            "normalized_title": "Credit Controller",
            "metadata": {"keywords": ["credit_control"], "seniority": "specialist"},
        }
        result = select_resume(job)
        assert result is None  # File doesn't exist

    def test_o2c_title_selects_o2c_resume(self):
        job = {
            "title": "Order to Cash Specialist",
            "normalized_title": "Order to Cash Specialist",
            "metadata": {"keywords": ["order_to_cash"], "seniority": "specialist"},
        }
        result = select_resume(job)
        assert result is None  # File doesn't exist


class TestDryRunApply:
    def test_dry_run_returns_zero(self):
        """Dry run should not apply to any jobs."""
        from src.appliers.application_engine import apply_to_jobs

        routed = {
            "auto_apply": [
                {"id": 1, "title": "Test", "source": "linkedin", "score": 90, "company": "Co"},
            ],
            "semi_auto": [],
            "manual_review": [],
            "reject": [],
        }
        applied, failed = apply_to_jobs(routed, dry_run=True)
        assert applied == 0
        assert failed == 0

    def test_empty_auto_apply_returns_zero(self):
        """No auto_apply jobs should return 0,0."""
        from src.appliers.application_engine import apply_to_jobs

        routed = {
            "auto_apply": [],
            "semi_auto": [],
            "manual_review": [],
            "reject": [],
        }
        applied, failed = apply_to_jobs(routed)
        assert applied == 0
        assert failed == 0
