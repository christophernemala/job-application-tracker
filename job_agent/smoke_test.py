"""Smoke tests for the job discovery scoring layer."""
from __future__ import annotations

try:
    from job_agent.job_selection_rules import JobRecord, score_job
except ImportError:  # Allows direct execution as: python job_agent/smoke_test.py
    from job_selection_rules import JobRecord, score_job


def main() -> None:
    job = JobRecord(
        title="Accounts Receivable Specialist",
        company="Test Company",
        location="Dubai, UAE",
        source="test",
        link="https://example.com",
        description=(
            "Accounts receivable, collections, credit control, reconciliation, "
            "Oracle Fusion, Power BI, aging report, DSO tracking, cash application."
        ),
    )
    result = score_job(job)
    print(result)
    assert result["match_score"] > 0
    assert result["priority"] != "Skip"


if __name__ == "__main__":
    main()
