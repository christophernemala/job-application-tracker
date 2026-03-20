"""Mock job data — used when MOCK_MODE=true or APIFY_TOKEN is missing."""
from __future__ import annotations
import hashlib
import json
from datetime import datetime, timedelta
import random

_TODAY = datetime.utcnow().date()

_MOCK_JOBS = [
    {
        "title": "Accounts Receivable Analyst",
        "company": "Mashreq Bank",
        "location": "Dubai, UAE",
        "salary_text": "AED 16,000 – 20,000 per month",
        "description": (
            "Manage the full AR cycle including invoicing, cash allocation, "
            "aged debt reporting and collections. Proficiency in SAP, Excel "
            "(vlookups, pivot tables) required. Experience with ERP systems "
            "preferred. Strong communication skills essential."
        ),
        "url": "https://www.linkedin.com/jobs/view/mock-001",
        "source": "linkedin",
        "posted_date": str(_TODAY - timedelta(days=1)),
        "easy_apply_url": "https://www.linkedin.com/jobs/view/mock-001/apply",
    },
    {
        "title": "Credit Control Officer",
        "company": "Emirates Group",
        "location": "Dubai, UAE",
        "salary_text": "",
        "description": (
            "Monitor credit limits, chase outstanding invoices, negotiate "
            "payment plans. Reconciliation of customer accounts, month-end "
            "close support. Oracle Financials experience preferred."
        ),
        "url": "https://www.bayt.com/en/uae/jobs/mock-002",
        "source": "bayt",
        "posted_date": str(_TODAY - timedelta(days=2)),
        "easy_apply_url": None,
    },
    {
        "title": "Collections Specialist",
        "company": "Accenture",
        "location": "Dubai, UAE",
        "salary_text": "AED 15,000 per month",
        "description": (
            "Handle inbound/outbound collection calls, maintain aging reports, "
            "resolve billing disputes. Excel advanced, Power BI a plus. "
            "Finance degree required, 3+ years UAE experience."
        ),
        "url": "https://www.indeed.com/jobs/mock-003",
        "source": "indeed",
        "posted_date": str(_TODAY - timedelta(days=3)),
        "easy_apply_url": "https://www.indeed.com/apply/mock-003",
    },
    {
        "title": "Billing Analyst",
        "company": "Etisalat (e&)",
        "location": "Abu Dhabi, UAE",
        "salary_text": "AED 13,000 per month",
        "description": (
            "Generate and validate invoices, reconcile billing discrepancies, "
            "support month-end close. SAP billing module required."
        ),
        "url": "https://www.gulftaient.com/jobs/mock-004",
        "source": "gulftaient",
        "posted_date": str(_TODAY - timedelta(days=4)),
        "easy_apply_url": None,
    },
    {
        "title": "Finance Operations Manager",
        "company": "DP World",
        "location": "Dubai, UAE",
        "salary_text": "AED 25,000 – 30,000",
        "description": (
            "Lead finance operations team, oversee AR/AP, month-end close, "
            "variance analysis and financial reporting. CPA/ACCA preferred. "
            "10+ years experience in finance operations."
        ),
        "url": "https://www.bayt.com/en/uae/jobs/mock-005",
        "source": "bayt",
        "posted_date": str(_TODAY - timedelta(days=1)),
        "easy_apply_url": None,
    },
    {
        "title": "Reconciliation Analyst",
        "company": "ADCB Bank",
        "location": "Abu Dhabi, UAE",
        "salary_text": "AED 18,000",
        "description": (
            "Daily bank and ledger reconciliation, investigation of breaks, "
            "reporting to finance manager. Advanced Excel, SQL knowledge. "
            "Banking sector experience preferred."
        ),
        "url": "https://www.linkedin.com/jobs/view/mock-006",
        "source": "linkedin",
        "posted_date": str(_TODAY),
        "easy_apply_url": "https://www.linkedin.com/jobs/view/mock-006/apply",
    },
    {
        "title": "Marketing Coordinator",
        "company": "Noon",
        "location": "Dubai, UAE",
        "salary_text": "AED 8,000",
        "description": "Manage social media campaigns and brand activations.",
        "url": "https://www.indeed.com/jobs/mock-007",
        "source": "indeed",
        "posted_date": str(_TODAY - timedelta(days=5)),
        "easy_apply_url": None,
    },
    {
        "title": "AR Specialist – Revenue Recognition",
        "company": "Deloitte",
        "location": "Dubai, UAE",
        "salary_text": "",
        "description": (
            "Support revenue recognition, AR reconciliation, prepare schedules "
            "for audit. ASC 606 / IFRS 15 knowledge required. Big 4 background preferred."
        ),
        "url": "https://www.linkedin.com/jobs/view/mock-008",
        "source": "linkedin",
        "posted_date": str(_TODAY),
        "easy_apply_url": "https://www.linkedin.com/jobs/view/mock-008/apply",
    },
    {
        "title": "Treasury Analyst",
        "company": "Emaar Properties",
        "location": "Dubai, UAE",
        "salary_text": "AED 17,500",
        "description": (
            "Cash flow forecasting, liquidity management, bank relationship management. "
            "Experience with Bloomberg, treasury management systems. CFA candidate preferred."
        ),
        "url": "https://www.bayt.com/en/uae/jobs/mock-009",
        "source": "bayt",
        "posted_date": str(_TODAY - timedelta(days=2)),
        "easy_apply_url": None,
    },
    {
        "title": "Accounts Receivable Officer",
        "company": "Random Startup XYZ",
        "location": "Sharjah, UAE",
        "salary_text": "AED 9,000",
        "description": "Basic AR duties, invoicing and filing.",
        "url": "https://www.gulftaient.com/jobs/mock-010",
        "source": "gulftaient",
        "posted_date": str(_TODAY - timedelta(days=7)),
        "easy_apply_url": None,
    },
]


def _make_id(job: dict) -> str:
    key = f"{job['company']}|{job['title']}|{job['url']}"
    return hashlib.md5(key.encode()).hexdigest()[:12]


def fetch_mock_jobs(source: str | None = None) -> list[dict]:
    """Return normalised mock job records, optionally filtered by source."""
    jobs = []
    for raw in _MOCK_JOBS:
        if source and raw["source"] != source:
            continue
        job = dict(raw)
        job["id"] = _make_id(job)
        job["salary_aed_min"] = _parse_salary(job["salary_text"])
        jobs.append(job)
    return jobs


def _parse_salary(text: str) -> int | None:
    """Best-effort AED min salary extraction from free text."""
    import re
    text = text.replace(",", "")
    nums = re.findall(r"\d{4,6}", text)
    if nums:
        return int(min(nums, key=int))
    return None


if __name__ == "__main__":
    jobs = fetch_mock_jobs()
    print(json.dumps(jobs, indent=2, default=str))
