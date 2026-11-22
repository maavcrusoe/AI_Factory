import hashlib
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.db import SessionLocal
from app.main import app
from app.models import DeveloperToken, Project, User, WorkItem, WorkItemEvent
from app.security import hash_password
from app.services import claims
from app.services.intake import QUEUED

client = TestClient(app)
SLUG = "fase3-api"
DEV1 = "api-dev1@test.local"
DEV2 = "api-dev2@test.local"
T0 = datetime(2026, 11, 21, 12, 0, tzinfo=UTC)


def _login(email: str, password: str) -> str:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def _dev_token(email: str) -> str:
    session = _login(email, "pw-test")
    response = client.post(
        "/api/v1/tokens", json={"name": "portátil"}, headers={"Authorization": f"Bearer {session}"}
    )
    assert response.status_code == 201, response.text
    return response.json()["token"]


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def world():
    with SessionLocal() as db:
        if db.scalar(select(Project).where(Project.slug == SLUG)) is None:
            db.add(Project(slug=SLUG, name="Fase 3 API"))
        for email in (DEV1, DEV2):
            if db.scalar(select(User).where(User.email == email)) is None:
                db.add(User(email=email, password_hash=hash_password("pw-test"), role="developer"))
        db.commit()
        project_id = db.scalar(select(Project.id).where(Project.slug == SLUG))
        db.execute(delete(WorkItemEvent).where(WorkItemEvent.work_item_id.in_(
            select(WorkItem.id).where(WorkItem.project_id == project_id))))
        db.execute(delete(WorkItem).where(WorkItem.project_id == project_id))
        db.commit()
    yield {"project": SLUG, "dev1": _dev_token(DEV1), "dev2": _dev_token(DEV2)}


def _queued(title: str) -> int:
    with SessionLocal() as db:
        project = db.scalar(select(Project).where(Project.slug == SLUG))
        item = WorkItem(
            project_id=project.id,
            idempotency_key=str(uuid4()),
            source="api",
            original_payload={},
            title=title,
            body="cuerpo",
            status=QUEUED,
            labels=[],
        )
        db.add(item)
        db.commit()
        return item.id


def test_queue_lists_only_queued_oldest_first(world):
    first = _queued("primero")
    second = _queued("segundo")
    claims.claim(SessionLocal(), first, DEV1)
    response = client.get(f"/api/v1/projects/{SLUG}/queue", headers=_headers(world["dev2"]))
    assert response.status_code == 200
    assert [row["id"] for row in response.json()] == [second]


def test_claim_second_developer_gets_409_with_owner(world):
    item_id = _queued("meme")
    first = client.post(f"/api/v1/work/{item_id}/claim", headers=_headers(world["dev1"]))
    assert first.status_code == 200
    assert first.json()["owner"] == DEV1
    second = client.post(f"/api/v1/work/{item_id}/claim", headers=_headers(world["dev2"]))
    assert second.status_code == 409
    assert second.json()["detail"] == "ya cogido por api-dev1"


def test_heartbeat_after_expiry_is_409_over_http(world):
    item_id = _queued("meme")
    client.post(f"/api/v1/work/{item_id}/claim", headers=_headers(world["dev1"]))
    with SessionLocal() as db:
        claims.expire_stale_claims(db, now=datetime.now(UTC) + timedelta(days=1))
    response = client.post(
        f"/api/v1/work/{item_id}/heartbeat",
        json={"state": "working"},
        headers=_headers(world["dev1"]),
    )
    assert response.status_code == 409


def test_heartbeat_release_and_event_over_http(world):
    item_id = _queued("meme")
    client.post(f"/api/v1/work/{item_id}/claim", headers=_headers(world["dev1"]))
    beat = client.post(
        f"/api/v1/work/{item_id}/heartbeat",
        json={"state": "testing", "message": "pasando tests"},
        headers=_headers(world["dev1"]),
    )
    assert beat.status_code == 200
    assert beat.json()["heartbeat_state"] == "testing"
    assert beat.json()["heartbeat_message"] == "pasando tests"
    log = client.post(
        f"/api/v1/work/{item_id}/events",
        json={"kind": "log", "message": "build ok", "detail": {"ms": 1200}},
        headers=_headers(world["dev1"]),
    )
    assert log.status_code == 201
    release = client.post(
        f"/api/v1/work/{item_id}/release",
        json={"reason": "sin crédito"},
        headers=_headers(world["dev1"]),
    )
    assert release.status_code == 200
    assert release.json()["status"] == QUEUED
    assert release.json()["owner"] is None


def test_events_reject_long_kind_and_big_detail(world):
    item_id = _queued("meme")
    client.post(f"/api/v1/work/{item_id}/claim", headers=_headers(world["dev1"]))
    long_kind = client.post(
        f"/api/v1/work/{item_id}/events",
        json={"kind": "k" * 41, "message": "x"},
        headers=_headers(world["dev1"]),
    )
    assert long_kind.status_code == 422
    big = client.post(
        f"/api/v1/work/{item_id}/events",
        json={"kind": "log", "message": "x", "detail": {"blob": "a" * 4001}},
        headers=_headers(world["dev1"]),
    )
    assert big.status_code == 422


def test_dev_token_is_stored_only_as_hash(world):
    plaintext = world["dev1"]
    assert plaintext.startswith("fct_")
    with SessionLocal() as db:
        rows = db.scalars(select(DeveloperToken)).all()
        assert all(plaintext not in str(vars(row)) for row in rows)
        assert hashlib.sha256(plaintext.encode()).hexdigest() in {row.token_hash for row in rows}


def test_wrong_and_revoked_tokens_are_401(world):
    assert client.get(f"/api/v1/projects/{SLUG}/queue", headers=_headers("fct_inventado")).status_code == 401
    session = _login(DEV2, "pw-test")
    created = client.post("/api/v1/tokens", json={"name": "temporal"}, headers=_headers(session)).json()
    assert client.get(f"/api/v1/projects/{SLUG}/queue", headers=_headers(created["token"])).status_code == 200
    assert client.delete(f"/api/v1/tokens/{created['id']}", headers=_headers(session)).status_code == 200
    assert client.get(f"/api/v1/projects/{SLUG}/queue", headers=_headers(created["token"])).status_code == 401
