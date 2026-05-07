from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

from career_agent.config import Config
from career_agent.job_sources import (
    fetch_adzuna_jobs,
    fetch_brave_search_jobs,
    fetch_google_search_jobs,
    fetch_jobs_for_company,
    fetch_reed_jobs,
)
from career_agent.models import ModelClient
from career_agent.sheets import DocsStore, SheetsStore


class CareerSearchAgent:
    def __init__(
        self,
        config: Config,
        store: SheetsStore,
        model: ModelClient,
        stage_two_model: ModelClient | None = None,
        docs: DocsStore | None = None,
    ) -> None:
        self.config = config
        self.store = store
        self.model = model
        self.stage_two_model = stage_two_model or model
        self.docs = docs

    def run(self) -> dict[str, int]:
        profile = self.store.profile()
        companies = self.store.target_companies()
        existing_ids = self.store.existing_job_ids()
        monthly_remaining = self.config.max_jobs_per_month - self.store.current_month_job_count()
        run_limit = max(0, min(self.config.max_jobs_per_run, monthly_remaining))
        if run_limit == 0:
            return {
                "companies_checked": len(companies),
                "jobs_discovered": 0,
                "new_jobs_scored": 0,
                "shortlisted_for_stage_two": 0,
                "monthly_remaining": 0,
            }

        discovered = self._discover(companies)
        fresh_jobs = _select_diverse_fresh_jobs(discovered, existing_ids, run_limit)

        scored = []
        for job in fresh_jobs:
            fit = self.model.score_job(profile, job)
            job["fit_score"] = fit.score
            job["role_type"] = fit.role_type
            job["practice_area"] = fit.practice_area
            job["application_deadline"] = fit.application_deadline
            job["deadline_status"] = fit.deadline_status
            job["eligibility"] = _eligibility_note(fit)
            job["fit_summary"] = fit.summary
            job["risks"] = _risk_note(fit)
            job["recommended_action"] = fit.recommended_action
            job["tailored_pitch"] = fit.tailored_pitch
            job["eligibility_status"] = fit.eligibility_status
            job["role_level"] = fit.role_level
            job["practice_area_match"] = fit.practice_area_match
            job["candidate_evidence_match"] = fit.candidate_evidence_match
            job["explicit_disqualifiers"] = fit.explicit_disqualifiers
            job["stage_two_reason"] = fit.stage_two_reason
            job["shortlisted"] = "yes" if self._is_stage_two_candidate(job) else "no"

            if job["shortlisted"] == "yes" and self.docs:
                research = self.stage_two_model.deep_research(profile, job)
                job["research_doc_url"] = self.docs.create_research_doc(
                    research.title,
                    research.content,
                )

            job.update(
                {
                    "status": "shortlisted"
                    if job["shortlisted"] == "yes"
                    else "review"
                    if fit.score >= self.config.min_fit_score
                    else "low_fit",
                }
            )
            scored.append(job)

        self.store.append_jobs(scored)
        return {
            "companies_checked": len(companies),
            "jobs_discovered": len(discovered),
            "new_jobs_scored": len(scored),
            "shortlisted_for_stage_two": sum(1 for job in scored if job.get("shortlisted") == "yes"),
            "monthly_remaining": max(0, monthly_remaining - len(scored)),
            "reed_discovered": _count_source(discovered, "reed"),
            "brave_discovered": _count_source(discovered, "brave_search"),
            "adzuna_discovered": _count_source(discovered, "adzuna"),
            "google_discovered": _count_source(discovered, "google_search"),
            "direct_discovered": _count_source(discovered, "direct"),
        }

    def _discover(self, companies: list[dict[str, str]]) -> list[dict[str, str]]:
        jobs = fetch_adzuna_jobs(
            queries=self.config.job_queries,
            country=self.config.adzuna_country,
            where=self.config.adzuna_where,
            results_per_query=self.config.adzuna_results_per_query,
        )
        jobs.extend(
            fetch_reed_jobs(
                queries=self.config.job_queries,
                location=self.config.reed_location,
                results_per_query=self.config.reed_results_per_query,
            )
        )
        jobs.extend(
            fetch_google_search_jobs(
                queries=self.config.job_queries,
                sites=self.config.google_search_sites,
                results_per_site=self.config.google_search_results_per_site,
            )
        )
        jobs.extend(
            fetch_brave_search_jobs(
                queries=self.config.job_queries,
                sites=self.config.brave_search_sites,
                results_per_site=self.config.brave_search_results_per_site,
            )
        )
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

    def _is_stage_two_candidate(self, job: dict[str, str]) -> bool:
        if int(job.get("fit_score") or 0) < self.config.stage_two_min_fit_score:
            return False
        if _deadline_expired(job.get("application_deadline", ""), job.get("deadline_status", "")):
            return False
        if _normalise_label(job.get("eligibility_status", "")) == "not_eligible":
            return False
        if _has_explicit_disqualifier(job.get("explicit_disqualifiers", "")):
            return False
        if _normalise_label(job.get("role_level", "")) not in _STAGE_TWO_ROLE_LEVELS:
            return False
        if _normalise_label(job.get("practice_area_match", "")) not in {"exact", "related"}:
            return False
        if _normalise_label(job.get("candidate_evidence_match", "")) not in {"strong", "medium"}:
            return False
        practice_area = (job.get("practice_area") or "").lower()
        summary = (job.get("fit_summary") or "").lower()
        description = (job.get("raw_description") or "").lower()
        haystack = " ".join([practice_area, summary, description])
        return any(area in haystack for area in self.config.shortlist_practice_areas)


_STAGE_TWO_ROLE_LEVELS = {
    "paralegal",
    "legal_assistant",
    "trainee_solicitor",
    "caseworker",
    "vacation_scheme",
    "training_contract",
    "graduate_scheme",
    "unclear",
}


def _eligibility_note(fit: object) -> str:
    parts = [
        getattr(fit, "eligibility", ""),
        f"Eligibility status: {getattr(fit, 'eligibility_status', 'unclear')}",
        f"Role level: {getattr(fit, 'role_level', 'unclear')}",
        f"Degree requirement: {getattr(fit, 'degree_requirement', 'not stated')}",
        f"SQE/LPC requirement: {getattr(fit, 'sqe_lpc_requirement', 'not stated')}",
        f"Work authorisation: {getattr(fit, 'work_authorisation', 'not stated')}",
        f"Application route: {getattr(fit, 'application_route', 'not stated')}",
    ]
    return " | ".join(part for part in parts if str(part).strip())


def _risk_note(fit: object) -> str:
    parts = [
        getattr(fit, "risks", ""),
        f"Practice area match: {getattr(fit, 'practice_area_match', 'unclear')}",
        f"Candidate evidence match: {getattr(fit, 'candidate_evidence_match', 'unclear')}",
        f"Explicit disqualifiers: {getattr(fit, 'explicit_disqualifiers', 'none found')}",
        f"Stage 2 reason: {getattr(fit, 'stage_two_reason', '')}",
    ]
    return " | ".join(part for part in parts if str(part).strip())


def _normalise_label(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (value or "").strip().lower()).strip("_") or "unclear"


def _has_explicit_disqualifier(value: str) -> bool:
    lowered = (value or "").strip().lower()
    return bool(lowered and lowered not in {"none", "none found", "not stated", "n/a", "no", "unclear"})


def _deadline_expired(deadline: str, status: str) -> bool:
    if status.lower() == "expired":
        return True
    dates = re.findall(r"\b(\d{4}-\d{2}-\d{2})\b", deadline or "")
    if not dates:
        return False
    try:
        parsed = datetime.fromisoformat(dates[0]).replace(tzinfo=timezone.utc)
    except ValueError:
        return False
    return parsed.date() < datetime.now(timezone.utc).date()


def _select_diverse_fresh_jobs(
    jobs: list[dict[str, str]],
    existing_ids: set[str],
    limit: int,
) -> list[dict[str, str]]:
    buckets: dict[str, list[dict[str, str]]] = {}
    seen = set(existing_ids)
    for job in jobs:
        job_id = job.get("job_id", "")
        if not job_id or job_id in seen:
            continue
        seen.add(job_id)
        buckets.setdefault(_source_family(job), []).append(job)

    priority = ["brave_search", "reed", "adzuna", "google_search", "direct", "error"]
    selected = []
    while len(selected) < limit and any(buckets.values()):
        for family in priority:
            if len(selected) >= limit:
                break
            bucket = buckets.get(family) or []
            if bucket:
                selected.append(bucket.pop(0))
        for family in list(buckets):
            if len(selected) >= limit:
                break
            if family not in priority and buckets[family]:
                selected.append(buckets[family].pop(0))
    return selected


def _source_family(job: dict[str, str]) -> str:
    source = (job.get("source") or "").lower()
    if source.startswith("brave_search"):
        return "brave_search"
    if source.startswith("reed"):
        return "reed"
    if source.startswith("adzuna"):
        return "adzuna"
    if source.startswith("google_search"):
        return "google_search"
    if source in {"rss", "career_page"}:
        return "direct"
    if source == "error":
        return "error"
    return source.split(":", 1)[0] or "unknown"


def _count_source(jobs: list[dict[str, str]], family: str) -> int:
    return sum(1 for job in jobs if _source_family(job) == family)
