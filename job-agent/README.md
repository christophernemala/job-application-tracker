# Job Agent – Automated Job Monitoring & Application System

A production-grade job monitoring and controlled application system targeting finance roles (AR, O2C, Credit Control, Collections) in the UAE.

## Architecture

```
job-agent/
  config/              # JSON configuration files
    profile.json       # Candidate profile and preferences
    rules.json         # Scoring weights and filtering rules
    answers.json       # Pre-filled form answers
    sources.json       # Job board configurations
  data/
    jobs.db            # SQLite database (auto-created)
    resumes/           # Resume PDF variants
  logs/
    job_agent.log      # Main rotating log file
    screenshots/       # Application screenshots
    run_logs/          # Per-run log files
    reports/           # Generated HTML reports
    notifications.jsonl # Notification payloads
  src/
    collectors/        # Source-specific job scrapers
    parsers/           # Title/salary/keyword normalization
    scorers/           # Weighted scoring engine + routing
    appliers/          # Browser-based application engine
    storage/           # SQLite repositories
    notifications/     # Telegram/email/console notifier
    utils/             # Logging and config loader
    reports/           # Terminal + HTML report generator
  tests/               # Pytest test suite
  main.py              # CLI entry point
```

## Setup

### 1. Install dependencies

```bash
cd job-agent
pip install -r requirements.txt
playwright install chromium
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your credentials
```

Required environment variables for automation:
- `LINKEDIN_EMAIL` / `LINKEDIN_PASSWORD` – LinkedIn login
- `NAUKRIGULF_EMAIL` / `NAUKRIGULF_PASSWORD` – NaukriGulf login

Optional:
- `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` – Telegram notifications
- `SMTP_HOST` / `SMTP_USER` / `SMTP_PASSWORD` / `NOTIFICATION_EMAIL_TO` – Email notifications

### 3. Add resume files

Place your resume PDFs in `data/resumes/`:
- `christopher_ar_collections.pdf`
- `christopher_credit_control.pdf`
- `christopher_o2c.pdf`
- `christopher_general_finance.pdf`

### 4. Customize configuration

Edit files in `config/`:

- **profile.json** – Update candidate details, target titles, excluded titles, locations, salary floor
- **rules.json** – Tune scoring weights, keyword lists, threshold scores
- **answers.json** – Pre-fill common screening question answers
- **sources.json** – Enable/disable job boards, adjust search URLs

### 5. Initialize database

```bash
python main.py --init-db
```

## Usage

### Full pipeline run
```bash
python main.py
```

### Collect and score only (no applications)
```bash
python main.py --collect-only
```

### Dry run (simulate applications)
```bash
python main.py --dry-run
```

### Single source
```bash
python main.py --source linkedin
python main.py --source naukrigulf
```

### Reports only
```bash
python main.py --report-only
```

## Pipeline Flow

1. **Collect** – Playwright-based scrapers gather job listings from LinkedIn, NaukriGulf
2. **Parse** – Normalize titles, parse salaries, extract keywords, classify apply types
3. **Score** – Weighted scoring (0-100) across 6 factors:
   - Title relevance (30%)
   - Keyword match (20%)
   - Location match (15%)
   - Seniority fit (15%)
   - Salary fit (10%)
   - ERP/skill match (10%)
4. **Route** – Jobs assigned to: `auto_apply`, `semi_auto`, `manual_review`, or `reject`
5. **Apply** – Browser automation for `auto_apply` jobs with form filling, resume upload, screenshot capture
6. **Report** – Terminal + HTML summary reports
7. **Notify** – Console alerts + JSONL log (Telegram/email when configured)

## Routing Rules

| Route | Criteria |
|-------|----------|
| `auto_apply` | Score >= 80 + easy_apply/internal + non-manager |
| `semi_auto` | Score >= 60 + internal/simple external |
| `manual_review` | Manager roles, complex ATS, unknown flow, borderline scores |
| `reject` | Score < 40, excluded patterns, wrong seniority |

## Running Tests

```bash
cd job-agent
python -m pytest tests/ -v
```

## Safety

- Score-based filtering prevents applications to irrelevant roles
- Deduplication by source + URL prevents duplicate applications
- Rate limiting between applications
- Screenshots at every key stage for auditability
- All actions logged with timestamps and reasons
- Dry-run mode for safe testing
- Max applications per run/day limits in `rules.json`
