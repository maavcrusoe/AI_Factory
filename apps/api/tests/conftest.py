import os
from pathlib import Path

API_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEST_DB = "postgresql+psycopg://factory:factory@localhost:5432/factory_test"

# Base de tests separada de la de desarrollo. Se fija antes de importar app.*.
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", DEFAULT_TEST_DB)
os.environ["APP_SECRET_KEY"] = "test-secret"
os.environ["ADMIN_EMAIL"] = "admin@test.local"
os.environ["ADMIN_PASSWORD"] = "test-password"
os.environ["WEBHOOK_SECRET"] = "test-webhook-secret"
os.environ["TRACKER_POLLING_ENABLED"] = "false"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["TOKEN_ENCRYPTION_KEY"] = Fernet.generate_key().decode()

import pytest  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.engine import make_url  # noqa: E402


def _ensure_database(url: str) -> None:
    target = make_url(url)
    server = create_engine(target.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with server.connect() as conn:
        exists = conn.execute(
            text("select 1 from pg_database where datname = :name"), {"name": target.database}
        ).scalar()
        if not exists:
            conn.execute(text(f'create database "{target.database}"'))
    server.dispose()


@pytest.fixture(scope="session", autouse=True)
def migrated_database() -> None:
    from alembic import command
    from alembic.config import Config

    from app.seed import seed_admin

    _ensure_database(os.environ["DATABASE_URL"])
    cfg = Config(str(API_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(API_ROOT / "migrations"))
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    seed_admin()
