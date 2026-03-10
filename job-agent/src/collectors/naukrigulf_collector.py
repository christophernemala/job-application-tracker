"""NaukriGulf job collector using Playwright.

Collects job listings from NaukriGulf search pages.
Handles login, job card extraction, and apply type detection.
"""

import os
from typing import Optional

from src.collectors.base_collector import BaseCollector, RawJob
from src.utils.logger import get_logger, get_screenshot_path

logger = get_logger(__name__)

# Configurable selectors for NaukriGulf
SELECTORS = {
    "job_card": "div.srp-tuple, article.jobTuple, div.list-card",
    "job_title": "a.desig, h2.title a, a.jobTitle",
    "job_company": "a.comp-name, span.company-name, a.companyInfo",
    "job_location": "span.loc, span.location, span.ellipsis.loc",
    "job_salary": "span.salary, span.sal, div.salary-range",
    "job_date": "span.date, span.posted-date, span.fleft.fw500.fs12.grey-text",
    "job_link": "a.desig, h2.title a, a.jobTitle",
    "apply_button": "button.apply-btn, a.apply-btn, button.chatbot-apply-btn",
    "login_email": "#usernameField, input[name='username'], input[type='email']",
    "login_password": "#passwordField, input[name='password'], input[type='password']",
    "login_submit": "button[type='submit'], button.loginButton",
}

MAX_PAGES_PER_SEARCH = 3
PAGE_LOAD_WAIT_SEC = 3


class NaukriGulfCollector(BaseCollector):
    """Collector for NaukriGulf job listings.

    Primary UAE job board with internal application system.
    """

    def __init__(self, source_config: dict, page=None):
        """Initialize NaukriGulf collector.

        Args:
            source_config: Source configuration from sources.json.
            page: Optional Playwright page to reuse an existing session.
        """
        super().__init__(source_config)
        self._page = page
        self._owns_browser = page is None

    def collect(self) -> list[RawJob]:
        """Collect jobs from all configured NaukriGulf search URLs.

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
        """Attempt NaukriGulf login.

        Args:
            page: Playwright page instance.

        Returns:
            True if login succeeded.
        """
        email = os.environ.get("NAUKRIGULF_EMAIL", "")
        password = os.environ.get("NAUKRIGULF_PASSWORD", "")

        if not email or not password:
            self.logger.warning(
                "NaukriGulf credentials not set. Collecting in public mode."
            )
            return False

        try:
            login_url = self.source_config.get(
                "login_url", "https://www.naukrigulf.com/login"
            )
            page.goto(login_url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2000)

            # Try each selector variant for email field
            for selector in SELECTORS["login_email"].split(", "):
                try:
                    el = page.query_selector(selector)
                    if el:
                        el.fill(email)
                        break
                except Exception:
                    continue

            # Try each selector variant for password field
            for selector in SELECTORS["login_password"].split(", "):
                try:
                    el = page.query_selector(selector)
                    if el:
                        el.fill(password)
                        break
                except Exception:
                    continue

            # Submit
            for selector in SELECTORS["login_submit"].split(", "):
                try:
                    el = page.query_selector(selector)
                    if el:
                        el.click()
                        break
                except Exception:
                    continue

            page.wait_for_timeout(5000)
            self.logger.info("NaukriGulf login attempted")
            return True

        except Exception as e:
            self.logger.error("NaukriGulf login failed: %s", str(e))
            screenshot = get_screenshot_path("login_error", source="naukrigulf")
            try:
                page.screenshot(path=str(screenshot))
            except Exception:
                pass
            return False

    def _collect_from_url(self, page, search_url: str) -> list[RawJob]:
        """Collect jobs from a single NaukriGulf search URL.

        Args:
            page: Playwright page instance.
            search_url: NaukriGulf search URL.

        Returns:
            List of RawJob objects.
        """
        jobs: list[RawJob] = []

        try:
            self.logger.info("Collecting from: %s", search_url)
            page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(PAGE_LOAD_WAIT_SEC * 1000)

            for page_num in range(MAX_PAGES_PER_SEARCH):
                # Scroll to load content
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
                if not self._go_to_next_page(page):
                    break

        except Exception as e:
            self.logger.error("Error collecting from %s: %s", search_url, str(e))
            screenshot = get_screenshot_path("collect_error", source="naukrigulf")
            try:
                page.screenshot(path=str(screenshot))
            except Exception:
                pass

        self.logger.info("Collected %d jobs from %s", len(jobs), search_url)
        return jobs

    def _extract_job_from_card(self, card) -> Optional[RawJob]:
        """Extract job data from a NaukriGulf job card.

        Args:
            card: Playwright element handle.

        Returns:
            RawJob or None.
        """
        try:
            # Title + URL
            title_el = card.query_selector(SELECTORS["job_title"])
            title = title_el.inner_text().strip() if title_el else None
            if not title:
                return None

            link_el = card.query_selector(SELECTORS["job_link"])
            url = link_el.get_attribute("href") if link_el else None
            if not url:
                return None
            if url.startswith("/"):
                url = "https://www.naukrigulf.com" + url

            # Company
            company_el = card.query_selector(SELECTORS["job_company"])
            company = company_el.inner_text().strip() if company_el else None

            # Location
            location_el = card.query_selector(SELECTORS["job_location"])
            location = location_el.inner_text().strip() if location_el else None

            # Salary
            salary_el = card.query_selector(SELECTORS["job_salary"])
            salary_text = salary_el.inner_text().strip() if salary_el else None

            # Date
            date_el = card.query_selector(SELECTORS["job_date"])
            posted_date = date_el.inner_text().strip() if date_el else None

            return RawJob(
                source="naukrigulf",
                title=title,
                url=url,
                company=company,
                location=location,
                salary_text=salary_text,
                posted_date=posted_date,
                apply_type="internal",  # NaukriGulf has internal apply
            )

        except Exception as e:
            self.logger.debug("Failed to extract NaukriGulf card: %s", str(e))
            return None

    def _scroll_page(self, page, scrolls: int = 3) -> None:
        """Scroll to trigger lazy loading."""
        for _ in range(scrolls):
            page.evaluate("window.scrollBy(0, window.innerHeight)")
            page.wait_for_timeout(1500)

    def _go_to_next_page(self, page) -> bool:
        """Navigate to the next page of results."""
        try:
            next_btn = page.query_selector(
                "a.next-page, a[class*='next'], a.pagination-next, "
                "a[aria-label='Next']"
            )
            if next_btn:
                next_btn.click()
                page.wait_for_timeout(PAGE_LOAD_WAIT_SEC * 1000)
                return True
        except Exception:
            pass
        return False
