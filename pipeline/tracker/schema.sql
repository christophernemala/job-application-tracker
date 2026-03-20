-- Job application tracker schema

CREATE TABLE IF NOT EXISTS jobs (
    id              TEXT PRIMARY KEY,
    date_captured   TEXT NOT NULL,
    company         TEXT NOT NULL,
    title           TEXT NOT NULL,
    location        TEXT,
    salary_text     TEXT,
    salary_aed_min  INTEGER,
    source          TEXT,
    url             TEXT,
    score           INTEGER,
    shortlist_reason TEXT,
    missing_skills  TEXT,        -- JSON array
    cv_file         TEXT,        -- path to tailored CV
    status          TEXT DEFAULT 'new',
    apply_mode      TEXT,        -- easy_apply | external | browser_assist | manual
    easy_apply_url  TEXT,
    applied_at      TEXT,
    notes           TEXT,
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS run_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    run_at      TEXT DEFAULT (datetime('now')),
    jobs_found  INTEGER,
    shortlisted INTEGER,
    applied     INTEGER,
    errors      INTEGER,
    notes       TEXT
);

CREATE INDEX IF NOT EXISTS idx_jobs_status  ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_score   ON jobs(score DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_source  ON jobs(source);
