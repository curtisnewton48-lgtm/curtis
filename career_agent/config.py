from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    google_sheet_id: str
    google_research_doc_id: str
    model_provider: str
    model_name: str
    max_jobs_per_run: int
    min_fit_score: int
    job_queries: list[str]
    adzuna_country: str
    adzuna_where: str
    adzuna_results_per_query: int


def load_config() -> Config:
    load_dotenv()
    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    if not sheet_id:
        raise RuntimeError("GOOGLE_SHEET_ID is required.")
    research_doc_id = os.getenv("GOOGLE_RESEARCH_DOC_ID", "").strip()

    provider = os.getenv("MODEL_PROVIDER", "openai").strip().lower()
    default_model = "gpt-5.4-mini" if provider == "openai" else "mistral-medium-3.5"

    return Config(
        google_sheet_id=sheet_id,
        google_research_doc_id=research_doc_id,
        model_provider=provider,
        model_name=os.getenv("MODEL_NAME", default_model).strip(),
        max_jobs_per_run=int(os.getenv("MAX_JOBS_PER_RUN", "50")),
        min_fit_score=int(os.getenv("MIN_FIT_SCORE", "65")),
        job_queries=[
            query.strip()
            for query in os.getenv(
                "JOB_QUERIES",
                "paralegal, trainee solicitor, legal caseworker, immigration caseworker, housing caseworker",
            ).split(",")
            if query.strip()
        ],
        adzuna_country=os.getenv("ADZUNA_COUNTRY", "gb").strip().lower(),
        adzuna_where=os.getenv("ADZUNA_WHERE", "United Kingdom").strip(),
        adzuna_results_per_query=int(os.getenv("ADZUNA_RESULTS_PER_QUERY", "25")),
    )
