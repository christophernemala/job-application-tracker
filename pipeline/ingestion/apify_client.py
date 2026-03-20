"""Apify integration — fetches jobs from live actors.

Falls back to mock mode automatically when APIFY_TOKEN is missing.
"""
from __future__ import annotations
import hashlib
import re
import time
from typing import Any

from pipeline.config import (
    APIFY_TOKEN,
    APIFY_ACTORS,
    APIFY_ACTOR_INPUTS,
    MOCK_MODE,
)
from pipeline.ingestion.mock_client import fetch_mock_jobs
from pipeline.utils.logger import get_logger
from pipeline.utils.retry import retry

log = get_logger(__name__)


def _make_id(company: str, title: str, url: str) -> str:
    key = f"{company.lower()}|{title.lower()}|{url}"
    return hashlib.md5(key.encode()).hexdigest()[:12]


def _parse_salary(text: str) -> int | None:
    """Extract the lower-bound AED number from a salary string."""
    if not text:
        return None
    text = text.replace(",", "").upper()
    # Strip non-AED currencies
    if any(c in text for c in ["USD", "GBP", "EUR"]):
        return None
    nums = re.findall(r"\d{4,6}", text)
    if nums:
        return int(min(nums, key=int))
    return None


def _normalise(raw: dict, source: str) -> dict:
    """Map actor-specific fields to our canonical schema."""
    title = raw.get("title") or raw.get("jobTitle") or raw.get("name") or ""
    company = raw.get("company") or raw.get("companyName") or raw.get("employer") or ""
    location = raw.get("location") or raw.get("jobLocation") or raw.get("place") or ""
    salary_text = raw.get("salary") or raw.get("salaryRange") or raw.get("compensation") or ""
    description = raw.get("description") or raw.get("jobDescription") or raw.get("body") or ""
    url = raw.get("url") or raw.get("jobUrl") or raw.get("link") or ""
    posted = raw.get("postedAt") or raw.get("publishedAt") or raw.get("date") or ""
    easy_apply = raw.get("applyUrl") or raw.get("easyApplyUrl") or None

    return {
        "id": _make_id(company, title, url),
        "title": title.strip(),
        "company": company.strip(),
        "location": location.strip(),
        "salary_text": salary_text.strip(),
        "salary_aed_min": _parse_salary(salary_text),
        "description": description.strip()[:3000],
        "url": url.strip(),
        "source": source,
        "posted_date": str(posted)[:10],
        "easy_apply_url": easy_apply,
    }


@retry(max_attempts=3, delay=5.0)
def _run_actor(actor_id: str, actor_input: dict) -> list[dict]:
    """Run an Apify actor and return the dataset items."""
    try:
        from apify_client import ApifyClient  # type: ignore
    except ImportError as e:
        raise RuntimeError(
            "apify-client not installed. Run: pip install apify-client"
        ) from e

    client = ApifyClient(APIFY_TOKEN)
    log.info("Running actor %s …", actor_id)
    run = client.actor(actor_id).call(run_input=actor_input)
    items: list[dict] = []
    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
        items.append(item)
    log.info("Actor %s returned %d items.", actor_id, len(items))
    return items


def fetch_jobs(source: str) -> list[dict]:
    """Fetch jobs for a given source. Returns normalised job dicts."""
    if MOCK_MODE or not APIFY_TOKEN:
        if not APIFY_TOKEN:
            log.warning(
                "APIFY_TOKEN not set — using mock data for source '%s'.", source
            )
        else:
            log.info("MOCK_MODE=true — using mock data for source '%s'.", source)
        return fetch_mock_jobs(source=source)

    actor_id = APIFY_ACTORS.get(source)
    if not actor_id:
        log.warning("No actor configured for source '%s'. Skipping.", source)
        return []

    actor_input = APIFY_ACTOR_INPUTS.get(source, {})
    raw_items = _run_actor(actor_id, actor_input)
    return [_normalise(item, source) for item in raw_items]


def fetch_all_jobs() -> list[dict]:
    """Fetch and merge jobs from all configured sources."""
    all_jobs: list[dict] = []
    for source in APIFY_ACTORS:
        try:
            jobs = fetch_jobs(source)
            all_jobs.extend(jobs)
            log.info("Source %-12s → %d jobs fetched.", source, len(jobs))
        except Exception as exc:  # pylint: disable=broad-except
            log.error("Source %s failed: %s — skipping.", source, exc)
    return all_jobs
