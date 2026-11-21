import json
import time
from collections.abc import Callable
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select

from app.db import SessionLocal
from app.main import app
from app.models import Project, WorkItem, WorkItemEvent
from app.routers.inputs import event_frames
from app.seed import seed_demo_project
from app.config import get_settings
from app.services.intake import (
    NEEDS_INFO,
    QUEUED,
    RECEIVED,
    REJECTED,
    TRIAGE,
    WAITING_HUMAN_TRIAGE,
    plan_outcome,
    sweep_stuck_items,
)
from app.services.intake_model import IntakeAssessment, IntakeInput
from app.services.llm_ollama import OllamaIntakeModel, get_intake_model

client = TestClient(app)


class FakeModel:
    def __init__(self, result: IntakeAssessment | None = None, error: Exception | None = None) -> None:
        self.result = result
        self.error = error

    def assess(self, item: IntakeInput) -> IntakeAssessment:
        if self.error is not None:
            raise self.error
        assert self.result is not None
        return self.result


def assessment(**overrides: Any) -> IntakeAssessment:
    data: dict[str, Any] = {
        "decision": "accept",
        "confidence": 0.95,
        "type": "feature",
        "difficulty": "low",
        "risk": "low",
        "summary": "Resumen de prueba",
        "suggestedLabels": ["meme"],
        "valuation": "Óptima para automatizar",
        "expandedBody": None,
    }
    data.update(overrides)
    return IntakeAssessment.model_validate(data)


def ollama_with(handler: Callable[[httpx.Request], httpx.Response]) -> OllamaIntakeModel:
    return OllamaIntakeModel(
        "http://ollama.test", "qwen3.5:4b", 60, transport=httpx.MockTransport(handler)
    )


def ollama_reply(content: str) -> Callable[[httpx.Request], httpx.Response]:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"message": {"content": content}})

    return handler


@pytest.fixture(autouse=True)
def clean_state() -> Any:
    token = client.post(
        "/api/v1/auth/login", json={"email": "admin@test.local", "password": "test-password"}
    ).json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    seed_demo_project()
    with SessionLocal() as db:
        db.execute(delete(WorkItemEvent))
        db.execute(delete(WorkItem))
        db.commit()
    yield
    app.dependency_overrides.clear()


def use_model(model: Any) -> None:
    app.dependency_overrides[get_intake_model] = lambda: model


def post_input(key: str = "k1", project: str = "meme-demo", **extra: Any) -> httpx.Response:
    body = {"projectId": project, "title": "Añadir modo oscuro", "body": "Un botón de tema oscuro."}
    body.update(extra)
    return client.post("/api/v1/inputs", json=body, headers={"X-Idempotency-Key": key})


def item_count() -> int:
    with SessionLocal() as db:
        return db.scalar(select(func.count()).select_from(WorkItem)) or 0


def test_same_idempotency_key_twice_creates_one_item() -> None:
    use_model(FakeModel(assessment()))
    first = post_input("dup-1")
    second = post_input("dup-1")
    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]
    assert item_count() == 1


def test_unknown_project_is_404() -> None:
    use_model(FakeModel(assessment()))
    assert post_input(project="no-existe").status_code == 404
    assert item_count() == 0


def test_missing_idempotency_key_is_422() -> None:
    use_model(FakeModel(assessment()))
    body = {"projectId": "meme-demo", "title": "t", "body": "b"}
    assert client.post("/api/v1/inputs", json=body).status_code == 422


def test_high_confidence_accept_is_queued_with_auto_label() -> None:
    use_model(FakeModel(assessment()))
    item_id = post_input().json()["id"]
    detail = client.get(f"/api/v1/inputs/{item_id}").json()
    assert detail["status"] == QUEUED
    assert "factory:auto" in detail["labels"]
    assert detail["summary"] == "Resumen de prueba"
    assert detail["work_type"] == "feature"


def test_high_confidence_needs_info_is_not_queued() -> None:
    use_model(FakeModel(assessment(decision="needs_info")))
    item_id = post_input().json()["id"]
    assert client.get(f"/api/v1/inputs/{item_id}").json()["status"] == NEEDS_INFO


def test_low_confidence_goes_to_human_triage() -> None:
    use_model(FakeModel(assessment(confidence=0.5)))
    item_id = post_input().json()["id"]
    detail = client.get(f"/api/v1/inputs/{item_id}").json()
    assert detail["status"] == WAITING_HUMAN_TRIAGE
    assert "factory:auto" not in detail["labels"]


def test_invalid_json_goes_to_human_triage() -> None:
    use_model(ollama_with(ollama_reply("esto no es json")))
    item_id = post_input().json()["id"]
    detail = client.get(f"/api/v1/inputs/{item_id}").json()
    assert detail["status"] == WAITING_HUMAN_TRIAGE
    assert detail["reason"].startswith("Intake fallido")


def test_schema_violation_goes_to_human_triage() -> None:
    bad = json.dumps({"decision": "accept", "confidence": 1.7, "type": "feature"})
    use_model(ollama_with(ollama_reply(bad)))
    item_id = post_input().json()["id"]
    assert client.get(f"/api/v1/inputs/{item_id}").json()["status"] == WAITING_HUMAN_TRIAGE


def test_timeout_goes_to_human_triage_and_never_accepts() -> None:
    def timeout(_: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("tardó demasiado")

    use_model(ollama_with(timeout))
    item_id = post_input().json()["id"]
    detail = client.get(f"/api/v1/inputs/{item_id}").json()
    assert detail["status"] == WAITING_HUMAN_TRIAGE
    assert "factory:auto" not in detail["labels"]
    assert detail["events"][-1]["kind"] == "intake_failed"


def test_ollama_request_disables_thinking_and_sends_schema() -> None:
    sent: dict[str, Any] = {}

    def capture(request: httpx.Request) -> httpx.Response:
        sent.update(json.loads(request.content))
        return httpx.Response(200, json={"message": {"content": json.dumps({})}})

    use_model(ollama_with(capture))
    post_input()
    assert sent["think"] is False
    assert sent["stream"] is False
    assert sent["model"] == "qwen3.5:4b"
    assert sent["format"]["type"] == "object"
    assert "expandedBody" in sent["format"]["properties"]


def test_original_and_expanded_body_are_stored_separately() -> None:
    use_model(FakeModel(assessment(expandedBody="Versión ampliada de la petición.")))
    item_id = post_input(body="Pobre").json()["id"]
    detail = client.get(f"/api/v1/inputs/{item_id}").json()
    assert detail["body"] == "Pobre"
    assert detail["expanded_body"] == "Versión ampliada de la petición."
    assert detail["original_payload"]["body"] == "Pobre"


def test_manual_accept_from_human_triage_sets_label_and_is_audited() -> None:
    use_model(FakeModel(assessment(confidence=0.5)))
    item_id = post_input().json()["id"]
    response = client.post(
        f"/api/v1/inputs/{item_id}/decision", json={"action": "accept", "label": "factory:demo"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == QUEUED
    assert body["decision"] == "accept"
    assert "factory:demo" in body["labels"]
    kinds = [e["kind"] for e in body["events"]]
    assert kinds[-1] == "manual_decision"
    assert body["events"][-1]["actor"] == "admin@test.local"


def test_manual_decision_on_queued_item_is_409() -> None:
    use_model(FakeModel(assessment()))
    item_id = post_input().json()["id"]
    response = client.post(f"/api/v1/inputs/{item_id}/decision", json={"action": "reject"})
    assert response.status_code == 409


def test_event_frames_stream_each_audit_event() -> None:
    use_model(FakeModel(assessment()))
    with SessionLocal() as db:
        after = db.scalar(select(func.coalesce(func.max(WorkItemEvent.id), 0))) or 0
    post_input()
    frames = event_frames(after, poll_seconds=0)
    kinds = [json.loads(next(frames).split("data: ", 1)[1])["kind"] for _ in range(4)]
    assert kinds == ["received", "normalized", "triage_started", "intake_assessed"]


@pytest.mark.parametrize(
    ("decision", "confidence", "expected"),
    [
        ("accept", 0.80, QUEUED),
        ("accept", 0.79, WAITING_HUMAN_TRIAGE),
        ("accept", 0.65, WAITING_HUMAN_TRIAGE),
        ("accept", 0.64, WAITING_HUMAN_TRIAGE),
        ("needs_info", 0.90, NEEDS_INFO),
        ("reject", 0.90, REJECTED),
        ("reject", 0.70, WAITING_HUMAN_TRIAGE),
    ],
)
def test_plan_outcome_thresholds(decision: str, confidence: float, expected: str) -> None:
    status, _ = plan_outcome(assessment(decision=decision, confidence=confidence))
    assert status == expected




def test_model_slower_than_deadline_goes_to_human_triage(monkeypatch: pytest.MonkeyPatch) -> None:
    class SlowModel:
        def assess(self, item: IntakeInput) -> IntakeAssessment:
            time.sleep(1.0)
            return assessment()

    monkeypatch.setattr(get_settings(), "intake_deadline_seconds", 0.2)
    use_model(SlowModel())
    item_id = post_input().json()["id"]
    detail = client.get(f"/api/v1/inputs/{item_id}").json()
    assert detail["status"] == WAITING_HUMAN_TRIAGE
    assert "plazo" in detail["reason"]
    assert detail["events"][-1]["kind"] == "intake_failed"


def test_startup_sweep_moves_stuck_items_to_human_triage() -> None:
    with SessionLocal() as db:
        project = db.scalar(select(Project).where(Project.slug == "meme-demo"))
        assert project is not None
        for key, status in [("s-recv", RECEIVED), ("s-triage", TRIAGE), ("s-queued", QUEUED)]:
            db.add(
                WorkItem(
                    project_id=project.id,
                    idempotency_key=key,
                    source="api",
                    original_payload={"projectId": "meme-demo", "title": "t", "body": "b"},
                    title="t",
                    body="b",
                    status=status,
                    labels=[],
                )
            )
        db.commit()
        assert sweep_stuck_items(db) == 2
        statuses = {
            i.idempotency_key: i.status
            for i in db.scalars(select(WorkItem)).all()
        }
    assert statuses == {
        "s-recv": WAITING_HUMAN_TRIAGE,
        "s-triage": WAITING_HUMAN_TRIAGE,
        "s-queued": QUEUED,
    }
