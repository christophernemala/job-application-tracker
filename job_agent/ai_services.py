"""AI helpers for cover-letter generation and resume tailoring."""

from __future__ import annotations

import json
from typing import Any

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None


def _get_client() -> Any:
    if OpenAI is None:
        raise RuntimeError("openai package is not installed")
    return OpenAI()


def _safe_json_loads(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text.replace("json", "", 1).strip()
    return json.loads(text)


def generate_cover_letter(job_description: str, company_name: str, job_title: str, user_profile: dict[str, Any]) -> str:
    """Generate a concise personalized cover letter."""
    client = _get_client()

    prompt = f"""
Write a professional, compelling cover letter for this role.
Job Title: {job_title}
Company: {company_name}
Job Description: {job_description}
Candidate Profile:
- Name: {user_profile['name']}
- Current Role: {user_profile['current_role']}
- Experience: {user_profile['years_experience']} years
- Key Skills: {', '.join(user_profile['skills'])}
- Achievements: {user_profile['achievements']}

Constraints:
- max 3 paragraphs
- plain text only
- end with clear call to action
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You write high-quality finance and O2C cover letters for UAE job applications.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
        max_tokens=500,
    )
    return response.choices[0].message.content.strip()


def tailor_resume_to_jjd(job_description: str, master_resume_data: dict[str, Any]) -> dict[str, Any]:
    """Use AI to extract requirements and tailor a resume JSON safely."""
    client = _get_client()

    analysis_prompt = f"""
Analyze the job description and return strict JSON with keys:
skills, responsibilities, experience_level, keywords, culture.
Job description:\n{job_description}
"""

    analysis_response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": analysis_prompt}],
        temperature=0.2,
    )
    insights = _safe_json_loads(analysis_response.choices[0].message.content)

    tailoring_prompt = (
        "Customize the resume for this role and return strict JSON with keys summary, skills, experience.\n"
        f"MASTER RESUME:\n{json.dumps(master_resume_data)}\n"
        f"JOB REQUIREMENTS:\n{json.dumps(insights)}"
    )

    tailoring_response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You optimize resumes for ATS without fabricating details."},
            {"role": "user", "content": tailoring_prompt},
        ],
        temperature=0.4,
    )

    tailored = _safe_json_loads(tailoring_response.choices[0].message.content)

    final_resume = master_resume_data.copy()
    final_resume["summary"] = tailored["summary"]
    final_resume["skills"] = tailored["skills"]
    final_resume["experience"] = tailored["experience"]
    return final_resume
