"""Configuration for AI Job Agent user profile, credentials, and job preferences."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any


def _load_local_env() -> None:
    """Load key=value pairs from local .env if present (no external dependency)."""
    env_file = Path(__file__).resolve().parent / ".env"
    if not env_file.exists():
        return

    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


_load_local_env()

USER_PROFILE = {
    "name": os.getenv("JOB_AGENT_NAME", "Christopher Nemala"),
    "current_role": os.getenv(
        "JOB_AGENT_CURRENT_ROLE",
        "Senior Credit & Collections Executive - Order-to-Cash",
    ),
    "years_experience": os.getenv("JOB_AGENT_YEARS_EXPERIENCE", "5+"),
    "location": os.getenv("JOB_AGENT_LOCATION", "Dubai, UAE"),
    "phone": os.getenv("JOB_AGENT_PHONE", "+971 565839277"),
    "email": os.getenv("JOB_AGENT_EMAIL", "christophernemala@gmail.com"),
    "linkedin": os.getenv("JOB_AGENT_LINKEDIN", "linkedin.com/in/christophernemala"),
    "skills": [
        "Oracle Fusion",
        "Power BI",
        "Advanced Excel",
        "SAP (Basic)",
        "Order-to-Cash (O2C)",
        "AR Ageing Management",
        "DSO Reduction",
        "Cash Flow Forecasting",
        "Sub-Ledger Reconciliation",
        "Month-End Closing",
        "IFRS 9 ECL Provisioning",
        "SOX Compliance",
        "Customer-Facing Collections",
        "Dispute Resolution",
        "Credit Control",
        "PDC Management",
        "Escrow Account Reconciliation",
    ],
    "education": [
        "MBA in Finance - Swiss School of Business Management, Geneva",
        "Bachelor of Commerce - Andhra University, India",
    ],
}

NAUKRI_GULF_CREDENTIALS = {
    "email": os.getenv("NAUKRI_GULF_EMAIL", USER_PROFILE["email"]),
    "password": os.getenv("NAUKRI_GULF_PASSWORD", ""),
}

JOB_SEARCH_PREFERENCES = {
    "target_roles": [
        "Credit & Collections Executive",
        "AR Specialist",
        "O2C Specialist",
        "Finance Executive",
        "Accounts Receivable Manager",
    ],
    "target_industries": [
        "Real Estate",
        "Financial Services",
        "Banking",
        "FMCG",
        "Retail",
    ],
    "target_locations": ["Dubai", "Abu Dhabi", "Sharjah", "UAE"],
    "minimum_salary_aed": 12000,
    "experience_level": "Mid-Senior Level (5-7 years)",
}


def get_naukri_gulf_credentials() -> tuple[str, str]:
    """Return configured Naukri Gulf credentials and validate they exist."""
    email = NAUKRI_GULF_CREDENTIALS.get("email", "").strip()
    password = NAUKRI_GULF_CREDENTIALS.get("password", "")
    if not email or not password:
        raise RuntimeError(
            "Naukri Gulf credentials are missing. Set NAUKRI_GULF_EMAIL and NAUKRI_GULF_PASSWORD in environment or job_agent/.env"
        )
    return email, password


def get_runtime_config_snapshot() -> dict[str, Any]:
    """Safe config snapshot for diagnostics without exposing secrets."""
    return {
        "user_profile": USER_PROFILE,
        "job_search_preferences": JOB_SEARCH_PREFERENCES,
        "naukri_gulf_email": NAUKRI_GULF_CREDENTIALS.get("email", ""),
        "naukri_gulf_password_set": bool(NAUKRI_GULF_CREDENTIALS.get("password")),
    }
