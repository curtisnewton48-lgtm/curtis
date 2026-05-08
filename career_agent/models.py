from __future__ import annotations

import json
import os
from typing import Any
from typing import Protocol

import httpx
from pydantic import BaseModel, Field, field_validator


class JobFit(BaseModel):
    score: int = Field(ge=0, le=100)
    role_type: str
    practice_area: str
    application_deadline: str
    deadline_status: str
    eligibility: str
    eligibility_status: str = "unclear"
    role_level: str = "unclear"
    degree_requirement: str = "not stated"
    sqe_lpc_requirement: str = "not stated"
    work_authorisation: str = "not stated"
    application_route: str = "not stated"
    explicit_disqualifiers: str = "none found"
    practice_area_match: str = "unclear"
    candidate_evidence_match: str = "unclear"
    stage_two_reason: str = ""
    summary: str
    risks: str
    recommended_action: str
    tailored_pitch: str


class FirmResearch(BaseModel):
    title: str
    content: str


class JobVerification(BaseModel):
    is_real_job: bool
    deadline_correct: bool
    location_correct: bool
    salary_experience_accurate: bool
    firm_exists: bool
    job_still_open: bool
    accept_for_stage_two: bool
    confidence: int = Field(ge=0, le=100)
    corrected_deadline: str = "not stated"
    corrected_location: str = "not stated"
    corrected_salary_or_experience: str = "not stated"
    evidence: str
    risks: str

    @field_validator("confidence", mode="before")
    @classmethod
    def _coerce_confidence(cls, value: object) -> int:
        if isinstance(value, float) and 0 <= value <= 1:
            return round(value * 100)
        if isinstance(value, (float, int)):
            return round(value)
        if isinstance(value, str):
            try:
                parsed = float(value.strip().rstrip("%"))
            except ValueError:
                return 0
            return round(parsed * 100) if 0 <= parsed <= 1 else round(parsed)
        return 0

    @field_validator(
        "corrected_deadline",
        "corrected_location",
        "corrected_salary_or_experience",
        "evidence",
        "risks",
        mode="before",
    )
    @classmethod
    def _coerce_text(cls, value: object) -> str:
        if value is None:
            return "not stated"
        if isinstance(value, str):
            return value
        return json.dumps(value, ensure_ascii=True)


class ModelClient(Protocol):
    def score_job(self, profile: dict[str, str], job: dict[str, str]) -> JobFit:
        ...

    def verify_job(self, profile: dict[str, str], job: dict[str, str]) -> JobVerification:
        ...

    def deep_research(self, profile: dict[str, str], job: dict[str, str]) -> FirmResearch:
        ...


STAGE_ONE_PROMPT = """You are Stage 1 of a UK legal career-search agent.
Extract and triage paralegal, trainee solicitor, and legal caseworker roles.
Return concise structured facts only. Do not do deep firm research.
Extract application deadline and eligibility requirements when present. Use "not stated" when not provided.
deadline_status must be one of: active, expired, not_stated, unclear.
eligibility_status must be one of: eligible, probably_eligible, unclear, not_eligible.
role_level must be one of: paralegal, legal_assistant, trainee_solicitor, caseworker, vacation_scheme, training_contract, graduate_scheme, other, unclear.
practice_area_match must be one of: exact, related, weak, none, unclear.
candidate_evidence_match must be one of: strong, medium, weak, none, unclear.
Only mark not_eligible when the listing contains a clear blocker, such as required qualification/status the candidate lacks, expired deadline, location/work authorisation barrier, or role seniority mismatch.
Treat missing eligibility information as unclear, not not_eligible.
Return only valid JSON with keys: score, role_type, role_level, practice_area, practice_area_match, application_deadline, deadline_status, eligibility, eligibility_status, degree_requirement, sqe_lpc_requirement, work_authorisation, application_route, explicit_disqualifiers, candidate_evidence_match, stage_two_reason, summary, risks, recommended_action, tailored_pitch."""

STAGE_TWO_PROMPT = """You are Stage 2 of a UK legal career-search agent for Curtis Newton, a first-class law graduate.
Create a comprehensive, application-ready firm and role research dossier for a shortlisted UK legal job. Use supplied job context and web-grounded information available to the model/tool. Do not invent facts; write "not found" where evidence is unavailable.
The dossier must be detailed enough that a strong 2026 legal applicant can use it without further routine research before tailoring a CV, cover letter, application form, or interview preparation.
Write in clear sections with concise but substantive notes, not vague summaries. Include practical application angles tied to Curtis's profile where possible.
At minimum cover:
1. Role snapshot: role title, firm/organisation, location, working pattern, salary, deadline, source URL, application route, and eligibility caveats.
2. Why this role is shortlisted: practice-area fit, candidate evidence fit, risks, and how Curtis should position himself.
3. Firm/organisation overview: type of firm or organisation, size/structure, UK and international office locations, and market positioning.
4. Legal areas advised on: especially private client, wills/probate, employment, competition/antitrust, human rights, EU law, immigration, real estate, housing, public/international law, and adjacent practices.
5. Culture and why work there: values, training style, supervision, inclusion, pro bono/social impact, and what a realistic applicant should know.
6. Training and progression: training contract/SQE/seats structure where relevant, paralegal progression, NQ retention, NQ salary, trainee salary, and any published development programmes.
7. Application process: stages, deadlines, tests/interviews, written exercises, assessment centres, documents required, and likely competencies.
8. Candidate expectations: academic requirements, legal work experience, commercial awareness, client skills, languages, right-to-work issues, and red flags.
9. Clients, matters, deals, cases, campaigns, or policy work: include recent examples where available.
10. Recent news: firm/organisation news, rankings, awards, expansion, lateral hires, financial performance, or regulatory/public-interest developments.
11. AI and technology: legal tech use, innovation, AI stance, case management systems, digital services, or "not found".
12. Reviews and reputation: Chambers/Legal 500/RollOnFriday/Glassdoor/Indeed/student forums where available, noting reliability and uncertainty.
13. Application strategy: a short tailored pitch, 5 CV/cover-letter keywords, 5 interview talking points, and 5 questions Curtis could ask them.
14. Verification notes: what should be manually checked before applying, especially deadline, eligibility, salary, and application portal.
Return only valid JSON with keys: title, content."""

VERIFICATION_PROMPT = """You are a cheap verification micro-agent for a UK legal career-search system.
Before expensive Stage 2 research runs, verify whether the shortlisted role appears real, current, and accurately represented.
Use the supplied job title, company, URL, source, description, deadline, salary, location, and extracted facts. Be strict but fair.
Check:
- Is the job a real vacancy or application page, not an advice article, index page, advert, or stale search result?
- Is the application deadline correct or at least not contradicted by the source text?
- Is the location correct or at least not contradicted by the source text?
- Is the salary/experience information accurate or at least not contradicted by the source text?
- Does the firm or organisation actually exist based on the supplied context?
- Is the job still open, or is there strong evidence it has closed/expired?
Set accept_for_stage_two to false if the role is likely fake, closed, an article, a non-vacancy page, has a clearly expired deadline, or has a major factual contradiction.
Do not treat a fixed-term contract end date as an application deadline or proof that the job is closed. If a date is clearly a contract end date, set deadline_correct=false only if the supplied application_deadline mislabeled it, keep job_still_open=true unless the vacancy page says applications are closed, and explain the correction in risks.
Do not reject a role merely because it is home-based, remote, hybrid, or has a broader location than the tracker extracted. Correct the location and keep accept_for_stage_two true unless the location creates a clear eligibility or commute barrier.
When the evidence is incomplete but not contradicted, keep the relevant correctness field true and explain uncertainty in risks.
Return only valid JSON with keys: is_real_job, deadline_correct, location_correct, salary_experience_accurate, firm_exists, job_still_open, accept_for_stage_two, confidence, corrected_deadline, corrected_location, corrected_salary_or_experience, evidence, risks."""


def build_user_prompt(profile: dict[str, str], job: dict[str, str]) -> str:
    return json.dumps(
        {
            "profile": profile,
            "job": job,
            "scoring_rubric": {
                "90_100": "Excellent match, prioritize today.",
                "75_89": "Strong match, apply if interested.",
                "60_74": "Possible match, review manually.",
                "0_59": "Weak match or clear mismatch.",
            },
        },
        ensure_ascii=True,
    )


class OpenAIModelClient:
    def __init__(self, model: str) -> None:
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is required when MODEL_PROVIDER=openai.")
        self.model = model

    def score_job(self, profile: dict[str, str], job: dict[str, str]) -> JobFit:
        response = httpx.post(
            "https://api.openai.com/v1/responses",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "input": [
                    {"role": "system", "content": STAGE_ONE_PROMPT},
                    {"role": "user", "content": build_user_prompt(profile, job)},
                ],
                "text": {"format": {"type": "json_object"}},
            },
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json()
        output_text = payload.get("output_text") or _extract_openai_output_text(payload)
        return JobFit.model_validate_json(output_text)

    def verify_job(self, profile: dict[str, str], job: dict[str, str]) -> JobVerification:
        response = httpx.post(
            "https://api.openai.com/v1/responses",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "input": [
                    {"role": "system", "content": VERIFICATION_PROMPT},
                    {"role": "user", "content": build_user_prompt(profile, job)},
                ],
                "text": {"format": {"type": "json_object"}},
            },
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json()
        output_text = payload.get("output_text") or _extract_openai_output_text(payload)
        return _validate_job_verification(output_text)

    def deep_research(self, profile: dict[str, str], job: dict[str, str]) -> FirmResearch:
        response = httpx.post(
            "https://api.openai.com/v1/responses",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "input": [
                    {"role": "system", "content": STAGE_TWO_PROMPT},
                    {"role": "user", "content": build_user_prompt(profile, job)},
                ],
                "text": {"format": {"type": "json_object"}},
            },
            timeout=120,
        )
        response.raise_for_status()
        payload = response.json()
        output_text = payload.get("output_text") or _extract_openai_output_text(payload)
        return FirmResearch.model_validate_json(output_text)


class MistralModelClient:
    def __init__(self, model: str) -> None:
        self.api_key = os.getenv("MISTRAL_API_KEY")
        if not self.api_key:
            raise RuntimeError("MISTRAL_API_KEY is required when MODEL_PROVIDER=mistral.")
        self.model = model

    def score_job(self, profile: dict[str, str], job: dict[str, str]) -> JobFit:
        response = httpx.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": STAGE_ONE_PROMPT},
                    {"role": "user", "content": build_user_prompt(profile, job)},
                ],
                "response_format": {"type": "json_object"},
            },
            timeout=60,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        if not isinstance(content, str):
            content = json.dumps(content, ensure_ascii=True)
        return JobFit.model_validate_json(content)

    def verify_job(self, profile: dict[str, str], job: dict[str, str]) -> JobVerification:
        response = httpx.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": VERIFICATION_PROMPT},
                    {"role": "user", "content": build_user_prompt(profile, job)},
                ],
                "response_format": {"type": "json_object"},
            },
            timeout=60,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        if not isinstance(content, str):
            content = json.dumps(content, ensure_ascii=True)
        return _validate_job_verification(content)

    def deep_research(self, profile: dict[str, str], job: dict[str, str]) -> FirmResearch:
        response = httpx.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": STAGE_TWO_PROMPT},
                    {"role": "user", "content": build_user_prompt(profile, job)},
                ],
                "response_format": {"type": "json_object"},
            },
            timeout=120,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        if not isinstance(content, str):
            content = json.dumps(content, ensure_ascii=True)
        return FirmResearch.model_validate_json(content)


class GeminiModelClient:
    def __init__(self, model: str) -> None:
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY is required when MODEL_PROVIDER=gemini.")
        self.model = model

    def score_job(self, profile: dict[str, str], job: dict[str, str]) -> JobFit:
        content = self._generate_json(STAGE_ONE_PROMPT, build_user_prompt(profile, job))
        return JobFit.model_validate_json(_json_object_text(content))

    def verify_job(self, profile: dict[str, str], job: dict[str, str]) -> JobVerification:
        content = self._generate_json(VERIFICATION_PROMPT, build_user_prompt(profile, job))
        return _validate_job_verification(content)

    def deep_research(self, profile: dict[str, str], job: dict[str, str]) -> FirmResearch:
        content = self._generate_json(STAGE_TWO_PROMPT, build_user_prompt(profile, job))
        return FirmResearch.model_validate_json(_json_object_text(content))

    def _generate_json(self, system_prompt: str, user_prompt: str) -> str:
        response = httpx.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent",
            params={"key": self.api_key},
            json={
                "systemInstruction": {"parts": [{"text": system_prompt}]},
                "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
                "generationConfig": {"responseMimeType": "application/json"},
            },
            timeout=120,
        )
        response.raise_for_status()
        return response.json()["candidates"][0]["content"]["parts"][0]["text"]


def create_model_client(provider: str, model_name: str) -> ModelClient:
    if provider == "openai":
        return OpenAIModelClient(model_name)
    if provider == "mistral":
        return MistralModelClient(model_name)
    if provider == "gemini":
        return GeminiModelClient(model_name)
    raise ValueError(f"Unsupported MODEL_PROVIDER: {provider}")


def _extract_openai_output_text(payload: dict) -> str:
    parts = []
    for item in payload.get("output", []):
        for content in item.get("content", []):
            if content.get("type") in {"output_text", "text"}:
                parts.append(content.get("text", ""))
    if not parts:
        raise RuntimeError(f"No text output returned by OpenAI: {payload}")
    return "".join(parts)


def _json_object_text(value: str) -> str:
    text = value.strip()
    if text.startswith("```"):
        text = text.strip("`").strip()
        if text.lower().startswith("json"):
            text = text[4:].strip()
    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char != "{":
            continue
        try:
            parsed, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return json.dumps(parsed, ensure_ascii=True)
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return value
    return text[start : end + 1]


def _validate_job_verification(value: str) -> JobVerification:
    text = _json_object_text(value)
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise ValueError("Verification response must be a JSON object.")
    return JobVerification.model_validate(_normalise_verification_payload(payload))


def _normalise_verification_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalised = dict(payload)
    normalised["confidence"] = _normalise_confidence(normalised.get("confidence", 0))
    for key in (
        "corrected_deadline",
        "corrected_location",
        "corrected_salary_or_experience",
        "evidence",
        "risks",
    ):
        normalised[key] = _normalise_text(normalised.get(key, "not stated"))
    return normalised


def _normalise_confidence(value: object) -> int:
    if isinstance(value, float) and 0 <= value <= 1:
        return round(value * 100)
    if isinstance(value, (float, int)):
        return round(value)
    if isinstance(value, str):
        try:
            parsed = float(value.strip().rstrip("%"))
        except ValueError:
            return 0
        return round(parsed * 100) if 0 <= parsed <= 1 else round(parsed)
    return 0


def _normalise_text(value: object) -> str:
    if value is None:
        return "not stated"
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=True)
