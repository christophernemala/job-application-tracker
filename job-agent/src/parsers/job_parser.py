"""Job parser and normalizer.

Normalizes raw job data collected from various sources into
consistent formats, classifies apply types, and extracts
structured metadata from titles and descriptions.
"""

import re
from typing import Optional

from src.collectors.base_collector import RawJob
from src.utils.logger import get_logger

logger = get_logger(__name__)


def normalize_title(title: str) -> str:
    """Normalize a job title for consistent matching.

    Removes extra whitespace, strips common prefixes/suffixes,
    and standardizes abbreviations.

    Args:
        title: Raw job title.

    Returns:
        Cleaned, normalized title string.
    """
    if not title:
        return ""

    t = title.strip()

    # Remove common prefixes
    prefixes = [
        r"^(?:Hiring|Urgent(?:ly)?|Immediate)\s*[-:!]?\s*",
        r"^(?:WE ARE HIRING)\s*[-:!]?\s*",
    ]
    for pattern in prefixes:
        t = re.sub(pattern, "", t, flags=re.IGNORECASE)

    # Remove location suffixes like "- Dubai" or "(UAE)"
    t = re.sub(r"\s*[-–]\s*(?:Dubai|Abu Dhabi|UAE|Sharjah|Remote)\s*$", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\s*\((?:Dubai|Abu Dhabi|UAE|Sharjah|Remote)\)\s*$", "", t, flags=re.IGNORECASE)

    # Normalize common abbreviations
    replacements = {
        r"\bSr\.?\b": "Senior",
        r"\bJr\.?\b": "Junior",
        r"\bMgr\.?\b": "Manager",
        r"\bAsst\.?\b": "Assistant",
        r"\bA/R\b": "AR",
        r"\bA\.R\.\b": "AR",
        r"\bAccts?\b": "Accounts",
    }
    for pattern, replacement in replacements.items():
        t = re.sub(pattern, replacement, t, flags=re.IGNORECASE)

    # Collapse whitespace
    t = re.sub(r"\s+", " ", t).strip()
    return t


def normalize_company(company: Optional[str]) -> Optional[str]:
    """Normalize company name."""
    if not company:
        return None
    c = company.strip()
    # Remove common suffixes
    c = re.sub(r"\s*(LLC|Ltd\.?|Inc\.?|Corp\.?|FZ-LLC|FZCO|DMCC)\s*$", "", c, flags=re.IGNORECASE)
    c = re.sub(r"\s+", " ", c).strip()
    return c if c else None


def parse_salary(salary_text: Optional[str]) -> tuple[Optional[float], Optional[float]]:
    """Parse salary text into min/max numeric values in AED.

    Handles formats like:
    - "AED 14,000 - 18,000"
    - "14000-18000 AED per month"
    - "AED 15K - 20K"
    - "15,000 AED"

    Args:
        salary_text: Raw salary string.

    Returns:
        Tuple of (salary_min, salary_max) in AED, or (None, None).
    """
    if not salary_text:
        return None, None

    text = salary_text.upper().replace(",", "").replace(" ", "")

    # Detect currency – only process AED/no currency (assume AED for UAE)
    # Skip if clearly USD, EUR, etc.
    if any(curr in text for curr in ["USD", "EUR", "GBP", "INR"]):
        return None, None

    # Extract numbers
    numbers = re.findall(r"(\d+(?:\.\d+)?)\s*K?", text)
    if not numbers:
        return None, None

    values = []
    for num_str in numbers:
        val = float(num_str)
        # Check if "K" follows this number in original text
        idx = text.find(num_str)
        if idx >= 0 and idx + len(num_str) < len(text) and text[idx + len(num_str)] == "K":
            val *= 1000
        # If value seems too low for monthly salary, might be in thousands
        if val < 100:
            val *= 1000
        values.append(val)

    if len(values) >= 2:
        return min(values[0], values[1]), max(values[0], values[1])
    elif len(values) == 1:
        return values[0], values[0]

    return None, None


def normalize_location(location: Optional[str]) -> Optional[str]:
    """Normalize location string.

    Args:
        location: Raw location text.

    Returns:
        Normalized location string.
    """
    if not location:
        return None

    loc = location.strip()
    # Standardize common UAE locations
    loc_map = {
        r"(?i)\bdxb\b": "Dubai",
        r"(?i)\bauh\b": "Abu Dhabi",
        r"(?i)\bshj\b": "Sharjah",
        r"(?i)\bajm\b": "Ajman",
        r"(?i)\bunited arab emirates\b": "UAE",
    }
    for pattern, replacement in loc_map.items():
        loc = re.sub(pattern, replacement, loc)

    return re.sub(r"\s+", " ", loc).strip()


def classify_apply_type(raw_apply_type: Optional[str], url: str, description: Optional[str] = None) -> str:
    """Classify the application type for routing decisions.

    Categories:
    - easy_apply: Platform internal one-click apply (LinkedIn Easy Apply, NaukriGulf internal)
    - internal: Platform's own multi-step form
    - external_simple: External site with simple form
    - external_complex: External ATS (Workday, Taleo, iCIMS, etc.)
    - unknown: Cannot determine

    Args:
        raw_apply_type: Apply type from collector.
        url: Job URL.
        description: Job description text.

    Returns:
        Classified apply type string.
    """
    if raw_apply_type == "easy_apply":
        return "easy_apply"

    if raw_apply_type == "internal":
        return "internal"

    url_lower = url.lower()

    # Detect complex ATS systems
    complex_ats = [
        "workday", "taleo", "icims", "greenhouse", "lever.co",
        "successfactors", "smartrecruiters", "bamboohr",
        "myworkdayjobs", "jobs.lever.co",
    ]
    for ats in complex_ats:
        if ats in url_lower:
            return "external_complex"

    # Simple external forms
    if any(domain in url_lower for domain in ["naukrigulf.com", "bayt.com", "indeed.com"]):
        return "internal"

    if "linkedin.com" in url_lower:
        return "external_simple"

    return "unknown"


def extract_keywords(title: str, description: Optional[str] = None) -> list[str]:
    """Extract relevant finance/AR keywords from title and description.

    Args:
        title: Job title.
        description: Optional job description.

    Returns:
        List of matched keyword strings.
    """
    text = (title + " " + (description or "")).lower()

    keyword_patterns = {
        "accounts_receivable": r"\b(?:accounts?\s*receivable|a/?r)\b",
        "order_to_cash": r"\b(?:order\s*to\s*cash|o2c|otc)\b",
        "credit_control": r"\b(?:credit\s*control|credit\s*controller)\b",
        "collections": r"\b(?:collections?|debt\s*collection)\b",
        "credit_risk": r"\b(?:credit\s*risk|risk\s*analyst)\b",
        "reconciliation": r"\b(?:reconciliation|reconciling)\b",
        "aging": r"\b(?:aging|ageing|aged?\s*analysis)\b",
        "dispute_resolution": r"\b(?:dispute\s*resolution|disputes?)\b",
        "oracle": r"\b(?:oracle\s*(?:fusion|ebs|erp|cloud)?)\b",
        "sap": r"\b(?:sap\s*(?:fico|fi|s/?4)?)\b",
        "erp": r"\b(?:erp|enterprise\s*resource)\b",
        "dunning": r"\b(?:dunning)\b",
        "dso": r"\b(?:dso|days\s*sales\s*outstanding)\b",
        "bad_debt": r"\b(?:bad\s*debt|write.?off|provision)\b",
        "cash_application": r"\b(?:cash\s*application|payment\s*allocation)\b",
        "revenue": r"\b(?:revenue\s*recognition|ifrs\s*15)\b",
    }

    matched = []
    for keyword, pattern in keyword_patterns.items():
        if re.search(pattern, text, re.IGNORECASE):
            matched.append(keyword)

    return matched


def detect_seniority(title: str) -> Optional[str]:
    """Detect seniority level from job title.

    Args:
        title: Job title string.

    Returns:
        Seniority label or None.
    """
    title_lower = title.lower()

    seniority_map = [
        (r"\b(?:director|head\s+of|vp|vice\s+president)\b", "director"),
        (r"\b(?:assistant\s+manager|asst\.?\s*manager)\b", "assistant_manager"),
        (r"\b(?:manager|mgr)\b", "manager"),
        (r"\b(?:team\s*lead|lead)\b", "lead"),
        (r"\b(?:senior|sr\.?)\b", "senior"),
        (r"\b(?:specialist|analyst)\b", "specialist"),
        (r"\b(?:executive|officer)\b", "executive"),
        (r"\b(?:junior|jr\.?)\b", "junior"),
        (r"\b(?:intern|trainee|fresher)\b", "intern"),
    ]

    for pattern, level in seniority_map:
        if re.search(pattern, title_lower):
            return level

    return None


def parse_raw_job(raw_job: RawJob) -> dict:
    """Parse and normalize a raw job into a storage-ready dict.

    Args:
        raw_job: RawJob instance from a collector.

    Returns:
        Dict with normalized fields ready for database insertion.
    """
    normalized_title = normalize_title(raw_job.title)
    salary_min, salary_max = parse_salary(raw_job.salary_text)
    apply_type = classify_apply_type(raw_job.apply_type, raw_job.url, raw_job.description)
    keywords = extract_keywords(raw_job.title, raw_job.description)
    seniority = detect_seniority(normalized_title)

    return {
        "source": raw_job.source,
        "title": raw_job.title,
        "normalized_title": normalized_title,
        "company": normalize_company(raw_job.company),
        "location": normalize_location(raw_job.location),
        "salary_text": raw_job.salary_text,
        "salary_min": salary_min,
        "salary_max": salary_max,
        "posted_date": raw_job.posted_date,
        "url": raw_job.url,
        "description": raw_job.description,
        "apply_type": apply_type,
        "metadata": {
            "keywords": keywords,
            "seniority": seniority,
            "collected_at": raw_job.collected_at,
        },
    }
