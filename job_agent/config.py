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
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        os.environ.setdefault(key.strip(), value)


_load_local_env()

USER_PROFILE = {
    "name": os.getenv("JOB_AGENT_NAME", "Christopher Nemala"),
    "current_role": os.getenv(
        "JOB_AGENT_CURRENT_ROLE",
        "Senior Credit & Collections Executive | Order-to-Cash (O2C) | AR Governance | Credit Control | Community/Real Estate Receivables",
    ),
    "years_experience": os.getenv("JOB_AGENT_YEARS_EXPERIENCE", "5+"),
    "location": os.getenv("JOB_AGENT_LOCATION", "Dubai, UAE"),
    "phone": os.getenv("JOB_AGENT_PHONE", "+971-565839277"),
    "email": os.getenv("JOB_AGENT_EMAIL", "christophernemala@gmail.com"),
    "linkedin": os.getenv("JOB_AGENT_LINKEDIN", "linkedin.com/in/christophernemala"),
    "professional_summary": (
        "Senior AR, credit control, and collections professional with 5+ years of "
        "progressive experience supporting enterprise shared services outcomes in "
        "receivables governance, billing-to-cash controls, cash application, dispute "
        "resolution, and close readiness. Proven track record across banking, financial "
        "services, and real estate sectors in UAE, delivering best-in-class service "
        "delivery, robust controls, digital innovation, and continuous improvement."
    ),
    "core_competencies": [
        "Order-to-Cash (O2C) Governance",
        "Accounts Receivable Management",
        "Credit Control",
        "Collections Strategy & Execution",
        "Cash Application & Reconciliation",
        "Dispute & Deduction Management",
        "IFRS 9 ECL Provisioning",
        "Revenue Assurance",
        "Real Estate Receivables",
        "Community Management Billing",
        "Regulatory Reporting",
        "Oracle Fusion AR/GL",
        "Salesforce CRM",
        "Yardi Integration",
        "Power BI Dashboards",
    ],
    "professional_experience": [
        {
            "company": "Dubai Holding Group Services",
            "role": "Senior AR Credit & Collections Executive",
            "period": "May 2025 - Present",
            "highlights": [
                "Orchestrated end-to-end Order-to-Cash receivables governance across community management entities, covering billing controls, collections execution, dispute closure, cash application, and AR close readiness.",
                "Drove monthly debt collection plans through aging bucket governance and case prioritization, enhancing cash realization across portfolios.",
                "Negotiated repayment solutions for overdue accounts, documenting interactions and enforcing adherence through effective escalation pathways.",
                "Administered credit control actions, including account accuracy validation and risk escalation, ensuring compliance with policy and controls.",
                "Governed cash application quality by matching receipts to invoices, resolving discrepancies, and reconciling cash with bank records.",
                "Led dispute and deduction management by collaborating with internal stakeholders, investigating root causes, and issuing corrective documentation.",
                "Maintained audit-ready AR records through subledger integrity and strong documentation discipline, supporting month-end closing.",
                "Produced leadership-grade AR reporting for management, highlighting aging movement, collection progress, and cash forecast inputs.",
                "Implemented ERP-enabled automation in collections using Oracle Fusion and Power BI, improving process efficiency and reducing manual touchpoints.",
            ],
        },
        {
            "company": "Emaar Properties PJSC",
            "role": "Finance Executive - Accounts Receivable & Credit Control",
            "period": "March 2024 - May 2025",
            "highlights": [
                "Managed full-cycle accounts receivable operations for real estate portfolios, overseeing invoice governance, collections follow-up, and dispute handling.",
                "Executed revenue assurance controls by validating invoice accuracy and documentation, reducing preventable disputes and leakage.",
                "Assessed customer payment risk, maintained credit limits, and recommended credit holds/releases to protect against defaults.",
                "Captured remittance details, reconciled applied payments, and resolved short/unapplied items to uphold cash application integrity.",
                "Coordinated finance clearances for property transfers, ensuring compliance with enterprise AR controls and documentation standards.",
                "Managed service charge and community receivables cycles in compliance with Dubai's community management standards.",
                "Supported IFRS 9 impairment awareness by preparing aging-based provision inputs per simplified approaches.",
                "Strengthened data integrity across finance systems (Oracle, Yardi) through consistent monitoring and corrective actions.",
                "Enhanced stakeholder coordination for dispute resolution, ensuring timely engagement with sales and leasing teams.",
            ],
        },
        {
            "company": "Emirates International Exchange",
            "role": "Accountant - Treasury and Foreign Exchange Operations",
            "period": "March 2023 - March 2024",
            "highlights": [
                "Ensured accurate and complete financial accounting for exchange operations, maintaining compliance with UAE Central Bank requirements.",
                "Supported regulatory report submissions, ensuring timely and accurate reporting of remittance and exchange operations.",
                "Conducted daily reconciliations with banks, escalating unreconciled items promptly to uphold control standards.",
                "Monitored liquidity and capital adequacy indicators, assisting management oversight in regulatory functions.",
                "Executed multi-currency remittance activities with strict adherence to documentation and transaction support evidence.",
                "Produced treasury oversight reports identifying cash positions, reconciliation statuses, and operational risks.",
                "Collaborated across branches and banking partners to resolve transaction exceptions effectively.",
                "Standardized reconciliation templates to enhance accuracy and reduce unresolved discrepancies.",
                "Maintained organized records consistent with AML/CFT compliance for audit readiness.",
            ],
        },
        {
            "company": "Bank of Baroda / Firstsource Solutions",
            "role": "Accounts Executive",
            "period": "September 2020 - January 2023",
            "highlights": [
                "Processed account services workflows including account openings, maintenance, and closures with strong adherence to procedures.",
                "Ensured master data integrity through thorough documentation validation and controlled handling of exceptions.",
                "Executed operational controls for transaction processing, ensuring compliance with banking standards.",
                "Supported wire operations, meeting strict deadlines and maintaining documentation for audit purposes.",
                "Conducted control-account balancing and reconciliation tasks, identifying discrepancies and proposing corrective actions.",
                "Researched and resolved account queries, maintaining clear audit trails and service quality.",
                "Produced operational tracking reports to identify recurring defects and improve efficiency.",
                "Maintained audit-ready documentation, completing periodic certifications as required.",
                "Escalated suspicious items through established control channels, contributing to overall fraud prevention strategies.",
            ],
        },
    ],
    "education": [
        "MBA (Business Management - Finance) - Swiss School of Business and Management, Geneva | 2025",
        "B.Com. (Bachelor of Commerce) - Andhra University | 2020",
    ],
    "certifications": [
        "Microsoft Certified: Data Analyst Associate | 2025",
        "Business Analytics Program | Ongoing",
        "Generative AI Learning Track | In Progress",
    ],
    "technical_skills": {
        "ERP Systems": "Oracle Fusion (AR, GL, Cash Management), SAP FI/RE, Yardi Property Management, Salesforce CRM",
        "Analytics & Reporting": "Power BI, Advanced Excel (Pivot Tables, VBA), Financial Forecasting",
        "Financial Controls": "Bank Reconciliation Systems, IFRS Reporting, Multi-Entity Consolidation, AML Compliance",
        "Treasury & FX": "Multi-Currency Processing, SWIFT Operations, Regulatory Reporting",
    },
    "skills": [
        "Order-to-Cash (O2C) Governance",
        "Accounts Receivable Management",
        "Credit Control",
        "Collections Strategy & Execution",
        "Cash Application & Reconciliation",
        "Dispute & Deduction Management",
        "IFRS 9 ECL Provisioning",
        "Revenue Assurance",
        "Real Estate Receivables",
        "Community Management Billing",
        "Regulatory Reporting",
        "Oracle Fusion (AR, GL, Cash Management)",
        "SAP FI/RE",
        "Yardi Property Management",
        "Salesforce CRM",
        "Power BI",
        "Advanced Excel (Pivot Tables, VBA)",
        "Financial Forecasting",
        "Bank Reconciliation Systems",
        "IFRS Reporting",
        "Multi-Entity Consolidation",
        "AML Compliance",
        "Multi-Currency Processing",
        "SWIFT Operations",
    ],
}

NAUKRI_GULF_CREDENTIALS = {
    "email": os.getenv("NAUKRI_GULF_EMAIL", USER_PROFILE["email"]),
    "password": os.getenv("NAUKRI_GULF_PASSWORD", ""),
}

# =============================================================================
# JOB SEARCH PREFERENCES
# Target: Senior AR / Credit & Collections roles from Senior to Assistant Manager
# =============================================================================
JOB_SEARCH_PREFERENCES = {
    "target_roles": [
        # Senior-level AR & Collections
        "Senior Accounts Receivable Executive",
        "Senior Credit and Collections Executive",
        "Senior AR Executive",
        "Senior Credit Control Executive",
        "AR Credit Collections Executive",
        # Team Leader level
        "Team Leader Accounts Receivable",
        "AR Team Leader",
        "Collections Team Leader",
        "Credit Control Team Leader",
        # Assistant Manager level
        "Assistant Manager Accounts Receivable",
        "Assistant Manager AR",
        "Assistant Manager Credit Control",
        "Assistant Manager Collections",
        "Assistant Manager Order to Cash",
        # Manager level (Credit Control)
        "Credit Control Manager",
        "AR Manager",
        "Accounts Receivable Manager",
        "Collections Manager",
        # O2C / Order-to-Cash
        "Order to Cash Specialist",
        "Order to Cash Manager",
        "O2C Lead",
        "O2C Manager",
        "O2C Specialist",
        # General AR roles in range
        "Finance Executive Accounts Receivable",
        "Receivables Executive",
        "Credit and Collections Specialist",
    ],
    # Search keywords used when querying job boards
    "search_keywords": [
        "accounts receivable",
        "credit control",
        "collections",
        "order to cash",
        "AR manager",
        "credit collections",
        "O2C",
        "receivables",
    ],
    "target_industries": [
        "Real Estate",
        "Community Management",
        "Financial Services",
        "Banking",
        "Property Management",
        "FMCG",
        "Retail",
        "Shared Services",
        "Technology",
        "Healthcare",
    ],
    "target_locations": ["Dubai", "Abu Dhabi", "Sharjah", "UAE"],
    "minimum_salary_aed": 12000,
    "experience_level": "Mid-Senior Level (5-8 years)",
    # Seniority range: Senior Executive up to Assistant Manager / Manager
    "seniority_range": ["Senior", "Team Leader", "Assistant Manager", "Manager"],
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
