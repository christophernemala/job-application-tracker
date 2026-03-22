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

# Codebase Overview

## Project: Job Application Tracker

A dual-architecture project with:
1. **Static Web Tracker** — vanilla JS frontend using localStorage (GitHub Pages deployable)
2. **Automation System** — Python/Flask backend with Selenium automation and SQLite

---

## Repository Structure

```
/
├── index.html              # Static web tracker UI (tabs: Dashboard, Applications, AI Studio)
├── app.js                  # Frontend logic (localStorage persistence, ~11KB)
├── styles.css              # Frontend styles
├── test.html               # Test HTML file
├── test_automation_login.py # Login automation test
├── Procfile                # gunicorn start command for Render/Heroku
├── render.yaml             # Render deployment config (installs Chrome)
├── runtime.txt             # python-3.12.10
├── requirements.txt        # Top-level Python deps (Flask, Selenium, OpenAI, pytest, gunicorn)
├── CLAUDE.md               # This file
├── README.md               # User-facing documentation
├── QUICK_START.md          # Quick start guide
├── SETUP_GUIDE.md          # Detailed setup instructions
├── BEGINNERS_GUIDE.md      # Beginner guide
├── AGENTS.md               # Agent documentation
├── TROUBLESHOOTING.md      # Troubleshooting guide
├── SAMPLE_DATA_GUIDE.md    # Sample data guide
├── SECURITY.md             # Security notes
├── .github/
│   ├── workflows/main.yml  # CI: pytest on push/PR to main
│   ├── hooks/
│   └── copilot-instructions.md
└── job_agent/              # Python automation package
    ├── __init__.py
    ├── app.py              # Flask app (login, dashboard, REST API)
    ├── automation.py       # Selenium WebDriver setup, Naukri Gulf login
    ├── config.py           # User profile, credentials, search preferences
    ├── database.py         # SQLite schema + CRUD (applications, jobs, logs)
    ├── ai_services.py      # OpenAI: cover letters, resume tailoring
    ├── naukri_runner.py    # Naukri Gulf auto-apply automation
    ├── linkedin_runner.py  # LinkedIn automation
    ├── apify_runner.py     # Apify API integration
    ├── requirements.txt    # Package-level deps (same as top-level)
    ├── .env.example        # Environment variable template
    ├── templates/
    │   ├── dashboard.html  # Flask dashboard (dark theme, modals)
    │   └── login.html      # Login form
    ├── static/
    │   └── styles.css      # Dashboard styles
    └── tests/
        ├── __init__.py
        ├── test_config.py
        └── test_database.py
```

---

## Technology Stack

| Layer | Technology |
|-------|------------|
| Frontend | HTML5, CSS3, Vanilla JS (ES6+), localStorage |
| Backend | Python 3.12, Flask 3.1.0 |
| Database | SQLite (file: `job_agent.db`) |
| Automation | Selenium 4.28.1, webdriver-manager 4.0.2 |
| AI | OpenAI 1.62.0 |
| Testing | pytest 8.3.4 |
| Server | gunicorn 21.2.0 |
| CI/CD | GitHub Actions, Render |

---

## Database Schema

**`applications`** — logged job applications
- `id`, `job_title`, `company`, `platform`, `job_url`
- `applied_date`, `status`, `match_score`
- `cover_letter`, `resume_version`, `application_id`, `screenshot_path`
- `response_received`, `interview_date`, `notes`

**`jobs`** — discovered job listings (auto-applied or scraped)
- `id`, `job_title`, `company`, `platform`, `job_url` (UNIQUE)
- `discovered_date`, `description`, `salary_range`, `location`
- `applied` (BOOLEAN), `match_score`, `skills_required`

**`logs`** — automation activity log
- `id`, `timestamp`, `action`, `status`, `error_message`, `job_id`

---

## Flask API Endpoints

| Route | Method | Auth | Purpose |
|-------|--------|------|---------|
| `/login` | GET, POST | None | Login form |
| `/logout` | GET | Session | Clear session |
| `/` | GET | Session | Main dashboard |
| `/api/config` | GET | Session | Runtime config snapshot |
| `/api/application/<id>` | GET | Session | Application details |
| `/api/application/<id>/notes` | PUT | Session | Update notes |

Authentication: session-based cookie + HTTP Basic Auth supported.

---

## Environment Variables

Defined in `job_agent/.env.example`. Copy to `job_agent/.env` (never commit `.env`).

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `NAUKRI_GULF_EMAIL` | Yes | — | Naukri Gulf login |
| `NAUKRI_GULF_PASSWORD` | Yes | — | Naukri Gulf login |
| `OPENAI_API_KEY` | For AI features | — | Cover letters, resume tailoring |
| `APIFY_API_TOKEN` | For Apify | — | Apify scraping |
| `LINKEDIN_EMAIL` | For LinkedIn | — | LinkedIn automation |
| `LINKEDIN_PASSWORD` | For LinkedIn | — | LinkedIn automation |
| `JOB_AGENT_NAME` | No | Christopher Nemala | User display name |
| `JOB_AGENT_EMAIL` | No | — | User email |
| `JOB_AGENT_LOCATION` | No | Dubai, UAE | Search location |
| `DASHBOARD_USERNAME` | No | admin | Dashboard login |
| `DASHBOARD_PASSWORD` | No | admin123 | Dashboard login |
| `FLASK_SECRET_KEY` | No | job-tracker-secret-2024 | Session signing |

---

## Development Workflows

### Local Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp job_agent/.env.example job_agent/.env
# Edit job_agent/.env with real credentials
python -m job_agent.app    # Start Flask dashboard at http://localhost:5000
```

### Run Tests

```bash
pytest job_agent/tests/ -v
```

### Run Automation

```bash
python -m job_agent.naukri_runner    # Naukri Gulf auto-apply
python -m job_agent.linkedin_runner  # LinkedIn automation
python -m job_agent.apify_runner     # Apify-based scraping
```

### Deploy to Render

Push to `main`. `render.yaml` handles:
1. `pip install -r requirements.txt`
2. Install Google Chrome via apt-get
3. Start: `gunicorn job_agent.app:app`

---

## Key Conventions

### Python (job_agent/)
- Module entry points use `if __name__ == "__main__"` guards
- All credentials loaded from environment variables via `config.py` — never hardcoded
- Selenium operations wrapped in try/except; screenshots saved on error (`*.png`)
- SQLite connection managed per-function in `database.py`
- Flask routes require `@login_required` decorator (session check)

### Frontend (index.html / app.js)
- All data stored in `localStorage` under namespaced keys
- No build step, no framework — plain HTML/CSS/JS
- Tab switching via CSS class toggling
- Export/import via JSON file download/upload

### Git / CI
- CI runs `pytest job_agent/tests/ -v` on every push and PR to `main`
- `.gitignore` excludes: `.env`, `job_agent.db`, `.venv/`, `__pycache__/`, `*.png`, `*.pkl`
- Never commit secrets or the SQLite database file

### Security
- Rotate `FLASK_SECRET_KEY` and `DASHBOARD_PASSWORD` before any public deployment
- `.env` file must never be committed (enforced by `.gitignore`)
- See `SECURITY.md` for full guidance
