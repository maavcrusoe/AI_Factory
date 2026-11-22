import threading
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import delete, select

from app.db import SessionLocal
from app.models import Project, User, WorkItem, WorkItemEvent
from app.security import hash_password
from app.services import claims
from app.services.intake import QUEUED
from app.services.tracker_sync import TAKEN_PREFIX

SLUG = "fase3-demo"
DEV1 = "dev1@test.local"
DEV2 = "dev2@test.local"
T0 = datetime(2026, 11, 21, 12, 0, tzinfo=UTC)
TIMEOUT = 1800


def _ensure_user(db, email: str) -> None:
    if db.scalar(select(User).where(User.email == email)) is None:
        db.add(User(email=email, password_hash=hash_password("pw-test"), role="developer"))
        db.commit()


@pytest.fixture
def db():
    with SessionLocal() as session:
        project = session.scalar(select(Project).where(Project.slug == SLUG))
        if project is None:
            session.add(Project(slug=SLUG, name="Fase 3"))
            session.commit()
        _ensure_user(session, DEV1)
        _ensure_user(session, DEV2)
        yield session
        project = session.scalar(select(Project).where(Project.slug == SLUG))
        ids = select(WorkItem.id).where(WorkItem.project_id == project.id)
        session.execute(delete(WorkItemEvent).where(WorkItemEvent.work_item_id.in_(ids)))
        session.execute(delete(WorkItem).where(WorkItem.project_id == project.id))
        session.commit()


def new_item(db, title: str = "Meme") -> WorkItem:
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
    return item


def conflict_detail(exc: HTTPException) -> str:
    assert exc.status_code == 409
    return exc.detail


def test_first_claim_wins_second_gets_409_with_owner(db):
    item = new_item(db)
    claims.claim(db, item.id, DEV1, now=T0)
    with pytest.raises(HTTPException) as exc:
        claims.claim(db, item.id, DEV2, now=T0)
    assert conflict_detail(exc.value) == "ya cogido por dev1"
    db.refresh(item)
    assert item.owner == DEV1
    assert item.labels == [f"{TAKEN_PREFIX}dev1"]


def test_concurrent_claims_have_exactly_one_winner(db, monkeypatch):
    """Dos hilos con sesión propia. El primero mantiene la fila bloqueada 0,5 s antes del commit;
    sin FOR UPDATE ambos leerían QUEUED y ganarían los dos."""
    item_id = new_item(db).id  # id fuera de los hilos: la sesión de la fixture no se comparte
    real_record = claims.record

    def slow_record(*args, **kwargs):
        threading.Event().wait(0.5)
        return real_record(*args, **kwargs)

    monkeypatch.setattr(claims, "record", slow_record)
    barrier = threading.Barrier(2)
    outcomes: list[str] = []

    def attempt(email: str) -> None:
        barrier.wait()
        with SessionLocal() as session:
            try:
                claims.claim(session, item_id, email)
                outcomes.append(f"ok:{email}")
            except HTTPException as exc:
                outcomes.append(f"409:{exc.detail}")

    threads = [threading.Thread(target=attempt, args=(email,)) for email in (DEV1, DEV2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    winners = [o for o in outcomes if o.startswith("ok:")]
    losers = [o for o in outcomes if o.startswith("409:")]
    assert len(winners) == 1, outcomes
    assert len(losers) == 1, outcomes
    winner = winners[0].removeprefix("ok:")
    assert losers[0] == f"409:ya cogido por {winner.split('@')[0]}"
    item = db.get(WorkItem, item_id, populate_existing=True)
    assert item.owner == winner


def test_only_owner_can_heartbeat_release_and_log(db):
    item = new_item(db)
    claims.claim(db, item.id, DEV1, now=T0)
    with pytest.raises(HTTPException) as exc:
        claims.heartbeat(db, item.id, DEV2, "testing", None, now=T0)
    assert exc.value.status_code == 409
    with pytest.raises(HTTPException):
        claims.release(db, item.id, DEV2, "sin crédito")
    with pytest.raises(HTTPException):
        claims.add_event(db, item.id, DEV2, "log", "hola", None)

    claims.heartbeat(db, item.id, DEV1, "testing", "pasando tests", now=T0 + timedelta(minutes=1))
    db.refresh(item)
    assert (item.heartbeat_state, item.heartbeat_message) == ("testing", "pasando tests")

    claims.add_event(db, item.id, DEV1, "log", "tests ok", {"passed": 54})
    claims.release(db, item.id, DEV1, "sin crédito")
    db.refresh(item)
    assert item.status == QUEUED
    assert item.owner is None
    assert item.labels == []
    assert item.reason.endswith("sin crédito")


def test_expiry_at_timeout_minus_one_second_keeps_claim(db):
    item = new_item(db)
    claims.claim(db, item.id, DEV1, now=T0)
    assert claims.expire_stale_claims(db, now=T0 + timedelta(seconds=TIMEOUT - 1), timeout_seconds=TIMEOUT) == 0
    db.refresh(item)
    assert item.owner == DEV1


def test_expiry_at_timeout_plus_one_second_requeues_and_removes_label(db):
    item = new_item(db)
    claims.claim(db, item.id, DEV1, now=T0)
    expired = claims.expire_stale_claims(db, now=T0 + timedelta(seconds=TIMEOUT + 1), timeout_seconds=TIMEOUT)
    assert expired == 1
    db.refresh(item)
    assert item.status == QUEUED
    assert item.owner is None
    assert item.labels == []
    kinds = [e.kind for e in db.scalars(select(WorkItemEvent).where(WorkItemEvent.work_item_id == item.id))]
    assert kinds == ["claimed", "heartbeat_expired"]


def test_heartbeat_resets_expiry_timer(db):
    item = new_item(db)
    claims.claim(db, item.id, DEV1, now=T0)
    claims.heartbeat(db, item.id, DEV1, "working", None, now=T0 + timedelta(seconds=1000))
    # Desde el claim ya pasó el plazo, pero el último latido es reciente: sigue reclamado.
    assert claims.expire_stale_claims(db, now=T0 + timedelta(seconds=TIMEOUT + 1), timeout_seconds=TIMEOUT) == 0
    assert claims.expire_stale_claims(db, now=T0 + timedelta(seconds=1000 + TIMEOUT + 1), timeout_seconds=TIMEOUT) == 1


def test_heartbeat_after_expiry_is_refused(db):
    item = new_item(db)
    claims.claim(db, item.id, DEV1, now=T0)
    claims.expire_stale_claims(db, now=T0 + timedelta(seconds=TIMEOUT + 1), timeout_seconds=TIMEOUT)
    with pytest.raises(HTTPException) as exc:
        claims.heartbeat(db, item.id, DEV1, "working", None, now=T0 + timedelta(seconds=TIMEOUT + 2))
    assert exc.value.status_code == 409
