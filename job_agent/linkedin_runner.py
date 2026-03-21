"""LinkedIn Job Search & Auto-Apply Runner (Easy Apply only)."""
from __future__ import annotations

import logging
import time
from datetime import datetime

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from job_agent.automation import authenticate_linkedin_with_config
from job_agent.config import JOB_SEARCH_PREFERENCES
from job_agent.database import save_application

logger = logging.getLogger(__name__)


def _build_linkedin_search_url(keyword: str, location: str = "Dubai") -> str:
    """Build a LinkedIn job search URL with Easy Apply filter."""
    from urllib.parse import quote_plus
    return (
        f"https://www.linkedin.com/jobs/search/"
        f"?keywords={quote_plus(keyword)}"
        f"&location={quote_plus(location)}"
        f"&f_AL=true"  # Easy Apply filter
    )


def _try_easy_apply(driver, job_title: str, company: str) -> tuple[bool, str]:
    """Attempt LinkedIn Easy Apply on the current job page."""
    try:
        # Look for Easy Apply button
        apply_btn = None
        for selector in [
            "button.jobs-apply-button",
            "button[aria-label*='Easy Apply']",
            "button.jobs-apply-button--top-card",
        ]:
            try:
                apply_btn = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                )
                break
            except Exception:
                continue

        if not apply_btn:
            return False, "No Easy Apply button found"

        apply_btn.click()
        time.sleep(2)

        # Walk through the Easy Apply modal (up to 5 steps)
        for step in range(5):
            # Check if application was submitted
            try:
                driver.find_element(By.CSS_SELECTOR, "[data-test-modal-close-btn]")
                # Check for success indicators
                page_text = driver.page_source.lower()
                if "application sent" in page_text or "applied" in page_text:
                    return True, "Easy Apply completed successfully"
            except Exception:
                pass

            # Check for success icon
            try:
                driver.find_element(By.CSS_SELECTOR, "svg[data-test-icon='success']")
                return True, "Easy Apply completed successfully"
            except Exception:
                pass

            # Look for Submit button
            try:
                submit_btn = driver.find_element(
                    By.CSS_SELECTOR, "button[aria-label='Submit application']"
                )
                if submit_btn.is_displayed():
                    submit_btn.click()
                    time.sleep(3)
                    return True, "Application submitted via Easy Apply"
            except Exception:
                pass

            # Look for Next button
            try:
                next_btn = driver.find_element(
                    By.CSS_SELECTOR, "button[aria-label='Continue to next step']"
                )
                if next_btn.is_displayed():
                    next_btn.click()
                    time.sleep(2)
                    continue
            except Exception:
                pass

            # Look for Review button
            try:
                review_btn = driver.find_element(
                    By.CSS_SELECTOR, "button[aria-label='Review your application']"
                )
                if review_btn.is_displayed():
                    review_btn.click()
                    time.sleep(2)
                    continue
            except Exception:
                pass

            # If we find a form with required fields we can't fill, bail out
            try:
                required_fields = driver.find_elements(
                    By.CSS_SELECTOR, "input[required]:not([value]), textarea[required]"
                )
                empty_required = [f for f in required_fields if not f.get_attribute("value")]
                if empty_required:
                    # Close the modal
                    try:
                        dismiss_btn = driver.find_element(By.CSS_SELECTOR, "[data-test-modal-close-btn], button[aria-label='Dismiss']")
                        dismiss_btn.click()
                        time.sleep(1)
                        # Confirm discard if prompted
                        try:
                            discard_btn = driver.find_element(By.CSS_SELECTOR, "button[data-test-dialog-primary-btn]")
                            discard_btn.click()
                        except Exception:
                            pass
                    except Exception:
                        pass
                    return False, f"Required fields need manual input (step {step + 1})"
            except Exception:
                pass

            time.sleep(1)

        return False, "Easy Apply flow did not complete within 5 steps"

    except Exception as exc:
        # Try to close any open modal
        try:
            driver.find_element(By.CSS_SELECTOR, "[data-test-modal-close-btn]").click()
            time.sleep(1)
            try:
                driver.find_element(By.CSS_SELECTOR, "button[data-test-dialog-primary-btn]").click()
            except Exception:
                pass
        except Exception:
            pass
        return False, f"Easy Apply error: {exc}"


def run_linkedin_job_search(max_applications: int = 5, headless: bool = True) -> dict:
    """
    Run automated job search and Easy Apply on LinkedIn.

    Args:
        max_applications: Maximum number of applications to submit
        headless: Whether to run browser in headless mode

    Returns:
        Dictionary with summary of run results
    """
    results = {
        "start_time": datetime.now().isoformat(),
        "platform": "LinkedIn",
        "applications_attempted": 0,
        "applications_successful": 0,
        "applications_failed": 0,
        "applications_skipped": 0,
        "errors": [],
        "jobs_found": [],
    }

    driver = None
    try:
        logger.info("Authenticating to LinkedIn...")
        driver = authenticate_linkedin_with_config(headless=headless)
        logger.info("LinkedIn authentication successful!")

        search_keywords = JOB_SEARCH_PREFERENCES.get("search_keywords", [])
        target_locations = JOB_SEARCH_PREFERENCES.get("target_locations", ["Dubai"])
        location = target_locations[0] if target_locations else "Dubai"

        if not search_keywords:
            search_keywords = ["accounts receivable", "credit control"]

        for keyword in search_keywords[:3]:
            if results["applications_successful"] >= max_applications:
                break

            search_url = _build_linkedin_search_url(keyword, location)
            logger.info("Searching LinkedIn for: %s", keyword)
            driver.get(search_url)
            time.sleep(4)

            # Scroll to load more results
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 2)")
            time.sleep(2)

            # Find job cards
            job_cards = driver.find_elements(
                By.CSS_SELECTOR,
                ".job-card-container, .jobs-search-results__list-item, .scaffold-layout__list-item"
            )
            logger.info("Found %d job cards for '%s'", len(job_cards), keyword)

            for card in job_cards:
                if results["applications_successful"] >= max_applications:
                    break

                try:
                    # Click on the job card to load details
                    card.click()
                    time.sleep(2)

                    # Extract job info from the detail panel
                    job_title = "Unknown"
                    company = "Unknown"
                    job_url = driver.current_url

                    try:
                        title_elem = driver.find_element(
                            By.CSS_SELECTOR,
                            ".job-details-jobs-unified-top-card__job-title, .jobs-unified-top-card__job-title, h1.t-24"
                        )
                        job_title = title_elem.text.strip()
                    except Exception:
                        try:
                            job_title = card.find_element(By.CSS_SELECTOR, ".job-card-list__title, strong").text.strip()
                        except Exception:
                            pass

                    try:
                        company_elem = driver.find_element(
                            By.CSS_SELECTOR,
                            ".job-details-jobs-unified-top-card__company-name, .jobs-unified-top-card__company-name"
                        )
                        company = company_elem.text.strip()
                    except Exception:
                        try:
                            company = card.find_element(By.CSS_SELECTOR, ".job-card-container__primary-description, .artdeco-entity-lockup__subtitle").text.strip()
                        except Exception:
                            pass

                    if not job_title or job_title == "Unknown":
                        continue

                    logger.info("Found: %s at %s", job_title, company)
                    results["jobs_found"].append({
                        "job_title": job_title,
                        "company": company,
                        "url": job_url,
                    })

                    # Attempt Easy Apply
                    results["applications_attempted"] += 1
                    success, message = _try_easy_apply(driver, job_title, company)

                    if success:
                        save_application(
                            job_title=job_title,
                            company=company,
                            platform="LinkedIn",
                            job_url=job_url,
                            status="applied",
                            match_score=None,
                            cover_letter=None,
                            resume_path=None,
                            screenshot_path=None,
                        )
                        results["applications_successful"] += 1
                        logger.info("Applied to: %s at %s", job_title, company)
                    else:
                        results["applications_skipped"] += 1
                        logger.info("Skipped %s: %s", job_title, message)

                    time.sleep(1)

                except Exception as job_error:
                    results["errors"].append(f"Error processing job: {str(job_error)}")
                    logger.error("Error processing job: %s", job_error)
                    continue

        logger.info("LinkedIn run complete")

    except Exception as e:
        results["errors"].append(f"Fatal error: {str(e)}")
        logger.error("Fatal error: %s", e)

    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
        results["end_time"] = datetime.now().isoformat()

    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    print("Starting LinkedIn job search runner...")
    result = run_linkedin_job_search(max_applications=3, headless=False)
    print(f"\n=== LINKEDIN RUN SUMMARY ===")
    print(f"Jobs found: {len(result['jobs_found'])}")
    print(f"Applications attempted: {result['applications_attempted']}")
    print(f"Applications successful: {result['applications_successful']}")
    print(f"Skipped (manual needed): {result['applications_skipped']}")
    if result["errors"]:
        print(f"Errors: {result['errors']}")
