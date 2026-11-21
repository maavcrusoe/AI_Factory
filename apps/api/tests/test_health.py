from unittest.mock import MagicMock

from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.db import get_db
from app.main import app


def test_health_ok_with_database() -> None:
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_health_503_when_database_unreachable() -> None:
    broken = MagicMock()
    broken.execute.side_effect = OperationalError("select 1", {}, Exception("down"))
    app.dependency_overrides[get_db] = lambda: broken
    try:
        response = TestClient(app).get("/health")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 503
    assert response.json()["database"] == "unreachable"
