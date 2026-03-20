"""Smoke tests for the pipeline — all run in MOCK_MODE with no API keys."""
import os
import tempfile
from pathlib import Path

import pytest

# Force mock mode for all tests
os.environ["MOCK_MODE"] = "true"
os.environ["APIFY_TOKEN"] = ""
os.environ["OPENAI_API_KEY"] = ""


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------

def test_mock_fetch_returns_jobs():
    from pipeline.ingestion.mock_client import fetch_mock_jobs
    jobs = fetch_mock_jobs()
    assert len(jobs) >= 5
    for j in jobs:
        assert "id" in j
        assert "title" in j
        assert "company" in j
        assert "url" in j


def test_mock_fetch_filtered_by_source():
    from pipeline.ingestion.mock_client import fetch_mock_jobs
    jobs = fetch_mock_jobs(source="linkedin")
    assert all(j["source"] == "linkedin" for j in jobs)


def test_apify_client_falls_back_to_mock():
    from pipeline.ingestion.apify_client import fetch_jobs
    jobs = fetch_jobs("linkedin")
    assert isinstance(jobs, list)
    assert len(jobs) > 0


# ---------------------------------------------------------------------------
# Filtering & Scoring
# ---------------------------------------------------------------------------

def test_scorer_title_match():
    from pipeline.filtering.scorer import score_title
    pts, matches = score_title("Accounts Receivable Analyst")
    assert pts > 0
    assert "accounts receivable" in matches


def test_scorer_location():
    from pipeline.filtering.scorer import score_location
    pts, match = score_location("Dubai, UAE")
    assert pts == 20
    assert match == "dubai"


def test_scorer_salary_pass():
    from pipeline.filtering.scorer import score_salary
    pts, reason = score_salary(16000, "SomeCompany")
    assert pts == 10


def test_scorer_salary_fail():
    from pipeline.filtering.scorer import score_salary
    pts, reason = score_salary(8000, "SomeCompany")
    assert pts == 0


def test_scorer_salary_strong_company_override():
    from pipeline.filtering.scorer import score_salary
    pts, reason = score_salary(None, "Deloitte")
    assert pts == 5
    assert "strong_company" in reason


def test_score_job_full():
    from pipeline.filtering.scorer import score_job
    from pipeline.ingestion.mock_client import fetch_mock_jobs
    job = fetch_mock_jobs()[0]
    scored = score_job(job)
    assert "score" in scored
    assert "score_breakdown" in scored
    assert 0 <= scored["score"] <= 100


def test_dedup_removes_duplicates():
    from pipeline.filtering.dedup import deduplicate
    jobs = [
        {"company": "ACME", "title": "AR", "url": "https://x.com/1"},
        {"company": "ACME", "title": "AR", "url": "https://x.com/1"},
        {"company": "ACME", "title": "AP", "url": "https://x.com/2"},
    ]
    seen: set[str] = set()
    unique, dupes = deduplicate(jobs, seen)
    assert len(unique) == 2
    assert dupes == 1


def test_shortlist_filters_and_scores():
    from pipeline.filtering.rules import build_shortlist
    from pipeline.ingestion.mock_client import fetch_mock_jobs
    raw = fetch_mock_jobs()
    seen: set[str] = set()
    shortlisted, rejected = build_shortlist(raw, seen)
    # At least some shortlisted
    assert isinstance(shortlisted, list)
    # All shortlisted have scores
    for j in shortlisted:
        assert j["score"] >= 0


# ---------------------------------------------------------------------------
# Tracker
# ---------------------------------------------------------------------------

def test_tracker_init_and_upsert():
    from pipeline.tracker.db import init_db, upsert_job, get_jobs, get_seen_ids
    from pipeline.filtering.scorer import score_job
    from pipeline.ingestion.mock_client import fetch_mock_jobs

    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        init_db(db_path)

        job = score_job(fetch_mock_jobs()[0])
        upsert_job(job, db_path=db_path)

        jobs = get_jobs(db_path=db_path)
        assert len(jobs) == 1
        assert jobs[0]["company"] == job["company"]

        seen = get_seen_ids(db_path=db_path)
        assert job["id"] in seen


# ---------------------------------------------------------------------------
# Application layer
# ---------------------------------------------------------------------------

def test_apply_mode_detection():
    from pipeline.application.detector import detect_apply_type
    assert detect_apply_type({
        "url": "https://linkedin.com/jobs/view/123",
        "easy_apply_url": "https://linkedin.com/jobs/view/123/apply",
    }) == "easy_apply"

    assert detect_apply_type({
        "url": "https://acme.myworkdayjobs.com/en-US/jobs/job/123",
        "easy_apply_url": None,
    }) == "external_form"

    assert detect_apply_type({
        "url": "https://bayt.com/en/uae/jobs/ar-123",
        "easy_apply_url": None,
    }) == "browser_assist"


# ---------------------------------------------------------------------------
# Full mock pipeline run
# ---------------------------------------------------------------------------

def test_full_pipeline_mock(tmp_path, monkeypatch):
    """End-to-end smoke test — all in mock mode, no API calls."""
    monkeypatch.setenv("MOCK_MODE", "true")

    # Redirect output dirs to tmp
    import pipeline.config as cfg
    cfg.TRACKER_DB = tmp_path / "tracker.db"
    cfg.TAILORED_CVS_DIR = tmp_path / "tailored_cvs"
    cfg.QUEUE_DIR = tmp_path / "queue"
    cfg.TAILORED_CVS_DIR.mkdir()
    cfg.QUEUE_DIR.mkdir()

    from pipeline.main import run_pipeline
    summary = run_pipeline(auto_submit=False)
    assert summary["shortlisted"] >= 0
    assert "queue_dir" in summary
