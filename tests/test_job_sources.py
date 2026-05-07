from career_agent.job_sources import _is_search_job_result, stable_job_id


def test_stable_job_id_is_repeatable() -> None:
    first = stable_job_id("Acme", "Product Manager", "https://example.com/job/1")
    second = stable_job_id("Acme", "Product Manager", "https://example.com/job/1")
    assert first == second
    assert len(first) == 16


def test_search_filter_rejects_legal_cheek_advice_articles() -> None:
    assert not _is_search_job_result(
        "49 tips to succeed as a candidate - Legal Cheek",
        "https://www.legalcheek.com/2026/01/49-tips-to-succeed-as-a-candidate/",
        "Advice for candidates applying for vacation schemes and training contracts.",
        "trainee solicitor",
    )


def test_search_filter_keeps_real_legal_vacancies() -> None:
    assert _is_search_job_result(
        "Paralegal vacancy - Immigration team",
        "https://examplelaw.com/careers/paralegal-immigration",
        "Apply by 31 May 2026. Salary and eligibility requirements listed.",
        "paralegal",
    )
