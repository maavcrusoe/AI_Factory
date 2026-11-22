"""Fase 7: rotación de claves de tokens, logs JSON, métricas por proyecto y permisos de /metrics."""

import json
import logging
from types import SimpleNamespace
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import SessionLocal
from app.logging_setup import JsonFormatter
from app.main import app
from app.models import Project, ProjectIntegration, WorkItem
from app.ops import rotate_integration
from app.services import crypto

client = TestClient(app)
SLUG = "fase7-metrics"


def _use_key(monkeypatch: pytest.MonkeyPatch, keys: str) -> None:
    monkeypatch.setattr(crypto, "get_settings", lambda: SimpleNamespace(token_encryption_key=keys))


def test_rotation_keeps_old_ciphertext_readable_and_drops_old_key(monkeypatch: pytest.MonkeyPatch) -> None:
    old, new = Fernet.generate_key().decode(), Fernet.generate_key().decode()
    _use_key(monkeypatch, old)
    stored = crypto.encrypt_token("ghp_secreto")

    _use_key(monkeypatch, f"{new},{old}")
    assert crypto.decrypt_token(stored) == "ghp_secreto"
    rotated = crypto.rotate_ciphertext(stored)

    _use_key(monkeypatch, new)
    assert crypto.decrypt_token(rotated) == "ghp_secreto"
    with pytest.raises(crypto.TokenCryptoError):
        crypto.decrypt_token(stored)


def test_rotate_integration_reencrypts_both_tokens(monkeypatch: pytest.MonkeyPatch) -> None:
    old, new = Fernet.generate_key().decode(), Fernet.generate_key().decode()
    _use_key(monkeypatch, old)
    slug = f"rot-{uuid4().hex[:8]}"
    with SessionLocal() as db:
        project = Project(slug=slug, name="Rotación")
        db.add(project)
        db.flush()
        integration = ProjectIntegration(
            project_id=project.id,
            provider="generic",
            config={},
            token_encrypted=crypto.encrypt_token("tracker"),
            merge_token_encrypted=crypto.encrypt_token("merge"),
        )
        db.add(integration)
        db.commit()

        _use_key(monkeypatch, f"{new},{old}")
        assert rotate_integration(integration) == 2
        db.commit()

    _use_key(monkeypatch, new)
    with SessionLocal() as db:
        row = db.scalar(select(ProjectIntegration).join(Project).where(Project.slug == slug))
        assert crypto.decrypt_token(row.token_encrypted) == "tracker"
        assert crypto.decrypt_token(row.merge_token_encrypted) == "merge"


def test_json_formatter_emits_one_line_with_request_fields() -> None:
    record = logging.LogRecord("factory.http", logging.INFO, __file__, 1, "request", None, None)
    record.method, record.path, record.status, record.duration_ms = "GET", "/metrics", 200, 1.5

    line = JsonFormatter().format(record)

    data = json.loads(line)
    assert "\n" not in line
    assert data["msg"] == "request"
    assert data["level"] == "INFO"
    assert (data["method"], data["path"], data["status"]) == ("GET", "/metrics", 200)


def test_unhandled_error_is_logged_as_500(caplog: pytest.LogCaptureFixture) -> None:
    @app.get("/__fase7_boom")
    def boom() -> None:
        raise RuntimeError("fallo de prueba")

    failing = TestClient(app, raise_server_exceptions=False)
    with caplog.at_level(logging.ERROR, logger="factory.http"):
        response = failing.get("/__fase7_boom")

    assert response.status_code == 500
    record = next(r for r in caplog.records if r.name == "factory.http")
    assert (record.method, record.path, record.status) == ("GET", "/__fase7_boom", 500)


def _admin_headers() -> dict[str, str]:
    response = client.post("/api/v1/auth/login", json={"email": "admin@test.local", "password": "test-password"})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_metrics_requires_admin() -> None:
    assert client.get("/metrics").status_code == 401


def test_metrics_reports_queue_per_project() -> None:
    with SessionLocal() as db:
        project = db.scalar(select(Project).where(Project.slug == SLUG))
        if project is None:
            project = Project(slug=SLUG, name="Métricas")
            db.add(project)
            db.flush()
        db.add(
            WorkItem(
                project_id=project.id,
                idempotency_key=f"metrics-{uuid4()}",
                source="generic",
                original_payload={},
                title="Item de métricas",
                body="cuerpo",
                status="QUEUED",
                labels=[],
            )
        )
        db.commit()

    response = client.get("/metrics", headers=_admin_headers())

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "# TYPE factory_queue_size gauge" in response.text
    assert "# TYPE factory_heartbeat_expiries_total counter" in response.text
    assert f'factory_queue_size{{project="{SLUG}"}} 1' in response.text
