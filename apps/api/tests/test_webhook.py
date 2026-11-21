import json
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select

from app.db import SessionLocal
from app.main import app
from app.models import WorkItem, WorkItemEvent
from app.security import sign_body
from app.seed import seed_demo_project
from app.services.intake_model import IntakeInput, IntakeModelError
from app.services.llm_ollama import get_intake_model

client = TestClient(app)
SECRET = "test-webhook-secret"
URL = "/api/v1/webhooks/generic"


class UnavailableModel:
    def assess(self, item: IntakeInput) -> Any:
        raise IntakeModelError("stub")


def payload(**overrides: Any) -> bytes:
    data = {"projectId": "meme-demo", "title": "Desde webhook", "body": "Cuerpo del evento."}
    data.update(overrides)
    return json.dumps(data).encode()


def post(raw: bytes, key: str = "wh-1", signature: str | None = None) -> httpx.Response:
    headers = {"Content-Type": "application/json", "X-Idempotency-Key": key}
    if signature is not None:
        headers["X-Hub-Signature-256"] = signature
    return client.post(URL, content=raw, headers=headers)


@pytest.fixture(autouse=True)
def clean_state() -> Any:
    seed_demo_project()
    app.dependency_overrides[get_intake_model] = lambda: UnavailableModel()
    with SessionLocal() as db:
        db.execute(delete(WorkItemEvent))
        db.execute(delete(WorkItem))
        db.commit()
    yield
    app.dependency_overrides.clear()


def item_count() -> int:
    with SessionLocal() as db:
        return db.scalar(select(func.count()).select_from(WorkItem)) or 0


def test_valid_signature_creates_item_audited_as_webhook() -> None:
    raw = payload()
    response = post(raw, signature=sign_body(raw, SECRET))
    assert response.status_code == 201
    assert response.json()["status"] == "RECEIVED"
    with SessionLocal() as db:
        event = db.scalars(select(WorkItemEvent).order_by(WorkItemEvent.id)).first()
        assert event is not None
        assert event.actor == "webhook"


def test_wrong_signature_is_401_and_creates_nothing() -> None:
    raw = payload()
    response = post(raw, signature=sign_body(raw, "otro-secreto"))
    assert response.status_code == 401
    assert item_count() == 0


def test_missing_signature_is_401() -> None:
    assert post(payload()).status_code == 401
    assert item_count() == 0


def test_signature_over_different_body_is_401() -> None:
    signature = sign_body(payload(title="Original"), SECRET)
    assert post(payload(title="Manipulado"), signature=signature).status_code == 401


def test_missing_idempotency_key_is_422() -> None:
    raw = payload()
    response = client.post(
        URL,
        content=raw,
        headers={"Content-Type": "application/json", "X-Hub-Signature-256": sign_body(raw, SECRET)},
    )
    assert response.status_code == 422


def test_same_idempotency_key_twice_does_not_duplicate() -> None:
    raw = payload()
    signature = sign_body(raw, SECRET)
    first = post(raw, key="wh-dup", signature=signature)
    second = post(raw, key="wh-dup", signature=signature)
    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]
    assert item_count() == 1


def test_valid_signature_with_invalid_body_is_422() -> None:
    raw = payload(title="")
    response = post(raw, signature=sign_body(raw, SECRET))
    assert response.status_code == 422
    assert item_count() == 0


def test_unknown_project_is_404() -> None:
    raw = payload(projectId="no-existe")
    assert post(raw, signature=sign_body(raw, SECRET)).status_code == 404
