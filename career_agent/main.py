from __future__ import annotations

from career_agent.agent import CareerSearchAgent
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
    model = create_model_client(config.model_provider, config.model_name)
    stage_two_model = create_model_client(config.model_provider, config.stage_two_model_name)
    micro_agent_model = create_model_client(
        config.micro_agent_model_provider,
        config.micro_agent_model_name,
    )
    verification_model = create_model_client(
        config.verification_model_provider,
        config.verification_model_name,
    )
    result = CareerSearchAgent(
        config,
        store,
        model,
        stage_two_model,
        docs,
        verification_model,
        micro_agent_model,
    ).run()
    print(result)


if __name__ == "__main__":
    main()
