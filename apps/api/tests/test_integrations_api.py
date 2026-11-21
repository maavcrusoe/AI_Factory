import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.config import get_settings
from app.db import SessionLocal
from app.main import app
from app.models import Project, ProjectIntegration, User
from app.security import hash_password
from app.seed import seed_demo_project

client = TestClient(app)
SLUG = "meme-demo"
TOKEN = "ghp_TOKEN_DE_API_NO_DEVOLVER"


@pytest.fixture(autouse=True)
def clean_integrations():
    seed_demo_project()  # el lifespan no corre con TestClient sin "with"
    with SessionLocal() as db:
        project = db.scalar(select(Project).where(Project.slug == SLUG))
        db.execute(delete(ProjectIntegration).where(ProjectIntegration.project_id == project.id))
        db.execute(delete(User).where(User.email == "miembro@test.local"))
        db.add(User(email="miembro@test.local", password_hash=hash_password("x-pass"), role="member"))
        db.commit()
    yield
    with SessionLocal() as db:
        project = db.scalar(select(Project).where(Project.slug == SLUG))
        db.execute(delete(ProjectIntegration).where(ProjectIntegration.project_id == project.id))
        db.execute(delete(User).where(User.email == "miembro@test.local"))
        db.commit()


def _login(email: str, password: str) -> dict[str, str]:
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _admin() -> dict[str, str]:
    return _login("admin@test.local", "test-password")


def test_admin_saves_token_encrypted_and_response_never_contains_it():
    body = {"provider": "github", "config": {"repo": "maavcrusoe/meme-demo"}, "token": TOKEN}
    resp = client.put(f"/api/v1/projects/{SLUG}/integration", json=body, headers=_admin())

    assert resp.status_code == 200
    assert resp.json()["has_token"] is True
    assert TOKEN not in resp.text
    got = client.get(f"/api/v1/projects/{SLUG}/integration", headers=_admin())
    assert got.json()["has_token"] is True and TOKEN not in got.text
    with SessionLocal() as db:
        stored = db.scalar(select(ProjectIntegration.token_encrypted))
    assert stored and TOKEN not in stored


def test_update_without_token_keeps_stored_token():
    headers = _admin()
    client.put(
        f"/api/v1/projects/{SLUG}/integration",
        json={"provider": "github", "config": {"repo": "maavcrusoe/meme-demo"}, "token": TOKEN},
        headers=headers,
    )
    resp = client.put(
        f"/api/v1/projects/{SLUG}/integration",
        json={"provider": "github", "config": {"repo": "maavcrusoe/meme-demo", "label": "factory"}},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["has_token"] is True


def test_non_admin_is_forbidden():
    resp = client.put(
        f"/api/v1/projects/{SLUG}/integration",
        json={"provider": "github", "config": {"repo": "maavcrusoe/meme-demo"}, "token": TOKEN},
        headers=_login("miembro@test.local", "x-pass"),
    )
    assert resp.status_code == 403


def test_token_inside_config_is_rejected():
    resp = client.put(
        f"/api/v1/projects/{SLUG}/integration",
        json={"provider": "github", "config": {"repo": "maavcrusoe/meme-demo", "token": TOKEN}, "token": TOKEN},
        headers=_admin(),
    )
    assert resp.status_code == 422


def test_invalid_config_and_short_poll_are_rejected():
    headers = _admin()
    bad_repo = client.put(
        f"/api/v1/projects/{SLUG}/integration",
        json={"provider": "github", "config": {"repo": "sin-barra"}, "token": TOKEN},
        headers=headers,
    )
    fast_poll = client.put(
        f"/api/v1/projects/{SLUG}/integration",
        json={"provider": "github", "config": {"repo": "a/b", "pollSeconds": 1}, "token": TOKEN},
        headers=headers,
    )
    assert bad_repo.status_code == 422
    assert fast_poll.status_code == 422


def test_provider_requires_token_except_generic():
    resp = client.put(
        f"/api/v1/projects/{SLUG}/integration",
        json={"provider": "github", "config": {"repo": "maavcrusoe/meme-demo"}},
        headers=_admin(),
    )
    assert resp.status_code == 422


def test_saving_token_without_key_is_503_and_stores_nothing(monkeypatch):
    monkeypatch.setattr(get_settings(), "token_encryption_key", None)
    resp = client.put(
        f"/api/v1/projects/{SLUG}/integration",
        json={"provider": "github", "config": {"repo": "maavcrusoe/meme-demo"}, "token": TOKEN},
        headers=_admin(),
    )
    assert resp.status_code == 503
    assert TOKEN not in resp.text
    with SessionLocal() as db:
        assert db.scalar(select(ProjectIntegration)) is None


def test_repo_change_is_blocked_only_while_items_are_linked():
    from app.models import TrackerLink, WorkItem, WorkItemEvent
    from app.services.ingest import ingest

    headers = _admin()
    url = f"/api/v1/projects/{SLUG}/integration"
    body_a = {"provider": "github", "config": {"repo": "maavcrusoe/meme-demo"}, "token": TOKEN}
    body_b = {"provider": "github", "config": {"repo": "maavcrusoe/otro-repo"}, "token": TOKEN}
    assert client.put(url, json=body_a, headers=headers).status_code == 200
    assert client.put(url, json=body_b, headers=headers).status_code == 200  # sin enlaces: permitido

    with SessionLocal() as db:
        project = db.scalar(select(Project).where(Project.slug == SLUG))
        item, _ = ingest(
            db, project, source="github", title="t", body="b", payload={},
            idempotency_key="github:777", actor="test",
            link={"provider": "github", "remote_id": "777", "remote_url": None},
        )
        item_id = item.id
    try:
        blocked = client.put(url, json=body_a, headers=headers)
        assert blocked.status_code == 409
        assert client.put(url, json=body_b, headers=headers).status_code == 200  # mismo repo: permitido
    finally:
        with SessionLocal() as db:
            db.execute(delete(TrackerLink).where(TrackerLink.work_item_id == item_id))
            db.execute(delete(WorkItemEvent).where(WorkItemEvent.work_item_id == item_id))
            db.execute(delete(WorkItem).where(WorkItem.id == item_id))
            db.commit()
