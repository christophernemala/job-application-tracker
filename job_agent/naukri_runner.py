"""Naukri Gulf Job Search & Auto-Apply Runner"""
from __future__ import annotations

import time
from datetime import datetime

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from job_agent.automation import authenticate_naukri_gulf_with_config, try_apply_and_verify
from job_agent.config import JOB_SEARCH_PREFERENCES
from job_agent.database import save_application

# ──────────────────────────────────────────────────────────────────────────────
# CSS selector sets — multiple fallbacks so one wrong guess doesn't kill the run
# ──────────────────────────────────────────────────────────────────────────────

# Job card container selectors (most specific first)
JOB_CARD_SELECTORS = [
    "article.jobTuple",
    "li.jobTuple",
    ".job-tuple",
    ".srp-jobtuple-wrapper",
    "li.ng-star-inserted",
    ".list",
]

# Job title link selectors within a card
JOB_TITLE_SELECTORS = [
    "a.jt-title",
    "a.title",
    ".jobTitle a",
    "h3 a",
    "a[title]",
]

# Company name selectors within a card
COMPANY_SELECTORS = [
    ".jt-company-name",
    ".comp-name a",
    ".comp-name",
    ".company a",
    ".companyInfo a",
    "[data-company]",
]

# Apply button selectors on the job detail page
APPLY_BTN_SELECTORS = [
    (By.ID, "apply-button"),
    (By.CSS_SELECTOR, "button.apply-button"),
    (By.CSS_SELECTOR, "a.apply-button"),
    (By.CSS_SELECTOR, "#applyButton"),
    (By.CSS_SELECTOR, "button[data-ga-track*='apply']"),
    (By.XPATH, "//button[normalize-space()='Apply']"),
    (By.XPATH, "//button[normalize-space()='Apply Now']"),
    (By.XPATH, "//a[normalize-space()='Apply']"),
    (By.XPATH, "//a[normalize-space()='Apply Now']"),
]


def _find_first(driver, selectors: list[str]):
    """Return first matching element from a list of CSS selector strings, or None."""
    for sel in selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, sel)
            if elements:
                return elements
        except Exception:
            continue
    return []


def _find_text(element, selectors: list[str]) -> str:
    """Try multiple selectors on an element and return the first non-empty text."""
    for sel in selectors:
        try:
            el = element.find_element(By.CSS_SELECTOR, sel)
            text = el.text.strip()
            if text:
                return text, el
        except Exception:
            continue
    return "", None


def _find_apply_button(driver):
    """Try each apply-button selector and return the first clickable element."""
    for locator in APPLY_BTN_SELECTORS:
        try:
            btn = WebDriverWait(driver, 6).until(EC.element_to_be_clickable(locator))
            return btn, locator
        except Exception:
            continue
    return None, None


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
        print("[NAUKRI RUNNER] Authenticating to Naukri Gulf...")
        driver = authenticate_naukri_gulf_with_config(headless=headless)
        print("[NAUKRI RUNNER] Authentication successful!")

        # Step 2: Get search keywords from config
        search_keywords = JOB_SEARCH_PREFERENCES.get("search_keywords", [])
        target_locations = JOB_SEARCH_PREFERENCES.get("target_locations", ["Dubai"])

        if not search_keywords:
            search_keywords = ["accounts receivable", "credit control"]

        # Step 3: For each keyword, run a search
        for keyword in search_keywords[:3]:  # Limit to first 3 keywords
            if results["applications_attempted"] >= max_applications:
                break

            print(f"[NAUKRI RUNNER] Searching for: {keyword}")

            # Build search URL for Naukri Gulf
            location = target_locations[0].lower().replace(" ", "-")
            search_keyword_url = keyword.lower().replace(" ", "-")
            search_url = f"https://www.naukrigulf.com/{search_keyword_url}-jobs-in-{location}"

            print(f"[NAUKRI RUNNER] Navigating to: {search_url}")
            driver.get(search_url)
            time.sleep(3)

            # Step 4: Extract job listings using multiple selector fallbacks
            try:
                job_cards = _find_first(driver, JOB_CARD_SELECTORS)
                print(f"[NAUKRI RUNNER] Found {len(job_cards)} job listings")

                for job_card in job_cards:
                    if results["applications_attempted"] >= max_applications:
                        break

                    try:
                        # Extract job title + URL
                        job_title, title_elem = _find_text(job_card, JOB_TITLE_SELECTORS)
                        if not job_title or not title_elem:
                            print("[NAUKRI RUNNER] Skipping card: no title found")
                            continue

                        job_url = title_elem.get_attribute("href") or ""

                        # Extract company name
                        company, _ = _find_text(job_card, COMPANY_SELECTORS)
                        if not company:
                            company = "Unknown"

                        print(f"[NAUKRI RUNNER] Found job: {job_title} at {company}")
                        results["jobs_found"].append({
                            "job_title": job_title,
                            "company": company,
                            "url": job_url,
                        })

                        # Step 5: Open job detail page
                        if job_url:
                            driver.get(job_url)
                        else:
                            title_elem.click()
                        time.sleep(2)

                        # Switch to new tab if opened
                        if len(driver.window_handles) > 1:
                            driver.switch_to.window(driver.window_handles[-1])

                        # Step 6: Find Apply button using multiple locators
                        apply_btn, locator = _find_apply_button(driver)

                        if apply_btn and locator:
                            results["applications_attempted"] += 1
                            print(f"[NAUKRI RUNNER] Applying to: {job_title} at {company}")

                            # Step 7: Use try_apply_and_verify for real verification
                            result = try_apply_and_verify(
                                driver=driver,
                                apply_button_locator=locator,
                                job_title=job_title,
                                company=company,
                            )

                            status = "applied" if result.success else "failed"
                            save_application(
                                job_title=job_title,
                                company=company,
                                platform="Naukri Gulf",
                                job_url=job_url,
                                status=status,
                                match_score=None,
                                cover_letter=None,
                                resume_path=None,
                                screenshot_path=None,
                            )

                            if result.success:
                                results["applications_successful"] += 1
                                print(f"[NAUKRI RUNNER] SUCCESS: {result.message}")
                            else:
                                results["applications_failed"] += 1
                                results["errors"].append(result.message)
                                print(f"[NAUKRI RUNNER] FAILED: {result.message}")
                        else:
                            print(f"[NAUKRI RUNNER] No apply button found for: {job_title}")

                        # Close extra tab and return to search results
                        if len(driver.window_handles) > 1:
                            driver.close()
                            driver.switch_to.window(driver.window_handles[0])
                        else:
                            driver.back()
                            time.sleep(2)

                    except Exception as job_error:
                        results["errors"].append(f"Error processing job: {job_error}")
                        print(f"[NAUKRI RUNNER] Error processing job: {job_error}")
                        continue

            except Exception as search_error:
                results["errors"].append(f"Search failed for '{keyword}': {search_error}")
                print(f"[NAUKRI RUNNER] Search error: {search_error}")

        print("[NAUKRI RUNNER] Run complete")

    except Exception as e:
        results["errors"].append(f"Fatal error: {e}")
        print(f"[NAUKRI RUNNER] Fatal error: {e}")

    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
        results["end_time"] = datetime.now().isoformat()

    return results


if __name__ == "__main__":
    print("Starting Naukri Gulf job search runner...")
    result = run_naukri_job_search(max_applications=3, headless=False)
    print("\n=== RUN SUMMARY ===")
    print(f"Applications attempted:  {result['applications_attempted']}")
    print(f"Applications successful: {result['applications_successful']}")
    print(f"Applications failed:     {result['applications_failed']}")
    print(f"Jobs found:              {len(result['jobs_found'])}")
    if result["errors"]:
        print(f"Errors: {result['errors']}")
