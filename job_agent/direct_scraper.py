"""Direct HTTP scraper for Naukri Gulf job listings.

Uses requests + BeautifulSoup to scrape job listings without requiring a
browser or an Apify API token. Works on Render free tier.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from urllib.parse import quote_plus

import requests

from job_agent.config import JOB_SEARCH_PREFERENCES
from job_agent.database import save_application

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/121.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}


def _extract_jobs_from_html(html: str) -> list[dict]:
    """Parse job listings out of a Naukri Gulf search-results page."""
    jobs: list[dict] = []

    # 1) Try Next.js __NEXT_DATA__ embedded JSON first.
    match = re.search(
        r'<script[^>]+id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>',
        html,
        re.DOTALL,
    )
    if match:
        try:
            data = json.loads(match.group(1))
            page_props = data.get("props", {}).get("pageProps", {})
            job_list = (
                page_props.get("jobList")
                or page_props.get("jobs")
                or page_props.get("jobListings")
                or (page_props.get("initialData") or {}).get("jobList")
                or []
            )
            for job in job_list:
                if not isinstance(job, dict):
                    continue
                title = (
                    job.get("title")
                    or job.get("jobTitle")
                    or job.get("designation")
                    or ""
                )
                company = (
                    job.get("company")
                    or job.get("companyName")
                    or job.get("orgName")
                    or ""
                )
                url = (
                    job.get("jdURL")
                    or job.get("url")
                    or job.get("jobUrl")
                    or ""
                )
                if title and company:
                    jobs.append({"title": title, "company": company, "url": url})
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            logger.debug("__NEXT_DATA__ extraction failed: %s", exc)

    # 2) Fallback: BeautifulSoup HTML parsing.
    if not jobs:
        try:
            from bs4 import BeautifulSoup  # noqa: PLC0415

            soup = BeautifulSoup(html, "lxml")
            selectors = [
                ".srp-tuple",
                ".jobTuple",
                "article[class*='job']",
                ".job-card",
                "li[class*='job']",
            ]
            cards = []
            for sel in selectors:
                cards = soup.select(sel)
                if cards:
                    break

            for card in cards:
                title_el = card.select_one(
                    ".desig a, .jobTitle a, h3 a, .title a, h2 a"
                ) or card.select_one(".desig, .jobTitle, h3, h2, .title")
                company_el = card.select_one(
                    ".comp-name a, .companyName a, .company a"
                ) or card.select_one(".comp-name, .companyName, .company")

                if not (title_el and company_el):
                    continue

                title = title_el.get_text(strip=True)
                company = company_el.get_text(strip=True)
                url = (
                    title_el.get("href", "")
                    if title_el.name == "a"
                    else ""
                )
                if title and company:
                    jobs.append({"title": title, "company": company, "url": url})

        except ImportError:
            logger.debug("BeautifulSoup not available for HTML parsing fallback")
        except Exception as exc:
            logger.debug("BeautifulSoup parsing failed: %s", exc)

    return jobs


def scrape_naukri_gulf_direct(max_results: int = 30) -> dict:
    """Scrape Naukri Gulf job listings via plain HTTP requests.

    No browser and no Apify token required — works on Render free tier.
    """
    results: dict = {
        "start_time": datetime.now().isoformat(),
        "platform": "Naukri Gulf (Direct)",
        "jobs_found": 0,
        "jobs_saved": 0,
        "errors": [],
    }

    keywords = JOB_SEARCH_PREFERENCES.get("search_keywords", ["accounts receivable"])
    locations = JOB_SEARCH_PREFERENCES.get("target_locations", ["Dubai"])
    location = locations[0].lower().replace(" ", "-") if locations else "dubai"

    session = requests.Session()
    session.headers.update(_HEADERS)

    for keyword in keywords[:4]:  # limit to 4 keywords to stay within Render's free-tier request budget
        if results["jobs_found"] >= max_results:
            break

        kw_slug = quote_plus(keyword.lower().replace(" ", "-"))
        url = f"https://www.naukrigulf.com/{kw_slug}-jobs-in-{location}"

        try:
            resp = session.get(url, timeout=20)
            resp.raise_for_status()
            jobs_on_page = _extract_jobs_from_html(resp.text)
            logger.info("Keyword '%s': found %d jobs on %s", keyword, len(jobs_on_page), url)

            for job in jobs_on_page:
                if results["jobs_found"] >= max_results:
                    break
                try:
                    save_application(
                        job_title=job["title"],
                        company=job["company"],
                        platform="Naukri Gulf (Direct)",
                        job_url=job.get("url", ""),
                        status="scraped",
                        match_score=None,
                        cover_letter=None,
                        resume_path=None,
                        screenshot_path=None,
                    )
                    results["jobs_found"] += 1
                    results["jobs_saved"] += 1
                except Exception as save_err:
                    results["errors"].append(f"Error saving job: {save_err}")

        except Exception as exc:
            results["errors"].append(f"Scrape failed for '{keyword}': {exc}")
            logger.error("Direct scrape failed for '%s': %s", keyword, exc)

    results["end_time"] = datetime.now().isoformat()
    return results


def run_direct_scrape(max_results: int = 30) -> dict:
    """Convenience entry point for the direct scraper."""
    return scrape_naukri_gulf_direct(max_results=max_results)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    print("Running direct Naukri Gulf scraper...")
    result = run_direct_scrape(max_results=20)
    print(
        f"Jobs found: {result['jobs_found']}  saved: {result['jobs_saved']}  "
        f"errors: {len(result['errors'])}"
    )
    if result["errors"]:
        for err in result["errors"]:
            print(f"  ERROR: {err}")
