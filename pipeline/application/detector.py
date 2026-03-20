"""Apply-type detection — classifies each job into a submission strategy.

Modes
-----
easy_apply      LinkedIn Easy Apply or Indeed's direct API apply
external_form   Company ATS (Workday, Greenhouse, Lever, Taleo, etc.)
browser_assist  We open the URL in a browser for the user; one-click send
manual          CAPTCHA / advanced anti-bot / no apply path detected
"""
from __future__ import annotations
import re

_EASY_APPLY_DOMAINS = [
    "linkedin.com",
]
_INDEED_DOMAINS = ["indeed.com", "indeed.ae"]
_ATS_PATTERNS = [
    r"workday\.com",
    r"greenhouse\.io",
    r"lever\.co",
    r"taleo\.net",
    r"icims\.com",
    r"successfactors\.",
    r"smartrecruiters\.com",
    r"oracle\.com/taleo",
    r"myworkdayjobs\.com",
    r"jobs\.ashbyhq\.com",
    r"apply\.workable\.com",
    r"bamboohr\.com",
    r"recruitee\.com",
    r"jobvite\.com",
]
_BLOCKED_PATTERNS = [
    r"captcha",
    r"recaptcha",
    r"hcaptcha",
    r"cf_clearance",
]

# Fields commonly required in ATS forms — used to pre-fill answers
COMMON_ATS_FIELDS = [
    "first_name",
    "last_name",
    "email",
    "phone",
    "current_location",
    "nationality",
    "visa_status",
    "notice_period",
    "current_salary",
    "expected_salary",
    "years_experience",
    "cover_letter",
    "linkedin_url",
    "portfolio_url",
    "resume_file",
]


def detect_apply_type(job: dict) -> str:
    """Return one of: easy_apply | external_form | browser_assist | manual."""
    url = (job.get("url") or "").lower()
    easy_url = (job.get("easy_apply_url") or "").lower()

    # LinkedIn Easy Apply
    if easy_url and any(d in easy_url for d in _EASY_APPLY_DOMAINS):
        return "easy_apply"

    # Indeed direct apply
    if easy_url and any(d in easy_url for d in _INDEED_DOMAINS):
        return "easy_apply"

    # Known ATS platforms
    if any(re.search(p, url) for p in _ATS_PATTERNS):
        return "external_form"

    # External company site with apply path
    if "/apply" in url or "/careers/" in url or "/job/" in url:
        return "browser_assist"

    # Bayt / GulfTalent native
    if "bayt.com" in url or "gulftaient.com" in url:
        return "browser_assist"

    return "manual"


def annotate_apply_modes(jobs: list[dict]) -> list[dict]:
    """Add apply_mode field to each job dict."""
    for job in jobs:
        job["apply_mode"] = detect_apply_type(job)
    return jobs
