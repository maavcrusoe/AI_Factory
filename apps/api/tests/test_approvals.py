"""Roles, políticas versionadas, bloqueo optimista y merge controlado (Fase 5). Remoto falso, sin red."""

from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

import app.services.merge as merge_mod
from app.adapters.github import GitHubAdapter
from app.db import SessionLocal
from app.main import app
from app.models import MergePolicy, Project, ProjectIntegration, TrackerLink, User, WorkItem, WorkItemEvent
from app.security import hash_password
from app.services.crypto import encrypt_token
from tests.fakes import FakeGitHub

client = TestClient(app)
SLUG = "fase5-api"
REVIEWER = "rev-f5@test.local"
DEV = "dev-f5@test.local"
DEV2 = "dev2-f5@test.local"
ADMIN = ("admin@test.local", "test-password")
SHA_1 = "1" * 40
SHA_2 = "2" * 40
PASSWORD = "pw-test"


def _login(email: str, password: str) -> dict[str, str]:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _ensure_user(db, email: str, role: str) -> None:
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        db.add(User(email=email, password_hash=hash_password(PASSWORD), role=role))
    else:
        user.role = role
        user.password_hash = hash_password(PASSWORD)
        user.is_active = True


@pytest.fixture
def world(monkeypatch):
    fake = FakeGitHub()
    fake.add_pull(9, SHA_1, draft=True)
    monkeypatch.setitem(
        merge_mod.ADAPTERS,
        "github",
        lambda config, token: GitHubAdapter(config, token, transport=httpx.MockTransport(fake.handler)),
    )
    with SessionLocal() as db:
        if db.scalar(select(Project).where(Project.slug == SLUG)) is None:
            db.add(Project(slug=SLUG, name="Fase 5 API"))
            db.commit()
        project = db.scalar(select(Project).where(Project.slug == SLUG))
        item_ids = select(WorkItem.id).where(WorkItem.project_id == project.id)
        db.execute(delete(WorkItemEvent).where(WorkItemEvent.work_item_id.in_(item_ids)))
        db.execute(delete(TrackerLink).where(TrackerLink.project_id == project.id))
        db.execute(delete(WorkItem).where(WorkItem.project_id == project.id))
        db.execute(delete(MergePolicy).where(MergePolicy.project_id == project.id))
        db.execute(delete(ProjectIntegration).where(ProjectIntegration.project_id == project.id))
        db.add(
            ProjectIntegration(
                project_id=project.id,
                provider="github",
                config={"repo": "maavcrusoe/meme-demo"},
                token_encrypted=encrypt_token("tracker-token"),
                merge_token_encrypted=encrypt_token("merge-secret"),
            )
        )
        _ensure_user(db, REVIEWER, "reviewer")
        _ensure_user(db, DEV, "developer")
        _ensure_user(db, DEV2, "developer")
        db.commit()
        project_id = project.id
    yield {
        "fake": fake,
        "reviewer": _login(REVIEWER, PASSWORD),
        "dev": _login(DEV, PASSWORD),
        "dev2": _login(DEV2, PASSWORD),
        "admin": _login(*ADMIN),
        "project_id": project_id,
    }
    # Limpieza: otros tests comprueban que no hay integraciones; no dejar la de este módulo.
    with SessionLocal() as db:
        db.execute(delete(ProjectIntegration).where(ProjectIntegration.project_id == project_id))
        db.commit()


def _pr_item(project_id: int, status: str = "PR_OPEN") -> int:
    with SessionLocal() as db:
        item = WorkItem(
            project_id=project_id,
            idempotency_key=str(uuid4()),
            source="api",
            original_payload={},
            title="meme",
            body="cuerpo",
            status=status,
            owner=DEV,
            pr_number=9,
            pr_url="https://github.com/maavcrusoe/meme-demo/pull/9",
            difficulty="low",
            labels=[],
        )
        db.add(item)
        db.commit()
        return item.id


def _gate(item_id: int, headers: dict, sha: str = SHA_1, result: str = "passed", **extra) -> dict:
    body = {
        "sha": sha,
        "result": result,
        "meaning_change": "none",
        "planned": True,
        "touched_paths": ["src/button.tsx"],
        "review_findings": [],
        **extra,
    }
    response = client.post(f"/api/v1/work/{item_id}/gate-report", json=body, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def _detail(item_id: int, headers: dict) -> dict:
    response = client.get(f"/api/v1/inputs/{item_id}", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def _set_policy(headers: dict, **body) -> None:
    policy = {
        "require_human_always": False,
        "human_if_difficulty": [],
        "sensitive_paths": [],
        "human_if_unplanned": False,
        "human_if_meaning": [],
        **body,
    }
    response = client.put(f"/api/v1/projects/{SLUG}/merge-policy", json=policy, headers=headers)
    assert response.status_code == 201, response.text


def _kinds(item_id: int, headers: dict) -> list[str]:
    return [event["kind"] for event in _detail(item_id, headers)["events"]]


def test_wrong_roles_get_403_and_no_session_gets_401(world) -> None:
    item_id = _pr_item(world["project_id"])
    assert client.post(f"/api/v1/work/{item_id}/approve", json={"expected_version": 0}, headers=world["dev"]).status_code == 403
    assert client.post("/api/v1/users", json={"email": "x@t.local", "password": "12345678", "role": "admin"}, headers=world["reviewer"]).status_code == 403
    assert client.put(f"/api/v1/projects/{SLUG}/merge-policy", json={}, headers=world["dev"]).status_code == 403
    assert client.post(f"/api/v1/work/{item_id}/approve", json={"expected_version": 0}).status_code == 401


def test_admin_creates_users_duplicates_and_bad_roles_are_rejected(world) -> None:
    email = f"nuevo-{uuid4().hex[:8]}@test.local"
    body = {"email": email, "password": "contraseña-larga", "role": "reviewer"}
    created = client.post("/api/v1/users", json=body, headers=world["admin"])
    assert created.status_code == 201, created.text
    assert created.json()["role"] == "reviewer"
    assert client.post("/api/v1/users", json=body, headers=world["admin"]).status_code == 409
    assert client.post("/api/v1/users", json={**body, "role": "member"}, headers=world["admin"]).status_code == 422
    assert _login(email, "contraseña-larga")


def test_policy_is_versioned_and_default_is_human_for_everything(world) -> None:
    assert client.get(f"/api/v1/projects/{SLUG}/merge-policy", headers=world["reviewer"]).json()["version"] == 0
    _set_policy(world["admin"], require_human_always=True)
    _set_policy(world["admin"], require_human_always=False)
    latest = client.get(f"/api/v1/projects/{SLUG}/merge-policy", headers=world["reviewer"]).json()
    assert latest["version"] == 2
    assert latest["body"]["require_human_always"] is False


def test_gate_passed_under_default_policy_waits_for_human(world) -> None:
    item_id = _pr_item(world["project_id"])
    detail = _gate(item_id, world["dev"])
    assert detail["status"] == "WAITING_HUMAN_MERGE"
    assert "política: todo merge requiere humano" in detail["policy_reasons"]
    assert detail["approval_version"] == 1
    queue = client.get("/api/v1/approvals", headers=world["reviewer"]).json()
    assert item_id in [row["id"] for row in queue]


def test_approve_with_stale_version_is_409_and_second_approve_is_409(world) -> None:
    item_id = _pr_item(world["project_id"])
    _gate(item_id, world["dev"])
    first = client.post(f"/api/v1/work/{item_id}/approve", json={"expected_version": 1}, headers=world["reviewer"])
    assert first.status_code == 200, first.text
    assert first.json()["status"] == "READY_TO_MERGE"
    second = client.post(f"/api/v1/work/{item_id}/approve", json={"expected_version": 1}, headers=world["reviewer"])
    assert second.status_code == 409
    assert "recarga" in second.json()["detail"]


def test_approval_on_old_sha_is_stale_after_changes_and_a_new_report(world) -> None:
    item_id = _pr_item(world["project_id"])
    _gate(item_id, world["dev"], sha=SHA_1)
    seen = _detail(item_id, world["reviewer"])["approval_version"]
    changed = client.post(
        f"/api/v1/work/{item_id}/request-changes",
        json={"expected_version": seen, "reason": "revisar"},
        headers=world["reviewer"],
    )
    assert changed.status_code == 200, changed.text
    _gate(item_id, world["dev"], sha=SHA_2)
    stale = client.post(f"/api/v1/work/{item_id}/approve", json={"expected_version": seen}, headers=world["reviewer"])
    assert stale.status_code == 409
    current = _detail(item_id, world["reviewer"])["approval_version"]
    fresh = client.post(f"/api/v1/work/{item_id}/approve", json={"expected_version": current}, headers=world["reviewer"])
    assert fresh.status_code == 200, fresh.text


def test_ready_item_cannot_be_reported_again(world) -> None:
    item_id = _pr_item(world["project_id"])
    _gate(item_id, world["dev"], sha=SHA_1)
    client.post(f"/api/v1/work/{item_id}/approve", json={"expected_version": 1}, headers=world["reviewer"])
    body = {"sha": SHA_2, "result": "passed", "meaning_change": "none", "planned": True, "touched_paths": []}
    assert client.post(f"/api/v1/work/{item_id}/gate-report", json=body, headers=world["dev"]).status_code == 409


def test_approved_item_merges_exact_sha_with_merge_credential_and_audits_each_step(world) -> None:
    item_id = _pr_item(world["project_id"])
    _gate(item_id, world["dev"])
    approved = client.post(f"/api/v1/work/{item_id}/approve", json={"expected_version": 1}, headers=world["reviewer"])
    merged = client.post(
        f"/api/v1/work/{item_id}/merge",
        json={"expected_version": approved.json()["approval_version"]},
        headers=world["reviewer"],
    )
    assert merged.status_code == 200, merged.text
    assert merged.json()["status"] == "MERGED"
    assert world["fake"].merges == [(9, SHA_1)]
    merge_calls = [r for r in world["fake"].requests if r.method == "PUT" and r.url.path.endswith("/merge")]
    assert merge_calls[-1].headers["Authorization"] == "Bearer merge-secret"
    kinds = _kinds(item_id, world["reviewer"])
    for kind in ("gate_reported", "policy_evaluated", "approved", "merge_started", "merged"):
        assert kind in kinds
    approved_event = next(e for e in merged.json()["events"] if e["kind"] == "approved")
    assert approved_event["detail"]["gate_sha"] == SHA_1


def test_relaxed_policy_merges_trivial_change_without_human(world) -> None:
    _set_policy(world["admin"])
    item_id = _pr_item(world["project_id"])
    detail = _gate(item_id, world["dev"])
    assert detail["status"] == "MERGED"
    assert world["fake"].merges == [(9, SHA_1)]
    policy_event = next(e for e in detail["events"] if e["kind"] == "policy_evaluated")
    assert policy_event["actor"] == "system:policy"


def test_relaxed_policy_still_waits_for_human_on_sensitive_path(world) -> None:
    _set_policy(world["admin"], sensitive_paths=["auth/**"])
    item_id = _pr_item(world["project_id"])
    detail = _gate(item_id, world["dev"], touched_paths=["auth/login.py"])
    assert detail["status"] == "WAITING_HUMAN_MERGE"
    assert detail["policy_reasons"] == ["ruta sensible: auth/login.py"]
    assert world["fake"].merges == []


def test_head_moved_after_gate_rejects_merge_and_returns_to_pr_open(world) -> None:
    item_id = _pr_item(world["project_id"])
    _gate(item_id, world["dev"])
    approved = client.post(f"/api/v1/work/{item_id}/approve", json={"expected_version": 1}, headers=world["reviewer"])
    world["fake"].move_head(9, SHA_2)
    response = client.post(
        f"/api/v1/work/{item_id}/merge",
        json={"expected_version": approved.json()["approval_version"]},
        headers=world["reviewer"],
    )
    assert response.status_code == 409
    detail = _detail(item_id, world["reviewer"])
    assert detail["status"] == "PR_OPEN"
    assert detail["gate_result"] is None
    assert "merge_rejected_sha" in [e["kind"] for e in detail["events"]]
    assert world["fake"].merges == []


def test_request_changes_moves_to_fixing_and_owner_reports_again(world) -> None:
    item_id = _pr_item(world["project_id"])
    _gate(item_id, world["dev"])
    changed = client.post(
        f"/api/v1/work/{item_id}/request-changes",
        json={"expected_version": 1, "reason": "el botón no es accesible"},
        headers=world["reviewer"],
    )
    assert changed.status_code == 200, changed.text
    assert changed.json()["status"] == "FIXING"
    again = _gate(item_id, world["dev"], sha=SHA_2)
    assert again["status"] == "WAITING_HUMAN_MERGE"


def test_failed_gate_keeps_pr_open_and_cannot_be_approved(world) -> None:
    item_id = _pr_item(world["project_id"])
    detail = _gate(item_id, world["dev"], result="failed")
    assert detail["status"] == "PR_OPEN"
    assert detail["gate_result"] == "failed"
    response = client.post(f"/api/v1/work/{item_id}/approve", json={"expected_version": 1}, headers=world["reviewer"])
    assert response.status_code == 409


def test_only_the_owner_reports_the_gate(world) -> None:
    item_id = _pr_item(world["project_id"])
    body = {"sha": SHA_1, "result": "passed", "meaning_change": "none", "planned": True, "touched_paths": []}
    assert client.post(f"/api/v1/work/{item_id}/gate-report", json=body, headers=world["dev2"]).status_code == 409


def test_merge_without_merge_credential_is_422_and_keeps_ready(world) -> None:
    item_id = _pr_item(world["project_id"])
    _gate(item_id, world["dev"])
    approved = client.post(f"/api/v1/work/{item_id}/approve", json={"expected_version": 1}, headers=world["reviewer"])
    with SessionLocal() as db:
        integration = db.scalar(select(ProjectIntegration).where(ProjectIntegration.project_id == world["project_id"]))
        integration.merge_token_encrypted = None
        db.commit()
    response = client.post(
        f"/api/v1/work/{item_id}/merge",
        json={"expected_version": approved.json()["approval_version"]},
        headers=world["reviewer"],
    )
    assert response.status_code == 422
    assert _detail(item_id, world["reviewer"])["status"] == "READY_TO_MERGE"


def test_merge_credential_is_admin_only_and_never_returned(world) -> None:
    body = {"token": "otro-token-de-merge"}
    assert client.put(f"/api/v1/projects/{SLUG}/merge-credential", json=body, headers=world["dev"]).status_code == 403
    response = client.put(f"/api/v1/projects/{SLUG}/merge-credential", json=body, headers=world["admin"])
    assert response.status_code == 200
    assert response.json()["has_merge_token"] is True
    assert "otro-token-de-merge" not in response.text
