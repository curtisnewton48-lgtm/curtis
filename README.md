# Career Search Agent

A scheduled AI agent that reads your career profile from Google Sheets, finds UK legal-sector opportunities, researches each firm from the available posting context, scores roles against your preferences, and writes ranked recommendations back to your tracker.

Tracker created in your Google Drive:

https://docs.google.com/spreadsheets/d/1LllF4mn8sg1CtsTwmJ9Tbmw0ABg2bPflYilpMbsmz2c/edit

Firm research document:

https://docs.google.com/document/d/1vqIEkoUoNTlbNAO-jvxWqkxDeiUrzpfeexIJwiUE8vQ/edit

## What It Does

- Reads `Profile`, `TargetCompanies`, and `Settings` tabs from Google Sheets.
- Searches UK roles for paralegal, trainee solicitor, and caseworker positions with Adzuna.
- Pulls additional postings from configurable RSS feeds and career-page URLs.
- Deduplicates jobs by URL/title/company.
- Uses OpenAI or Mistral to score each job, extract application deadlines, and assess eligibility.
- Writes role title, deadline, eligibility, and application-tracking fields to the `Jobs` tab.
- Writes longer firm research notes to the Google Doc.
- Leaves applications and outbound messages under human approval.

## Quick Start

1. Create API credentials:
   - OpenAI: set `OPENAI_API_KEY`, or
   - Mistral: set `MISTRAL_API_KEY`.
2. Create Adzuna API credentials at https://developer.adzuna.com/ and set `ADZUNA_APP_ID` and `ADZUNA_APP_KEY`.
3. Create Google service account credentials with access to the tracker Sheet and firm research Doc.
4. Share both Google files with the service account email.
5. Copy `.env.example` to `.env` and fill in the values.
6. Install dependencies:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

On Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

7. Run once:

```bash
python -m career_agent.main
```

## GitHub Deployment

This repo includes `.github/workflows/daily-career-agent.yml`, which runs the agent once per day.

Add these GitHub repository secrets:

- `GOOGLE_SERVICE_ACCOUNT_JSON`
- `GOOGLE_SHEET_ID`
- `GOOGLE_RESEARCH_DOC_ID`
- `MODEL_PROVIDER`
- `MODEL_NAME`
- `OPENAI_API_KEY` if using OpenAI
- `MISTRAL_API_KEY` if using Mistral
- `ADZUNA_APP_ID`
- `ADZUNA_APP_KEY`

Recommended default:

```text
MODEL_PROVIDER=openai
MODEL_NAME=gpt-5.4-mini
GOOGLE_SHEET_ID=1LllF4mn8sg1CtsTwmJ9Tbmw0ABg2bPflYilpMbsmz2c
GOOGLE_RESEARCH_DOC_ID=1vqIEkoUoNTlbNAO-jvxWqkxDeiUrzpfeexIJwiUE8vQ
```

Mistral option:

```text
MODEL_PROVIDER=mistral
MODEL_NAME=mistral-medium-3.5
```

## Sheet Setup

Fill in:

- `Profile`: your resume text, target roles, locations, salary, dealbreakers.
- `TargetCompanies`: optional firm names and careers URLs for extra direct-source checks.
- `Settings`: model provider, model name, max jobs per run.

The agent writes to `Jobs`, including role title, application deadline, eligibility, practice-area clues, role type, fit score, risks, and tailored pitch. Longer firm research is appended to the research Google Doc. You manually move serious opportunities into `Applications` when you apply.

## Safety

The agent does not apply to jobs, email recruiters, or mutate application status without you. It only researches, scores, drafts, and tracks.
