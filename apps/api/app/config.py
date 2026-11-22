from functools import lru_cache
from pathlib import Path

from pydantic import Field
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
    # Plazo total del intake (incluye esperar al modelo). Pasado el plazo: revisión humana.
    intake_deadline_seconds: float = 60
    # Secreto compartido del webhook genérico. Sin valor, el webhook rechaza todo.
    # ponytail: secreto global; por proyecto cuando haya adapters de GitHub/Azure DevOps.
    webhook_secret: str | None = None
    # Clave Fernet para cifrar tokens de proyecto. Sin valor, no se guarda ningún token.
    token_encryption_key: str | None = None
    # Sondeo de trackers en segundo plano. Los tests lo desactivan.
    tracker_polling_enabled: bool = True
    # Caducidad de claims: sin heartbeat durante este tiempo, el item vuelve a QUEUED.
    heartbeat_timeout_seconds: int = 30 * 60
    # Job de caducidad en segundo plano, independiente del sondeo de trackers. Los tests lo desactivan.
    claim_expiry_enabled: bool = True
    # Retención de logs (artefactos `log`) en Postgres. Pasados N días, el job los borra.
    log_retention_days: int = Field(default=30, ge=1, le=3650)
    # Job de limpieza en segundo plano. Los tests lo desactivan.
    log_retention_enabled: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
