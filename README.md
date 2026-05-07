# Career Search Agent

A scheduled AI agent that reads your career profile from Google Sheets, finds job opportunities from configured sources, scores them against your preferences, and writes ranked recommendations back to your tracker.

Tracker created in your Google Drive:

https://docs.google.com/spreadsheets/d/1LllF4mn8sg1CtsTwmJ9Tbmw0ABg2bPflYilpMbsmz2c/edit

## What It Does

- Reads `Profile`, `TargetCompanies`, and `Settings` tabs from Google Sheets.
- Pulls job postings from configurable RSS feeds and career-page URLs.
- Deduplicates jobs by URL/title/company.
- Uses OpenAI or Mistral to score each job.
- Writes results to the `Jobs` tab.
- Leaves applications and outbound messages under human approval.

## Quick Start

1. Create API credentials:
   - OpenAI: set `OPENAI_API_KEY`, or
   - Mistral: set `MISTRAL_API_KEY`.
2. Create Google service account credentials with access to the tracker Sheet.
3. Share the Google Sheet with the service account email.
4. Copy `.env.example` to `.env` and fill in the values.
5. Install dependencies:

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

6. Run once:

```bash
python -m career_agent.main
```

## GitHub Deployment

This repo includes `.github/workflows/daily-career-agent.yml`, which runs the agent once per day.

Add these GitHub repository secrets:

- `GOOGLE_SERVICE_ACCOUNT_JSON`
- `GOOGLE_SHEET_ID`
- `MODEL_PROVIDER`
- `MODEL_NAME`
- `OPENAI_API_KEY` if using OpenAI
- `MISTRAL_API_KEY` if using Mistral

Recommended default:

```text
MODEL_PROVIDER=openai
MODEL_NAME=gpt-5.4-mini
```

Mistral option:

```text
MODEL_PROVIDER=mistral
MODEL_NAME=mistral-medium-3.5
```

## Sheet Setup

Fill in:

- `Profile`: your resume text, target roles, locations, salary, dealbreakers.
- `TargetCompanies`: company name and careers URL.
- `Settings`: model provider, model name, max jobs per run.

The agent writes to `Jobs`. You manually move serious opportunities into `Applications` when you apply.

## Safety

The agent does not apply to jobs, email recruiters, or mutate application status without you. It only researches, scores, drafts, and tracks.
