"""Application packager — builds a self-contained apply package per job.

Output layout (QUEUE_DIR/<job_id>/)
------------------------------------
  job.json          — full job record + metadata
  cv_tailored.md    — tailored CV (copy from tailored_cvs/)
  answers.json      — pre-filled ATS answers
  cover_letter.md   — optional cover letter
  README.md         — human-readable submit instructions
"""
from __future__ import annotations
import json
import shutil
from datetime import date
from pathlib import Path

from pipeline.config import QUEUE_DIR, OPENAI_API_KEY, MOCK_MODE
from pipeline.tailoring.prompts import COVER_LETTER_SYSTEM, COVER_LETTER_USER
from pipeline.utils.logger import get_logger

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Pre-fill ATS answers
# ---------------------------------------------------------------------------

def _build_answers(job: dict, candidate: dict) -> dict:
    """Return a dict of common ATS field → candidate answer."""
    return {
        "first_name": candidate.get("first_name", "[FIRST_NAME]"),
        "last_name": candidate.get("last_name", "[LAST_NAME]"),
        "email": candidate.get("email", "[EMAIL]"),
        "phone": candidate.get("phone", "[PHONE]"),
        "current_location": candidate.get("location", "Dubai, UAE"),
        "nationality": candidate.get("nationality", "[NATIONALITY]"),
        "visa_status": candidate.get("visa_status", "[VISA_STATUS]"),
        "notice_period": candidate.get("notice_period", "1 month"),
        "current_salary": candidate.get("current_salary", "[CURRENT_SALARY_AED]"),
        "expected_salary": candidate.get(
            "expected_salary",
            f"AED {job.get('salary_aed_min', 14000):,}+",
        ),
        "years_experience": candidate.get("years_experience", "[YEARS]"),
        "linkedin_url": candidate.get("linkedin_url", "[LINKEDIN_URL]"),
        "portfolio_url": candidate.get("portfolio_url", ""),
        "source": job.get("source", ""),
        "apply_url": job.get("easy_apply_url") or job.get("url", ""),
    }


# ---------------------------------------------------------------------------
# Cover letter (mock or OpenAI)
# ---------------------------------------------------------------------------

def _generate_cover_letter(job: dict, cv_content: str) -> str:
    if MOCK_MODE or not OPENAI_API_KEY:
        return (
            f"Dear Hiring Manager,\n\n"
            f"[MOCK COVER LETTER — replace with live OpenAI output]\n\n"
            f"Role: {job.get('title')} at {job.get('company')}\n\n"
            f"Yours sincerely,\n[CANDIDATE NAME]\n"
        )
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        jd = (job.get("description") or "")[:1500]
        # Extract first 600 chars of CV as summary
        cv_summary = cv_content[:600]
        user_msg = COVER_LETTER_USER.format(
            company=job.get("company", ""),
            title=job.get("title", ""),
            location=job.get("location", ""),
            cv_summary=cv_summary,
            jd_requirements=jd,
        )
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": COVER_LETTER_SYSTEM},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.4,
            max_tokens=600,
        )
        return resp.choices[0].message.content or ""
    except Exception as exc:  # pylint: disable=broad-except
        log.warning("Cover letter generation failed: %s", exc)
        return "[Cover letter generation failed — write manually]"


# ---------------------------------------------------------------------------
# README instructions
# ---------------------------------------------------------------------------

def _build_readme(job: dict) -> str:
    mode = job.get("apply_mode", "manual")
    url = job.get("easy_apply_url") or job.get("url", "")

    mode_instructions = {
        "easy_apply": f"1. Open: {url}\n2. Click **Easy Apply**.\n3. Upload cv_tailored.md (convert to PDF first).\n4. Paste answers from answers.json.\n5. Submit.",
        "external_form": f"1. Open: {url}\n2. Complete the ATS form using answers.json.\n3. Upload cv_tailored.md (convert to PDF).\n4. Paste cover_letter.md if requested.\n5. Submit.",
        "browser_assist": f"1. Open: {url}\n2. Locate the Apply button.\n3. Use answers.json to fill the form.\n4. Upload CV and cover letter.\n5. Submit.",
        "manual": f"1. Open: {url}\n2. Review the application process.\n3. Apply manually using the documents in this folder.",
    }

    return f"""# Application Package — {job.get('company')} / {job.get('title')}

**Date:**      {date.today()}
**Score:**     {job.get('score', 0)}/100
**Location:**  {job.get('location', '')}
**Salary:**    {job.get('salary_text') or 'Not listed'}
**Source:**    {job.get('source', '')}
**Apply URL:** {url}
**Mode:**      {mode}

## Files
- `cv_tailored.md` — Tailored CV for this role (convert to PDF before upload)
- `answers.json`    — Pre-filled form answers
- `cover_letter.md` — Cover letter draft
- `job.json`        — Full job record

## Steps to Apply
{mode_instructions.get(mode, 'See job.json for details.')}

## Matched Skills
{', '.join(job.get('matched_skills') or [])}

## Missing Skills (gaps to address in cover letter)
{', '.join(job.get('missing_skills') or [])}
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_package(
    job: dict,
    cv_path: Path | None = None,
    candidate: dict | None = None,
) -> Path:
    """Build a complete application package directory for *job*."""
    pkg_dir = QUEUE_DIR / job["id"]
    pkg_dir.mkdir(parents=True, exist_ok=True)

    # job.json
    (pkg_dir / "job.json").write_text(
        json.dumps(job, indent=2, default=str), encoding="utf-8"
    )

    # Tailored CV copy
    if cv_path and Path(cv_path).exists():
        shutil.copy(cv_path, pkg_dir / "cv_tailored.md")
        cv_content = Path(cv_path).read_text(encoding="utf-8")
    else:
        cv_content = "[CV not yet generated — run tailor step first]"
        (pkg_dir / "cv_tailored.md").write_text(cv_content, encoding="utf-8")

    # Answers
    answers = _build_answers(job, candidate or {})
    (pkg_dir / "answers.json").write_text(
        json.dumps(answers, indent=2), encoding="utf-8"
    )

    # Cover letter
    cl = _generate_cover_letter(job, cv_content)
    (pkg_dir / "cover_letter.md").write_text(cl, encoding="utf-8")

    # README
    (pkg_dir / "README.md").write_text(_build_readme(job), encoding="utf-8")

    log.info("Package built → %s", pkg_dir)
    return pkg_dir


def build_batch(
    jobs: list[dict],
    cv_paths: dict[str, Path] | None = None,
    candidate: dict | None = None,
) -> dict[str, Path]:
    """Build packages for a list of jobs. Returns {job_id: pkg_dir}."""
    results: dict[str, Path] = {}
    for job in jobs:
        try:
            cv = (cv_paths or {}).get(job["id"])
            pkg = build_package(job, cv_path=cv, candidate=candidate)
            results[job["id"]] = pkg
        except Exception as exc:  # pylint: disable=broad-except
            log.error("Package build failed for %s: %s", job.get("id"), exc)
    return results
