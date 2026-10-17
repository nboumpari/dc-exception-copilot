"""Central settings and project paths. Values come from environment variables / .env."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = PROJECT_ROOT / "config"
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
SYNTHETIC_DIR = DATA_DIR / "synthetic"
DC_DB_PATH = DATA_DIR / "dc.db"  # synthetic warehouse database (step 3)
REFERENCE_DB_PATH = DATA_DIR / "reference.db"  # tables parsed from regulations (step 5)
# answer key for planted demo scenarios - deliberately NOT inside dc.db, so the agent
# cannot read the answers through its SQL tool
SCENARIOS_PATH = DATA_DIR / "eval" / "scenarios.json"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=PROJECT_ROOT / ".env", extra="ignore")

    llm_provider: str = "openai"
    openai_api_key: str = ""
    chat_model: str = "gpt-5.4-mini"  # agent LLM; any tool-calling OpenAI model works
    reasoning_effort: str = "low"  # none | low | medium | high

    azure_openai_api_key: str = ""
    azure_openai_endpoint: str = ""
    azure_openai_api_version: str = "2024-10-21"
    azure_openai_chat_deployment: str = ""
    azure_openai_embedding_deployment: str = ""

    corpus_contact: str = "anonymous"

    # LangSmith tracing and evaluation (off unless enabled and a key is set)
    langsmith_tracing: bool = False
    langsmith_api_key: str = ""
    langsmith_project: str = "dc-exception-copilot"
    langsmith_endpoint: str = "https://api.smith.langchain.com"


settings = Settings()
