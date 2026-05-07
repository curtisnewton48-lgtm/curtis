from __future__ import annotations

from career_agent.agent import CareerSearchAgent
from career_agent.config import load_config
from career_agent.models import create_model_client
from career_agent.sheets import DocsStore, SheetsStore


def main() -> None:
    config = load_config()
    store = SheetsStore(config.google_sheet_id)
    docs = DocsStore(config.google_research_doc_id) if config.google_research_doc_id else None
    model = create_model_client(config.model_provider, config.model_name)
    result = CareerSearchAgent(config, store, model, docs).run()
    print(result)


if __name__ == "__main__":
    main()
