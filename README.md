# Career Search Agent

A scheduled cloud agent that runs from GitHub Actions every morning at 09:00 GMT. Stage 1 uses Gemini 3 Flash plus multiple job sources to find UK legal-sector opportunities, extract deadlines and requirements, and write them to Google Sheets. Shortlisted jobs then move to Stage 2, which creates one comprehensive Google Doc research file per firm/job.

Tracker created in your Google Drive:

https://docs.google.com/spreadsheets/d/1LllF4mn8sg1CtsTwmJ9Tbmw0ABg2bPflYilpMbsmz2c/edit

Legacy firm research document:

https://docs.google.com/document/d/1vqIEkoUoNTlbNAO-jvxWqkxDeiUrzpfeexIJwiUE8vQ/edit

## What It Does

- Reads `Profile`, `TargetCompanies`, and `Settings` tabs from Google Sheets.
- Searches UK roles for paralegal, trainee solicitor, and caseworker positions with Adzuna, Reed, Google Programmable Search, and Brave Search.
- Looks across legal-specific sources such as Legal Cheek, LawCareers.Net, Law Gazette Jobs, TotallyLegal, jobs.ac.uk, charity legal roles, Civil Service Jobs, and Indeed search results.
- Pulls additional postings from configurable RSS feeds and career-page URLs.
- Deduplicates jobs by URL/title/company.
- Uses Gemini 3 Flash to extract role title, location, salary, deadline, requirements, eligibility, practice area, and first-pass fit score.
- Writes application-tracking fields to the `Jobs` tab.
- Shortlists active jobs in target practice areas.
- Reuses existing firm research docs when a later shortlisted job is from the same firm.
- Creates one comprehensive Google Doc per shortlisted firm/job for Stage 2 deep research.
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
3. Create a Reed Jobseeker API key at https://www.reed.co.uk/developers/jobseeker and set `REED_API_KEY`.
4. Optional but recommended for broad coverage: create a Google Programmable Search engine and set `GOOGLE_SEARCH_API_KEY` and `GOOGLE_SEARCH_ENGINE_ID`.
5. Optional but recommended if Google Search is blocked: create a Brave Search API key and set `BRAVE_SEARCH_API_KEY`.
6. Create Google service account credentials with access to the tracker Sheet and your research Drive folder.
7. Share the Google Sheet and research folder with the service account email.
8. Add the GitHub repository secrets listed below.

## GitHub Deployment

This repo includes `.github/workflows/daily-career-agent.yml`, which runs the agent once per day.

Add these GitHub repository secrets:

- `GOOGLE_SERVICE_ACCOUNT_JSON`
- `GOOGLE_SHEET_ID`
- `GOOGLE_RESEARCH_FOLDER_ID`
- `PROFILE_CONTEXT`
- `MODEL_PROVIDER`
- `MODEL_NAME`
- `GEMINI_API_KEY`
- `ADZUNA_APP_ID`
- `ADZUNA_APP_KEY`
- `REED_API_KEY`
- `GOOGLE_SEARCH_API_KEY`
- `GOOGLE_SEARCH_ENGINE_ID`
- `BRAVE_SEARCH_API_KEY`

Recommended defaults:

```text
MODEL_PROVIDER=gemini
MODEL_NAME=gemini-3-flash-preview
STAGE_TWO_MODEL_NAME=gemini-3.1-pro-preview
GOOGLE_SHEET_ID=1LllF4mn8sg1CtsTwmJ9Tbmw0ABg2bPflYilpMbsmz2c
MAX_JOBS_PER_RUN=20
MAX_JOBS_PER_MONTH=300
STAGE_TWO_MIN_FIT_SCORE=50
ADZUNA_RESULTS_PER_QUERY=20
REED_RESULTS_PER_QUERY=20
REED_LOCATION=United Kingdom
GOOGLE_SEARCH_RESULTS_PER_SITE=3
GOOGLE_SEARCH_SITES=legalcheek.com, lawcareers.net, jobs.lawgazette.co.uk, totallylegal.com, jobs.ac.uk, charityjob.co.uk, civilservicejobs.service.gov.uk, indeed.com
BRAVE_SEARCH_RESULTS_PER_SITE=5
BRAVE_SEARCH_SITES=legalcheek.com, lawcareers.net, jobs.lawgazette.co.uk, totallylegal.com, jobs.ac.uk, charityjob.co.uk, civilservicejobs.service.gov.uk, indeed.com
```

Recommended `PROFILE_CONTEXT` secret format:

```text
Name:
Education:
Target roles:
Location preferences:
Languages:
Relevant experience:
Key strengths:
Practice interests:
```

## Shortlist Areas

Stage 2 runs only when a job passes the stricter shortlist gate:

- fit score is at least `STAGE_TWO_MIN_FIT_SCORE`
- deadline is active or unclear, not expired
- eligibility is `eligible`, `probably_eligible`, or `unclear`
- there are no explicit disqualifiers
- role level is a relevant graduate legal role
- practice area match is `exact` or `related`
- candidate evidence match is `strong` or `medium`

The target practice areas are:

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

If the tracker already contains a research document for the same firm, the agent reuses that document link instead of spending Stage 2 tokens on duplicate firm research. The row's `Risks` field notes when firm memory was reused.

## Sheet Setup

Fill in:

- `Profile`: your resume text, target roles, locations, salary, dealbreakers.
- `TargetCompanies`: optional firm names and careers URLs for extra direct-source checks.
- `Settings`: model provider, model name, max jobs per run, monthly cap, and shortlist settings.

The agent writes to `Jobs`, including role title, application deadline, deadline status, eligibility, salary, location, practice-area clues, role type, fit score, risks, tailored pitch, shortlist status, and the Stage 2 research Doc URL.

## Safety

The agent does not apply to jobs, email recruiters, or mutate application status without you. It researches, scores, drafts, and tracks.
