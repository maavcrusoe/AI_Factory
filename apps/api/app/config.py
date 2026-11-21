from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=REPO_ROOT / ".env", extra="ignore")

    database_url: str
    app_secret_key: str
    admin_email: str | None = None
    admin_password: str | None = None
    token_ttl_seconds: int = 8 * 3600
    ollama_url: str = "http://192.168.100.6:11434"
    ollama_model: str = "qwen3.5:4b"
    ollama_timeout_seconds: float = 60


@lru_cache
def get_settings() -> Settings:
    return Settings()
