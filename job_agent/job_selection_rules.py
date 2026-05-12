"""Rule-based UAE finance job scoring for Christopher Nemala.

This module intentionally avoids auto-applying. It scores and selects jobs so the
candidate can manually review and apply from Notion.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class JobRecord:
    title: str
    company: str
    location: str
    source: str
    link: str
    description: str


INCLUDE_KEYWORDS = {
    "ar_o2c_collections": [
        "accounts receivable", "account receivable", " ar ", "order to cash", "o2c",
        "credit control", "collections", "collection", "dso", "aging", "ageing",
        "receivables", "cash application", "customer receipts", "payment follow-up",
        "dunning", "dispute resolution", "bad debt", "doubtful debt", "ecl",
        "credit hold", "credit limit", "customer reconciliation",
    ],
    "billing_invoicing": [
        "billing", "invoicing", "invoice preparation", "invoice issuance",
        "billing accuracy", "credit note", "customer statement", "payment statement",
        "contract billing", "milestone billing", "revenue validation",
    ],
    "reconciliation_month_end": [
        "reconciliation", "reconciliations", "subledger", "general ledger", " gl ",
        "bank reconciliation", "customer reconciliation", "intercompany", "trial balance",
        "month-end", "month end", "journals", "actuals", "forecasts", "audit support",
        "working papers", "variance analysis",
    ],
    "reporting_analytics": [
        "power bi", "dashboard", "aging report", "ageing report", "dso tracking",
        "cash forecasting", "collections performance", "mis", "management reporting",
        "cfo reporting", "excel", "power query", "pivot", "vba", "xlookup",
        "financial analysis", "data visualization",
    ],
    "systems": [
        "oracle fusion", "oracle erp", "oracle ar", "oracle gl", "oracle cash management",
        "salesforce", "yardi", "sap", "advanced excel", "ms office",
    ],
    "compliance_controls": [
        "ifrs 9", "ecl", "ifrs 15", "uae vat", "fta", "corporate tax", "rera",
        "aml", "uae central bank", "audit readiness", "internal controls", "statutory",
        "compliance",
    ],
}

TITLE_KEYWORDS = [
    "accounts receivable", "receivable", "credit controller", "credit control",
    "collections", "collection", "order to cash", "o2c", "billing", "finance operations",
    "reconciliation", "revenue assurance", "finance executive", "accountant",
]

UAE_KEYWORDS = ["dubai", "abu dhabi", "sharjah", "uae", "united arab emirates", "gcc"]

EXCLUDE_IF_MAINLY = [
    "payroll", "fixed asset", "fixed assets", "procurement", "inventory", "cost accountant",
    "internal auditor", "external auditor", "tax manager", "hr", "sales executive",
    "marketing", "software engineer", "it support", "developer", "warehouse",
]

ROLE_TYPE_MAP = [
    ("Credit Control", ["credit controller", "credit control", "credit collections"]),
    ("Collections", ["collections", "collection officer", "collection executive"]),
    ("O2C", ["order to cash", "o2c"]),
    ("Billing", ["billing", "invoicing", "invoice"]),
    ("Reconciliation", ["reconciliation", "reconciliations"]),
    ("Finance Operations", ["finance operations", "finance executive"]),
    ("Finance Admin", ["finance admin", "administration", "admin executive"]),
    ("Accountant", ["accountant", "accounting"]),
    ("AR", ["accounts receivable", "receivable", " ar "]),
]


def normalize(text: str) -> str:
    return f" {re.sub(r'\s+', ' ', (text or '').lower())} "


def count_matches(text: str, keywords: Iterable[str]) -> int:
    haystack = normalize(text)
    return sum(1 for keyword in keywords if normalize(keyword).strip() in haystack)


def detect_role_type(title: str, description: str) -> str:
    combined = normalize(f"{title} {description}")
    for role_type, keywords in ROLE_TYPE_MAP:
        if any(normalize(keyword).strip() in combined for keyword in keywords):
            return role_type
    return "Skip"


def select_cv(role_type: str, text: str) -> str:
    combined = normalize(text)
    if role_type in {"AR", "O2C", "Credit Control", "Collections"}:
        return "Senior AR/O2C CV"
    if role_type == "Finance Admin":
        return "Finance Admin CV"
    if any(k in combined for k in ["month-end", "month end", "journals", "financial reporting", "audit support"]):
        return "Financial Controller CV"
    if role_type in {"Billing", "Reconciliation", "Finance Operations", "Accountant"}:
        return "Financial Controller CV"
    return "Senior AR/O2C CV"


def score_job(job: JobRecord) -> dict:
    title = job.title or ""
    description = job.description or ""
    combined = f"{title} {job.company} {job.location} {description}"
    combined_norm = normalize(combined)

    excluded_hits = [kw for kw in EXCLUDE_IF_MAINLY if kw in combined_norm]
    include_total = sum(count_matches(combined, kws) for kws in INCLUDE_KEYWORDS.values())
    if excluded_hits and include_total < 4:
        return build_result(job, 0, "Skip", "Skip", [], [], excluded_hits, "Skip")

    role_title_points = min(15, count_matches(title, TITLE_KEYWORDS) * 5)
    ar_points = min(20, count_matches(combined, INCLUDE_KEYWORDS["ar_o2c_collections"]) * 3)
    billing_points = min(10, count_matches(combined, INCLUDE_KEYWORDS["billing_invoicing"]) * 3)
    recon_points = min(15, count_matches(combined, INCLUDE_KEYWORDS["reconciliation_month_end"]) * 3)
    reporting_points = min(10, count_matches(combined, INCLUDE_KEYWORDS["reporting_analytics"]) * 2)
    systems_points = min(10, count_matches(combined, INCLUDE_KEYWORDS["systems"]) * 3)
    uae_points = 10 if count_matches(combined, UAE_KEYWORDS) else 4
    seniority_points = 10 if count_matches(combined, ["senior", "executive", "specialist", "analyst", "assistant manager", "manager"]) else 6

    score = role_title_points + ar_points + billing_points + recon_points + reporting_points + systems_points + uae_points + seniority_points
    score = max(0, min(100, score))

    if score >= 80:
        priority = "High"
        status = "Apply Today"
        next_action = "Apply"
    elif score >= 65:
        priority = "Medium"
        status = "Scored"
        next_action = "Message Recruiter"
    elif score >= 50:
        priority = "Low"
        status = "Scored"
        next_action = "Apply"
    else:
        priority = "Skip"
        status = "Skip"
        next_action = "Skip"

    matched_skills = []
    ats_keywords = []
    for group_keywords in INCLUDE_KEYWORDS.values():
        for keyword in group_keywords:
            if normalize(keyword).strip() in combined_norm:
                ats_keywords.append(keyword)
                matched_skills.append(keyword)

    missing_gaps = excluded_hits[:]
    role_type = detect_role_type(title, description)
    recommended_cv = select_cv(role_type, combined)

    return build_result(
        job=job,
        score=score,
        priority=priority,
        status=status,
        ats_keywords=sorted(set(ats_keywords))[:30],
        matched_skills=sorted(set(matched_skills))[:30],
        missing_gaps=missing_gaps,
        next_action=next_action,
        role_type=role_type,
        recommended_cv=recommended_cv,
    )


def build_result(
    job: JobRecord,
    score: int,
    priority: str,
    status: str,
    ats_keywords: list[str],
    matched_skills: list[str],
    missing_gaps: list[str],
    next_action: str,
    role_type: str | None = None,
    recommended_cv: str | None = None,
) -> dict:
    role_type = role_type or detect_role_type(job.title, job.description)
    recommended_cv = recommended_cv or select_cv(role_type, f"{job.title} {job.description}")
    recruiter_message = (
        f"Hi [Name], I am interested in the {job.title} role at {job.company}. "
        "My background is aligned with AR, O2C, credit control, collections, billing, "
        "reconciliations, Oracle Fusion, and Power BI reporting. I have managed AED 100M+ "
        "receivables portfolios and supported DSO, aging, and management reporting across UAE entities. "
        "Please let me know if my profile can be reviewed."
    )
    hiring_manager_message = (
        f"Hi [Name], I noticed the {job.title} opening at {job.company}. "
        "My experience is focused on AR, O2C, collections, credit control, billing, reconciliations, "
        "Oracle Fusion, and Power BI reporting across UAE finance operations. I would be glad to be considered "
        "if the role is still open."
    )
    return {
        "real_role_type": role_type,
        "match_score": score,
        "priority": priority,
        "recommended_cv": recommended_cv,
        "status": status,
        "ats_keywords": ats_keywords,
        "matched_skills": matched_skills,
        "missing_gaps": missing_gaps,
        "apply_decision": "Skip" if priority == "Skip" else ("Apply" if score >= 80 else "Apply Selectively"),
        "recruiter_message": recruiter_message,
        "hiring_manager_message": hiring_manager_message,
        "interview_prep_points": [
            "Explain AR/O2C cycle from billing to cash application.",
            "Explain collections strategy using aging and risk tiering.",
            "Explain reconciliation and month-end support experience.",
            "Explain Power BI reporting for DSO, aging, and collections.",
            "Explain AED 100M+ portfolio and AED 9M recovery impact.",
        ],
        "next_action": next_action,
    }
