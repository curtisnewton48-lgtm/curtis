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
    eligibility: str
    firm_research: str
    summary: str
    risks: str
    recommended_action: str
    tailored_pitch: str


class ModelClient(Protocol):
    def score_job(self, profile: dict[str, str], job: dict[str, str]) -> JobFit:
        ...


SYSTEM_PROMPT = """You are a careful career-search agent.
Score UK legal jobs against the user's career profile. Focus on paralegal, trainee solicitor, and caseworker suitability.
Research the firm only from the provided job posting context. Do not invent facts.
Extract application deadline and eligibility requirements when present. Use "not stated" when not provided.
If salary, location, practice area, firm details, deadline, or requirements are missing, note that as a risk.
Return only valid JSON with keys: score, role_type, practice_area, application_deadline, eligibility, firm_research, summary, risks, recommended_action, tailored_pitch."""


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
                    {"role": "system", "content": SYSTEM_PROMPT},
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
                    {"role": "system", "content": SYSTEM_PROMPT},
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


def create_model_client(provider: str, model_name: str) -> ModelClient:
    if provider == "openai":
        return OpenAIModelClient(model_name)
    if provider == "mistral":
        return MistralModelClient(model_name)
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
