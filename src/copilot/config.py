"""Central settings and project paths. Values come from environment variables / .env."""

import os
import warnings
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Some environments (e.g. an activated Anaconda base env on Windows) export certificate
# paths that do not exist; HTTPS clients then crash on start-up. Ignore them with a warning
# so the default system certificates are used instead.
for _var in ("SSL_CERT_FILE", "REQUESTS_CA_BUNDLE"):
    _path = os.environ.get(_var)
    if _path and not Path(_path).exists():
        del os.environ[_var]
        warnings.warn(f"Ignoring {_var}={_path!r}: file does not exist.", stacklevel=1)

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
    # evaluation judge: a different provider than the agent (avoids self-preference bias)
    judge_provider: str = "google"  # google | openai
    judge_model: str = ""  # empty = provider default (see eval/agent_eval.py)
    google_api_key: str = ""

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
