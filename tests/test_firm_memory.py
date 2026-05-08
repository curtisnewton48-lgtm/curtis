from types import SimpleNamespace

from career_agent.agent import CareerSearchAgent
from career_agent.sheets import normalize_company_name


class FakeStore:
    def __init__(self, memory: dict[str, str] | None = None) -> None:
        self.appended_jobs = []
        self.memory = memory if memory is not None else {"acme": "https://docs.google.com/document/d/existing/edit"}

    def profile(self) -> dict[str, str]:
        return {"name": "Curtis Newton"}

    def target_companies(self) -> list[dict[str, str]]:
        return []

    def existing_job_ids(self) -> set[str]:
        return set()

    def research_memory_by_company(self) -> dict[str, str]:
        return self.memory

    def current_month_job_count(self) -> int:
        return 0

    def append_jobs(self, jobs: list[dict[str, str]]) -> None:
        self.appended_jobs = jobs


class FakeModel:
    def __init__(self) -> None:
        self.deep_research_calls = 0

    def score_job(self, profile: dict[str, str], job: dict[str, str]) -> SimpleNamespace:
        return SimpleNamespace(
            score=50,
            role_type="paralegal",
            practice_area="immigration law",
            application_deadline="not stated",
            deadline_status="unclear",
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

    def verify_job(self, profile: dict[str, str], job: dict[str, str]) -> SimpleNamespace:
        return SimpleNamespace(
            is_real_job=True,
            deadline_correct=True,
            location_correct=True,
            salary_experience_accurate=True,
            firm_exists=True,
            job_still_open=True,
            accept_for_stage_two=True,
            confidence=90,
            corrected_deadline="not stated",
            corrected_location="not stated",
            corrected_salary_or_experience="not stated",
            evidence="Test role appears active.",
            risks="No verification risks found.",
        )

    def deep_research(self, profile: dict[str, str], job: dict[str, str]) -> SimpleNamespace:
        self.deep_research_calls += 1
        return SimpleNamespace(
            title="Acme LLP - Immigration Paralegal Research",
            content="Comprehensive firm research for Acme LLP.",
        )


class FakeDocs:
    def __init__(self) -> None:
        self.created_docs = []

    def create_research_doc(self, title: str, content: str) -> str:
        self.created_docs.append({"title": title, "content": content})
        return "https://docs.google.com/document/d/new/edit"


class MemoryAgent(CareerSearchAgent):
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


def test_normalize_company_name_removes_common_suffixes() -> None:
    assert normalize_company_name("Acme Solicitors LLP") == "acme"


def test_stage_two_reuses_existing_firm_research_doc() -> None:
    store = FakeStore()
    stage_two_model = FakeModel()
    docs = FakeDocs()
    agent = MemoryAgent(_config(), store, FakeModel(), stage_two_model, docs)

    result = agent.run()

    assert result["shortlisted_for_stage_two"] == 1
    assert store.appended_jobs[0]["research_doc_url"] == "https://docs.google.com/document/d/existing/edit"
    assert "reused existing research document" in store.appended_jobs[0]["risks"]
    assert stage_two_model.deep_research_calls == 0
    assert docs.created_docs == []


def test_stage_two_creates_research_doc_when_no_memory_exists() -> None:
    store = FakeStore(memory={})
    stage_two_model = FakeModel()
    docs = FakeDocs()
    agent = MemoryAgent(_config(), store, FakeModel(), stage_two_model, docs)

    result = agent.run()

    assert result["shortlisted_for_stage_two"] == 1
    assert stage_two_model.deep_research_calls == 1
    assert docs.created_docs == [
        {
            "title": "Acme LLP - Immigration Paralegal Research",
            "content": "Comprehensive firm research for Acme LLP.",
        }
    ]
    assert store.appended_jobs[0]["research_doc_url"] == "https://docs.google.com/document/d/new/edit"
