"""Apify-based job scraper for LinkedIn and Naukri Gulf.

Uses Apify actors to collect job listings without browser overhead,
then stores them in the local database for review and application.
"""
from __future__ import annotations

import logging
import os
import time
from datetime import datetime
from typing import Any

import requests

from job_agent.config import JOB_SEARCH_PREFERENCES
from job_agent.database import save_application
from job_agent.slack_notifier import notify_error, notify_scrape_results

logger = logging.getLogger(__name__)

APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN", "")
APIFY_BASE_URL = "https://api.apify.com/v2"

# Well-known Apify actor IDs for job scraping
LINKEDIN_ACTOR = "hMvNSpz3JnHgl5jkh"  # LinkedIn Jobs Scraper
NAUKRI_ACTOR = "moJRLRc85AitArpNN"  # Naukri Jobs Scraper (generic web scraper fallback)


def _call_apify_actor(actor_id: str, run_input: dict, timeout_secs: int = 120) -> list[dict[str, Any]]:
    """Run an Apify actor synchronously and return the dataset items."""
    if not APIFY_API_TOKEN:
        raise RuntimeError(
            "APIFY_API_TOKEN is not set. Get one from https://console.apify.com/account#/integrations"
        )

    headers = {"Authorization": f"Bearer {APIFY_API_TOKEN}"}

    # Start the actor run
    start_url = f"{APIFY_BASE_URL}/acts/{actor_id}/runs"
    resp = requests.post(
        start_url,
        json=run_input,
        headers=headers,
        params={"timeout": timeout_secs},
        timeout=30,
    )
    resp.raise_for_status()
    run_data = resp.json().get("data", {})
    run_id = run_data.get("id")

    if not run_id:
        raise RuntimeError(f"Apify actor did not return a run ID: {run_data}")

    logger.info("Apify run started: %s (actor: %s)", run_id, actor_id)

    # Poll until the run finishes
    status_url = f"{APIFY_BASE_URL}/actor-runs/{run_id}"
    deadline = time.time() + timeout_secs + 30
    while time.time() < deadline:
        status_resp = requests.get(status_url, headers=headers, timeout=15)
        status_resp.raise_for_status()
        status = status_resp.json().get("data", {}).get("status")

        if status == "SUCCEEDED":
            break
        elif status in ("FAILED", "ABORTED", "TIMED-OUT"):
            raise RuntimeError(f"Apify run {run_id} ended with status: {status}")

        time.sleep(5)
    else:
        raise RuntimeError(f"Apify run {run_id} timed out after {timeout_secs}s")

    # Fetch dataset items
    dataset_id = status_resp.json().get("data", {}).get("defaultDatasetId")
    if not dataset_id:
        return []

    items_url = f"{APIFY_BASE_URL}/datasets/{dataset_id}/items"
    items_resp = requests.get(items_url, headers=headers, params={"limit": 100}, timeout=30)
    items_resp.raise_for_status()
    return items_resp.json()


def scrape_linkedin_jobs(max_results: int = 50) -> dict:
    """Scrape LinkedIn job listings via Apify and save to database."""
    results = {
        "start_time": datetime.now().isoformat(),
        "platform": "LinkedIn (Apify)",
        "jobs_found": 0,
        "jobs_saved": 0,
        "errors": [],
    }

    search_keywords = JOB_SEARCH_PREFERENCES.get("search_keywords", ["accounts receivable"])
    locations = JOB_SEARCH_PREFERENCES.get("target_locations", ["Dubai"])

    # Build search URLs for the LinkedIn actor
    search_urls = []
    for keyword in search_keywords[:4]:
        for location in locations[:2]:
            from urllib.parse import quote_plus
            search_urls.append(
                f"https://www.linkedin.com/jobs/search/"
                f"?keywords={quote_plus(keyword)}&location={quote_plus(location)}&f_AL=true"
            )

    run_input = {
        "searchUrl": search_urls[0] if len(search_urls) == 1 else search_urls,
        "scrapeJobDetails": True,
        "maxItems": max_results,
    }

    try:
        logger.info("Running LinkedIn Apify scraper with %d search URLs", len(search_urls))
        items = _call_apify_actor(LINKEDIN_ACTOR, run_input, timeout_secs=180)
        results["jobs_found"] = len(items)
        logger.info("Apify returned %d LinkedIn jobs", len(items))

        for item in items:
            try:
                job_title = item.get("title") or item.get("jobTitle") or "Unknown"
                company = item.get("companyName") or item.get("company") or "Unknown"
                job_url = item.get("url") or item.get("jobUrl") or ""
                location = item.get("location") or item.get("jobLocation") or ""
                description = item.get("description") or item.get("jobDescription") or ""

                if not job_title or job_title == "Unknown":
                    continue

                save_application(
                    job_title=job_title,
                    company=company,
                    platform="LinkedIn (Apify)",
                    job_url=job_url,
                    status="scraped",
                    match_score=None,
                    cover_letter=None,
                    resume_path=None,
                    screenshot_path=None,
                )
                results["jobs_saved"] += 1
            except Exception as e:
                results["errors"].append(f"Error saving job: {e}")

    except Exception as e:
        results["errors"].append(str(e))
        logger.error("LinkedIn Apify scrape failed: %s", e)
        notify_error(str(e), platform="LinkedIn (Apify)")

    results["end_time"] = datetime.now().isoformat()
    notify_scrape_results(results)
    return results


def scrape_naukri_jobs(max_results: int = 50) -> dict:
    """Scrape Naukri Gulf job listings via Apify and save to database."""
    results = {
        "start_time": datetime.now().isoformat(),
        "platform": "Naukri Gulf (Apify)",
        "jobs_found": 0,
        "jobs_saved": 0,
        "errors": [],
    }

    search_keywords = JOB_SEARCH_PREFERENCES.get("search_keywords", ["accounts receivable"])
    locations = JOB_SEARCH_PREFERENCES.get("target_locations", ["Dubai"])

    # Build Naukri Gulf search URLs
    search_urls = []
    for keyword in search_keywords[:4]:
        location = locations[0].lower().replace(" ", "-") if locations else "dubai"
        kw_slug = keyword.lower().replace(" ", "-")
        search_urls.append(f"https://www.naukrigulf.com/{kw_slug}-jobs-in-{location}")

    run_input = {
        "startUrls": [{"url": u} for u in search_urls],
        "maxPagesPerCrawl": 3,
        "maxItems": max_results,
    }

    try:
        logger.info("Running Naukri Gulf Apify scraper with %d URLs", len(search_urls))
        items = _call_apify_actor(NAUKRI_ACTOR, run_input, timeout_secs=180)
        results["jobs_found"] = len(items)
        logger.info("Apify returned %d Naukri Gulf jobs", len(items))

        for item in items:
            try:
                job_title = item.get("title") or item.get("jobTitle") or "Unknown"
                company = item.get("company") or item.get("companyName") or "Unknown"
                job_url = item.get("url") or item.get("link") or ""

                if not job_title or job_title == "Unknown":
                    continue

                save_application(
                    job_title=job_title,
                    company=company,
                    platform="Naukri Gulf (Apify)",
                    job_url=job_url,
                    status="scraped",
                    match_score=None,
                    cover_letter=None,
                    resume_path=None,
                    screenshot_path=None,
                )
                results["jobs_saved"] += 1
            except Exception as e:
                results["errors"].append(f"Error saving job: {e}")

    except Exception as e:
        results["errors"].append(str(e))
        logger.error("Naukri Apify scrape failed: %s", e)
        notify_error(str(e), platform="Naukri Gulf (Apify)")

    results["end_time"] = datetime.now().isoformat()
    notify_scrape_results(results)
    return results


def run_apify_scrape(platform: str = "all", max_results: int = 50) -> dict:
    """Run Apify scraping for specified platform(s).

    Args:
        platform: "linkedin", "naukri", or "all"
        max_results: Max job listings to fetch per platform

    Returns:
        Combined results dictionary
    """
    results = []

    if platform in ("linkedin", "all"):
        results.append(scrape_linkedin_jobs(max_results=max_results))

    if platform in ("naukri", "all"):
        results.append(scrape_naukri_jobs(max_results=max_results))

    if len(results) == 1:
        return results[0]
    return {"runs": results}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    print("Running Apify job scraper...")
    result = run_apify_scrape(platform="all", max_results=10)
    print(result)
