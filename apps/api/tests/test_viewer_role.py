"""Rol viewer: lee /metrics y vistas de lectura; todo lo demás, 403. admin conserva el acceso."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import SessionLocal
from app.main import app
from app.models import User
from app.security import hash_password

client = TestClient(app)
VIEWER = "viewer-f15@test.local"
PASSWORD = "pw-test"


@pytest.fixture(scope="module")
def viewer() -> dict[str, str]:
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.email == VIEWER)) is None:
            db.add(User(email=VIEWER, password_hash=hash_password(PASSWORD), role="viewer"))
            db.commit()
    return _login(VIEWER, PASSWORD)


def _login(email: str, password: str) -> dict[str, str]:
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_viewer_reads_metrics_and_dashboard_views(viewer) -> None:
    assert client.get("/metrics", headers=viewer).status_code == 200
    for path in ("/api/v1/projects", "/api/v1/inputs", "/api/v1/approvals", "/api/v1/auth/me", "/api/v1/settings"):
        assert client.get(path, headers=viewer).status_code == 200, path


def test_admin_keeps_metrics() -> None:
    assert client.get("/metrics", headers=_login("admin@test.local", "test-password")).status_code == 200


def test_viewer_is_denied_every_write(viewer) -> None:
    calls = [
        ("post", "/api/v1/inputs", {"json": {"projectId": "x", "title": "t", "body": "b"}, "headers": {**viewer, "X-Idempotency-Key": "viewer-1"}}),
        ("post", "/api/v1/inputs/1/decision", {"json": {"action": "reject"}, "headers": viewer}),
        ("post", "/api/v1/work/1/approve", {"json": {"reason": "ok", "expected_version": 1}, "headers": viewer}),
        ("post", "/api/v1/work/1/claim", {"headers": viewer}),
        ("post", "/api/v1/work/1/heartbeat", {"headers": viewer}),
        ("post", "/api/v1/users", {"json": {"email": "x@test.local", "password": "long-password-1", "role": "viewer"}, "headers": viewer}),
        ("get", "/api/v1/users", {"headers": viewer}),
    ]
    for method, path, kwargs in calls:
        assert getattr(client, method)(path, **kwargs).status_code == 403, path


def test_metrics_still_denies_developer_and_anonymous() -> None:
    assert client.get("/metrics").status_code == 401
