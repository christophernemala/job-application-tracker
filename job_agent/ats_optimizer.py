"""Legitimate ATS resume optimization using Claude AI.

All features help candidates present their real experience more effectively.
No fabrication, hidden text, or deceptive techniques.
"""

from __future__ import annotations

import json
import os
from typing import Any

import anthropic

MODEL = "claude-opus-4-6"


def _client() -> anthropic.Anthropic:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY environment variable is not set")
    return anthropic.Anthropic(api_key=api_key)


def _ask(system: str, user: str, max_tokens: int = 2048) -> str:
    """Single Claude call with streaming, returns full text."""
    client = _client()
    with client.messages.stream(
        model=MODEL,
        max_tokens=max_tokens,
        thinking={"type": "adaptive"},
        system=system,
        messages=[{"role": "user", "content": user}],
    ) as stream:
        return stream.get_final_message().content[-1].text


def _ask_json(system: str, user: str, max_tokens: int = 2048) -> dict[str, Any]:
    """Claude call that returns parsed JSON."""
    result = _ask(system, user + "\n\nRespond with valid JSON only, no markdown fences.", max_tokens)
    result = result.strip()
    if result.startswith("```"):
        lines = result.splitlines()
        lines = lines[1:] if lines[0].startswith("```") else lines
        lines = lines[:-1] if lines and lines[-1].strip() == "```" else lines
        result = "\n".join(lines).strip()
    return json.loads(result)


# ---------------------------------------------------------------------------
# 1. Job Description Parser
# ---------------------------------------------------------------------------

def parse_job_description(jd_text: str) -> dict[str, Any]:
    """Extract structured requirements from a job description.

    Returns keys: skills, tools, certifications, responsibilities,
                  keywords, experience_level, industry, location.
    """
    system = (
        "You are an expert recruiter and job analyst. "
        "Extract structured information from job descriptions accurately."
    )
    user = f"""Analyze this job description and extract:
- skills: list of required and preferred technical/soft skills
- tools: list of software, platforms, or technologies mentioned
- certifications: list of required or preferred certifications
- responsibilities: list of key job duties (max 8)
- keywords: ATS keywords a candidate's resume should include
- experience_level: one of Entry / Mid / Senior / Manager / Director
- industry: primary industry sector
- location: location and remote policy if mentioned

Job Description:
{jd_text}"""
    return _ask_json(system, user, max_tokens=1500)


# ---------------------------------------------------------------------------
# 2. Resume-JD Alignment Scorer
# ---------------------------------------------------------------------------

def score_alignment(resume_text: str, jd_text: str) -> dict[str, Any]:
    """Score how well a resume matches a job description.

    Returns: score (0-100), matched_skills, missing_skills,
             partial_matches, top_recommendations.
    """
    system = (
        "You are an ATS and recruitment expert. "
        "Evaluate resume-to-job-description alignment objectively and honestly."
    )
    user = f"""Compare this resume against the job description and produce an alignment report.

RESUME:
{resume_text}

JOB DESCRIPTION:
{jd_text}

Return JSON with:
- score: integer 0-100 representing overall match strength
- matched_skills: list of skills/keywords present in both resume and JD
- missing_skills: list of skills/keywords in the JD that are absent from the resume
- partial_matches: list of skills the candidate has partially but could strengthen
- top_recommendations: list of 3-5 specific, actionable things to improve the resume
- summary: one paragraph honest assessment of the candidate's fit"""
    return _ask_json(system, user, max_tokens=2000)


# ---------------------------------------------------------------------------
# 3. Skill Gap Analysis
# ---------------------------------------------------------------------------

def analyze_skill_gaps(resume_text: str, jd_text: str) -> dict[str, Any]:
    """Detailed gap analysis with learning path suggestions.

    Returns: critical_gaps, nice_to_have_gaps, learning_paths, timeline_estimate.
    """
    system = (
        "You are a career development coach specializing in skills analysis. "
        "Provide honest, constructive gap analysis with actionable learning paths."
    )
    user = f"""Perform a detailed skill gap analysis.

RESUME:
{resume_text}

JOB DESCRIPTION:
{jd_text}

Return JSON with:
- critical_gaps: list of must-have skills the candidate lacks
- nice_to_have_gaps: list of preferred skills the candidate lacks
- learning_paths: dict mapping each critical gap to {{resource, duration, free_option}}
- transferable_skills: list of candidate skills that partially bridge the gaps
- timeline_estimate: estimated months to close critical gaps with focused effort
- overall_readiness: one of "Apply Now" / "Apply with Gaps" / "Upskill First (3-6 months)" / "Upskill First (6-12 months)" """
    return _ask_json(system, user, max_tokens=2000)


# ---------------------------------------------------------------------------
# 4. Bullet Point Rewriter
# ---------------------------------------------------------------------------

def rewrite_bullets(
    bullets: list[str],
    jd_context: str,
    candidate_context: str = "",
) -> list[str]:
    """Rewrite resume bullet points to be stronger and more ATS-friendly.

    Uses only the candidate's real experience — no fabrication.
    Adds metrics framing where the candidate provides them.
    """
    system = (
        "You are an expert resume writer. Rewrite bullet points to be strong, "
        "metrics-driven, and ATS-friendly. Use only information provided — "
        "never fabricate achievements, numbers, or experiences. "
        "If a metric is missing, use language like 'resulting in improved X' "
        "rather than inventing a number."
    )
    user = f"""Rewrite these resume bullets to be stronger for this role.
Rules:
- Use action verbs (Led, Reduced, Improved, Managed, Delivered...)
- Add metrics where the candidate has provided them; use qualitative language otherwise
- Include relevant keywords from the job description naturally
- Keep each bullet under 2 lines
- Do NOT invent numbers, companies, or experiences

JOB DESCRIPTION CONTEXT:
{jd_context}

CANDIDATE ADDITIONAL CONTEXT (if any):
{candidate_context}

ORIGINAL BULLETS:
{chr(10).join(f'- {b}' for b in bullets)}

Return JSON: {{"rewritten": ["bullet 1", "bullet 2", ...]}}"""
    result = _ask_json(system, user, max_tokens=1500)
    return result.get("rewritten", bullets)


# ---------------------------------------------------------------------------
# 5. ATS-Safe Resume Generator
# ---------------------------------------------------------------------------

def generate_ats_resume(
    resume_data: dict[str, Any],
    jd_text: str,
    target_role: str,
    target_company: str = "",
) -> str:
    """Generate a complete ATS-optimized resume in plain text.

    Uses only the candidate's real experience and qualifications.
    Optimizes structure, keyword placement, and formatting for ATS parsing.
    """
    system = (
        "You are an expert resume writer creating ATS-optimized resumes. "
        "Use ONLY the candidate's real experience provided. "
        "Never fabricate skills, roles, dates, companies, or achievements. "
        "Format for maximum ATS compatibility: plain text, clear headings, "
        "no tables, no columns, no graphics."
    )
    user = f"""Create an ATS-optimized resume for this candidate targeting this role.

TARGET ROLE: {target_role}
TARGET COMPANY: {target_company or "Not specified"}

JOB DESCRIPTION:
{jd_text}

CANDIDATE DATA:
{json.dumps(resume_data, indent=2)}

Instructions:
- Order sections: Summary → Core Skills → Experience → Education → Certifications
- Write a 3-sentence professional summary tailored to this role
- List skills that match the JD first
- Rewrite experience bullets using strong action verbs and metrics from candidate data
- Use keywords from the JD naturally throughout (where truthful)
- Plain text only: no columns, tables, special characters
- Each section clearly labeled with ALL CAPS heading

Output the complete resume as plain text."""
    return _ask(system, user, max_tokens=3000)


# ---------------------------------------------------------------------------
# 6. LinkedIn Optimizer
# ---------------------------------------------------------------------------

def optimize_linkedin(
    profile_data: dict[str, Any],
    target_role: str,
    target_industry: str = "",
) -> dict[str, Any]:
    """Generate optimized LinkedIn sections based on real qualifications.

    Returns: headline, about, skills_to_add, experience_tips.
    """
    system = (
        "You are a LinkedIn optimization expert. Create compelling, "
        "keyword-rich LinkedIn content using only the candidate's real experience. "
        "No fabrication of roles, skills, or achievements."
    )
    user = f"""Optimize this LinkedIn profile for the target role.

TARGET ROLE: {target_role}
TARGET INDUSTRY: {target_industry or "Not specified"}

CANDIDATE PROFILE:
{json.dumps(profile_data, indent=2)}

Return JSON with:
- headline: LinkedIn headline (max 220 chars, keyword-rich, compelling)
- about: full About section (first-person, 3-4 paragraphs, ends with CTA)
- skills_to_add: list of up to 10 skills to add to LinkedIn Skills section
- experience_tips: list of tips to improve individual experience descriptions
- open_to_work_title: suggested job title for Open to Work feature"""
    return _ask_json(system, user, max_tokens=2000)


# ---------------------------------------------------------------------------
# 7. Cover Letter Generator
# ---------------------------------------------------------------------------

def generate_cover_letter(
    resume_text: str,
    jd_text: str,
    company_name: str,
    role_title: str,
    candidate_name: str = "",
    hiring_manager: str = "",
) -> str:
    """Generate a targeted cover letter grounded in the candidate's real experience."""
    system = (
        "You are an expert cover letter writer. "
        "Write compelling, specific cover letters using only the candidate's real experience. "
        "Never fabricate achievements. Be concise and professional."
    )
    user = f"""Write a cover letter for this application.

CANDIDATE: {candidate_name or "the candidate"}
ROLE: {role_title}
COMPANY: {company_name}
HIRING MANAGER: {hiring_manager or "Hiring Manager"}

JOB DESCRIPTION:
{jd_text}

CANDIDATE RESUME / EXPERIENCE:
{resume_text}

Requirements:
- 3 paragraphs maximum
- Opening: why this role + company (specific, not generic)
- Middle: 2-3 most relevant achievements/experiences that match the JD
- Closing: clear call to action
- Plain text, no formatting symbols
- Tone: professional but human"""
    return _ask(system, user, max_tokens=800)


# ---------------------------------------------------------------------------
# 8. Role-Specific Resume Variant
# ---------------------------------------------------------------------------

def generate_resume_variant(
    resume_data: dict[str, Any],
    jd_text: str,
    job_family: str,
) -> dict[str, Any]:
    """Suggest resume customizations for a specific job family.

    Returns variant guidance without altering facts.
    """
    system = (
        "You are a resume strategy expert. Advise on how to tailor a resume "
        "for different job families using the candidate's actual experience. "
        "Do not suggest fabricating anything."
    )
    user = f"""Suggest how to tailor this resume for the {job_family} job family.

JOB DESCRIPTION:
{jd_text}

CANDIDATE DATA:
{json.dumps(resume_data, indent=2)}

Return JSON with:
- summary_variant: rewritten professional summary for this job family
- skills_to_emphasize: list of candidate's existing skills to move to top
- skills_to_de-emphasize: list of less relevant skills to move down or remove
- experience_focus: dict of role → specific bullets to emphasize for this family
- section_order: recommended section order for this job family
- keywords_to_add: keywords from JD that can be honestly added based on candidate experience"""
    return _ask_json(system, user, max_tokens=2000)
