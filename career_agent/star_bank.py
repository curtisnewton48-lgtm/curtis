from __future__ import annotations

import os

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
    model = create_model_client(provider, model_name)
    star_bank = model.generate_star_bank(store.profile(), [])
    url = docs.create_support_doc(star_bank.title, star_bank.content)
    print({"star_bank_url": url})


if __name__ == "__main__":
    main()
