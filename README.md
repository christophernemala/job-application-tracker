# 🎯 AI Job Application Tracker

**Complete job search automation system with web tracking, Selenium automation, and AI-powered cover letters!**

---

## 🌟 What Is This?

This project has **TWO parts**:

### **Part 1: Web-Based Tracker** 🌐
- Simple browser-based job application tracker
- No installation needed
- Manual job tracking
- **Live at:** https://christophernemala.github.io/job-application-tracker/

### **Part 2: Automated Job Agent** 🤖
- **Uses Selenium web drivers** to automate job applications
- Logs into Naukri Gulf automatically
- Applies to jobs on your behalf
- AI-powered cover letter generation
- SQLite database for tracking
- Flask dashboard
- **Requires setup** (see below)

---

## 🚀 Quick Links

| What | Link |
|------|------|
| **Live Web Tracker** | https://christophernemala.github.io/job-application-tracker/ |
| **Setup Guide (Automation)** | [SETUP_GUIDE.md](SETUP_GUIDE.md) |
| **GitHub Repository** | https://github.com/christophernemala/job-application-tracker |

---

## 📦 What's Included

### **Web Tracker** (`index.html`, `app.js`, `styles.css`)
- ✅ Track job applications manually
- ✅ Dashboard with statistics
- ✅ AI cover letter generator (basic)
- ✅ Export/import data
- ✅ Works in any browser
- ✅ No installation needed

### **Automation System** (`job_agent/` folder)
- ✅ **Selenium web automation** - Controls browser automatically
- ✅ **Naukri Gulf integration** - Logs in and applies to jobs
- ✅ **SQLite database** - Stores all applications
- ✅ **OpenAI integration** - Generates personalized cover letters
- ✅ **Flask dashboard** - View applications in browser
- ✅ **Verification system** - Confirms applications succeeded
- ⚠️ **Requires setup** - See [SETUP_GUIDE.md](SETUP_GUIDE.md)

---

## 🎯 Which One Should You Use?

### **Use Web Tracker If:**
- ✅ You want something simple
- ✅ You apply to jobs manually
- ✅ You don't want to install anything
- ✅ You just need tracking

### **Use Automation System If:**
- ✅ You want to automate job applications
- ✅ You're comfortable with Python
- ✅ You have Naukri Gulf account
- ✅ You want AI cover letters
- ✅ You understand the risks (see warnings below)

---

## 🚀 Getting Started

### **Option 1: Web Tracker (Easy)**

Just visit: https://christophernemala.github.io/job-application-tracker/

No setup needed!

### **Option 2: Automation System (Advanced)**

**Follow the complete setup guide:** [SETUP_GUIDE.md](SETUP_GUIDE.md)

**Quick version:**

```bash
# 1. Clone repository
git clone https://github.com/christophernemala/job-application-tracker.git
cd job-application-tracker/job_agent

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Mac/Linux
.venv\Scripts\activate     # Windows

# 3. Install packages
pip install -r requirements.txt

# 4. Configure credentials
cp .env.example .env
# Edit .env with your Naukri Gulf credentials

# 5. Run dashboard
python app.py

# 6. Open browser
# Go to: http://127.0.0.1:5001
```

**Full instructions:** [SETUP_GUIDE.md](SETUP_GUIDE.md)

---

## 🛠️ System Requirements (Automation Only)

- **Python 3.8+** - Programming language
- **Google Chrome** - Browser (for Selenium)
- **Naukri Gulf Account** - Your login credentials
- **OpenAI API Key** (Optional) - For AI cover letters

---

## ⚠️ Important Warnings (Automation)

### **Legal & Ethical Considerations:**

❌ **Terms of Service** - Naukri Gulf may prohibit automated applications  
❌ **Account Ban Risk** - You could get banned for using automation  
❌ **Quality Issues** - Automated applications are generic and less effective  
❌ **Spam Concerns** - Mass applications can damage your reputation  

### **Recommendations:**

✅ **Use for job discovery** - Let it find relevant jobs  
✅ **Review before applying** - Manually check each job  
✅ **Customize applications** - Don't send generic applications  
✅ **Respect rate limits** - Apply to 5-10 jobs/day max  
✅ **Test thoroughly** - Start with manual testing  

**We are not responsible for any account bans or legal issues. Use at your own risk.**

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [SETUP_GUIDE.md](SETUP_GUIDE.md) | Complete setup instructions for automation |
| [job_agent/README.md](job_agent/README.md) | Technical details of automation system |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | Common issues and solutions |

---

## 🎯 Features Breakdown

### **Web Tracker Features:**

| Feature | Description |
|---------|-------------|
| Dashboard | View stats, pipeline, recent applications |
| Add Applications | Log job applications manually |
| Filter & Search | Filter by status (Applied, Interview, etc.) |
| AI Generator | Basic cover letter generation |
| Export/Import | Backup and restore data |
| LocalStorage | Data stays in your browser |

### **Automation System Features:**

| Feature | Description |
|---------|-------------|
| Selenium Automation | Controls Chrome browser automatically |
| Naukri Gulf Login | Logs in with your credentials |
| Job Application | Clicks "Apply" button automatically |
| Verification | Confirms application succeeded |
| SQLite Database | Stores all jobs and applications |
| OpenAI Integration | Generates personalized cover letters |
| Flask Dashboard | Web interface to view applications |
| Screenshot Capture | Saves screenshots on errors |
| Session Management | Persists login cookies |

---

## 🔧 Technology Stack

### **Web Tracker:**
- HTML5
- CSS3
- JavaScript (ES6+)
- LocalStorage API
- GitHub Pages

### **Automation System:**
- **Python 3.8+**
- **Selenium** - Web automation (the web driver!)
- **Flask** - Web framework
- **SQLite** - Database
- **OpenAI API** - AI cover letters
- **webdriver-manager** - Auto-downloads ChromeDriver

---

## 📊 Project Structure

```
job-application-tracker/
│
├── index.html              # Web tracker (main page)
├── app.js                  # Web tracker logic
├── styles.css              # Web tracker styling
│
├── job_agent/              # Automation system
│   ├── automation.py       # Selenium web driver code
│   ├── config.py          # User profile & credentials
│   ├── database.py        # SQLite database
│   ├── ai_services.py     # OpenAI integration
│   ├── app.py             # Flask dashboard
│   ├── requirements.txt   # Python packages
│   ├── .env.example       # Credentials template
│   ├── templates/         # HTML templates
│   └── static/            # CSS/JS files
│
├── README.md              # This file
├── SETUP_GUIDE.md         # Complete setup instructions
└── TROUBLESHOOTING.md     # Common issues
```

---

## 🎓 Understanding Web Drivers

### **What is a Web Driver?**

A web driver (like Selenium) is a tool that **controls your browser automatically**:

```python
# Example: Automated login
driver.get("https://naukrigulf.com/login")
driver.find_element(By.ID, "email").send_keys("your@email.com")
driver.find_element(By.ID, "password").send_keys("password")
driver.find_element(By.ID, "submit").click()
```

### **How It Works:**

```
Your Python Code → Selenium → ChromeDriver → Chrome Browser
```

### **What You Need:**

1. **Selenium** - Python library (installed via pip)
2. **ChromeDriver** - Bridge to Chrome (auto-downloaded by webdriver-manager)
3. **Chrome Browser** - Must be installed on your computer

**The automation system handles all of this automatically!**

---

## 🚀 Usage Examples

### **Web Tracker:**

1. Visit: https://christophernemala.github.io/job-application-tracker/
2. Click "Applications DB" tab
3. Fill in job details
4. Click "Add Application"
5. View in dashboard

### **Automation System:**

```python
# Example: Login and apply to a job
from job_agent.automation import authenticate_naukri_gulf_with_config

# Login (uses web driver!)
driver = authenticate_naukri_gulf_with_config(headless=False)

# Navigate to job
driver.get("https://www.naukrigulf.com/job-listing-...")

# Click apply button
driver.find_element(By.CLASS_NAME, "apply-button").click()

# Close browser
driver.quit()
```

**See [SETUP_GUIDE.md](SETUP_GUIDE.md) for complete examples.**

---

## 🐛 Troubleshooting

### **Web Tracker Issues:**

| Problem | Solution |
|---------|----------|
| Website won't load | Clear browser cache, try different browser |
| Data disappeared | Check same browser, import backup |
| Buttons not working | Enable JavaScript, check console (F12) |

### **Automation Issues:**

| Problem | Solution |
|---------|----------|
| ChromeDriver not found | Run `pip install webdriver-manager` |
| Login failed | Check `.env` credentials, try manual login |
| Module not found | Activate virtual environment, reinstall packages |

**Full troubleshooting:** [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

---

## 📞 Support

### **Documentation:**
- [Setup Guide](SETUP_GUIDE.md) - Complete setup instructions
- [Troubleshooting](TROUBLESHOOTING.md) - Common issues

### **Contact:**
- **Email:** christophernemala@gmail.com
- **GitHub Issues:** Report bugs or request features
- **GitHub Repo:** https://github.com/christophernemala/job-application-tracker

---

## 📜 License

This project is open source. Feel free to use, modify, and share!

**Disclaimer:** Use the automation features responsibly and at your own risk. We are not responsible for any account bans or legal issues resulting from automated job applications.

---

## 🎉 Credits

Built by **Christopher Nemala** with assistance from AI (ChatGPT/Codex).

**Technologies:**
- Web Tracker: HTML/CSS/JavaScript
- Automation: Python + Selenium + Flask + OpenAI

---

## 🔮 Future Enhancements

Ideas for future versions:

- [ ] LinkedIn automation support
- [ ] Email notifications for new jobs
- [ ] Advanced job matching algorithm
- [ ] Resume parsing and optimization
- [ ] Interview preparation notes
- [ ] Salary negotiation tracker
- [ ] Company research integration
- [ ] Mobile app version

---

**Choose your path:**
- 🌐 **Simple tracking?** Use the web tracker
- 🤖 **Full automation?** Follow the [SETUP_GUIDE.md](SETUP_GUIDE.md)

**Happy job hunting! 🚀**
