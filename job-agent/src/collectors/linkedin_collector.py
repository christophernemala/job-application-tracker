"""LinkedIn job collector using Playwright.

Collects job listings from LinkedIn job search pages.
Handles login, pagination, and job card extraction.
"""

import os
import time
from typing import Optional

from src.collectors.base_collector import BaseCollector, RawJob
from src.utils.logger import get_logger, get_screenshot_path

logger = get_logger(__name__)

# Configurable selectors for LinkedIn (can be updated if site changes)
SELECTORS = {
    "job_card": "div.job-search-card, li.jobs-search-results__list-item, div.base-card",
    "job_title": "h3.base-search-card__title, a.job-card-list__title, h3.job-search-card__title",
    "job_company": "h4.base-search-card__subtitle, span.job-search-card__company-name, a.job-card-container__company-name",
    "job_location": "span.job-search-card__location, span.job-card-container__metadata-item",
    "job_link": "a.base-card__full-link, a.job-card-list__title, a.job-card-container__link",
    "job_date": "time, span.job-search-card__listdate",
    "login_email": "#username",
    "login_password": "#password",
    "login_submit": "button[type='submit']",
    "easy_apply_badge": "span.job-card-container__apply-method, li-icon[type='linkedin-bug']",
}

MAX_PAGES_PER_SEARCH = 3
SCROLL_PAUSE_SEC = 1.5
PAGE_LOAD_WAIT_SEC = 3


class LinkedInCollector(BaseCollector):
    """Collector for LinkedIn job listings.

    Uses Playwright for browser-based scraping. Supports both
    logged-in and public (limited) collection modes.
    """

    def __init__(self, source_config: dict, page=None):
        """Initialize LinkedIn collector.

        Args:
            source_config: Source configuration from sources.json.
            page: Optional Playwright page to reuse an existing session.
        """
        super().__init__(source_config)
        self._page = page
        self._owns_browser = page is None

    def collect(self) -> list[RawJob]:
        """Collect jobs from all configured LinkedIn search URLs.

        Returns:
            List of RawJob objects.
        """
        all_jobs: list[RawJob] = []

        if self._owns_browser:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                    viewport={"width": 1280, "height": 800},
                )
                page = context.new_page()

                if self.requires_login:
                    self._login(page)

                for search_url in self.search_urls:
                    jobs = self._collect_from_url(page, search_url)
                    all_jobs.extend(jobs)

                browser.close()
        else:
            if self.requires_login:
                self._login(self._page)

            for search_url in self.search_urls:
                jobs = self._collect_from_url(self._page, search_url)
                all_jobs.extend(jobs)

        self._log_collection_result(all_jobs)
        return all_jobs

    def _login(self, page) -> bool:
        """Attempt LinkedIn login using environment credentials.

        Args:
            page: Playwright page instance.

        Returns:
            True if login succeeded or was already logged in.
        """
        email = os.environ.get("LINKEDIN_EMAIL", "")
        password = os.environ.get("LINKEDIN_PASSWORD", "")

        if not email or not password:
            self.logger.warning(
                "LinkedIn credentials not set. Collecting in public/limited mode."
            )
            return False

        try:
            login_url = self.source_config.get("login_url", "https://www.linkedin.com/login")
            page.goto(login_url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2000)

            # Check if already logged in
            if "feed" in page.url or "mynetwork" in page.url:
                self.logger.info("Already logged into LinkedIn")
                return True

            page.fill(SELECTORS["login_email"], email)
            page.fill(SELECTORS["login_password"], password)
            page.click(SELECTORS["login_submit"])
            page.wait_for_timeout(5000)

            if "challenge" in page.url or "checkpoint" in page.url:
                self.logger.warning(
                    "LinkedIn security challenge detected. Manual intervention needed."
                )
                screenshot = get_screenshot_path("login_challenge", source="linkedin")
                page.screenshot(path=str(screenshot))
                return False

            self.logger.info("LinkedIn login successful")
            return True

        except Exception as e:
            self.logger.error("LinkedIn login failed: %s", str(e))
            screenshot = get_screenshot_path("login_error", source="linkedin")
            try:
                page.screenshot(path=str(screenshot))
            except Exception:
                pass
            return False

    def _collect_from_url(self, page, search_url: str) -> list[RawJob]:
        """Collect jobs from a single LinkedIn search URL.

        Args:
            page: Playwright page instance.
            search_url: LinkedIn job search URL.

        Returns:
            List of RawJob objects found on this search page.
        """
        jobs: list[RawJob] = []

        try:
            self.logger.info("Collecting from: %s", search_url)
            page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(PAGE_LOAD_WAIT_SEC * 1000)

            for page_num in range(MAX_PAGES_PER_SEARCH):
                # Scroll to load more results
                self._scroll_page(page)

                # Extract job cards
                cards = page.query_selector_all(SELECTORS["job_card"])
                self.logger.debug(
                    "Page %d: Found %d job cards", page_num + 1, len(cards)
                )

                for card in cards:
                    raw_job = self._extract_job_from_card(card)
                    if raw_job and raw_job.url not in {j.url for j in jobs}:
                        jobs.append(raw_job)

                # Try next page
                if not self._go_to_next_page(page, page_num):
                    break

        except Exception as e:
            self.logger.error("Error collecting from %s: %s", search_url, str(e))
            screenshot = get_screenshot_path("collect_error", source="linkedin")
            try:
                page.screenshot(path=str(screenshot))
            except Exception:
                pass

        self.logger.info("Collected %d jobs from %s", len(jobs), search_url)
        return jobs

    def _extract_job_from_card(self, card) -> Optional[RawJob]:
        """Extract job data from a single job card element.

        Args:
            card: Playwright element handle for a job card.

        Returns:
            RawJob object or None if extraction fails.
        """
        try:
            # Title
            title_el = card.query_selector(SELECTORS["job_title"])
            title = title_el.inner_text().strip() if title_el else None
            if not title:
                return None

            # URL
            link_el = card.query_selector(SELECTORS["job_link"])
            url = link_el.get_attribute("href") if link_el else None
            if not url:
                return None
            # Clean tracking params
            if "?" in url:
                url = url.split("?")[0]

            # Company
            company_el = card.query_selector(SELECTORS["job_company"])
            company = company_el.inner_text().strip() if company_el else None

            # Location
            location_el = card.query_selector(SELECTORS["job_location"])
            location = location_el.inner_text().strip() if location_el else None

            # Date
            date_el = card.query_selector(SELECTORS["job_date"])
            posted_date = None
            if date_el:
                posted_date = date_el.get_attribute("datetime") or date_el.inner_text().strip()

            # Easy Apply detection
            easy_apply_el = card.query_selector(SELECTORS["easy_apply_badge"])
            apply_type = "easy_apply" if easy_apply_el else "external"

            return RawJob(
                source="linkedin",
                title=title,
                url=url,
                company=company,
                location=location,
                posted_date=posted_date,
                apply_type=apply_type,
            )

        except Exception as e:
            self.logger.debug("Failed to extract job card: %s", str(e))
            return None

    def _scroll_page(self, page, scrolls: int = 3) -> None:
        """Scroll down the page to trigger lazy-loaded content."""
        for _ in range(scrolls):
            page.evaluate("window.scrollBy(0, window.innerHeight)")
            page.wait_for_timeout(int(SCROLL_PAUSE_SEC * 1000))

    def _go_to_next_page(self, page, current_page: int) -> bool:
        """Try to navigate to the next page of results.

        Args:
            page: Playwright page.
            current_page: Current page number (0-indexed).

        Returns:
            True if navigation succeeded.
        """
        try:
            next_button = page.query_selector(
                "button[aria-label='Next'], li.artdeco-pagination__indicator--number button"
            )
            if next_button and next_button.is_enabled():
                next_button.click()
                page.wait_for_timeout(PAGE_LOAD_WAIT_SEC * 1000)
                return True
        except Exception:
            pass
        return False
