from job_agent.automation import authenticate_naukri_gulf_with_config
import time

print("Starting Naukri Gulf automated login test...")
try:
    # This will open Chrome and log into Naukri Gulf
    # Setting headless=False so the user can see it work
    driver = authenticate_naukri_gulf_with_config(headless=False)
    print("Login successful!")
    print("Current URL:", driver.current_url)
    driver.save_screenshot("login_success.png")
    print("Screenshot saved to login_success.png")
    print("Waiting 10 seconds so you can see the logged-in profile...")
    time.sleep(10)
    driver.quit()
    print("Browser closed.")
except Exception as e:
    print(f"Login failed: {e}")
