from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    """All config comes from environment variables / backend/.env. No secrets in code."""

    # Anchored to backend/ so it works regardless of the current working directory.
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    llm_base_url: str | None = None  # AI proxy endpoint; empty = provider default
    llm_api_key: str = ""
    llm_model: str = "gemini-2.5-flash"
    llm_timeout_seconds: float = 60.0

    database_url: str = "sqlite:///./invoices.db"
    max_upload_mb: int = 10


settings = Settings()
