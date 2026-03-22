"""Naukri Gulf Job Search & Auto-Apply Runner"""
from __future__ import annotations

import logging
import time
from datetime import datetime

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from job_agent.automation import authenticate_naukri_gulf_with_config
from job_agent.config import JOB_SEARCH_PREFERENCES
from job_agent.database import save_application
from job_agent.slack_notifier import notify_application_status, notify_run_summary

logger = logging.getLogger(__name__)


def run_naukri_job_search(max_applications: int = 5, headless: bool = True) -> dict:
    """
    Run automated job search and application on Naukri Gulf.

    Args:
        max_applications: Maximum number of applications to submit in this run
        headless: Whether to run browser in headless mode

    Returns:
        Dictionary with summary of run results
    """
    results = {
        "start_time": datetime.now().isoformat(),
        "applications_attempted": 0,
        "applications_successful": 0,
        "applications_failed": 0,
        "errors": [],
        "jobs_found": [],
    }

    driver = None
    try:
        # Step 1: Authenticate to Naukri Gulf
        logger.info("Authenticating to Naukri Gulf...")
        driver = authenticate_naukri_gulf_with_config(headless=headless)
        logger.info("Authentication successful!")

        # Step 2: Get search keywords from config
        search_keywords = JOB_SEARCH_PREFERENCES.get("search_keywords", [])
        target_locations = JOB_SEARCH_PREFERENCES.get("target_locations", ["Dubai"])

        if not search_keywords:
            search_keywords = ["accounts receivable", "credit control"]

        # Step 3: For each keyword, run a search
        for keyword in search_keywords[:3]:
            logger.info("Searching for: %s", keyword)

            location = target_locations[0].lower().replace(" ", "-")
            search_keyword_url = keyword.lower().replace(" ", "-")
            search_url = f"https://www.naukrigulf.com/{search_keyword_url}-jobs-in-{location}"

            logger.info("Navigating to: %s", search_url)
            driver.get(search_url)
            time.sleep(3)

            # Step 4: Extract job listings from the page
            try:
                job_cards = driver.find_elements(By.CSS_SELECTOR, ".list, .job-tuple, article.jobTuple")
                logger.info("Found %d job listings", len(job_cards))

                for job_card in job_cards[:max_applications]:
                    if results["applications_attempted"] >= max_applications:
                        break

                    try:
                        job_title_elem = job_card.find_element(By.CSS_SELECTOR, "a.title, .jobTitle a, h3 a")
                        job_title = job_title_elem.text.strip()
                        job_url = job_title_elem.get_attribute("href")

                        company_elem = job_card.find_element(By.CSS_SELECTOR, ".comp-name, .company a, .companyInfo a")
                        company = company_elem.text.strip()

                        logger.info("Found job: %s at %s", job_title, company)

                        results["jobs_found"].append({
                            "job_title": job_title,
                            "company": company,
                            "url": job_url,
                        })

                        # Step 5: Click on job to view details
                        job_title_elem.click()
                        time.sleep(2)

                        if len(driver.window_handles) > 1:
                            driver.switch_to.window(driver.window_handles[-1])

                        # Step 6: Look for "Apply" button
                        apply_button = None
                        try:
                            apply_button = WebDriverWait(driver, 10).until(
                                EC.presence_of_element_located((By.XPATH, "//button[contains(text(), 'Apply')]"))
                            )
                        except Exception:
                            try:
                                apply_button = driver.find_element(By.CSS_SELECTOR, "#apply-button, button.apply")
                            except Exception:
                                pass

                        if apply_button:
                            logger.info("Applying to: %s", job_title)
                            results["applications_attempted"] += 1

                            try:
                                apply_button.click()
                                time.sleep(2)

                                save_application(
                                    job_title=job_title,
                                    company=company,
                                    platform="Naukri Gulf",
                                    job_url=job_url,
                                    status="applied",
                                    match_score=None,
                                    cover_letter=None,
                                    resume_path=None,
                                    screenshot_path=None,
                                )
                                results["applications_successful"] += 1
                                logger.info("Successfully applied to: %s", job_title)
                                notify_application_status(
                                    job_title, company, "Naukri Gulf", "applied", job_url
                                )
                            except Exception as apply_error:
                                results["applications_failed"] += 1
                                results["errors"].append(f"Apply failed for {job_title}: {str(apply_error)}")
                                logger.error("Apply failed for %s: %s", job_title, apply_error)
                                notify_application_status(
                                    job_title, company, "Naukri Gulf", "failed", job_url
                                )
                        else:
                            logger.info("No apply button found for: %s", job_title)

                        # Close tab and return to main
                        if len(driver.window_handles) > 1:
                            driver.close()
                            driver.switch_to.window(driver.window_handles[0])
                        else:
                            driver.back()

                        time.sleep(1)

                    except Exception as job_error:
                        results["errors"].append(f"Error processing job: {str(job_error)}")
                        logger.error("Error processing job: %s", job_error)
                        continue

            except Exception as search_error:
                results["errors"].append(f"Search failed for {keyword}: {str(search_error)}")
                logger.error("Search error for %s: %s", keyword, search_error)

        logger.info("Run complete")

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
        notify_run_summary(
            platform="Naukri Gulf",
            attempted=results["applications_attempted"],
            successful=results["applications_successful"],
            failed=results["applications_failed"],
            errors=results["errors"] or None,
        )

    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    print("Starting Naukri Gulf job search runner...")
    result = run_naukri_job_search(max_applications=3, headless=False)
    print(f"\n=== RUN SUMMARY ===")
    print(f"Applications attempted: {result['applications_attempted']}")
    print(f"Applications successful: {result['applications_successful']}")
    print(f"Applications failed: {result['applications_failed']}")
    print(f"Jobs found: {len(result['jobs_found'])}")
    if result["errors"]:
        print(f"Errors: {result['errors']}")
