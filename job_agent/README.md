# AI Job Agent Module

This folder contains a production-oriented baseline for fixing the application tracking gap:

- **`automation.py`**: Selenium login + apply verification for Naukri Gulf.
- **`database.py`**: SQLite schema and persistence for jobs, applications, and logs.
- **`ai_services.py`**: OpenAI-powered cover letter and resume tailoring services.
- **`config.py`**: User profile, credentials, and job-search preferences (supports `.env` and env vars).
- **`app.py`**: Flask dashboard + APIs for application details and notes.
- **`templates/dashboard.html`** and **`static/styles.css`**: Clickable application cards with modal details.

## Run locally

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
