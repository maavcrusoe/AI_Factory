"""Fase 6: resumen de proyectos, filtros del tablero, admin de usuarios, ajustes, retención y SSE de latidos."""

from datetime import UTC, datetime, timedelta
from itertools import islice
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select

from app.db import SessionLocal
from app.main import app
from app.models import Project, User, WorkArtifact, WorkItem, WorkItemEvent
from app.routers.inputs import event_frames
from app.security import hash_password
from app.services import claims
from app.services.intake import QUEUED
from app.services.retention import purge_old_logs

client = TestClient(app)
SLUG = "fase6-dash"
OTHER_SLUG = "fase6-otro"
DEV = "fase6-dev@test.local"
ADMIN = "admin@test.local"
NOW = datetime(2026, 11, 22, 12, 0, tzinfo=UTC)


def _login(email: str, password: str) -> dict[str, str]:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def admin_headers():
    with SessionLocal() as db:
        for slug in (SLUG, OTHER_SLUG):
            if db.scalar(select(Project).where(Project.slug == slug)) is None:
                db.add(Project(slug=slug, name=slug))
        if db.scalar(select(User).where(User.email == DEV)) is None:
            db.add(User(email=DEV, password_hash=hash_password("pw-test"), role="developer"))
        db.commit()
        for slug in (SLUG, OTHER_SLUG):
            pid = db.scalar(select(Project.id).where(Project.slug == slug))
            db.execute(delete(WorkArtifact).where(WorkArtifact.work_item_id.in_(
                select(WorkItem.id).where(WorkItem.project_id == pid))))
            db.execute(delete(WorkItemEvent).where(WorkItemEvent.work_item_id.in_(
                select(WorkItem.id).where(WorkItem.project_id == pid))))
            db.execute(delete(WorkItem).where(WorkItem.project_id == pid))
        db.commit()
    return _login(ADMIN, "test-password")


def _item(slug: str, title: str, source: str = "api", status: str = QUEUED) -> int:
    with SessionLocal() as db:
        project = db.scalar(select(Project).where(Project.slug == slug))
        item = WorkItem(
            project_id=project.id,
            idempotency_key=str(uuid4()),
            source=source,
            original_payload={},
            title=title,
            body="cuerpo",
            status=status,
            labels=[],
        )
        db.add(item)
        db.commit()
        return item.id


def test_projects_summary_counts_items_by_status(admin_headers):
    _item(SLUG, "a")
    _item(SLUG, "b", status="PR_OPEN")
    response = client.get("/api/v1/projects", headers=admin_headers)
    assert response.status_code == 200
    summary = {p["slug"]: p for p in response.json()}
    assert summary[SLUG]["total"] == 2
    assert summary[SLUG]["by_status"] == {QUEUED: 1, "PR_OPEN": 1}
    assert summary[OTHER_SLUG]["total"] == 0


def test_projects_summary_needs_a_session():
    assert client.get("/api/v1/projects").status_code == 401


def test_inputs_filters_by_project_owner_and_source(admin_headers):
    mine = _item(SLUG, "de dev", source="github")
    _item(SLUG, "api", source="api")
    _item(OTHER_SLUG, "otro proyecto", source="github")
    with SessionLocal() as db:
        claims.claim(db, mine, DEV)

    rows = client.get("/api/v1/inputs?project=" + SLUG, headers=admin_headers).json()
    assert {r["title"] for r in rows} == {"de dev", "api"}
    assert all(r["project_slug"] == SLUG for r in rows)

    by_owner = client.get(f"/api/v1/inputs?owner={DEV}", headers=admin_headers).json()
    assert [r["id"] for r in by_owner] == [mine]
    assert by_owner[0]["owner"] == DEV

    by_source = client.get("/api/v1/inputs?project=" + SLUG + "&source=github", headers=admin_headers).json()
    assert [r["title"] for r in by_source] == ["de dev"]


def test_admin_changes_role_and_deactivation_blocks_the_user(admin_headers):
    with SessionLocal() as db:
        dev_id = db.scalar(select(User.id).where(User.email == DEV))
    dev_headers = _login(DEV, "pw-test")

    response = client.patch(f"/api/v1/users/{dev_id}", json={"role": "reviewer"}, headers=admin_headers)
    assert response.status_code == 200, response.text
    assert response.json()["role"] == "reviewer"

    response = client.patch(f"/api/v1/users/{dev_id}", json={"is_active": False}, headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["is_active"] is False
    assert client.get("/api/v1/auth/me", headers=dev_headers).status_code == 401

    client.patch(f"/api/v1/users/{dev_id}", json={"is_active": True, "role": "developer"}, headers=admin_headers)


def test_admin_cannot_demote_or_deactivate_himself(admin_headers):
    me = client.get("/api/v1/auth/me", headers=admin_headers).json()
    assert client.patch(f"/api/v1/users/{me['id']}", json={"role": "developer"}, headers=admin_headers).status_code == 422
    assert client.patch(f"/api/v1/users/{me['id']}", json={"is_active": False}, headers=admin_headers).status_code == 422


def test_only_admin_changes_users_and_unknown_user_is_404(admin_headers):
    dev_headers = _login(DEV, "pw-test")
    assert client.patch("/api/v1/users/1", json={"role": "admin"}, headers=dev_headers).status_code == 403
    assert client.patch("/api/v1/users/999999", json={"role": "admin"}, headers=admin_headers).status_code == 404
    assert client.patch("/api/v1/users/1", json={"password": "x"}, headers=admin_headers).status_code == 422


def test_settings_expose_retention_default_and_heartbeat_timeout(admin_headers):
    body = client.get("/api/v1/settings", headers=admin_headers).json()
    assert body == {"log_retention_days": 30, "heartbeat_timeout_seconds": 30 * 60}


def test_retention_deletes_only_old_logs(admin_headers):
    item_id = _item(SLUG, "retención")
    with SessionLocal() as db:
        db.add_all([
            WorkArtifact(work_item_id=item_id, client_key="old-log", stage="build", round=0, kind="log",
                         content="viejo", created_at=NOW - timedelta(days=31)),
            WorkArtifact(work_item_id=item_id, client_key="new-log", stage="build", round=0, kind="log",
                         content="nuevo", created_at=NOW - timedelta(days=29)),
            WorkArtifact(work_item_id=item_id, client_key="old-diff", stage="build", round=0, kind="diff",
                         content="diff", created_at=NOW - timedelta(days=400)),
        ])
        db.commit()
        removed = purge_old_logs(db, days=30, now=NOW)

    assert removed == 1
    with SessionLocal() as db:
        keys = set(db.scalars(select(WorkArtifact.client_key).where(WorkArtifact.work_item_id == item_id)))
        assert keys == {"new-log", "old-diff"}


def test_heartbeat_pushes_a_work_updated_frame_without_audit_event(admin_headers):
    item_id = _item(SLUG, "latido")
    with SessionLocal() as db:
        after = db.scalar(select(func.coalesce(func.max(WorkItemEvent.id), 0))) or 0
        since = db.scalar(select(func.now()))
        claims.claim(db, item_id, DEV)
        claims.heartbeat(db, item_id, DEV, "working", "compilando")

    frames = list(islice(event_frames(after, since, poll_seconds=0), 3))
    assert any(f'"kind": "work_updated", "workItemId": {item_id}' in f for f in frames), frames
