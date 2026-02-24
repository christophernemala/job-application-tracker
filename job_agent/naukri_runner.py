"""Naukri Gulf Job Search & Auto-Apply Runner"""
from __future__ import annotations

import time
from datetime import datetime

from job_agent.automation import authenticate_naukri_gulf_with_config
from job_agent.config import JOB_SEARCH_PREFERENCES
from job_agent.database import save_application


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
        for keyword in search_keywords[:3]:  # Limit to first 3 keywords for now
            print(f"[NAUKRI RUNNER] Searching for: {keyword}")
            
            # Build search URL for Naukri Gulf
            # Example: https://www.naukrigulf.com/accounts-receivable-jobs-in-dubai
            location = target_locations[0].lower().replace(" ", "-")
            search_keyword_url = keyword.lower().replace(" ", "-")
            search_url = f"https://www.naukrigulf.com/{search_keyword_url}-jobs-in-{location}"
            
            print(f"[NAUKRI RUNNER] Navigating to: {search_url}")
            driver.get(search_url)
            time.sleep(3)
            
            # Step 4: Extract job listings from the page
            try:
                # Naukri Gulf uses job cards with class 'list' or 'job-tuple'
                from selenium.webdriver.common.by import By
                job_cards = driver.find_elements(By.CSS_SELECTOR, ".list, .job-tuple, article.jobTuple")
                
                print(f"[NAUKRI RUNNER] Found {len(job_cards)} job listings")
                
                for job_card in job_cards[:max_applications]:
                    if results["applications_attempted"] >= max_applications:
                        break
                    
                    try:
                        # Extract job details
                        job_title_elem = job_card.find_element(By.CSS_SELECTOR, "a.title, .jobTitle a, h3 a")
                        job_title = job_title_elem.text.strip()
                        job_url = job_title_elem.get_attribute("href")
                        
                        company_elem = job_card.find_element(By.CSS_SELECTOR, ".comp-name, .company a, .companyInfo a")
                        company = company_elem.text.strip()
                        
                        print(f"[NAUKRI RUNNER] Found job: {job_title} at {company}")
                        
                        results["jobs_found"].append({
                            "job_title": job_title,
                            "company": company,
                            "url": job_url,
                        })
                        
                        # Step 5: Click on job to view details
                        job_title_elem.click()
                        time.sleep(2)
                        
                        # Switch to new tab if opened
                        if len(driver.window_handles) > 1:
                            driver.switch_to.window(driver.window_handles[-1])
                        
                        # Step 6: Look for "Apply" button
                        from selenium.webdriver.support.ui import WebDriverWait
                        from selenium.webdriver.support import expected_conditions as EC
                        
                        apply_button = None
                        try:
                            apply_button = WebDriverWait(driver, 10).until(
                                EC.presence_of_element_located((By.XPATH, "//button[contains(text(), 'Apply')]"))
                            )
                        except:
                            try:
                                apply_button = driver.find_element(By.CSS_SELECTOR, "#apply-button, button.apply")
                            except:
                                pass
                        
                        if apply_button:
                            print(f"[NAUKRI RUNNER] Applying to: {job_title}")
                            results["applications_attempted"] += 1
                            
                            try:
                                apply_button.click()
                                time.sleep(2)
                                
                                # Save to database
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
                                print(f"[NAUKRI RUNNER] Successfully applied to: {job_title}")
                            except Exception as apply_error:
                                results["applications_failed"] += 1
                                results["errors"].append(f"Apply failed for {job_title}: {str(apply_error)}")
                                print(f"[NAUKRI RUNNER] Apply failed: {apply_error}")
                        else:
                            print(f"[NAUKRI RUNNER] No apply button found for: {job_title}")
                        
                        # Close tab and return to main
                        if len(driver.window_handles) > 1:
                            driver.close()
                            driver.switch_to.window(driver.window_handles[0])
                        else:
                            driver.back()
                        
                        time.sleep(1)
                    
                    except Exception as job_error:
                        results["errors"].append(f"Error processing job: {str(job_error)}")
                        print(f"[NAUKRI RUNNER] Error processing job: {job_error}")
                        continue
            
            except Exception as search_error:
                results["errors"].append(f"Search failed for {keyword}: {str(search_error)}")
                print(f"[NAUKRI RUNNER] Search error: {search_error}")
        
        driver.quit()
        print("[NAUKRI RUNNER] Run complete")
    
    except Exception as e:
        results["errors"].append(f"Fatal error: {str(e)}")
        print(f"[NAUKRI RUNNER] Fatal error: {e}")
    
    finally:
        results["end_time"] = datetime.now().isoformat()
    
    return results


if __name__ == "__main__":
    # Run locally for testing
    print("Starting Naukri Gulf job search runner...")
    result = run_naukri_job_search(max_applications=3, headless=False)
    print("\n=== RUN SUMMARY ===")
    print(f"Applications attempted: {result['applications_attempted']}")
    print(f"Applications successful: {result['applications_successful']}")
    print(f"Applications failed: {result['applications_failed']}")
    print(f"Jobs found: {len(result['jobs_found'])}")
    if result['errors']:
        print(f"Errors: {result['errors']}")
