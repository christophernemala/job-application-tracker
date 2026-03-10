"""Tests for the scoring engine and routing logic."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.scorers.scoring_engine import ScoringEngine
from src.scorers.router import route_job, route_jobs


# Load real config for testing
from src.utils.config_loader import load_profile, load_rules

profile = load_profile()
rules = load_rules()


class TestScoringEngine:
    def setup_method(self):
        self.engine = ScoringEngine(profile=profile, rules=rules)

    def test_strong_match_high_score(self):
        """Perfect match should score high."""
        job = {
            "title": "Senior Accounts Receivable Analyst",
            "normalized_title": "Senior Accounts Receivable Analyst",
            "location": "Dubai, UAE",
            "salary_min": 16000,
            "salary_max": 20000,
            "description": "Oracle Fusion, collections management, aging analysis, reconciliation",
            "apply_type": "easy_apply",
            "metadata": {
                "keywords": ["accounts_receivable", "collections", "aging", "reconciliation", "oracle"],
                "seniority": "senior",
            },
        }
        score, reason = self.engine.score_job(job)
        assert score >= 75, f"Expected high score, got {score}: {reason}"

    def test_weak_match_low_score(self):
        """Poor match should score low."""
        job = {
            "title": "Customer Service Representative",
            "normalized_title": "Customer Service Representative",
            "location": "Mumbai, India",
            "salary_min": 5000,
            "salary_max": 8000,
            "description": "Handle customer complaints and support tickets",
            "apply_type": "external_complex",
            "metadata": {
                "keywords": [],
                "seniority": None,
            },
        }
        score, reason = self.engine.score_job(job)
        assert score < 40, f"Expected low score, got {score}: {reason}"

    def test_excluded_title_penalized(self):
        """Excluded titles should get max score of 20."""
        job = {
            "title": "Junior Accountant",
            "normalized_title": "Junior Accountant",
            "location": "Dubai, UAE",
            "description": "Basic accounting tasks",
            "metadata": {"keywords": [], "seniority": "junior"},
        }
        score, reason = self.engine.score_job(job)
        assert score <= 20, f"Excluded title should be capped at 20, got {score}"
        assert "EXCLUDED" in reason

    def test_credit_controller_dubai(self):
        """Credit Controller in Dubai should score well."""
        job = {
            "title": "Credit Controller",
            "normalized_title": "Credit Controller",
            "location": "Dubai, UAE",
            "salary_min": 15000,
            "salary_max": 18000,
            "description": "Credit control, collections, dispute resolution",
            "apply_type": "internal",
            "metadata": {
                "keywords": ["credit_control", "collections", "dispute_resolution"],
                "seniority": "specialist",
            },
        }
        score, reason = self.engine.score_job(job)
        assert score >= 60, f"Expected decent score for credit controller, got {score}"

    def test_no_salary_gets_neutral(self):
        """Missing salary should not heavily penalize."""
        job = {
            "title": "Senior AR Analyst",
            "normalized_title": "Senior AR Analyst",
            "location": "Dubai, UAE",
            "description": "AR management",
            "metadata": {"keywords": ["accounts_receivable"], "seniority": "senior"},
        }
        score, _ = self.engine.score_job(job)
        # Should still get a reasonable score without salary info
        assert score >= 40

    def test_o2c_role_matches(self):
        """O2C role should match target titles."""
        job = {
            "title": "Order to Cash Specialist",
            "normalized_title": "Order to Cash Specialist",
            "location": "Abu Dhabi, UAE",
            "description": "End-to-end O2C process",
            "metadata": {"keywords": ["order_to_cash"], "seniority": "specialist"},
        }
        score, _ = self.engine.score_job(job)
        assert score >= 50


class TestRouter:
    def test_high_score_easy_apply_auto(self):
        """High score + easy apply = auto_apply."""
        job = {
            "score": 85,
            "apply_type": "easy_apply",
            "score_reason": "Strong match",
            "title": "Senior AR",
            "metadata": {"seniority": "senior"},
        }
        assert route_job(job, rules) == "auto_apply"

    def test_low_score_rejected(self):
        """Low score = reject."""
        job = {
            "score": 25,
            "apply_type": "easy_apply",
            "score_reason": "Poor match",
            "title": "Data Entry Clerk",
            "metadata": {"seniority": None},
        }
        assert route_job(job, rules) == "reject"

    def test_manager_gets_manual_review(self):
        """Manager-level roles get manual review regardless of score."""
        job = {
            "score": 90,
            "apply_type": "internal",
            "score_reason": "Strong match",
            "title": "Manager Credit Control",
            "metadata": {"seniority": "manager"},
        }
        assert route_job(job, rules) == "manual_review"

    def test_complex_ats_manual_review(self):
        """Complex ATS gets manual review."""
        job = {
            "score": 85,
            "apply_type": "external_complex",
            "score_reason": "Strong match",
            "title": "Senior AR Analyst",
            "metadata": {"seniority": "senior"},
        }
        assert route_job(job, rules) == "manual_review"

    def test_moderate_score_semi_auto(self):
        """Moderate score + internal apply = semi_auto."""
        job = {
            "score": 70,
            "apply_type": "internal",
            "score_reason": "Partial match",
            "title": "AR Specialist",
            "metadata": {"seniority": "specialist"},
        }
        assert route_job(job, rules) == "semi_auto"

    def test_excluded_rejected(self):
        """EXCLUDED in reason = reject."""
        job = {
            "score": 18,
            "apply_type": "internal",
            "score_reason": "EXCLUDED: title matches reject pattern",
            "title": "Intern Finance",
            "metadata": {"seniority": "intern"},
        }
        assert route_job(job, rules) == "reject"

    def test_batch_routing(self):
        """Route a batch of jobs."""
        jobs = [
            {"score": 90, "apply_type": "easy_apply", "score_reason": "", "title": "Senior AR", "metadata": {"seniority": "senior"}},
            {"score": 65, "apply_type": "internal", "score_reason": "", "title": "AR Analyst", "metadata": {"seniority": "specialist"}},
            {"score": 20, "apply_type": "unknown", "score_reason": "", "title": "Receptionist", "metadata": {"seniority": None}},
        ]
        routed = route_jobs(jobs, rules)
        assert len(routed["auto_apply"]) == 1
        assert len(routed["semi_auto"]) == 1
        assert len(routed["reject"]) == 1
