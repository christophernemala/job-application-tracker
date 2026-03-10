"""Generic career page collector.

A flexible collector for company career pages and other job boards
that don't have a dedicated collector. Uses configurable selectors.
"""

from typing import Optional

from src.collectors.base_collector import BaseCollector, RawJob
from src.utils.logger import get_logger, get_screenshot_path

logger = get_logger(__name__)

PAGE_LOAD_WAIT_SEC = 3


class GenericCollector(BaseCollector):
    """Generic collector that works with configurable CSS selectors.

    Source config must include a 'selectors' dict with at minimum:
    - job_card: CSS selector for job card containers
    - job_title: CSS selector for title within a card
    - job_link: CSS selector for the link within a card
    """

    def __init__(self, source_config: dict, page=None):
        super().__init__(source_config)
        self._page = page
        self._owns_browser = page is None
        self._selectors = source_config.get("selectors", {})

    def collect(self) -> list[RawJob]:
        """Collect jobs using configurable selectors."""
        all_jobs: list[RawJob] = []

        if not self._selectors.get("job_card"):
            self.logger.warning(
                "[%s] No selectors configured. Skipping.", self.source_name
            )
            return all_jobs

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
                )
                page = context.new_page()

                for search_url in self.search_urls:
                    jobs = self._collect_from_url(page, search_url)
                    all_jobs.extend(jobs)

                browser.close()
        else:
            for search_url in self.search_urls:
                jobs = self._collect_from_url(self._page, search_url)
                all_jobs.extend(jobs)

        self._log_collection_result(all_jobs)
        return all_jobs

    def _collect_from_url(self, page, search_url: str) -> list[RawJob]:
        """Collect from a single URL."""
        jobs: list[RawJob] = []

        try:
            self.logger.info("Collecting from: %s", search_url)
            page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(PAGE_LOAD_WAIT_SEC * 1000)

            # Scroll to load content
            for _ in range(3):
                page.evaluate("window.scrollBy(0, window.innerHeight)")
                page.wait_for_timeout(1000)

            cards = page.query_selector_all(self._selectors["job_card"])
            self.logger.debug("Found %d job cards", len(cards))

            for card in cards:
                raw_job = self._extract_job_from_card(card)
                if raw_job and raw_job.url not in {j.url for j in jobs}:
                    jobs.append(raw_job)

        except Exception as e:
            self.logger.error("Error collecting from %s: %s", search_url, str(e))

        return jobs

    def _extract_job_from_card(self, card) -> Optional[RawJob]:
        """Extract job data using configured selectors."""
        try:
            sel = self._selectors

            # Title (required)
            title_el = card.query_selector(sel.get("job_title", ""))
            title = title_el.inner_text().strip() if title_el else None
            if not title:
                return None

            # URL (required)
            link_el = card.query_selector(sel.get("job_link", ""))
            url = link_el.get_attribute("href") if link_el else None
            if not url:
                return None

            # Company
            company_el = card.query_selector(sel.get("job_company", ""))
            company = company_el.inner_text().strip() if company_el else None

            # Location
            location_el = card.query_selector(sel.get("job_location", ""))
            location = location_el.inner_text().strip() if location_el else None

            # Salary
            salary_el = card.query_selector(sel.get("job_salary", ""))
            salary_text = salary_el.inner_text().strip() if salary_el else None

            return RawJob(
                source=self.source_name,
                title=title,
                url=url,
                company=company,
                location=location,
                salary_text=salary_text,
                apply_type="external",
            )

        except Exception as e:
            self.logger.debug("Failed to extract card: %s", str(e))
            return None
