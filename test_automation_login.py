"""Manual smoke test for Naukri Gulf login automation.

This file is intentionally executable as a script, but safe to import during test
collection without launching a browser.
"""

from __future__ import annotations

import time

from job_agent.automation import authenticate_naukri_gulf_with_config


def main() -> None:
    print("Starting Naukri Gulf automated login test...")
    try:
        driver = authenticate_naukri_gulf_with_config(headless=False)
        print("Login successful!")
        print("Current URL:", driver.current_url)
        driver.save_screenshot("login_success.png")
        print("Screenshot saved to login_success.png")
        print("Waiting 10 seconds so you can see the logged-in profile...")
        time.sleep(10)
        driver.quit()
        print("Browser closed.")
    except Exception as exc:
        print(f"Login failed: {exc}")


if __name__ == "__main__":
    main()
