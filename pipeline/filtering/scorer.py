"""Scoring engine — produces a 0-100 match score per job.

Breakdown
---------
Title match     : 0-30 pts
Function match  : 0-15 pts
Skills match    : 0-25 pts
Location match  : 0-20 pts
Salary pass     : 0-10 pts  (fail = 0, strong company override = 5)
"""
from __future__ import annotations
import re
from pipeline.config import (
    FINANCE_TITLES,
    FINANCE_SKILLS,
    LOCATION_SCORES,
    TARGET_LOCATIONS,
    SALARY_MIN_AED,
    STRONG_COMPANIES,
)


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z]+", text.lower())


def _contains(haystack: str, needles: list[str]) -> list[str]:
    h = haystack.lower()
    return [n for n in needles if n in h]


# ---------------------------------------------------------------------------
# Individual dimension scorers
# ---------------------------------------------------------------------------

def score_title(title: str) -> tuple[int, list[str]]:
    """0-30 points for title relevance."""
    matched = _contains(title, FINANCE_TITLES)
    pts = min(30, len(matched) * 15)
    return pts, matched


def score_function(description: str, title: str) -> tuple[int, list[str]]:
    """0-15 points for finance function keywords in description."""
    combined = f"{title} {description}"
    matched = _contains(combined, FINANCE_TITLES)
    pts = min(15, len(matched) * 5)
    return pts, matched


def score_skills(description: str, cv_skills: list[str] | None = None) -> tuple[int, list[str], list[str]]:
    """0-25 points for skills match.

    Returns (score, matched_skills, missing_skills).
    If cv_skills provided, also tracks what the job needs that we don't have.
    """
    jd_skills = _contains(description, FINANCE_SKILLS)
    cv = [s.lower() for s in (cv_skills or [])]
    if cv:
        matched = [s for s in jd_skills if s in cv]
        missing = [s for s in jd_skills if s not in cv]
    else:
        matched = jd_skills
        missing = []

    pts = min(25, len(matched) * 5) if cv else min(25, len(jd_skills) * 3)
    return pts, matched, missing


def score_location(location: str) -> tuple[int, str]:
    """0-20 points for location preference."""
    loc_lower = location.lower()
    for place, pts in sorted(LOCATION_SCORES.items(), key=lambda x: -x[1]):
        if place in loc_lower:
            return pts, place
    return 0, ""


def score_salary(
    salary_aed_min: int | None,
    company: str,
) -> tuple[int, str]:
    """0-10 points for salary compliance.

    Full 10 pts if above threshold.
    5 pts if missing but company is strong.
    0 pts if below threshold.
    """
    if salary_aed_min is None:
        company_l = company.lower()
        if any(sc in company_l for sc in STRONG_COMPANIES):
            return 5, "strong_company_override"
        return 3, "salary_unknown"
    if salary_aed_min >= SALARY_MIN_AED:
        return 10, f"AED {salary_aed_min:,}"
    return 0, f"below_min (AED {salary_aed_min:,})"


# ---------------------------------------------------------------------------
# Combined scorer
# ---------------------------------------------------------------------------

def score_job(job: dict, cv_skills: list[str] | None = None) -> dict:
    """Return the job dict augmented with score fields."""
    t_pts, t_match = score_title(job.get("title", ""))
    f_pts, f_match = score_function(job.get("description", ""), job.get("title", ""))
    s_pts, s_match, s_missing = score_skills(job.get("description", ""), cv_skills)
    l_pts, l_match = score_location(job.get("location", ""))
    sal_pts, sal_reason = score_salary(
        job.get("salary_aed_min"),
        job.get("company", ""),
    )

    total = t_pts + f_pts + s_pts + l_pts + sal_pts

    return {
        **job,
        "score": total,
        "score_breakdown": {
            "title": t_pts,
            "function": f_pts,
            "skills": s_pts,
            "location": l_pts,
            "salary": sal_pts,
        },
        "matched_titles": list(set(t_match + f_match)),
        "matched_skills": s_match,
        "missing_skills": s_missing,
        "location_match": l_match,
        "salary_reason": sal_reason,
    }
