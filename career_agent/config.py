from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    google_sheet_id: str
    model_provider: str
    model_name: str
    max_jobs_per_run: int
    min_fit_score: int


def load_config() -> Config:
    load_dotenv()
    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    if not sheet_id:
        raise RuntimeError("GOOGLE_SHEET_ID is required.")

    provider = os.getenv("MODEL_PROVIDER", "openai").strip().lower()
    default_model = "gpt-5.4-mini" if provider == "openai" else "mistral-medium-3.5"

    return Config(
        google_sheet_id=sheet_id,
        model_provider=provider,
        model_name=os.getenv("MODEL_NAME", default_model).strip(),
        max_jobs_per_run=int(os.getenv("MAX_JOBS_PER_RUN", "50")),
        min_fit_score=int(os.getenv("MIN_FIT_SCORE", "65")),
    )
