"""Weekly STAR Bank generator."""
from __future__ import annotations

import json
import os
from datetime import date

from career_agent.auth import get_credentials
from career_agent.sheets import SheetsStore


def _require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Environment variable {name!r} is required but not set.")
    return value


def _optional_env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


STAR_SYSTEM_PROMPT = """You are an elite career coach specialising in the UK legal sector.
Generate a comprehensive STAR bank for a paralegal / trainee-solicitor candidate.

For each competency category below, produce 3 STAR stories (Situation, Task, Action, Result).
Each story must be 150-220 words and end with a quantified Result.

Competency categories (produce 3 stories per category):
1. Communication & Client Care
2. Analytical & Research Skills
3. Teamwork & Collaboration
4. Initiative & Self-Management
5. Commercial Awareness
6. Resilience & Working Under Pressure
7. Attention to Detail
8. Leadership & Mentoring
9. Problem-Solving & Creative Thinking
10. Diversity, Equity & Inclusion

Output valid JSON:
{
  "title": "STAR Bank -- <Candidate Name> -- <YYYY-MM-DD>",
  "competencies": [
    {
      "category": "<name>",
      "stories": [{"headline": "...", "situation": "...", "task": "...", "action": "...", "result": "..."}]
    }
  ]
}
Return ONLY JSON - no markdown, no preamble."""


def _render_star_bank_as_text(data: dict) -> str:
    lines: list[str] = [data.get("title", "STAR Bank"), "=" * 80, ""]
    for comp in data.get("competencies", []):
        lines.append(f"\n{'=' * 60}")
        lines.append(comp.get("category", "").upper())
        lines.append("=" * 60)
        for i, story in enumerate(comp.get("stories", []), start=1):
            lines.append(f"\nStory {i}: {story.get('headline', '')}")
            lines.append(f"\nSITUATION\n{story.get('situation', '')}")
            lines.append(f"\nTASK\n{story.get('task', '')}")
            lines.append(f"\nACTION\n{story.get('action', '')}")
            lines.append(f"\nRESULT\n{story.get('result', '')}")
            lines.append("")
    return "\n".join(lines)


def _call_openai(api_key: str, model: str, profile: dict, context: str) -> dict:
    import httpx
    user_content = (
        f"Candidate profile:\n{json.dumps(profile, indent=2)}\n\n"
        f"Additional context:\n{context}\n\nToday: {date.today().isoformat()}"
    )
    r = httpx.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": STAR_SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            "response_format": {"type": "json_object"},
        },
        timeout=180,
    )
    r.raise_for_status()
    return json.loads(r.json()["choices"][0]["message"]["content"])


def _call_mistral(api_key: str, model: str, profile: dict, context: str) -> dict:
    import httpx
    user_content = (
        f"Candidate profile:\n{json.dumps(profile, indent=2)}\n\n"
        f"Additional context:\n{context}\n\nToday: {date.today().isoformat()}"
    )
    r = httpx.post(
        "https://api.mistral.ai/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": STAR_SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            "response_format": {"type": "json_object"},
        },
        timeout=180,
    )
    r.raise_for_status()
    content = r.json()["choices"][0]["message"]["content"]
    if not isinstance(content, str):
        content = json.dumps(content)
    return json.loads(content)


def _call_gemini(api_key: str, model: str, profile: dict, context: str) -> dict:
    import httpx
    user_content = (
        f"Candidate profile:\n{json.dumps(profile, indent=2)}\n\n"
        f"Additional context:\n{context}\n\nToday: {date.today().isoformat()}\n"
        "IMPORTANT: Return ONLY valid JSON, no markdown."
    )
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}"
        f":generateContent?key={api_key}"
    )
    r = httpx.post(
        url,
        json={
            "system_instruction": {"parts": [{"text": STAR_SYSTEM_PROMPT}]},
            "contents": [{"role": "user", "parts": [{"text": user_content}]}],
            "generationConfig": {"responseMimeType": "application/json"},
        },
        timeout=180,
    )
    r.raise_for_status()
    raw = r.json()["candidates"][0]["content"]["parts"][0]["text"]
    return json.loads(raw)


def generate_star_bank(profile: dict, provider: str, model: str, context: str) -> dict:
    provider = provider.strip().lower()
    if provider == "openai":
        return _call_openai(_require_env("OPENAI_API_KEY"), model, profile, context)
    if provider == "mistral":
        return _call_mistral(_require_env("MISTRAL_API_KEY"), model, profile, context)
    if provider == "gemini":
        return _call_gemini(_require_env("GEMINI_API_KEY"), model, profile, context)
    raise ValueError(f"Unsupported MICRO_AGENT_MODEL_PROVIDER: {provider!r}")


def _create_doc_in_folder(drive_service, docs_service, title: str, content: str) -> str:
    folder_id = _optional_env("GOOGLE_RESEARCH_FOLDER_ID")
    meta: dict = {"name": title, "mimeType": "application/vnd.google-apps.document"}
    if folder_id:
        meta["parents"] = [folder_id]
    file_res = drive_service.files().create(body=meta, fields="id").execute()
    doc_id = file_res["id"]
    docs_service.documents().batchUpdate(
        documentId=doc_id,
        body={"requests": [{"insertText": {"location": {"index": 1}, "text": content}}]},
    ).execute()
    return f"https://docs.google.com/document/d/{doc_id}/edit"


def _append_tab_to_existing_doc(docs_service, doc_id: str, title: str, content: str) -> str:
    short_title = title[:30]
    doc = docs_service.documents().get(documentId=doc_id).execute()
    existing_tab_id = None
    for tab in doc.get("tabs", []):
        props = tab.get("tabProperties", {})
        if props.get("title") == short_title:
            existing_tab_id = props.get("tabId")
            break

    if not existing_tab_id:
        resp = docs_service.documents().batchUpdate(
            documentId=doc_id,
            body={
                "requests": [
                    {
                        "addDocumentTab": {
                            "tabProperties": {
                                "title": short_title,
                                "iconEmoji": "\\u2b50",
                            }
                        }
                    }
                ]
            },
        ).execute()
        existing_tab_id = resp["replies"][0]["addDocumentTab"]["tabProperties"]["tabId"]

    docs_service.documents().batchUpdate(
        documentId=doc_id,
        body={
            "requests": [
                {
                    "insertText": {
                        "location": {"index": 1, "tabId": existing_tab_id},
                        "text": content + "\n\n",
                    }
                }
            ]
        },
    ).execute()
    return f"https://docs.google.com/document/d/{doc_id}/edit"


def main() -> None:
    from dotenv import load_dotenv
    load_dotenv()

    sheet_id = _require_env("GOOGLE_SHEET_ID")
    provider = _optional_env("MICRO_AGENT_MODEL_PROVIDER", "openai")
    default_model = (
        "gpt-4o-mini" if provider == "openai"
        else "gemini-2.0-flash" if provider == "gemini"
        else "mistral-small-latest"
    )
    model = _optional_env("MICRO_AGENT_MODEL_NAME", default_model)
    context = _optional_env("PROFILE_CONTEXT", "UK legal sector candidate.")

    creds = get_credentials()
    from googleapiclient.discovery import build as _build
    docs_service = _build("docs", "v1", credentials=creds)
    drive_service = _build("drive", "v3", credentials=creds)

    store = SheetsStore(sheet_id)
    profile = store.profile()
    if not profile:
        raise RuntimeError("No profile data found in Google Sheet 'Profile' tab.")

    print(f"Loaded profile with {len(profile)} fields.")
    print(f"Generating STAR bank using {provider}/{model} ...")

    star_data = generate_star_bank(profile, provider, model, context)
    title = star_data.get("title", f"STAR Bank -- {date.today().isoformat()}")
    content_text = _render_star_bank_as_text(star_data)

    research_doc_id = _optional_env("GOOGLE_RESEARCH_DOC_ID")
    if research_doc_id:
        url = _append_tab_to_existing_doc(docs_service, research_doc_id, title, content_text)
        print(f"Added new tab to existing doc: {url}")
    else:
        url = _create_doc_in_folder(drive_service, docs_service, title, content_text)
        print(f"Created new doc: {url}")

    print(json.dumps({"star_bank_url": url, "title": title}))


if __name__ == "__main__":
    main()
