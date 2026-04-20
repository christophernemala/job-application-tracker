"""Browser automation flows for external job platforms."""

from __future__ import annotations

import logging
import os
import pickle
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

try:
    from webdriver_manager.chrome import ChromeDriverManager
    WEBDRIVER_MANAGER_AVAILABLE = True
except ImportError:
    WEBDRIVER_MANAGER_AVAILABLE = False

from job_agent.config import get_linkedin_credentials, get_naukri_gulf_credentials

logger = logging.getLogger(__name__)

# Use temp directory for session/screenshots on ephemeral filesystems (Render)
_DATA_DIR = Path(tempfile.gettempdir()) / "job_agent"
_DATA_DIR.mkdir(parents=True, exist_ok=True)
SESSION_FILE = _DATA_DIR / "naukri_session.pkl"


@dataclass
class AuthResult:
    success: bool
    message: str


def setup_selenium_driver(headless: bool = True) -> webdriver.Chrome:
    """Set up Chrome driver with automatic ChromeDriver management."""
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1440,1080")

    # Fix for ERR_HTTP2_PROTOCOL_ERROR and bot detection
    options.add_argument("--disable-http2")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    )
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    # On Render/Linux, Chrome or Chromium is installed system-wide
    chrome_bin = os.environ.get("GOOGLE_CHROME_BIN")
    if chrome_bin and Path(chrome_bin).exists():
        options.binary_location = chrome_bin
    elif Path("/usr/bin/google-chrome-stable").exists():
        options.binary_location = "/usr/bin/google-chrome-stable"
    elif Path("/usr/bin/google-chrome").exists():
        options.binary_location = "/usr/bin/google-chrome"
    elif Path("/usr/bin/chromium-browser").exists():
        options.binary_location = "/usr/bin/chromium-browser"
    elif Path("/usr/bin/chromium").exists():
        options.binary_location = "/usr/bin/chromium"

    # Prefer system chromedriver (set via CHROMEDRIVER_PATH or standard location)
    chromedriver_path = os.environ.get("CHROMEDRIVER_PATH")
    if chromedriver_path and Path(chromedriver_path).exists():
        return webdriver.Chrome(service=Service(chromedriver_path), options=options)

    # Use webdriver-manager if available, otherwise use system ChromeDriver
    if WEBDRIVER_MANAGER_AVAILABLE:
        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=options)
    else:
        return webdriver.Chrome(options=options)


def authenticate_naukri_gulf(email: str, password: str, headless: bool = True) -> webdriver.Chrome:
    """Login to Naukri Gulf and persist session cookies."""
    driver = setup_selenium_driver(headless=headless)
    driver.get("https://www.naukrigulf.com/jobseeker/login")

    try:
        email_field = driver.find_element(By.ID, "loginPageLoginEmail")
        email_field.clear()
        email_field.send_keys(email)

        pass_field = driver.find_element(By.ID, "loginPassword")
        pass_field.clear()
        pass_field.send_keys(password)

        logger.info("Login fields filled for %s", email)

        # Try JavaScript click first
        button = driver.find_element(By.ID, "loginPageLoginSubmit")
        driver.execute_script("arguments[0].click();", button)

        # Fallback: Submit the form directly if no redirection after 3s
        time.sleep(3)
        if "/jobseeker/login" in driver.current_url:
            logger.info("No redirect yet, submitting form directly")
            driver.execute_script("document.getElementById('loginPageLoginForm').submit();")

        time.sleep(5)
        logger.info("Post-login URL: %s", driver.current_url)

        WebDriverWait(driver, 25).until(EC.url_contains("/mnj/userProfile"))
        with SESSION_FILE.open("wb") as handle:
            pickle.dump(driver.get_cookies(), handle)
        logger.info("Authentication successful, session saved")
        return driver
    except Exception as exc:
        logger.error("Authentication failed. URL: %s", driver.current_url)
        try:
            err_msg = driver.find_element(By.ID, "loginPageloginErr").text
            if err_msg:
                logger.error("On-page error: %s", err_msg)
        except Exception:
            pass

        screenshot_path = str(_DATA_DIR / "auth_failure.png")
        driver.save_screenshot(screenshot_path)
        logger.error("Auth failure screenshot saved to %s", screenshot_path)
        driver.quit()
        raise RuntimeError(f"Naukri Gulf authentication failed: {exc}") from exc


def authenticate_naukri_gulf_with_config(headless: bool = True) -> webdriver.Chrome:
    """Authenticate using configured Naukri Gulf credentials from config.py."""
    email, password = get_naukri_gulf_credentials()
    return authenticate_naukri_gulf(email=email, password=password, headless=headless)


def authenticate_linkedin(email: str, password: str, headless: bool = True) -> webdriver.Chrome:
    """Login to LinkedIn and return the authenticated driver."""
    driver = setup_selenium_driver(headless=headless)
    driver.get("https://www.linkedin.com/login")

    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "username"))
        )
        driver.find_element(By.ID, "username").send_keys(email)
        driver.find_element(By.ID, "password").send_keys(password)
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

        logger.info("LinkedIn login submitted for %s", email)

        # Wait for feed or security challenge
        time.sleep(5)
        current = driver.current_url

        if "/checkpoint" in current or "/challenge" in current:
            logger.warning("LinkedIn security challenge detected — manual verification may be needed")
            screenshot_path = str(_DATA_DIR / "linkedin_challenge.png")
            driver.save_screenshot(screenshot_path)
            driver.quit()
            raise RuntimeError("LinkedIn security challenge detected. Log in manually first to trust this device.")

        # Verify we're logged in
        if "/feed" in current or "/mynetwork" in current or "/in/" in current:
            logger.info("LinkedIn authentication successful")
            return driver

        # Try waiting for nav element
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".global-nav__primary-items, .feed-identity-module"))
        )
        logger.info("LinkedIn authentication successful")
        return driver

    except RuntimeError:
        raise
    except Exception as exc:
        screenshot_path = str(_DATA_DIR / "linkedin_auth_failure.png")
        driver.save_screenshot(screenshot_path)
        logger.error("LinkedIn auth failed: %s", exc)
        driver.quit()
        raise RuntimeError(f"LinkedIn authentication failed: {exc}") from exc


def authenticate_linkedin_with_config(headless: bool = True) -> webdriver.Chrome:
    """Authenticate using configured LinkedIn credentials from config.py."""
    email, password = get_linkedin_credentials()
    return authenticate_linkedin(email=email, password=password, headless=headless)


def verify_application_submitted(driver: webdriver.Chrome, job_title: str, company: str) -> bool:
    """Verify job title/company appears in applied-jobs page after submit."""
    driver.get("https://www.naukrigulf.com/my-naukri/applied-jobs")
    time.sleep(3)
    page_source = driver.page_source.lower()
    return job_title.lower() in page_source or company.lower() in page_source


def try_apply_and_verify(
    driver: webdriver.Chrome, apply_button_locator: tuple[str, str], job_title: str, company: str
) -> AuthResult:
    """Click apply and validate success to avoid silent failures."""
    try:
        WebDriverWait(driver, 15).until(EC.element_to_be_clickable(apply_button_locator)).click()
        time.sleep(2)
        verified = verify_application_submitted(driver, job_title, company)
        if verified:
            return AuthResult(True, f"Verified application for {job_title} at {company}")
        driver.save_screenshot(str(_DATA_DIR / "apply_not_verified.png"))
        return AuthResult(False, f"Apply flow completed but verification failed for {job_title} at {company}")
    except Exception as exc:
        driver.save_screenshot(str(_DATA_DIR / "apply_error.png"))
        return AuthResult(False, f"Apply flow failed: {exc}")
