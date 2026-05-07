from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    google_sheet_id: str
    google_research_doc_id: str
    google_research_folder_id: str
    model_provider: str
    model_name: str
    stage_two_model_name: str
    max_jobs_per_run: int
    max_jobs_per_month: int
    min_fit_score: int
    stage_two_min_fit_score: int
    job_queries: list[str]
    shortlist_practice_areas: list[str]
    adzuna_country: str
    adzuna_where: str
    adzuna_results_per_query: int
    reed_location: str
    reed_results_per_query: int
    google_search_sites: list[str]
    google_search_results_per_site: int


def load_config() -> Config:
    load_dotenv()
    sheet_id = os.getenv("GOOGLE_SHEET_ID", "").strip()
    if not sheet_id:
        raise RuntimeError("GOOGLE_SHEET_ID is required.")
    research_doc_id = os.getenv("GOOGLE_RESEARCH_DOC_ID", "").strip()
    research_folder_id = os.getenv("GOOGLE_RESEARCH_FOLDER_ID", "").strip()

    provider = os.getenv("MODEL_PROVIDER", "gemini").strip().lower()
    default_model = {
        "openai": "gpt-5.4-mini",
        "gemini": "gemini-3-flash-preview",
        "mistral": "mistral-medium-3.5",
    }.get(provider, "gemini-3-flash-preview")

    return Config(
        google_sheet_id=sheet_id,
        google_research_doc_id=research_doc_id,
        google_research_folder_id=research_folder_id,
        model_provider=provider,
        model_name=os.getenv("MODEL_NAME", default_model).strip(),
        stage_two_model_name=os.getenv("STAGE_TWO_MODEL_NAME", "gemini-3.1-pro-preview").strip(),
        max_jobs_per_run=int(os.getenv("MAX_JOBS_PER_RUN", "20")),
        max_jobs_per_month=int(os.getenv("MAX_JOBS_PER_MONTH", "300")),
        min_fit_score=int(os.getenv("MIN_FIT_SCORE", "65")),
        stage_two_min_fit_score=int(os.getenv("STAGE_TWO_MIN_FIT_SCORE", "70")),
        job_queries=[
            query.strip()
            for query in os.getenv(
                "JOB_QUERIES",
                "paralegal, trainee solicitor, legal caseworker, immigration caseworker, housing caseworker",
            ).split(",")
            if query.strip()
        ],
        shortlist_practice_areas=[
            area.strip().lower()
            for area in os.getenv(
                "SHORTLIST_PRACTICE_AREAS",
                "private client, wills, employment, antitrust, competition law, human rights, eu law, immigration law, real estate, housing, international law",
            ).split(",")
            if area.strip()
        ],
        adzuna_country=os.getenv("ADZUNA_COUNTRY", "gb").strip().lower(),
        adzuna_where=os.getenv("ADZUNA_WHERE", "United Kingdom").strip(),
        adzuna_results_per_query=int(os.getenv("ADZUNA_RESULTS_PER_QUERY", "25")),
        reed_location=os.getenv("REED_LOCATION", "United Kingdom").strip(),
        reed_results_per_query=int(os.getenv("REED_RESULTS_PER_QUERY", "20")),
        google_search_sites=[
            site.strip()
            for site in os.getenv(
                "GOOGLE_SEARCH_SITES",
                "legalcheek.com, lawcareers.net, jobs.lawgazette.co.uk, totallylegal.com, jobs.ac.uk, charityjob.co.uk, civilservicejobs.service.gov.uk, indeed.com",
            ).split(",")
            if site.strip()
        ],
        google_search_results_per_site=int(os.getenv("GOOGLE_SEARCH_RESULTS_PER_SITE", "3")),
    )
