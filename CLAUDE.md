# context-mode — MANDATORY routing rules

You have context-mode MCP tools available. These rules are NOT optional — they protect your context window from flooding. A single unrouted command can dump 56 KB into context and waste the entire session.

## BLOCKED commands — do NOT attempt these

### curl / wget — BLOCKED
Any Bash command containing `curl` or `wget` is intercepted and replaced with an error message. Do NOT retry.
Instead use:
- `ctx_fetch_and_index(url, source)` to fetch and index web pages
- `ctx_execute(language: "javascript", code: "const r = await fetch(...)")` to run HTTP calls in sandbox

### Inline HTTP — BLOCKED
Any Bash command containing `fetch('http`, `requests.get(`, `requests.post(`, `http.get(`, or `http.request(` is intercepted and replaced with an error message. Do NOT retry with Bash.
Instead use:
- `ctx_execute(language, code)` to run HTTP calls in sandbox — only stdout enters context

### WebFetch — BLOCKED
WebFetch calls are denied entirely. The URL is extracted and you are told to use `ctx_fetch_and_index` instead.
Instead use:
- `ctx_fetch_and_index(url, source)` then `ctx_search(queries)` to query the indexed content

## REDIRECTED tools — use sandbox equivalents

### Bash (>20 lines output)
Bash is ONLY for: `git`, `mkdir`, `rm`, `mv`, `cd`, `ls`, `npm install`, `pip install`, and other short-output commands.
For everything else, use:
- `ctx_batch_execute(commands, queries)` — run multiple commands + search in ONE call
- `ctx_execute(language: "shell", code: "...")` — run in sandbox, only stdout enters context

### Read (for analysis)
If you are reading a file to **Edit** it → Read is correct (Edit needs content in context).
If you are reading to **analyze, explore, or summarize** → use `ctx_execute_file(path, language, code)` instead. Only your printed summary enters context. The raw file content stays in the sandbox.

### Grep (large results)
Grep results can flood context. Use `ctx_execute(language: "shell", code: "grep ...")` to run searches in sandbox. Only your printed summary enters context.

## Tool selection hierarchy

1. **GATHER**: `ctx_batch_execute(commands, queries)` — Primary tool. Runs all commands, auto-indexes output, returns search results. ONE call replaces 30+ individual calls.
2. **FOLLOW-UP**: `ctx_search(queries: ["q1", "q2", ...])` — Query indexed content. Pass ALL questions as array in ONE call.
3. **PROCESSING**: `ctx_execute(language, code)` | `ctx_execute_file(path, language, code)` — Sandbox execution. Only stdout enters context.
4. **WEB**: `ctx_fetch_and_index(url, source)` then `ctx_search(queries)` — Fetch, chunk, index, query. Raw HTML never enters context.
5. **INDEX**: `ctx_index(content, source)` — Store content in FTS5 knowledge base for later search.

## Subagent routing

When spawning subagents (Agent/Task tool), the routing block is automatically injected into their prompt. Bash-type subagents are upgraded to general-purpose so they have access to MCP tools. You do NOT need to manually instruct subagents about context-mode.

## Output constraints

- Keep responses under 500 words.
- Write artifacts (code, configs, PRDs) to FILES — never return them as inline text. Return only: file path + 1-line description.
- When indexing content, use descriptive source labels so others can `ctx_search(source: "label")` later.

## ctx commands

| Command | Action |
|---------|--------|
| `ctx stats` | Call the `ctx_stats` MCP tool and display the full output verbatim |
| `ctx doctor` | Call the `ctx_doctor` MCP tool, run the returned shell command, display as checklist |
| `ctx upgrade` | Call the `ctx_upgrade` MCP tool, run the returned shell command, display as checklist |

---

# Job Application Tracker — Codebase Guide

## Project Overview

A full-stack job application automation tool for Finance/AR professionals in the UAE. It automates job discovery and applications on Naukri Gulf and LinkedIn, uses OpenAI for AI-generated cover letters and resume tailoring, and provides a dashboard for tracking applications.

## Architecture

```
job-application-tracker/
├── job_agent/                 # Python/Flask backend
│   ├── app.py                 # Flask app: routes, auth, API endpoints
│   ├── config.py              # User profile & job preferences (single source of truth)
│   ├── database.py            # SQLite layer (3 tables: applications, jobs, logs)
│   ├── ai_services.py         # OpenAI integration (cover letters, resume tailoring)
│   ├── automation.py          # Selenium browser setup & auth helpers
│   ├── naukri_runner.py       # Naukri Gulf job search + Easy Apply automation
│   ├── linkedin_runner.py     # LinkedIn job search + Easy Apply automation
│   ├── apify_runner.py        # Apify API-based scraping (no browser required)
│   ├── templates/             # Jinja2: dashboard.html, login.html
│   ├── static/                # CSS/JS frontend assets
│   └── tests/                 # pytest tests
│       ├── test_config.py
│       └── test_database.py
├── index.html                 # Standalone static UI (localStorage-based, no backend needed)
├── app.js                     # Client-side JS for static UI
├── styles.css                 # Shared styles
├── render.yaml                # Render.com deployment blueprint
├── vercel.json                # Vercel static hosting config
├── Procfile                   # gunicorn entrypoint
└── requirements.txt           # Python dependencies
```

## Backend: Flask API

**Entry point**: `job_agent/app.py`

### Authentication
- Session-based login via `/login` (HTML form)
- HTTP Basic Auth fallback for API clients
- Decorator: `@requires_auth` applied to all protected routes

### API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/login` | GET/POST | Form authentication |
| `/logout` | GET | Clear session |
| `/` | GET | Serve dashboard HTML |
| `/api/config` | GET | Runtime config snapshot (diagnostics) |
| `/api/applications` | POST | Create application record |
| `/api/application/<id>` | GET | Retrieve application details |
| `/api/application/<id>/notes` | PUT | Update notes |
| `/api/run-automation` | POST | Trigger Selenium automation (async, returns 202) |
| `/api/scrape` | POST | Trigger Apify scraping (async, returns 202) |
| `/api/automation-status` | GET | Poll automation run status |

Long-running jobs (automation, scraping) execute in **background threads**; poll `/api/automation-status` for results.

## Database Schema (SQLite)

File: `job_agent/job_agent.db` (gitignored, runtime only)

```sql
applications  -- tracked job applications
  id, job_title, company, platform, job_url
  applied_date, status, match_score
  cover_letter, resume_version, screenshot_path
  response_received, interview_date, notes

jobs          -- discovered job listings (before applying)
  id, job_title, company, platform, job_url (UNIQUE)
  discovered_date, description, salary_range, location
  applied, match_score, skills_required

logs          -- automation run history
  id, timestamp, action, status, error_message, job_id
```

Use `with get_connection() as conn:` (context manager) for all DB operations — defined in `database.py`.

## Configuration (`job_agent/config.py`)

All config lives here. Env vars override defaults at runtime.

Key config objects:
- `USER_PROFILE` — name, target roles, skills, experience, location
- `JOB_SEARCH_PREFERENCES` — keywords, platforms, salary range, experience filters
- Credentials: `NAUKRI_EMAIL`, `NAUKRI_PASSWORD`, `LINKEDIN_EMAIL`, `LINKEDIN_PASSWORD`, `APIFY_API_TOKEN`, `OPENAI_API_KEY` — all read from env vars via `os.getenv()`

**Never hardcode credentials.** Copy `job_agent/.env.example` to `job_agent/.env` for local development.

## Automation Runners

| File | Platform | Method |
|------|----------|--------|
| `naukri_runner.py` | Naukri Gulf | Selenium (Chrome headless) |
| `linkedin_runner.py` | LinkedIn | Selenium (Chrome headless) |
| `apify_runner.py` | Any | Apify API (no browser) |

Selenium setup is centralized in `automation.py`. Chrome binary location is auto-detected for both local and ephemeral (Render.com) environments.

## AI Features (`ai_services.py`)

Uses `openai` SDK. Two main functions:
- Cover letter generation — takes job description + user profile, returns formatted letter
- Resume tailoring — returns JSON with suggested edits

Response parsing uses JSON mode where possible; falls back to string parsing.

## Static Frontend (`index.html` + `app.js`)

A completely standalone UI requiring no backend. Uses **localStorage** for persistence. Tabs: Dashboard, Applications DB, AI Studio. Suitable for offline or Vercel static deployment.

## Development Workflows

### Local Setup
```bash
cp job_agent/.env.example job_agent/.env   # add credentials
pip install -r requirements.txt
python -m flask --app job_agent.app run    # starts at http://localhost:5000
```

### Running Tests
```bash
pytest job_agent/tests/
```

Tests use `monkeypatch` for env var mocking and temp files for DB isolation. Always run tests before committing automation or config changes.

### Deployment

**Render.com** (backend): defined in `render.yaml`. Start command: `gunicorn job_agent.app:app`. Required env vars set in Render dashboard (passwords marked `sync: false`).

**Vercel** (static): `vercel.json` rewrites all routes to `index.html` for SPA behavior.

## Code Conventions

| Concern | Convention |
|---------|-----------|
| Python naming | `snake_case` for functions, variables, module-level constants in `UPPER_SNAKE_CASE` |
| JS naming | `camelCase` for variables and functions |
| Error handling | `try/except` with `logging`; never swallow exceptions silently |
| DB access | Always use `with get_connection()` context manager |
| Secrets | Always via `os.getenv()`, never hardcoded |
| Async work | Background threads + status polling endpoint pattern |
| New routes | Add `@requires_auth` decorator; return JSON for `/api/*` routes |
| Templates | Jinja2 in `job_agent/templates/`; static assets in `job_agent/static/` |

## Key Files to Know

- **`job_agent/config.py`** — change user profile, job preferences, or add new env vars here first
- **`job_agent/app.py`** — add new API endpoints here
- **`job_agent/database.py`** — schema migrations and all SQL queries live here
- **`job_agent/ai_services.py`** — modify AI prompts or add new AI features here
- **`render.yaml`** — update when adding new env vars for deployment
