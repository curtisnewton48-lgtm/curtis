from __future__ import annotations

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

    model = create_model_client(
        config.micro_agent_model_provider,
        config.micro_agent_model_name,
    )
    star_bank = model.generate_star_bank(store.profile(), [])
    url = docs.create_support_doc(star_bank.title, star_bank.content)
    print({"star_bank_url": url})


if __name__ == "__main__":
    main()
