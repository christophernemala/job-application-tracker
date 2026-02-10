"""Browser automation flows for external job platforms."""

from __future__ import annotations

import pickle
import time
from dataclasses import dataclass
from pathlib import Path

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from job_agent.config import get_naukri_gulf_credentials

SESSION_FILE = Path(__file__).resolve().parent / "naukri_session.pkl"


@dataclass
class AuthResult:
    success: bool
    message: str


def setup_selenium_driver(headless: bool = True) -> webdriver.Chrome:
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1440,1080")
    return webdriver.Chrome(options=options)


def authenticate_naukri_gulf(email: str, password: str, headless: bool = True) -> webdriver.Chrome:
    """Login to Naukri Gulf and persist session cookies."""
    driver = setup_selenium_driver(headless=headless)
    driver.get("https://www.naukrigulf.com/nlogin/login")

    try:
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "usernameField")))
        driver.find_element(By.ID, "usernameField").send_keys(email)
        driver.find_element(By.ID, "passwordField").send_keys(password)
        driver.find_element(By.XPATH, "//button[@type='submit']").click()

        WebDriverWait(driver, 20).until(EC.url_contains("/mnj/userProfile"))
        with SESSION_FILE.open("wb") as handle:
            pickle.dump(driver.get_cookies(), handle)
        return driver
    except TimeoutException as exc:
        driver.save_screenshot(str(Path(__file__).resolve().parent / "auth_failure.png"))
        driver.quit()
        raise RuntimeError("Naukri Gulf authentication failed or timed out") from exc




def authenticate_naukri_gulf_with_config(headless: bool = True) -> webdriver.Chrome:
    """Authenticate using configured Naukri Gulf credentials from config.py."""
    email, password = get_naukri_gulf_credentials()
    return authenticate_naukri_gulf(email=email, password=password, headless=headless)

def verify_application_submitted(driver: webdriver.Chrome, job_title: str, company: str) -> bool:
    """Verify job title/company appears in applied-jobs page after submit."""
    driver.get("https://www.naukrigulf.com/my-naukri/applied-jobs")
    time.sleep(3)
    page_source = driver.page_source.lower()

    return job_title.lower() in page_source or company.lower() in page_source


def try_apply_and_verify(driver: webdriver.Chrome, apply_button_locator: tuple[str, str], job_title: str, company: str) -> AuthResult:
    """Click apply and validate success to avoid silent failures."""
    try:
        WebDriverWait(driver, 15).until(EC.element_to_be_clickable(apply_button_locator)).click()
        time.sleep(2)
        verified = verify_application_submitted(driver, job_title, company)
        if verified:
            return AuthResult(True, f"Verified application for {job_title} at {company}")
        driver.save_screenshot(str(Path(__file__).resolve().parent / "apply_not_verified.png"))
        return AuthResult(False, f"Apply flow completed but verification failed for {job_title} at {company}")
    except Exception as exc:  # noqa: BLE001
        driver.save_screenshot(str(Path(__file__).resolve().parent / "apply_error.png"))
        return AuthResult(False, f"Apply flow failed: {exc}")
