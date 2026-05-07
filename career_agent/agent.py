from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

from career_agent.config import Config
from career_agent.job_sources import fetch_jobs_for_company
from career_agent.models import ModelClient
from career_agent.sheets import SheetsStore


class CareerSearchAgent:
    def __init__(self, config: Config, store: SheetsStore, model: ModelClient) -> None:
        self.config = config
        self.store = store
        self.model = model

    def run(self) -> dict[str, int]:
        profile = self.store.profile()
        companies = self.store.target_companies()
        existing_ids = self.store.existing_job_ids()

        discovered = self._discover(companies)
        fresh_jobs = [
            job for job in discovered if job["job_id"] not in existing_ids
        ][: self.config.max_jobs_per_run]

        scored = []
        for job in fresh_jobs:
            fit = self.model.score_job(profile, job)
            job.update(
                {
                    "fit_score": fit.score,
                    "fit_summary": fit.summary,
                    "risks": fit.risks,
                    "recommended_action": fit.recommended_action,
                    "tailored_pitch": fit.tailored_pitch,
                    "status": "recommended" if fit.score >= self.config.min_fit_score else "review",
                }
            )
            scored.append(job)

        self.store.append_jobs(scored)
        return {
            "companies_checked": len(companies),
            "jobs_discovered": len(discovered),
            "new_jobs_scored": len(scored),
        }

    def _discover(self, companies: list[dict[str, str]]) -> list[dict[str, str]]:
        jobs = []
        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = [executor.submit(fetch_jobs_for_company, company) for company in companies]
            for future in as_completed(futures):
                try:
                    jobs.extend(future.result())
                except Exception as exc:
                    jobs.append(
                        {
                            "job_id": f"source-error-{abs(hash(str(exc))) % 100000}",
                            "title": "Source fetch failed",
                            "company": "",
                            "location": "",
                            "remote": "",
                            "salary": "",
                            "url": "",
                            "date_posted": "",
                            "source": "error",
                            "status": "source_error",
                            "raw_description": str(exc),
                        }
                    )
        return jobs
