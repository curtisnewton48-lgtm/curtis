# Career Search Agent

A scheduled cloud agent that runs from GitHub Actions every morning at 09:00 GMT. Stage 1 uses Gemini 3 Flash and Adzuna to find UK legal-sector opportunities, extract deadlines and requirements, and write them to Google Sheets. Shortlisted jobs then move to Stage 2, which creates one comprehensive Google Doc research file per firm/job.

Tracker created in your Google Drive:

https://docs.google.com/spreadsheets/d/1LllF4mn8sg1CtsTwmJ9Tbmw0ABg2bPflYilpMbsmz2c/edit

Legacy firm research document:

https://docs.google.com/document/d/1vqIEkoUoNTlbNAO-jvxWqkxDeiUrzpfeexIJwiUE8vQ/edit

## What It Does

- Reads `Profile`, `TargetCompanies`, and `Settings` tabs from Google Sheets.
- Searches UK roles for paralegal, trainee solicitor, and caseworker positions with Adzuna.
- Pulls additional postings from configurable RSS feeds and career-page URLs.
- Deduplicates jobs by URL/title/company.
- Uses Gemini 3 Flash to extract role title, location, salary, deadline, requirements, eligibility, practice area, and first-pass fit score.
- Writes application-tracking fields to the `Jobs` tab.
- Shortlists active jobs in target practice areas.
- Uses Gemini 3.1 Pro for one comprehensive Google Doc per shortlisted firm/job.
- Leaves applications and outbound messages under human approval.

## Limits

- Runs in GitHub Actions, not on this PC.
- Runs daily at 09:00 GMT.
- Processes at most 20 jobs per day.
- Processes at most 300 jobs per calendar month.
- Stage 2 only runs for shortlisted active jobs.

## Quick Start

1. Create a Gemini API key and set `GEMINI_API_KEY`.
2. Create Adzuna API credentials at https://developer.adzuna.com/ and set `ADZUNA_APP_ID` and `ADZUNA_APP_KEY`.
3. Create Google service account credentials with access to the tracker Sheet and your research Drive folder.
4. Share the Google Sheet and research folder with the service account email.
5. Add the GitHub repository secrets listed below.

## GitHub Deployment

This repo includes `.github/workflows/daily-career-agent.yml`, which runs the agent once per day.

Add these GitHub repository secrets:

- `GOOGLE_SERVICE_ACCOUNT_JSON`
- `GOOGLE_SHEET_ID`
- `GOOGLE_RESEARCH_FOLDER_ID`
- `MODEL_PROVIDER`
- `MODEL_NAME`
- `STAGE_TWO_MODEL_NAME`
- `GEMINI_API_KEY`
- `ADZUNA_APP_ID`
- `ADZUNA_APP_KEY`

Recommended defaults:

```text
MODEL_PROVIDER=gemini
MODEL_NAME=gemini-3-flash-preview
STAGE_TWO_MODEL_NAME=gemini-3.1-pro-preview
GOOGLE_SHEET_ID=1LllF4mn8sg1CtsTwmJ9Tbmw0ABg2bPflYilpMbsmz2c
MAX_JOBS_PER_RUN=20
MAX_JOBS_PER_MONTH=300
STAGE_TWO_MIN_FIT_SCORE=70
ADZUNA_RESULTS_PER_QUERY=20
```

## Shortlist Areas

Stage 2 runs only when a job appears active and matches one or more of:

```text
private client, wills, employment, antitrust, competition law, human rights, eu law, immigration law, real estate, housing, international law
```

## Stage 2 Research

Each shortlisted job gets an individual Google Doc covering:

- legal areas the firm advises on
- office locations
- culture and why to work there
- NQ retention rate
- NQ and trainee salary
- application process
- type of law firm
- clients, deals, and recent news
- firm structure
- training contract, SQE, and seats structure
- expectations of candidates
- use of AI and technology
- reviews

## Sheet Setup

Fill in:

- `Profile`: your resume text, target roles, locations, salary, dealbreakers.
- `TargetCompanies`: optional firm names and careers URLs for extra direct-source checks.
- `Settings`: model provider, model name, max jobs per run, monthly cap, and shortlist settings.

The agent writes to `Jobs`, including role title, application deadline, deadline status, eligibility, salary, location, practice-area clues, role type, fit score, risks, tailored pitch, shortlist status, and the Stage 2 research Doc URL.

## Safety

The agent does not apply to jobs, email recruiters, or mutate application status without you. It researches, scores, drafts, and tracks.
