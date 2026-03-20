"""Hard filter rules and shortlist logic."""
from __future__ import annotations
from pipeline.config import (
    SHORTLIST_THRESHOLD,
    SALARY_MIN_AED,
    TARGET_LOCATIONS,
    STRONG_COMPANIES,
)
from pipeline.filtering.scorer import score_job
from pipeline.filtering.dedup import deduplicate
from pipeline.utils.logger import get_logger

log = get_logger(__name__)


def _location_allowed(job: dict) -> bool:
    loc = job.get("location", "").lower()
    return any(t in loc for t in TARGET_LOCATIONS)


def _salary_allowed(job: dict) -> bool:
    sal = job.get("salary_aed_min")
    if sal is None:
        # Allow if company is strong (quality override)
        company = job.get("company", "").lower()
        return any(sc in company for sc in STRONG_COMPANIES)
    return sal >= SALARY_MIN_AED


def apply_hard_filters(jobs: list[dict]) -> tuple[list[dict], list[dict]]:
    """Returns (passed, rejected) after location + salary hard filters."""
    passed, rejected = [], []
    for job in jobs:
        reasons = []
        if not _location_allowed(job):
            reasons.append("location_mismatch")
        if not _salary_allowed(job):
            reasons.append("salary_below_min")
        if reasons:
            job["reject_reasons"] = reasons
            rejected.append(job)
        else:
            passed.append(job)

    log.info(
        "Hard filters: %d passed, %d rejected.", len(passed), len(rejected)
    )
    return passed, rejected


def build_shortlist(
    raw_jobs: list[dict],
    seen_ids: set[str],
    cv_skills: list[str] | None = None,
) -> tuple[list[dict], list[dict]]:
    """Full pipeline: dedup → hard filter → score → shortlist.

    Returns (shortlisted, rejected_all).
    """
    # 1. Dedup
    unique, _ = deduplicate(raw_jobs, seen_ids)

    # 2. Hard filters
    passed, rejected = apply_hard_filters(unique)

    # 3. Score
    scored = [score_job(j, cv_skills) for j in passed]

    # 4. Sort descending
    scored.sort(key=lambda j: j["score"], reverse=True)

    # 5. Shortlist threshold
    shortlisted = [j for j in scored if j["score"] >= SHORTLIST_THRESHOLD]
    below_threshold = [j for j in scored if j["score"] < SHORTLIST_THRESHOLD]

    for j in below_threshold:
        j.setdefault("reject_reasons", []).append(
            f"score_too_low ({j['score']}<{SHORTLIST_THRESHOLD})"
        )

    log.info(
        "Shortlist: %d qualified (score≥%d), %d below threshold.",
        len(shortlisted), SHORTLIST_THRESHOLD, len(below_threshold),
    )
    return shortlisted, rejected + below_threshold
