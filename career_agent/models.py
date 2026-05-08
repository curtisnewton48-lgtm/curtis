from __future__ import annotations

import json
import os
from typing import Any, Protocol

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


class TailoredCV(BaseModel):
    title: str
    content: str
    ats_keywords: list[str] = []


class STARBank(BaseModel):
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
        return _normalise_confidence(value)

    @field_validator("corrected_deadline", "corrected_location", "corrected_salary_or_experience", "evidence", "risks", mode="before")
    @classmethod
    def _coerce_text(cls, value: object) -> str:
        return _normalise_text(value)


class ModelClient(Protocol):
    def score_job(self, profile: dict[str, str], job: dict[str, str]) -> JobFit: ...
    def verify_job(self, profile: dict[str, str], job: dict[str, str]) -> JobVerification: ...
    def deep_research(self, profile: dict[str, str], job: dict[str, str]) -> FirmResearch: ...
    def tailor_cv(self, profile: dict[str, str], job: dict[str, str]) -> TailoredCV: ...
    def generate_star_bank(self, profile: dict[str, str], jobs: list[dict[str, str]]) -> STARBank: ...


STAGE_ONE_PROMPT = """You are Stage 1 of a UK legal career-search agent.
Extract and triage paralegal, trainee solicitor, and legal caseworker roles. Return concise structured facts only. Do not do deep firm research.
Extract application deadline and eligibility requirements when present. Use "not stated" when not provided.
deadline_status must be one of: active, expired, not_stated, unclear. eligibility_status must be one of: eligible, probably_eligible, unclear, not_eligible.
role_level must be one of: paralegal, legal_assistant, trainee_solicitor, caseworker, vacation_scheme, training_contract, graduate_scheme, other, unclear.
practice_area_match must be one of: exact, related, weak, none, unclear. candidate_evidence_match must be one of: strong, medium, weak, none, unclear.
Only mark not_eligible when the listing contains a clear blocker. Treat missing eligibility information as unclear, not not_eligible.
Return only valid JSON with keys: score, role_type, role_level, practice_area, practice_area_match, application_deadline, deadline_status, eligibility, eligibility_status, degree_requirement, sqe_lpc_requirement, work_authorisation, application_route, explicit_disqualifiers, candidate_evidence_match, stage_two_reason, summary, risks, recommended_action, tailored_pitch."""

STAGE_TWO_PROMPT = """You are Stage 2 of a UK legal career-search agent for Curtis Newton, a first-class law graduate.
Create a comprehensive, application-ready firm and role research dossier for a shortlisted UK legal job. Use supplied job context and web-grounded information available to the model/tool. Do not invent facts; write "not found" where evidence is unavailable.
The dossier must be detailed enough that a strong 2026 legal applicant can use it without further routine research before tailoring a CV, cover letter, application form, or interview preparation.
Go beyond the checklist by adding market context, commercial/legal awareness angles, comparator firms, interview themes, credibility signals, risks/unknowns, and a "how to win this application" section.
Cover: role snapshot; why shortlisted; firm overview; practice areas; culture; training/progression; application process; candidate expectations; clients/matters/deals/cases/campaigns; recent news; AI/technology; reviews/reputation; application strategy; verification notes; and a top-candidate preparation pack with 10 facts, 5 motivations, 5 commercial hooks, and 5 ways to frame Curtis's background.
Return only valid JSON with keys: title, content."""

CV_TAILORING_PROMPT = """You are a CV-tailoring micro-agent for Curtis Newton, a UK first-class law graduate.
Create a tailored legal CV draft for the supplied shortlisted role. Use only the supplied profile/CV context and job context. Do not invent experience, employment, grades, institutions, dates, awards, or languages.
Extract ATS keywords, rewrite honest CV bullets, and produce a final one-page UK legal graduate CV draft. If evidence is missing, use bracketed prompts such as [insert exact example].
Include: ATS keyword bank, tailored profile summary, education, experience bullet options, skills, languages, optional sections, do-not-claim warnings, and final CV draft.
Return only valid JSON with keys: title, content, ats_keywords."""

STAR_BANK_PROMPT = """You are an independent weekly STAR-bank generator for Curtis Newton, a UK first-class law graduate applying for legal graduate, paralegal, caseworker, and trainee solicitor roles.
This micro-agent is not job-specific and must not depend on shortlisted roles. Its purpose is to pre-build reusable competency content from Curtis's profile/CV context.
Generate 20 to 40 universal STAR competency answers from the supplied profile. Do not invent facts. If a missing detail is needed, mark it as [add specific real example].
Required competency categories: teamwork, client care, attention to detail, legal research, commercial awareness, communication, working under pressure, conflict resolution, organisation/time management.
Also include where evidence supports it: leadership, resilience, advocacy/persuasion, ethics, confidentiality, diversity/inclusion, technology/AI, initiative, empathy, and motivation for law.
For each STAR answer include: competency, likely interview question, Situation, Task, Action, Result, legal relevance, stronger wording to use, and risk/check before using. Include a quick index mapping competencies to answer numbers.
Return only valid JSON with keys: title, content."""

VERIFICATION_PROMPT = """You are a cheap verification micro-agent for a UK legal career-search system.
Before expensive Stage 2 research runs, verify whether the shortlisted role appears real, current, and accurately represented. Be strict but fair.
Set accept_for_stage_two to false if the role is likely fake, closed, an article, a non-vacancy page, has a clearly expired deadline, or has a major factual contradiction.
Do not treat a fixed-term contract end date as an application deadline or proof that the job is closed. Do not reject a role merely because it is home-based, remote, hybrid, or has a broader location than the tracker extracted.
Return only valid JSON with keys: is_real_job, deadline_correct, location_correct, salary_experience_accurate, firm_exists, job_still_open, accept_for_stage_two, confidence, corrected_deadline, corrected_location, corrected_salary_or_experience, evidence, risks."""


def build_user_prompt(profile: dict[str, str], job: dict[str, str]) -> str:
    return json.dumps({"profile": profile, "job": job}, ensure_ascii=True)


def build_star_bank_prompt(profile: dict[str, str], jobs: list[dict[str, str]] | None = None) -> str:
    return json.dumps(
        {
            "profile": profile,
            "recent_shortlisted_jobs": [],
            "output_requirements": {
                "answer_count": "20-40",
                "format": "Universal categorised STAR answer bank for UK legal graduate applications.",
                "truthfulness": "Do not invent facts; use bracketed prompts for missing evidence.",
                "job_specificity": "Do not tailor to any individual job. This is a reusable weekly competency library.",
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

    def _request(self, system_prompt: str, user_prompt: str, timeout: int = 120) -> str:
        response = httpx.post(
            "https://api.openai.com/v1/responses",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"model": self.model, "input": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}], "text": {"format": {"type": "json_object"}}},
            timeout=timeout,
        )
        response.raise_for_status()
        payload = response.json()
        return payload.get("output_text") or _extract_openai_output_text(payload)

    def score_job(self, profile: dict[str, str], job: dict[str, str]) -> JobFit:
        return JobFit.model_validate_json(self._request(STAGE_ONE_PROMPT, build_user_prompt(profile, job), 60))

    def verify_job(self, profile: dict[str, str], job: dict[str, str]) -> JobVerification:
        return _validate_job_verification(self._request(VERIFICATION_PROMPT, build_user_prompt(profile, job), 60))

    def deep_research(self, profile: dict[str, str], job: dict[str, str]) -> FirmResearch:
        return FirmResearch.model_validate_json(self._request(STAGE_TWO_PROMPT, build_user_prompt(profile, job), 120))

    def tailor_cv(self, profile: dict[str, str], job: dict[str, str]) -> TailoredCV:
        return TailoredCV.model_validate_json(self._request(CV_TAILORING_PROMPT, build_user_prompt(profile, job), 120))

    def generate_star_bank(self, profile: dict[str, str], jobs: list[dict[str, str]]) -> STARBank:
        return STARBank.model_validate_json(self._request(STAR_BANK_PROMPT, build_star_bank_prompt(profile), 120))


class MistralModelClient:
    def __init__(self, model: str) -> None:
        self.api_key = os.getenv("MISTRAL_API_KEY")
        if not self.api_key:
            raise RuntimeError("MISTRAL_API_KEY is required when MODEL_PROVIDER=mistral.")
        self.model = model

    def _request(self, system_prompt: str, user_prompt: str, timeout: int = 120) -> str:
        response = httpx.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"model": self.model, "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}], "response_format": {"type": "json_object"}},
            timeout=timeout,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return content if isinstance(content, str) else json.dumps(content, ensure_ascii=True)

    def score_job(self, profile: dict[str, str], job: dict[str, str]) -> JobFit:
        return JobFit.model_validate_json(self._request(STAGE_ONE_PROMPT, build_user_prompt(profile, job), 60))

    def verify_job(self, profile: dict[str, str], job: dict[str, str]) -> JobVerification:
        return _validate_job_verification(self._request(VERIFICATION_PROMPT, build_user_prompt(profile, job), 60))

    def deep_research(self, profile: dict[str, str], job: dict[str, str]) -> FirmResearch:
        return FirmResearch.model_validate_json(self._request(STAGE_TWO_PROMPT, build_user_prompt(profile, job), 120))

    def tailor_cv(self, profile: dict[str, str], job: dict[str, str]) -> TailoredCV:
        return TailoredCV.model_validate_json(self._request(CV_TAILORING_PROMPT, build_user_prompt(profile, job), 120))

    def generate_star_bank(self, profile: dict[str, str], jobs: list[dict[str, str]]) -> STARBank:
        return STARBank.model_validate_json(self._request(STAR_BANK_PROMPT, build_star_bank_prompt(profile), 120))


class GeminiModelClient:
    def __init__(self, model: str) -> None:
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY is required when MODEL_PROVIDER=gemini.")
        self.model = model

    def _generate_json(self, system_prompt: str, user_prompt: str) -> str:
        response = httpx.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent",
            params={"key": self.api_key},
            json={"systemInstruction": {"parts": [{"text": system_prompt}]}, "contents": [{"role": "user", "parts": [{"text": user_prompt}]}], "generationConfig": {"responseMimeType": "application/json"}},
            timeout=120,
        )
        response.raise_for_status()
        return response.json()["candidates"][0]["content"]["parts"][0]["text"]

    def score_job(self, profile: dict[str, str], job: dict[str, str]) -> JobFit:
        return JobFit.model_validate_json(_json_object_text(self._generate_json(STAGE_ONE_PROMPT, build_user_prompt(profile, job))))

    def verify_job(self, profile: dict[str, str], job: dict[str, str]) -> JobVerification:
        return _validate_job_verification(self._generate_json(VERIFICATION_PROMPT, build_user_prompt(profile, job)))

    def deep_research(self, profile: dict[str, str], job: dict[str, str]) -> FirmResearch:
        return FirmResearch.model_validate_json(_json_object_text(self._generate_json(STAGE_TWO_PROMPT, build_user_prompt(profile, job))))

    def tailor_cv(self, profile: dict[str, str], job: dict[str, str]) -> TailoredCV:
        return TailoredCV.model_validate_json(_json_object_text(self._generate_json(CV_TAILORING_PROMPT, build_user_prompt(profile, job))))

    def generate_star_bank(self, profile: dict[str, str], jobs: list[dict[str, str]]) -> STARBank:
        return STARBank.model_validate_json(_json_object_text(self._generate_json(STAR_BANK_PROMPT, build_star_bank_prompt(profile))))


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
    return text


def _validate_job_verification(value: str) -> JobVerification:
    payload = json.loads(_json_object_text(value))
    if not isinstance(payload, dict):
        raise ValueError("Verification response must be a JSON object.")
    return JobVerification.model_validate(_normalise_verification_payload(payload))


def _normalise_verification_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalised = dict(payload)
    normalised["confidence"] = _normalise_confidence(normalised.get("confidence", 0))
    for key in ("corrected_deadline", "corrected_location", "corrected_salary_or_experience", "evidence", "risks"):
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
