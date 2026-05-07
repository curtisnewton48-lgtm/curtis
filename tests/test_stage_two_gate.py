from types import SimpleNamespace

from career_agent.agent import CareerSearchAgent


def _agent() -> CareerSearchAgent:
    config = SimpleNamespace(
        stage_two_min_fit_score=50,
        shortlist_practice_areas=["immigration law", "housing", "employment"],
    )
    return CareerSearchAgent(config, store=None, model=None)


def _job(**overrides: str) -> dict[str, str]:
    job = {
        "fit_score": "50",
        "application_deadline": "not stated",
        "deadline_status": "unclear",
        "eligibility_status": "probably_eligible",
        "explicit_disqualifiers": "none found",
        "role_level": "paralegal",
        "practice_area_match": "exact",
        "candidate_evidence_match": "strong",
        "practice_area": "immigration law",
        "fit_summary": "Strong match for immigration law casework experience.",
        "raw_description": "Paralegal role in an immigration law team.",
    }
    job.update(overrides)
    return job


def test_stage_two_gate_accepts_strong_eligible_match() -> None:
    assert _agent()._is_stage_two_candidate(_job())


def test_stage_two_gate_rejects_not_eligible_job() -> None:
    assert not _agent()._is_stage_two_candidate(_job(eligibility_status="not_eligible"))


def test_stage_two_gate_rejects_explicit_disqualifier() -> None:
    assert not _agent()._is_stage_two_candidate(
        _job(explicit_disqualifiers="Requires completed LPC and 2 years PQE.")
    )


def test_stage_two_gate_rejects_weak_candidate_evidence() -> None:
    assert not _agent()._is_stage_two_candidate(_job(candidate_evidence_match="weak"))
