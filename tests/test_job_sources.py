from career_agent.job_sources import stable_job_id


def test_stable_job_id_is_repeatable() -> None:
    first = stable_job_id("Acme", "Product Manager", "https://example.com/job/1")
    second = stable_job_id("Acme", "Product Manager", "https://example.com/job/1")
    assert first == second
    assert len(first) == 16
