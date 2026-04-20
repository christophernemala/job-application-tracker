"""Auto-apply runner with human-like behavior for LinkedIn and Naukri Gulf."""

from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from job_agent.automation import (
    authenticate_linkedin_with_config,
    authenticate_naukri_gulf_with_config,
    setup_selenium_driver,
)
from job_agent.config import JOB_SEARCH_PREFERENCES, USER_PROFILE
from job_agent.database import (
    get_connection,
    init_database,
    log_event,
    save_application,
)
from job_agent.human_scheduler import (
    DailySchedule,
    HumanScheduler,
    RateLimits,
)
from job_agent import slack_notifier

logger = logging.getLogger(__name__)


@dataclass
class JobListing:
    """Represents a discovered job listing."""
    title: str
    company: str
    location: str
    url: str
    platform: str
    description: str = ""
    salary: str = ""
    easy_apply: bool = False


class HumanBehaviorMixin:
    """Mixin for human-like browser interactions."""

    def human_scroll(self, driver, direction: str = "down", amount: int | None = None) -> None:
        """Scroll with human-like speed and variation."""
        if amount is None:
            amount = random.randint(200, 500)

        scroll_amount = amount if direction == "down" else -amount

        # Smooth scroll in increments
        increments = random.randint(3, 7)
        per_increment = scroll_amount // increments

        for _ in range(increments):
            driver.execute_script(f"window.scrollBy(0, {per_increment})")
            time.sleep(random.uniform(0.05, 0.15))

    def human_type(self, element, text: str, clear_first: bool = True) -> None:
        """Type text with human-like speed variation."""
        if clear_first:
            element.clear()
            time.sleep(random.uniform(0.1, 0.3))

        for char in text:
            element.send_keys(char)
            # Variable typing speed
            delay = random.gauss(0.08, 0.03)
            time.sleep(max(0.02, delay))

            # Occasional longer pauses (thinking)
            if random.random() < 0.05:
                time.sleep(random.uniform(0.2, 0.5))

    def random_mouse_movement(self, driver) -> None:
        """Simulate random mouse movements via JavaScript."""
        # Move mouse to random positions (simulated via JS events)
        script = """
        var event = new MouseEvent('mousemove', {
            clientX: arguments[0],
            clientY: arguments[1],
            bubbles: true
        });
        document.dispatchEvent(event);
        """
        for _ in range(random.randint(2, 5)):
            x = random.randint(100, 1200)
            y = random.randint(100, 800)
            driver.execute_script(script, x, y)
            time.sleep(random.uniform(0.1, 0.3))


class AutoApplyRunner(HumanBehaviorMixin):
    """
    Main auto-apply runner that orchestrates job searching and applications
    across LinkedIn and Naukri Gulf with human-like behavior.
    """

    def __init__(
        self,
        rate_limits: RateLimits | None = None,
        schedule: DailySchedule | None = None,
        headless: bool = True,
    ):
        self.scheduler = HumanScheduler(rate_limits, schedule)
        self.headless = headless
        self.drivers: dict[str, Any] = {}
        self.search_keywords = JOB_SEARCH_PREFERENCES["search_keywords"]
        self.target_locations = JOB_SEARCH_PREFERENCES["target_locations"]

        # Track applied jobs to avoid duplicates
        self._applied_urls: set[str] = set()
        self._load_applied_jobs()

        # Register scheduler callbacks
        self.scheduler.register_callback("on_daily_limit_reached", self._on_limit_reached)
        self.scheduler.register_callback("on_application_complete", self._on_application_done)

    def _load_applied_jobs(self) -> None:
        """Load previously applied job URLs from database."""
        init_database()
        with get_connection() as conn:
            rows = conn.execute("SELECT job_url FROM applications WHERE job_url IS NOT NULL").fetchall()
            self._applied_urls = {row["job_url"] for row in rows}
        logger.info("Loaded %d previously applied job URLs", len(self._applied_urls))

    def _on_limit_reached(self, platform: str) -> None:
        logger.warning("Daily limit reached for %s", platform)
        log_event("daily_limit", "info", f"Daily limit reached for {platform}")

    def _on_application_done(self, platform: str, success: bool, total_today: dict) -> None:
        logger.info("Application complete: %s (success=%s), totals: %s", platform, success, total_today)
    def _get_driver(self, platform: str):
        """Get or create authenticated driver for platform."""
        if platform in self.drivers and self.drivers[platform]:
            try:
                # Check if driver is still alive
                _ = self.drivers[platform].current_url
                return self.drivers[platform]
            except Exception:
                logger.info("Driver for %s is stale, re-authenticating", platform)

        logger.info("Authenticating to %s...", platform)
        if platform == "linkedin":
            self.drivers[platform] = authenticate_linkedin_with_config(headless=self.headless)
        elif platform == "naukri":
            self.drivers[platform] = authenticate_naukri_gulf_with_config(headless=self.headless)
        else:
            raise ValueError(f"Unknown platform: {platform}")

        log_event("authenticate", "success", platform)
        return self.drivers[platform]

    def search_linkedin_jobs(self, keyword: str, location: str = "UAE") -> list[JobListing]:
        """Search LinkedIn for jobs matching keyword."""
        driver = self._get_driver("linkedin")
        jobs: list[JobListing] = []

        try:
            # Navigate to jobs search
            search_url = (
                f"https://www.linkedin.com/jobs/search/"
                f"?keywords={keyword.replace(' ', '%20')}"
                f"&location={location.replace(' ', '%20')}"
                f"&f_AL=true"  # Easy Apply filter
            )
            driver.get(search_url)

            # Human-like wait for page load
            time.sleep(self.scheduler.get_page_view_delay("linkedin"))
            self.human_scroll(driver, "down", random.randint(200, 400))

            # Wait for job cards to load
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".jobs-search-results-list"))
            )

            # Find job cards
            job_cards = driver.find_elements(
                By.CSS_SELECTOR,
                ".jobs-search-results__list-item, .job-card-container"
            )[:10]  # Limit to first 10

            for card in job_cards:
                try:
                    self.human_scroll(driver, "down", random.randint(50, 150))
                    time.sleep(random.uniform(0.5, 1.5))

                    title_elem = card.find_element(By.CSS_SELECTOR, ".job-card-list__title, .job-card-container__link")
                    company_elem = card.find_element(By.CSS_SELECTOR, ".job-card-container__company-name, .artdeco-entity-lockup__subtitle")
                    location_elem = card.find_element(By.CSS_SELECTOR, ".job-card-container__metadata-item, .artdeco-entity-lockup__caption")

                    job_url = title_elem.get_attribute("href") or ""
                    if job_url and job_url not in self._applied_urls:
                        jobs.append(JobListing(
                            title=title_elem.text.strip(),
                            company=company_elem.text.strip(),
                            location=location_elem.text.strip(),
                            url=job_url.split("?")[0],  # Clean URL
                            platform="linkedin",
                            easy_apply=True,  # Filtered for Easy Apply
                        ))
                except (NoSuchElementException, StaleElementReferenceException):
                    continue

            logger.info("Found %d LinkedIn jobs for '%s'", len(jobs), keyword)

        except Exception as e:
            logger.error("LinkedIn search failed: %s", e)
            log_event("linkedin_search", "error", str(e))

        return jobs

    def search_naukri_jobs(self, keyword: str, location: str = "Dubai") -> list[JobListing]:
        """Search Naukri Gulf for jobs matching keyword."""
        driver = self._get_driver("naukri")
        jobs: list[JobListing] = []

        try:
            # Navigate to search
            search_url = (
                f"https://www.naukrigulf.com/{keyword.replace(' ', '-')}-jobs-in-{location.lower()}"
            )
            driver.get(search_url)

            time.sleep(self.scheduler.get_page_view_delay("naukri"))
            self.human_scroll(driver, "down", random.randint(150, 350))

            # Wait for results
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".srp-tuple, .jobTuple"))
            )

            job_cards = driver.find_elements(By.CSS_SELECTOR, ".srp-tuple, .jobTuple")[:10]

            for card in job_cards:
                try:
                    self.human_scroll(driver, "down", random.randint(30, 100))
                    time.sleep(random.uniform(0.3, 1.0))

                    title_elem = card.find_element(By.CSS_SELECTOR, ".desig, .jobTitle a")
                    company_elem = card.find_element(By.CSS_SELECTOR, ".comp-name, .companyInfo a")
                    location_elem = card.find_element(By.CSS_SELECTOR, ".loc, .locWdth")

                    job_url = title_elem.get_attribute("href") or ""
                    if job_url and job_url not in self._applied_urls:
                        jobs.append(JobListing(
                            title=title_elem.text.strip(),
                            company=company_elem.text.strip(),
                            location=location_elem.text.strip(),
                            url=job_url,
                            platform="naukri",
                        ))
                except (NoSuchElementException, StaleElementReferenceException):
                    continue

            logger.info("Found %d Naukri jobs for '%s'", len(jobs), keyword)

        except Exception as e:
            logger.error("Naukri search failed: %s", e)
            log_event("naukri_search", "error", str(e))

        return jobs

    def apply_linkedin_easy_apply(self, job: JobListing) -> bool:
        """Apply to a LinkedIn Easy Apply job."""
        driver = self._get_driver("linkedin")

        try:
            driver.get(job.url)
            time.sleep(self.scheduler.get_page_view_delay("linkedin"))

            # Scroll to read job description (human behavior)
            self.human_scroll(driver, "down", random.randint(300, 600))
            time.sleep(random.uniform(2, 5))  # "Reading" the description
            self.random_mouse_movement(driver)

            # Find and click Easy Apply button
            easy_apply_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".jobs-apply-button, button[aria-label*='Easy Apply']"))
            )

            time.sleep(random.uniform(0.5, 1.5))
            easy_apply_btn.click()

            # Handle Easy Apply modal
            time.sleep(random.uniform(1, 2))

            # Try to submit (may have multiple steps)
            max_steps = 5
            for step in range(max_steps):
                time.sleep(random.uniform(1, 2))

                # Look for submit button
                try:
                    submit_btn = driver.find_element(
                        By.CSS_SELECTOR,
                        "button[aria-label*='Submit'], button[aria-label*='Review']"
                    )
                    submit_btn.click()

                    # Check if we're done
                    time.sleep(1)
                    if "application was sent" in driver.page_source.lower():
                        break
                except NoSuchElementException:
                    # Try next button
                    try:
                        next_btn = driver.find_element(
                            By.CSS_SELECTOR,
                            "button[aria-label*='Continue'], button[aria-label*='Next']"
                        )
                        next_btn.click()
                    except NoSuchElementException:
                        break

            # Verify success
            time.sleep(2)
            if "application was sent" in driver.page_source.lower() or "applied" in driver.page_source.lower():
                self._applied_urls.add(job.url)
                save_application(
                    job_title=job.title,
                    company=job.company,
                    platform="linkedin",
                    job_url=job.url,
                    status="applied",
                    match_score=None,
                    cover_letter=None,
                    resume_path=None,
                )
                log_event("apply_linkedin", "success", f"{job.title} at {job.company}")
                slack_notifier.notify_application_status(
                    job_title=job.title,
                    company=job.company,
                    platform="LinkedIn",
                    status="applied",
                    job_url=job.url,
                )
                return True

            log_event("apply_linkedin", "incomplete", f"Could not verify: {job.title}")
            return False

        except Exception as e:
            logger.error("LinkedIn apply failed for %s: %s", job.url, e)
            log_event("apply_linkedin", "error", str(e))
            slack_notifier.notify_error(str(e), platform="LinkedIn")
            return False
        """Apply to a Naukri Gulf job."""
        driver = self._get_driver("naukri")

        try:
            driver.get(job.url)
            time.sleep(self.scheduler.get_page_view_delay("naukri"))

            # Human-like job reading
            self.human_scroll(driver, "down", random.randint(250, 500))
            time.sleep(random.uniform(3, 7))
            self.random_mouse_movement(driver)

            # Find apply button
            apply_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((
                    By.CSS_SELECTOR,
                    "#applyButton, .apply-button, button[id*='apply'], .applybtn"
                ))
            )

            time.sleep(random.uniform(0.5, 1.5))
            driver.execute_script("arguments[0].click();", apply_btn)

            time.sleep(random.uniform(2, 4))

            # Check for success
            page_source = driver.page_source.lower()
            if "applied successfully" in page_source or "application submitted" in page_source:
                self._applied_urls.add(job.url)
                save_application(
                    job_title=job.title,
                    company=job.company,
                    platform="naukri",
                    job_url=job.url,
                    status="applied",
                    match_score=None,
                    cover_letter=None,
                    resume_path=None,
                )
                log_event("apply_naukri", "success", f"{job.title} at {job.company}")
                slack_notifier.notify_application_status(
                    job_title=job.title,
                    company=job.company,
                    platform="Naukri Gulf",
                    status="applied",
                    job_url=job.url,
                )
                return True

            log_event("apply_naukri", "incomplete", f"Could not verify: {job.title}")
            return False

        except Exception as e:
            logger.error("Naukri apply failed for %s: %s", job.url, e)
            log_event("apply_naukri", "error", str(e))
            slack_notifier.notify_error(str(e), platform="Naukri Gulf")
            return False

    def run_daily_session(self) -> dict:
        """
        Run a full day of job searching and applications.
        Spreads activity throughout the day with human-like patterns.
        """
        logger.info("Starting daily auto-apply session")
        self.scheduler.reset_daily_counters()

        stats = {
            "started_at": datetime.now().isoformat(),
            "linkedin_applied": 0,
            "naukri_applied": 0,
            "jobs_found": 0,
            "errors": 0,
        }

        # Randomize keyword order for each day
        keywords = self.search_keywords.copy()
        random.shuffle(keywords)

        # Alternate between platforms
        platforms = ["linkedin", "naukri"]
        platform_idx = 0

        for keyword in keywords:
            # Check if we should continue
            state = self.scheduler.get_current_state()
            if state.value == "sleeping":
                wait_until = self.scheduler.get_next_active_window()
                wait_seconds = (wait_until - datetime.now()).total_seconds()
                if wait_seconds > 0:
                    logger.info("Waiting until %s to resume", wait_until)
                    time.sleep(min(wait_seconds, 3600))  # Max 1 hour sleep at a time
                    continue

            platform = platforms[platform_idx % 2]
            platform_idx += 1

            can_apply, reason = self.scheduler.can_apply_now(platform)
            if not can_apply:
                logger.info("Skipping %s: %s", platform, reason)
                continue

            # Search for jobs
            if platform == "linkedin":
                jobs = self.search_linkedin_jobs(keyword, self.target_locations[0])
            else:
                jobs = self.search_naukri_jobs(keyword, self.target_locations[0])

            stats["jobs_found"] += len(jobs)

            # Apply to found jobs
            for job in jobs:
                can_apply, reason = self.scheduler.can_apply_now(platform)
                if not can_apply:
                    logger.info("Stopping applications: %s", reason)
                    break

                # Wait before applying (human-like delay)
                delay = self.scheduler.get_delay_before_action(platform)
                logger.info("Waiting %ds before applying to %s", delay, job.title[:40])
                time.sleep(delay)

                # Apply
                if platform == "linkedin":
                    success = self.apply_linkedin_easy_apply(job)
                    if success:
                        stats["linkedin_applied"] += 1
                else:
                    success = self.apply_naukri_job(job)
                    if success:
                        stats["naukri_applied"] += 1

                if not success:
                    stats["errors"] += 1

                self.scheduler.record_application(platform, success)

                # Check if break needed
                should_break, break_duration = self.scheduler.should_take_break()
                if should_break:
                    self.scheduler.take_break(break_duration)

        stats["ended_at"] = datetime.now().isoformat()
        stats["scheduler_status"] = self.scheduler.get_status_summary()

        total_applied = stats["linkedin_applied"] + stats["naukri_applied"]
        slack_notifier.notify_run_summary(
            platform="LinkedIn + Naukri Gulf",
            attempted=stats["jobs_found"],
            successful=total_applied,
            failed=stats["errors"],
        )

        logger.info("Daily session complete: %s", stats)
        return stats

    def cleanup(self) -> None:
        """Clean up browser drivers."""
        for platform, driver in self.drivers.items():
            try:
                driver.quit()
                logger.info("Closed %s driver", platform)
            except Exception:
                pass
        self.drivers.clear()


def run_auto_apply(
    headless: bool = True,
    linkedin_daily_limit: int = 15,
    naukri_daily_limit: int = 25,
) -> dict:
    """
    Convenience function to run auto-apply with custom limits.

    Args:
        headless: Run browsers in headless mode
        linkedin_daily_limit: Max LinkedIn applications per day
        naukri_daily_limit: Max Naukri applications per day

    Returns:
        Session statistics dict
    """
    limits = RateLimits(
        linkedin_jobs_per_day=linkedin_daily_limit,
        naukri_jobs_per_day=naukri_daily_limit,
    )

    runner = AutoApplyRunner(rate_limits=limits, headless=headless)

    try:
        return runner.run_daily_session()
    finally:
        runner.cleanup()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    result = run_auto_apply(headless=False)  # Visible for testing
    print(f"\nSession Results:\n{result}")
