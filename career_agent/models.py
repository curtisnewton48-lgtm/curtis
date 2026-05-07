from __future__ import annotations

import json
import os
from typing import Protocol

import httpx
from pydantic import BaseModel, Field


class JobFit(BaseModel):
    score: int = Field(ge=0, le=100)
    role_type: str
    practice_area: str
    application_deadline: str
    deadline_status: str
    eligibility: str
    summary: str
    risks: str
    recommended_action: str
    tailored_pitch: str


class FirmResearch(BaseModel):
    title: str
    content: str


class ModelClient(Protocol):
    def score_job(self, profile: dict[str, str], job: dict[str, str]) -> JobFit:
        ...

    def deep_research(self, profile: dict[str, str], job: dict[str, str]) -> FirmResearch:
        ...


STAGE_ONE_PROMPT = """You are Stage 1 of a UK legal career-search agent.
Extract and triage paralegal, trainee solicitor, and legal caseworker roles.
Return concise structured facts only. Do not do deep firm research.
Extract application deadline and eligibility requirements when present. Use "not stated" when not provided.
deadline_status must be one of: active, expired, not_stated, unclear.
Return only valid JSON with keys: score, role_type, practice_area, application_deadline, deadline_status, eligibility, summary, risks, recommended_action, tailored_pitch."""

STAGE_TWO_PROMPT = """You are Stage 2 of a UK legal career-search agent for a law graduate.
Create comprehensive firm research for a shortlisted legal job. Use only supplied job context and web-grounded information available to the model/tool. Do not invent facts; say "not found" where needed.
The note should be good enough that a strong 2026 legal applicant can use it without further routine research.
Cover at minimum: legal areas advised on, office locations, culture and why to work there, NQ retention rate, NQ and trainee salary, application process, type of firm, clients/deals/news, recent news, firm structure, training contract/SQE/seats structure, expectations of candidates, use of AI/technology, and reviews.
Return only valid JSON with keys: title, content."""


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
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return value
    return text[start : end + 1]
