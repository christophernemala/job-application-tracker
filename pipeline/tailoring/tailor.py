"""CV tailoring layer — generates ATS-optimised CVs per job.

Uses OpenAI when OPENAI_API_KEY is set; falls back to a keyword-insertion
stub in mock/no-key mode so the pipeline keeps running end-to-end.
"""
from __future__ import annotations
import re
from pathlib import Path

from pipeline.config import (
    CV_PATH,
    CV_TEMPLATE_PATH,
    TAILORED_CVS_DIR,
    OPENAI_API_KEY,
    MOCK_MODE,
)
from pipeline.tailoring.prompts import TAILOR_SYSTEM, TAILOR_USER
from pipeline.utils.logger import get_logger

log = get_logger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_file(path: Path, label: str) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8")
    log.warning("%s not found at %s — using placeholder.", label, path)
    return f"[{label.upper()} PLACEHOLDER — drop your file at {path}]"


def _output_path(job: dict) -> Path:
    safe_company = re.sub(r"[^\w]", "_", job.get("company", "unknown"))[:30]
    safe_title = re.sub(r"[^\w]", "_", job.get("title", "role"))[:40]
    fname = f"{job.get('id', 'job')}_{safe_company}_{safe_title}.md"
    return TAILORED_CVS_DIR / fname


# ---------------------------------------------------------------------------
# Mock tailor
# ---------------------------------------------------------------------------

def _mock_tailor(cv: str, job: dict) -> str:
    """Stub: appends a note about which keywords were injected."""
    from pipeline.config import FINANCE_SKILLS
    jd_text = (job.get("description") or "").lower()
    hits = [s for s in FINANCE_SKILLS if s in jd_text]
    note = (
        "\n\n---\n"
        f"*[MOCK MODE — tailored for: {job['company']} / {job['title']}]*\n"
        f"*Keywords detected in JD: {', '.join(hits[:8]) or 'none'}*\n"
    )
    return cv + note


# ---------------------------------------------------------------------------
# OpenAI tailor
# ---------------------------------------------------------------------------

def _openai_tailor(cv: str, template: str, job: dict) -> str:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("openai package not installed.") from exc

    client = OpenAI(api_key=OPENAI_API_KEY)
    user_msg = TAILOR_USER.format(
        cv_content=cv,
        template_content=template,
        company=job.get("company", ""),
        title=job.get("title", ""),
        location=job.get("location", ""),
        salary=job.get("salary_text", "Not listed"),
        description=(job.get("description") or "")[:2000],
    )

    log.info("Tailoring CV for %s @ %s …", job.get("title"), job.get("company"))
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": TAILOR_SYSTEM},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.3,
        max_tokens=2500,
    )
    return response.choices[0].message.content or ""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def tailor_cv(job: dict) -> Path:
    """Generate a tailored CV for *job*. Returns path to output file."""
    out = _output_path(job)
    if out.exists():
        log.info("Tailored CV already exists for %s — skipping.", job.get("id"))
        return out

    cv = _load_file(CV_PATH, "cv_base")
    template = _load_file(CV_TEMPLATE_PATH, "cv_template")

    if MOCK_MODE or not OPENAI_API_KEY:
        if not OPENAI_API_KEY:
            log.warning("OPENAI_API_KEY not set — using mock tailor.")
        content = _mock_tailor(cv, job)
    else:
        try:
            content = _openai_tailor(cv, template, job)
        except Exception as exc:  # pylint: disable=broad-except
            log.error("OpenAI tailoring failed (%s) — using mock.", exc)
            content = _mock_tailor(cv, job)

    out.write_text(content, encoding="utf-8")
    log.info("Tailored CV saved → %s", out.name)
    return out


def tailor_batch(jobs: list[dict]) -> dict[str, Path]:
    """Tailor CVs for a list of jobs. Returns {job_id: cv_path}."""
    results: dict[str, Path] = {}
    for job in jobs:
        try:
            path = tailor_cv(job)
            results[job["id"]] = path
        except Exception as exc:  # pylint: disable=broad-except
            log.error("Failed to tailor CV for %s: %s", job.get("id"), exc)
    return results
