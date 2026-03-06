"""ATS Optimizer MCP Server.

Exposes the ATS optimizer as MCP tools so Claude Code (or any MCP client)
can call them directly — no Flask backend or hosting required.

Works with ANY supported API key — set whichever you have:
  ANTHROPIC_API_KEY  → Claude claude-opus-4-6  (best quality)
  OPENAI_API_KEY     → GPT-4o
  GROQ_API_KEY       → Llama-3.3-70b (free tier at groq.com)

Usage:
    python -m job_agent.mcp_server

Add to ~/.claude/mcp_servers.json (pick one key):
    {
      "ats-optimizer": {
        "command": "python",
        "args": ["-m", "job_agent.mcp_server"],
        "cwd": "/path/to/job-application-tracker",
        "env": {
          "ANTHROPIC_API_KEY": "sk-ant-...",
          "__OR__OPENAI_API_KEY": "sk-...",
          "__OR__GROQ_API_KEY": "gsk_..."
        }
      }
    }

Cost: $0 hosting — only AI API token costs apply.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure project root on path when run as a module
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp.server.fastmcp import FastMCP
import job_agent.ats_optimizer as ats

mcp = FastMCP(
    name="ats-optimizer",
    instructions=(
        "ATS Resume Optimizer tools. Use these to help analyze job descriptions, "
        "score resume alignment, rewrite bullet points, generate cover letters, "
        "optimize LinkedIn profiles, and create ATS-safe resumes. "
        "All tools use only the candidate's real experience — no fabrication. "
        "Supports Anthropic, OpenAI, and Groq — auto-detected from env vars."
    ),
)


@mcp.tool(description="Check which AI provider is active (Anthropic / OpenAI / Groq).")
def check_provider() -> str:
    """Show the active AI provider and model."""
    provider = ats.active_provider()
    models = {"anthropic": "claude-opus-4-6", "openai": "gpt-4o", "groq": "llama-3.3-70b-versatile"}
    if provider == "none":
        return (
            "No API key configured. Set one of:\n"
            "  ANTHROPIC_API_KEY  → Claude claude-opus-4-6\n"
            "  OPENAI_API_KEY     → GPT-4o\n"
            "  GROQ_API_KEY       → Llama-3.3-70b (free tier)"
        )
    return f"Active provider: {provider.upper()} | Model: {models[provider]}"


# ---------------------------------------------------------------------------
# Tool: Parse Job Description
# ---------------------------------------------------------------------------

@mcp.tool(
    description=(
        "Parse a job description and extract structured requirements: "
        "required skills, tools/software, certifications, key responsibilities, "
        "ATS keywords, experience level, industry, and location."
    )
)
def parse_job_description(jd_text: str) -> str:
    """Extract structured data from a job description.

    Args:
        jd_text: Full text of the job description to analyze.
    """
    result = ats.parse_job_description(jd_text)
    return json.dumps(result, indent=2)


# ---------------------------------------------------------------------------
# Tool: Score Resume Alignment
# ---------------------------------------------------------------------------

@mcp.tool(
    description=(
        "Score how well a resume matches a job description (0-100). "
        "Returns matched skills, missing skills, partial matches, and "
        "top 5 actionable recommendations to improve the match."
    )
)
def score_resume_alignment(resume_text: str, jd_text: str) -> str:
    """Alignment score between a resume and job description.

    Args:
        resume_text: The candidate's resume as plain text.
        jd_text: The job description as plain text.
    """
    result = ats.score_alignment(resume_text, jd_text)
    return json.dumps(result, indent=2)


# ---------------------------------------------------------------------------
# Tool: Skill Gap Analysis
# ---------------------------------------------------------------------------

@mcp.tool(
    description=(
        "Detailed skill gap analysis comparing a resume to a job description. "
        "Identifies critical gaps (must-have), nice-to-have gaps, "
        "learning paths with resources, and an overall readiness assessment."
    )
)
def analyze_skill_gaps(resume_text: str, jd_text: str) -> str:
    """Identify skill gaps and suggest learning paths.

    Args:
        resume_text: The candidate's resume as plain text.
        jd_text: The job description as plain text.
    """
    result = ats.analyze_skill_gaps(resume_text, jd_text)
    return json.dumps(result, indent=2)


# ---------------------------------------------------------------------------
# Tool: Rewrite Bullet Points
# ---------------------------------------------------------------------------

@mcp.tool(
    description=(
        "Rewrite resume bullet points to be stronger and more ATS-friendly. "
        "Uses action verbs, incorporates JD keywords naturally, and frames "
        "achievements with metrics where available. Never fabricates data."
    )
)
def rewrite_resume_bullets(
    bullets: str,
    jd_context: str,
    candidate_context: str = "",
) -> str:
    """Rewrite bullet points for a specific role.

    Args:
        bullets: Bullet points to rewrite, one per line (with or without leading dash/bullet).
        jd_context: The job description text for keyword context.
        candidate_context: Optional extra context (metrics, details) the candidate wants included.
    """
    bullet_list = [
        b.lstrip("-•* ").strip()
        for b in bullets.splitlines()
        if b.strip()
    ]
    rewritten = ats.rewrite_bullets(bullet_list, jd_context, candidate_context)
    return "\n".join(f"• {b}" for b in rewritten)


# ---------------------------------------------------------------------------
# Tool: Generate Cover Letter
# ---------------------------------------------------------------------------

@mcp.tool(
    description=(
        "Generate a targeted, 3-paragraph cover letter based on the candidate's "
        "real experience. Tailored to the specific role and company. "
        "No fabricated achievements."
    )
)
def generate_cover_letter(
    resume_text: str,
    jd_text: str,
    company_name: str,
    role_title: str,
    candidate_name: str = "",
    hiring_manager: str = "",
) -> str:
    """Write a targeted cover letter from real experience.

    Args:
        resume_text: Candidate's resume as plain text.
        jd_text: Full job description.
        company_name: Name of the company being applied to.
        role_title: Job title being applied for.
        candidate_name: Candidate's full name (optional).
        hiring_manager: Hiring manager's name (optional).
    """
    return ats.generate_cover_letter(
        resume_text=resume_text,
        jd_text=jd_text,
        company_name=company_name,
        role_title=role_title,
        candidate_name=candidate_name,
        hiring_manager=hiring_manager,
    )


# ---------------------------------------------------------------------------
# Tool: Optimize LinkedIn Profile
# ---------------------------------------------------------------------------

@mcp.tool(
    description=(
        "Generate optimized LinkedIn sections based on a candidate's real qualifications: "
        "headline (max 220 chars), About section, skills to add, experience tips, "
        "and Open to Work title suggestion."
    )
)
def optimize_linkedin_profile(
    profile_text: str,
    target_role: str,
    target_industry: str = "",
) -> str:
    """Optimize LinkedIn headline, about, and skills sections.

    Args:
        profile_text: Candidate's resume or LinkedIn profile as plain text.
        target_role: The role the candidate is targeting (e.g. 'Senior AR Manager').
        target_industry: Target industry (e.g. 'Real Estate Finance').
    """
    result = ats.optimize_linkedin(
        profile_data={"raw_resume": profile_text},
        target_role=target_role,
        target_industry=target_industry,
    )
    return json.dumps(result, indent=2)


# ---------------------------------------------------------------------------
# Tool: Generate Full ATS Resume
# ---------------------------------------------------------------------------

@mcp.tool(
    description=(
        "Generate a complete ATS-optimized resume in plain text. "
        "Proper section order (Summary → Skills → Experience → Education → Certs), "
        "strong action verbs, natural keyword placement. "
        "Uses only the candidate's real experience."
    )
)
def generate_ats_resume(
    resume_text: str,
    jd_text: str,
    target_role: str,
    target_company: str = "",
) -> str:
    """Create a full ATS-safe resume tailored to a job.

    Args:
        resume_text: Candidate's existing resume as plain text.
        jd_text: Job description to tailor the resume for.
        target_role: Role title being applied for.
        target_company: Company name (optional, for personalization).
    """
    return ats.generate_ats_resume(
        resume_data={"raw_resume": resume_text},
        jd_text=jd_text,
        target_role=target_role,
        target_company=target_company,
    )


# ---------------------------------------------------------------------------
# Tool: Resume Variant Guidance
# ---------------------------------------------------------------------------

@mcp.tool(
    description=(
        "Suggest how to tailor a resume for a specific job family without "
        "changing any facts. Returns: rewritten summary, skills to emphasize, "
        "skills to de-emphasize, section order, and keywords to add honestly."
    )
)
def get_resume_variant_guidance(
    resume_text: str,
    jd_text: str,
    job_family: str,
) -> str:
    """Get tailoring guidance for a specific job family.

    Args:
        resume_text: Candidate's resume as plain text.
        jd_text: The job description.
        job_family: Job family to target (e.g. 'Accounts Receivable Manager',
                    'Credit Control', 'Finance Business Partner').
    """
    result = ats.generate_resume_variant(
        resume_data={"raw_resume": resume_text},
        jd_text=jd_text,
        job_family=job_family,
    )
    return json.dumps(result, indent=2)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="stdio")
