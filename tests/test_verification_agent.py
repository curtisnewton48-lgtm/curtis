from types import SimpleNamespace

from career_agent.agent import CareerSearchAgent


class FakeStore:
    def __init__(self) -> None:
        self.appended_jobs = []

    def profile(self) -> dict[str, str]:
        return {"name": "Curtis Newton"}

    def target_companies(self) -> list[dict[str, str]]:
        return []

    def existing_job_ids(self) -> set[str]:
        return set()

    def research_memory_by_company(self) -> dict[str, str]:
        return {}

    def current_month_job_count(self) -> int:
        return 0

    def append_jobs(self, jobs: list[dict[str, str]]) -> None:
        self.appended_jobs = jobs


class ScoringModel:
    def score_job(self, profile: dict[str, str], job: dict[str, str]) -> SimpleNamespace:
        return SimpleNamespace(
            score=80,
            role_type="paralegal",
            practice_area="immigration law",
            application_deadline="2026-06-01",
            deadline_status="active",
            eligibility="not stated",
            eligibility_status="probably_eligible",
            role_level="paralegal",
            degree_requirement="law degree preferred",
            sqe_lpc_requirement="not stated",
            work_authorisation="not stated",
            application_route="direct",
            explicit_disqualifiers="none found",
            practice_area_match="exact",
            candidate_evidence_match="strong",
            stage_two_reason="Strong legal casework match.",
            summary="Strong match.",
            risks="",
            recommended_action="Apply.",
            tailored_pitch="Client-facing casework experience.",
        )


class BlockingVerificationModel:
    def verify_job(self, profile: dict[str, str], job: dict[str, str]) -> SimpleNamespace:
        return SimpleNamespace(
            is_real_job=False,
            deadline_correct=False,
            location_correct=True,
            salary_experience_accurate=True,
            firm_exists=True,
            job_still_open=False,
            accept_for_stage_two=False,
            confidence=88,
            corrected_deadline="not stated",
            corrected_location="not stated",
            corrected_salary_or_experience="not stated",
            evidence="The source appears to be an article rather than an open vacancy.",
            risks="Likely not a current application page.",
        )


class FakeDocs:
    def create_research_doc(self, title: str, content: str) -> str:
        raise AssertionError("Stage 2 research should not run when verification blocks the job.")


class VerificationAgent(CareerSearchAgent):
    def _discover(self, companies: list[dict[str, str]]) -> list[dict[str, str]]:
        return [
            {
                "job_id": "job-1",
                "title": "Immigration Paralegal",
                "company": "Acme LLP",
                "location": "London",
                "raw_description": "Immigration law paralegal role.",
                "source": "test",
            }
        ]


def _config() -> SimpleNamespace:
    return SimpleNamespace(
        max_jobs_per_month=300,
        max_jobs_per_run=20,
        min_fit_score=65,
        stage_two_min_fit_score=50,
        shortlist_practice_areas=["immigration law"],
    )


def test_verification_blocks_stage_two_research() -> None:
    store = FakeStore()
    agent = VerificationAgent(
        _config(),
        store,
        ScoringModel(),
        ScoringModel(),
        FakeDocs(),
        BlockingVerificationModel(),
    )

    result = agent.run()

    assert result["shortlisted_for_stage_two"] == 0
    assert store.appended_jobs[0]["shortlisted"] == "no"
    assert "Blocked by verification micro-agent" in store.appended_jobs[0]["stage_two_reason"]
    assert "Verification: accepted=False" in store.appended_jobs[0]["risks"]
