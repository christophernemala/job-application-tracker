# 🚀 Complete Setup Guide - Job Automation System

This guide will help you set up and run your **automated job application system** that uses **Selenium web drivers** to apply to jobs on Naukri Gulf.

---

## 📋 What You're Setting Up

Your system has **TWO parts**:

### **Part 1: Simple Web Tracker** (Already Live!)
- 🌐 **URL:** https://christophernemala.github.io/job-application-tracker/
- ✅ Works in browser
- ✅ No installation needed
- ✅ Manual job tracking

### **Part 2: Automated Job Agent** (Needs Setup!)
- 🤖 Uses **Selenium web drivers**
- 🔄 Logs into Naukri Gulf automatically
- 📝 Applies to jobs on your behalf
- 💾 Stores everything in database
- 🎨 Has its own dashboard

---

## ⚙️ System Requirements

### **What You Need:**

✅ **Python 3.8+** - Programming language  
✅ **Google Chrome** - Browser (must be installed)  
✅ **Internet Connection** - For downloading packages  
✅ **Naukri Gulf Account** - Your login credentials  
✅ **OpenAI API Key** (Optional) - For AI cover letters  

---

## 🛠️ Step-by-Step Setup

### **Step 1: Install Python**

**Check if you have Python:**
```bash
python --version
# or
python3 --version
```

**If not installed:**
- **Windows:** Download from https://www.python.org/downloads/
  - ⚠️ **IMPORTANT:** Check "Add Python to PATH" during installation!
- **Mac:** `brew install python3`
- **Linux:** `sudo apt install python3 python3-pip`

---

### **Step 2: Download Your Code**

**Option A: Download ZIP (Easiest)**
1. Go to: https://github.com/christophernemala/job-application-tracker
2. Click green **"Code"** button
3. Click **"Download ZIP"**
4. Extract the ZIP file to a folder (e.g., `C:\job-tracker\`)

**Option B: Clone with Git**
```bash
git clone https://github.com/christophernemala/job-application-tracker.git
cd job-application-tracker
```

---

### **Step 3: Navigate to Job Agent Folder**

Open **Terminal** (Mac/Linux) or **Command Prompt** (Windows):

```bash
cd job-application-tracker/job_agent
```

---

### **Step 4: Create Virtual Environment**

This keeps your Python packages isolated:

```bash
# Create virtual environment
python -m venv .venv

# Activate it
# On Windows:
.venv\Scripts\activate

# On Mac/Linux:
source .venv/bin/activate
```

You should see `(.venv)` in your terminal prompt.

---

### **Step 5: Install Required Packages**

```bash
pip install -r requirements.txt
```

This installs:
- ✅ **Flask** - Web framework for dashboard
- ✅ **Selenium** - Web automation (the web driver!)
- ✅ **OpenAI** - AI cover letter generation
- ✅ **webdriver-manager** - Auto-downloads ChromeDriver
- ✅ **pytest** - Testing framework

**Wait 1-2 minutes for installation to complete.**

---

### **Step 6: Install Google Chrome**

**Check if Chrome is installed:**
- Open Chrome browser
- If not installed: Download from https://www.google.com/chrome/

**Note:** ChromeDriver will be **automatically downloaded** by webdriver-manager!

---

### **Step 7: Configure Your Credentials**

**Create your `.env` file:**

```bash
# Copy the example file
cp .env.example .env

# Edit it
# Windows: notepad .env
# Mac: nano .env
# Linux: nano .env
```

**Fill in your real credentials:**

```bash
# Naukri Gulf Login (REQUIRED)
NAUKRI_GULF_EMAIL=your-email@gmail.com
NAUKRI_GULF_PASSWORD=your-naukri-password

# Your Profile Info
JOB_AGENT_NAME=Christopher Nemala
JOB_AGENT_EMAIL=christophernemala@gmail.com

# OpenAI API Key (OPTIONAL - for AI cover letters)
OPENAI_API_KEY=sk-your-openai-key-here
```

**⚠️ SECURITY WARNING:**
- ❌ **NEVER** commit `.env` to GitHub
- ✅ It's already in `.gitignore` (safe)
- ✅ Keep your passwords secret

---

### **Step 8: Test the Setup**

**Run the Flask dashboard:**

```bash
python app.py
```

You should see:
```
 * Running on http://127.0.0.1:5001
 * Debug mode: on
```

**Open your browser:**
- Go to: **http://127.0.0.1:5001**
- You should see the dashboard!

**Press `Ctrl+C` to stop the server.**

---

## 🎯 How to Use the System

### **Test Naukri Gulf Login**

Create a test script `test_login.py`:

```python
from job_agent.automation import authenticate_naukri_gulf_with_config

# This will open Chrome and log into Naukri Gulf
driver = authenticate_naukri_gulf_with_config(headless=False)
print("✅ Login successful!")
input("Press Enter to close browser...")
driver.quit()
```

Run it:
```bash
python test_login.py
```

**What happens:**
1. Chrome browser opens
2. Goes to Naukri Gulf login page
3. Enters your email/password
4. Logs in automatically
5. Waits for you to press Enter
6. Closes browser

---

### **Apply to a Job (Manual Test)**

Create `test_apply.py`:

```python
from job_agent.automation import authenticate_naukri_gulf_with_config, try_apply_and_verify
from selenium.webdriver.common.by import By

# Login
driver = authenticate_naukri_gulf_with_config(headless=False)

# Go to a job posting (replace with real URL)
driver.get("https://www.naukrigulf.com/job-listing-...")

# Find and click Apply button
apply_button = (By.XPATH, "//button[contains(text(), 'Apply')]")
result = try_apply_and_verify(
    driver, 
    apply_button, 
    "Finance Executive",  # Job title
    "ABC Company"  # Company name
)

print(result.message)
driver.quit()
```

---

### **Generate AI Cover Letter**

Create `test_ai.py`:

```python
from job_agent.ai_services import generate_cover_letter
from job_agent.config import USER_PROFILE

job_description = """
We are looking for a Finance Executive with 5+ years experience
in AR, O2C, and Oracle Fusion. Must have strong Excel skills.
"""

cover_letter = generate_cover_letter(
    job_description=job_description,
    company_name="ABC Company",
    job_title="Finance Executive",
    user_profile=USER_PROFILE
)

print(cover_letter)
```

Run it:
```bash
python test_ai.py
```

---

## 🔄 Daily Automation (Advanced)

### **Option 1: Manual Daily Run**

Create `daily_job_search.py`:

```python
from job_agent.automation import authenticate_naukri_gulf_with_config
from job_agent.database import save_application
import time

# Login
driver = authenticate_naukri_gulf_with_config(headless=True)

# Search for jobs
driver.get("https://www.naukrigulf.com/finance-executive-jobs")
time.sleep(3)

# Get job listings
jobs = driver.find_elements(By.CLASS_NAME, "job-card")

for job in jobs[:5]:  # Apply to first 5 jobs
    title = job.find_element(By.CLASS_NAME, "title").text
    company = job.find_element(By.CLASS_NAME, "company").text
    
    # Click apply
    job.find_element(By.CLASS_NAME, "apply-button").click()
    time.sleep(2)
    
    # Save to database
    save_application(
        job_title=title,
        company=company,
        platform="Naukri Gulf",
        job_url=driver.current_url,
        status="applied",
        match_score=None,
        cover_letter=None,
        resume_path=None
    )
    
    print(f"✅ Applied to {title} at {company}")

driver.quit()
```

Run daily:
```bash
python daily_job_search.py
```

---

### **Option 2: Scheduled Automation**

**Windows Task Scheduler:**
1. Open Task Scheduler
2. Create Basic Task
3. Trigger: Daily at 9 AM
4. Action: Start Program
5. Program: `C:\path\to\.venv\Scripts\python.exe`
6. Arguments: `C:\path\to\daily_job_search.py`

**Mac/Linux Cron:**
```bash
crontab -e

# Add this line (runs daily at 9 AM):
0 9 * * * cd /path/to/job_agent && /path/to/.venv/bin/python daily_job_search.py
```

---

## 🐛 Troubleshooting

### **Problem: "ChromeDriver not found"**

**Solution:**
```bash
pip install webdriver-manager
```

The system will auto-download ChromeDriver!

---

### **Problem: "Naukri Gulf login failed"**

**Solutions:**
1. Check your `.env` file has correct email/password
2. Try logging in manually first
3. Check if Naukri Gulf changed their login page
4. Run with `headless=False` to see what's happening

---

### **Problem: "OpenAI API error"**

**Solutions:**
1. Get API key from: https://platform.openai.com/api-keys
2. Add to `.env`: `OPENAI_API_KEY=sk-...`
3. Or skip AI features (they're optional)

---

### **Problem: "Module not found"**

**Solution:**
```bash
# Make sure virtual environment is activated
source .venv/bin/activate  # Mac/Linux
.venv\Scripts\activate     # Windows

# Reinstall packages
pip install -r requirements.txt
```

---

### **Problem: "Database locked"**

**Solution:**
```bash
# Close all Python processes
# Delete the database file
rm job_agent.db

# Restart the app
python app.py
```

---

## 📊 View Your Applications

### **Web Dashboard:**

```bash
python app.py
```

Open: http://127.0.0.1:5001

### **Database Query:**

```python
from job_agent.database import list_applications

apps = list_applications()
for app in apps:
    print(f"{app['job_title']} at {app['company']} - {app['status']}")
```

---

## ⚠️ Important Warnings

### **Legal & Ethical:**

❌ **Naukri Gulf Terms of Service** - May prohibit automation  
❌ **Account Ban Risk** - You could get banned  
❌ **Quality Issues** - Automated applications are generic  

### **Recommendations:**

✅ **Use for job discovery** - Let it find jobs  
✅ **Review before applying** - Check each job manually  
✅ **Customize applications** - Don't spam generic applications  
✅ **Respect rate limits** - Don't apply to 100 jobs/day  

---

## 🎓 Understanding Web Drivers

### **What is Selenium?**

Selenium is a tool that **controls your browser automatically**:

```python
driver.get("https://naukrigulf.com")  # Opens website
driver.find_element(By.ID, "email").send_keys("test@email.com")  # Types text
driver.find_element(By.ID, "submit").click()  # Clicks button
```

### **What is ChromeDriver?**

ChromeDriver is the **bridge** between Selenium and Chrome:

```
Your Python Code → Selenium → ChromeDriver → Chrome Browser
```

### **Why Do You Need It?**

Without ChromeDriver, Selenium can't control Chrome!

---

## 📁 Project Structure

```
job_agent/
├── automation.py       # Selenium web driver code
├── config.py          # Your profile & credentials
├── database.py        # SQLite database
├── ai_services.py     # OpenAI integration
├── app.py             # Flask dashboard
├── requirements.txt   # Python packages
├── .env               # Your secrets (DON'T COMMIT!)
├── .env.example       # Template
├── templates/
│   └── dashboard.html # Dashboard UI
└── static/
    └── styles.css     # Dashboard styling
```

---

## 🚀 Next Steps

### **1. Test Everything**
- ✅ Login to Naukri Gulf
- ✅ View dashboard
- ✅ Generate cover letter
- ✅ Apply to one job manually

### **2. Customize**
- Edit `config.py` with your preferences
- Modify job search criteria
- Adjust automation scripts

### **3. Automate Carefully**
- Start with manual testing
- Gradually add automation
- Monitor for issues

---

## 💡 Tips for Success

### **Start Small:**
1. Test login first
2. Apply to 1 job manually
3. Then automate 5 jobs/day
4. Gradually increase

### **Monitor Results:**
- Check dashboard daily
- Review application success rate
- Adjust strategy based on results

### **Stay Safe:**
- Don't spam applications
- Customize each application
- Respect website terms of service

---

## 📞 Need Help?

### **Common Issues:**
- Check the Troubleshooting section above
- Read error messages carefully
- Try running with `headless=False` to see browser

### **Contact:**
- **Email:** christophernemala@gmail.com
- **GitHub Issues:** Report bugs on GitHub

---

## ✅ Quick Start Checklist

- [ ] Python installed
- [ ] Chrome installed
- [ ] Code downloaded
- [ ] Virtual environment created
- [ ] Packages installed
- [ ] `.env` file configured
- [ ] Login test successful
- [ ] Dashboard running
- [ ] First job application tested

---

**You're all set! Start with manual testing, then gradually add automation. Good luck with your job search! 🎉**
