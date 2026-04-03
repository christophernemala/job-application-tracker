# AI Job Agent Module

This folder contains a production-oriented baseline for fixing the application tracking gap:

- **`automation.py`**: Selenium login + apply verification for Naukri Gulf and LinkedIn.
- **`database.py`**: SQLite schema and persistence for jobs, applications, and logs.
- **`ai_services.py`**: OpenAI-powered cover letter and resume tailoring services.
- **`config.py`**: User profile, credentials, and job-search preferences (supports `.env` and env vars).
- **`app.py`**: Flask dashboard + APIs for application details and notes.
- **`human_scheduler.py`**: Human-like scheduling with rate limits, breaks, and activity patterns.
- **`auto_apply.py`**: Automated job search and application runner for LinkedIn and Naukri Gulf.
- **`daemon.py`**: Long-running daemon for all-day job application automation.

## Auto-Apply System

The auto-apply system mimics human behavior to avoid platform detection:

### Features
- **Slow, spread-out activity** - Applications distributed throughout the day
- **Random delays** - Variable wait times between actions (45s-5min)
- **Human-like browsing** - Scrolling, reading time, mouse movements
- **Platform rotation** - Alternates between LinkedIn and Naukri Gulf
- **Daily limits** - Configurable per-platform caps (default: 15 LinkedIn, 25 Naukri)
- **Automatic breaks** - Takes 10-45 min breaks every 4-5 applications
- **Active hours** - Only operates during configured hours (default: 8am-10pm)

### Quick Start

```bash
# One-time run
python -m job_agent.auto_apply

# Run as daemon (all day)
python -m job_agent.daemon --linkedin-limit 15 --naukri-limit 25

# With visible browser (for debugging)
python -m job_agent.daemon --visible --log-file job_agent.log
```

### Daemon Options

```
--linkedin-limit N   Max LinkedIn applications per day (default: 15)
--naukri-limit N     Max Naukri Gulf applications per day (default: 25)
--start-hour H       Start hour in 24h format (default: 8)
--end-hour H         End hour in 24h format (default: 22)
--visible            Show browser windows instead of headless
--log-file PATH      Write logs to file
```

## Run Dashboard Locally

```bash
cd job_agent
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env with your real credentials
python app.py
```

Then open `http://127.0.0.1:5001`.

## Configuration

- `config.py` has defaults for profile and job preferences.
- Naukri Gulf login credentials are loaded in this order:
  1. Process environment variables
  2. `job_agent/.env` file
- Required keys for login automation:
  - `NAUKRI_GULF_EMAIL`
  - `NAUKRI_GULF_PASSWORD`

Use `authenticate_naukri_gulf_with_config()` in `automation.py` to log in with configured credentials.

## Verification endpoint

- `GET /api/config` returns a **redacted** runtime configuration snapshot and confirms if password is set without exposing the password.
