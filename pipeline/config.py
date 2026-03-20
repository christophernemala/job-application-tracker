"""Central configuration — all tuneable values and secrets in one place."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).parent.parent
INPUTS_DIR = BASE_DIR / "inputs"
OUTPUTS_DIR = BASE_DIR / "outputs"
TAILORED_CVS_DIR = OUTPUTS_DIR / "tailored_cvs"
QUEUE_DIR = OUTPUTS_DIR / "application_queue"
LOGS_DIR = BASE_DIR / "logs"

for _d in [INPUTS_DIR, OUTPUTS_DIR, TAILORED_CVS_DIR, QUEUE_DIR, LOGS_DIR]:
    _d.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Mode
# ---------------------------------------------------------------------------
MOCK_MODE: bool = os.getenv("MOCK_MODE", "true").lower() == "true"

# ---------------------------------------------------------------------------
# API Keys / Secrets
# ---------------------------------------------------------------------------
APIFY_TOKEN: str = os.getenv("APIFY_TOKEN", "")
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
ZAPIER_WEBHOOK: str = os.getenv("ZAPIER_WEBHOOK", "")

# ---------------------------------------------------------------------------
# Input Files
# ---------------------------------------------------------------------------
CV_PATH = INPUTS_DIR / os.getenv("CV_FILE", "cv_base.md")
CV_TEMPLATE_PATH = INPUTS_DIR / os.getenv("CV_TEMPLATE", "cv_template.md")

# ---------------------------------------------------------------------------
# Tracker
# ---------------------------------------------------------------------------
TRACKER_DB = OUTPUTS_DIR / "tracker.db"

# ---------------------------------------------------------------------------
# Search Parameters
# ---------------------------------------------------------------------------
SEARCH_KEYWORDS: list[str] = [
    k.strip()
    for k in os.getenv(
        "SEARCH_KEYWORDS",
        "accounts receivable,credit control,collections,billing,"
        "reconciliation,finance operations,AR analyst,finance officer",
    ).split(",")
]

TARGET_LOCATIONS = [
    "dubai", "uae", "united arab emirates",
    "abu dhabi", "sharjah", "ajman", "remote",
]

LOCATION_SCORES: dict[str, int] = {
    "dubai": 20,
    "uae": 18,
    "united arab emirates": 18,
    "abu dhabi": 15,
    "sharjah": 12,
    "ajman": 10,
    "remote": 8,
}

SALARY_MIN_AED: int = int(os.getenv("SALARY_MIN_AED", "14000"))
SHORTLIST_THRESHOLD: int = int(os.getenv("SHORTLIST_THRESHOLD", "60"))

# ---------------------------------------------------------------------------
# Finance Domain Matching
# ---------------------------------------------------------------------------
FINANCE_TITLES: list[str] = [
    "accounts receivable", "ar analyst", "ar specialist", "ar officer",
    "credit control", "credit analyst", "credit officer",
    "collections", "collections analyst", "collections officer",
    "billing analyst", "billing specialist", "billing officer",
    "reconciliation", "reconciliation analyst",
    "finance analyst", "financial analyst", "finance officer",
    "finance operations", "finance manager", "senior finance",
    "reporting analyst", "financial reporting",
    "treasury analyst", "treasury officer",
    "accounts payable", "general ledger", "gl accountant",
    "revenue analyst", "cash management", "payment processing",
]

FINANCE_SKILLS: list[str] = [
    "excel", "sap", "oracle", "dynamics", "netsuite", "quickbooks",
    "accounts receivable", "credit control", "collections", "billing",
    "reconciliation", "aged debt", "debtors", "invoicing", "cash allocation",
    "financial reporting", "variance analysis", "month end", "year end",
    "vlookup", "pivot tables", "power bi", "sql", "erp",
    "journal entries", "bank reconciliation", "cash flow",
    "xero", "sage", "tally",
]

STRONG_COMPANIES: list[str] = [
    "emirates", "etisalat", "e&", "du telecom", "mashreq", "enbd", "adcb",
    "fab", "nbad", "cbd", "dib", "hsbc", "standard chartered", "citibank",
    "accenture", "deloitte", "pwc", "kpmg", "ey", "grant thornton", "bdo",
    "amazon", "microsoft", "google", "oracle", "sap", "salesforce",
    "dp world", "damac", "emaar", "aldar", "mubadala", "adq",
    "lufthansa", "air arabia", "flydubai", "dnata",
    "carrefour", "lulu", "majid al futtaim", "al futtaim",
    "schneider electric", "siemens", "ge", "abb", "honeywell",
    "parsons", "jacobs", "aecom", "wsp", "atkins",
    "unilever", "nestle", "p&g", "johnson & johnson", "abbott",
]

# ---------------------------------------------------------------------------
# Apify Actor IDs
# ---------------------------------------------------------------------------
APIFY_ACTORS: dict[str, str] = {
    "linkedin": os.getenv("ACTOR_LINKEDIN", "apify/linkedin-jobs-scraper"),
    "indeed": os.getenv("ACTOR_INDEED", "misceres/indeed-scraper"),
    "bayt": os.getenv("ACTOR_BAYT", "apify/website-content-crawler"),
    "gulftaient": os.getenv("ACTOR_GULFTAIENT", "apify/website-content-crawler"),
}

APIFY_ACTOR_INPUTS: dict[str, dict] = {
    "linkedin": {
        "queries": SEARCH_KEYWORDS[:5],
        "location": "United Arab Emirates",
        "count": 50,
        "proxy": {"useApifyProxy": True},
    },
    "indeed": {
        "queries": [f"{kw} UAE" for kw in SEARCH_KEYWORDS[:4]],
        "country": "AE",
        "maxItems": 50,
    },
    "bayt": {
        "startUrls": [
            {"url": "https://www.bayt.com/en/uae/jobs/accounts-receivable-jobs/"},
            {"url": "https://www.bayt.com/en/uae/jobs/credit-control-jobs/"},
            {"url": "https://www.bayt.com/en/uae/jobs/collections-specialist-jobs/"},
            {"url": "https://www.bayt.com/en/uae/jobs/billing-analyst-jobs/"},
        ],
        "maxCrawlDepth": 2,
        "maxCrawlPages": 100,
    },
    "gulftaient": {
        "startUrls": [
            {"url": "https://www.gulftaient.com/jobs/?q=accounts+receivable&l=UAE"},
            {"url": "https://www.gulftaient.com/jobs/?q=credit+control&l=UAE"},
            {"url": "https://www.gulftaient.com/jobs/?q=collections&l=UAE"},
        ],
        "maxCrawlDepth": 2,
        "maxCrawlPages": 80,
    },
}

# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------
SCHEDULE_HOUR: int = int(os.getenv("SCHEDULE_HOUR", "7"))   # 07:00 daily
SCHEDULE_MINUTE: int = int(os.getenv("SCHEDULE_MINUTE", "0"))

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = LOGS_DIR / "pipeline.log"
