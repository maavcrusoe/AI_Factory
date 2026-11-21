from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_login_with_admin_returns_token() -> None:
    response = client.post(
        "/api/v1/auth/login", json={"email": "admin@test.local", "password": "test-password"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["user"] == {"id": body["user"]["id"], "email": "admin@test.local", "role": "admin"}
    assert body["token_type"] == "bearer"


def test_login_wrong_password_is_401() -> None:
    response = client.post(
        "/api/v1/auth/login", json={"email": "admin@test.local", "password": "bad"}
    )
    assert response.status_code == 401


def test_me_requires_valid_token() -> None:
    token = client.post(
        "/api/v1/auth/login", json={"email": "admin@test.local", "password": "test-password"}
    ).json()["access_token"]
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get("/api/v1/auth/me", headers={"Authorization": "Bearer nope"}).status_code == 401
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "admin@test.local"
