# GitHub Job Selection Agent Operating Guide

This guide explains how to operate the safe UAE finance job selection agent.

The agent does not auto-apply. It finds and selects jobs, scores them against Christopher Nemala's CV skills, and sends selected jobs to the Notion Auto Job Selection Tracker.

## What the Agent Does

1. Reads job leads from `job_agent/job_leads.json` or the `JOB_AGENT_LEADS_JSON` secret/input.
2. Removes duplicate jobs.
3. Scores each job against Christopher's strongest job profile:
   - AR
   - O2C
   - Credit Control
   - Collections
   - Billing
   - Reconciliation
   - Oracle Fusion
   - Power BI
   - UAE Finance Operations
4. Selects jobs with match score of 65 or above.
5. Sends selected jobs to Notion.
6. Marks 80+ jobs as `Apply Today`.
7. Recommends the correct CV version.
8. Creates recruiter and hiring manager message drafts inside the Notion job page.

## What the Agent Does Not Do

It does not:

- Log in to LinkedIn.
- Log in to NaukriGulf.
- Auto-apply to jobs.
- Auto-send LinkedIn messages.
- Bypass CAPTCHA or portal restrictions.
- Use your job portal passwords.

This protects your accounts from restrictions.

## GitHub Secrets Required

Go to:

`GitHub Repository > Settings > Secrets and variables > Actions > New repository secret`

Add these secrets:

```text
NOTION_API_KEY
NOTION_DATABASE_ID
NOTION_DATA_SOURCE_ID
OPENAI_API_KEY
```

Use these Notion IDs:

```text
NOTION_DATABASE_ID=434a49cfcbbd466b94a550143b942cec
NOTION_DATA_SOURCE_ID=4c7fd33c-2c0d-4d3f-820b-45a9e83a50fd
```

`OPENAI_API_KEY` is optional for the current rule-based version. It is included for future AI scoring.

## Daily Workflow

Every day at 8 AM UAE time, the workflow runs automatically:

```text
.github/workflows/daily-job-selection-agent.yml
```

You can also run it manually:

1. Open GitHub repository.
2. Click `Actions`.
3. Select `Daily UAE Finance Job Selection Agent`.
4. Click `Run workflow`.
5. Wait for the run to finish.
6. Open the Notion tracker.

## How to Feed Jobs Into the Agent

### Option 1: Manual JSON File

Create this file:

```text
job_agent/job_leads.json
```

Use this format:

```json
[
  {
    "title": "Credit Controller",
    "company": "Example Real Estate Group",
    "location": "Dubai, UAE",
    "source": "LinkedIn",
    "link": "https://example.com/jobs/credit-controller",
    "description": "Full job description here"
  }
]
```

Commit the file, then run the workflow.

### Option 2: External Scraper or Automation Tool

Use Apify, Make, Zapier, n8n, or another safe job collection tool to produce JSON using the same structure.

Then pass it into the workflow as `JOB_AGENT_LEADS_JSON` or write it to `job_agent/job_leads.json`.

## Where to See Results

Open Notion:

```text
Auto Job Selection Tracker
https://app.notion.com/p/434a49cfcbbd466b94a550143b942cec
```

Use these views:

- `Apply Today` = jobs you should apply for immediately.
- `High Match Jobs` = strongest fit jobs.
- `Follow Up Queue` = jobs needing recruiter follow-up.

## How to Apply

For every job in `Apply Today`:

1. Open the job link.
2. Check the JD once manually.
3. Use the recommended CV version.
4. Apply manually.
5. Copy the recruiter message from the Notion page.
6. Send it manually on LinkedIn or email.
7. Mark `Applied` in Notion.
8. Follow up after 3 days.

## Score Meaning

```text
80 to 100 = Apply Today
65 to 79 = Medium Priority
50 to 64 = Review Only
Below 50 = Skip
```

## Recommended CV Logic

```text
Senior AR/O2C CV:
Use for AR, O2C, Credit Control, Collections, DSO, Cash Application jobs.

Financial Controller CV:
Use for month-end, journals, reporting, reconciliation, audit support jobs.

Finance Admin CV:
Use for invoicing, payment follow-up, documentation, admin, MIS jobs.
```

## Best Operating Rule

Do not apply randomly.

Use the agent to filter weak jobs. Apply only to jobs that match your strongest profile:

```text
AR + O2C + Credit Control + Collections + Billing + Reconciliation + Oracle Fusion + Power BI + UAE Finance Operations
```

## Troubleshooting

### Workflow fails with missing Notion key

Add `NOTION_API_KEY` in GitHub Actions secrets.

### Workflow runs but no jobs appear in Notion

Check:

1. `job_agent/job_leads.json` exists.
2. Job score is 65 or above.
3. Notion database ID is correct.
4. Notion integration has access to the database.

### Too many weak jobs selected

Increase this value in the workflow:

```text
JOB_AGENT_MIN_SCORE_TO_SAVE=75
```

### Too few jobs selected

Lower it to:

```text
JOB_AGENT_MIN_SCORE_TO_SAVE=60
```

## Final Operating Boundary

Automatic:

```text
Find jobs > score jobs > select jobs > update Notion > prepare messages
```

Manual:

```text
Apply > upload CV > send LinkedIn messages > speak to recruiter > attend interview
```
