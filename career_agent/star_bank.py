from __future__ import annotations

import json
import os
from datetime import date
from typing import Any

import httpx

from career_agent.models import STAR_BANK_PROMPT, STARBank
from career_agent.config import load_config
from career_agent.models import create_model_client
from career_agent.sheets import DocsStore, SheetsStore


def main() -> None:
    config = load_config()
    store = SheetsStore(config.google_sheet_id)
    docs = (
        DocsStore(config.google_research_doc_id, config.google_research_folder_id)
        if config.google_research_doc_id or config.google_research_folder_id
        else None
    )
    if not docs:
        raise RuntimeError("GOOGLE_RESEARCH_DOC_ID or GOOGLE_RESEARCH_FOLDER_ID is required.")

    provider = os.getenv("STAR_BANK_MODEL_PROVIDER", config.micro_agent_model_provider).strip().lower()
    model_name = os.getenv("STAR_BANK_MODEL_NAME", config.micro_agent_model_name).strip()
    if provider == "mistral" and model_name.startswith("ministral-"):
        model_name = os.getenv("STAR_BANK_FALLBACK_MODEL_NAME", "mistral-small-latest").strip()
    profile = store.profile()
    if provider == "mistral" and os.getenv("MISTRAL_API_KEY", "").strip():
        star_bank = _generate_mistral_star_bank(model_name, profile)
    else:
        model = create_model_client(provider, model_name)
        star_bank = model.generate_star_bank(profile, [])
    url = docs.create_support_doc(star_bank.title, star_bank.content)
    print({"star_bank_url": url})


def _generate_mistral_star_bank(model_name: str, profile: dict[str, str]) -> STARBank:
    api_key = os.getenv("MISTRAL_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("MISTRAL_API_KEY is required for the weekly STAR bank.")
    response = httpx.post(
        "https://api.mistral.ai/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": model_name,
            "messages": [
                {"role": "system", "content": STAR_BANK_PROMPT},
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "profile": profile,
                            "today": date.today().isoformat(),
                            "output_contract": (
                                "Return JSON with title as a string and content as a single "
                                "plain text string. Do not return content as an object or array."
                            ),
                        },
                        ensure_ascii=True,
                    ),
                },
            ],
            "response_format": {"type": "json_object"},
        },
        timeout=httpx.Timeout(360, connect=30, read=360, write=60, pool=30),
    )
    response.raise_for_status()
    raw = response.json()["choices"][0]["message"]["content"]
    if not isinstance(raw, str):
        raw = json.dumps(raw, ensure_ascii=True)
    payload = json.loads(raw)
    title = str(payload.get("title") or f"Curtis Newton - Weekly STAR Bank - {date.today().isoformat()}")
    content = payload.get("content", payload)
    return STARBank(title=title, content=_render_content(content))


def _render_content(value: Any) -> str:
    if isinstance(value, str):
        return value
    lines: list[str] = []
    _append_lines(lines, value)
    return "\n".join(lines).strip()


def _append_lines(lines: list[str], value: Any, heading: str = "") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            label = str(key).replace("_", " ").title()
            if isinstance(item, (dict, list)):
                lines.extend(["", label, "-" * min(len(label), 72)])
                _append_lines(lines, item, label)
            else:
                lines.append(f"{label}: {item}")
        return
    if isinstance(value, list):
        for index, item in enumerate(value, start=1):
            if isinstance(item, dict):
                title = item.get("competency") or item.get("category") or item.get("question") or item.get("headline") or f"{heading} {index}".strip()
                lines.extend(["", f"{index}. {title}", "-" * min(len(str(title)) + 3, 72)])
                _append_lines(lines, item, heading)
            else:
                lines.append(f"- {item}")
        return
    lines.append(str(value))


if __name__ == "__main__":
    main()
