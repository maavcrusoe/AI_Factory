"""Fase 4: complete (PR_OPEN), enlace a issue, artefactos idempotentes y caducidad."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import delete, select

from app.db import SessionLocal
from app.models import Project, TrackerLink, User, WorkArtifact, WorkItem, WorkItemEvent
from app.routers.inputs import _detail
from app.routers.work import ArtifactIn
from app.security import hash_password
from app.services import claims, pipeline
from app.services.intake import QUEUED

SLUG = "fase4-demo"
DEV1 = "dev1-f4@test.local"
DEV2 = "dev2-f4@test.local"
T0 = datetime(2026, 11, 21, 12, 0, tzinfo=UTC)
TIMEOUT = 1800
PR_URL = "https://github.com/maavcrusoe/meme-demo/pull/7"


def _ensure_user(db, email: str) -> None:
    if db.scalar(select(User).where(User.email == email)) is None:
        db.add(User(email=email, password_hash=hash_password("pw-test"), role="member"))
        db.commit()


@pytest.fixture
def db():
    session = SessionLocal()
    project = session.scalar(select(Project).where(Project.slug == SLUG))
    if project is None:
        session.add(Project(slug=SLUG, name="Fase 4"))
        session.commit()
    _ensure_user(session, DEV1)
    _ensure_user(session, DEV2)
    yield session
    project = session.scalar(select(Project).where(Project.slug == SLUG))
    ids = select(WorkItem.id).where(WorkItem.project_id == project.id)
    session.execute(delete(WorkArtifact).where(WorkArtifact.work_item_id.in_(ids)))
    session.execute(delete(TrackerLink).where(TrackerLink.project_id == project.id))
    session.execute(delete(WorkItemEvent).where(WorkItemEvent.work_item_id.in_(ids)))
    session.execute(delete(WorkItem).where(WorkItem.project_id == project.id))
    session.commit()
    session.close()


def _claimed_item(db, owner: str = DEV1, now: datetime = T0) -> WorkItem:
    project = db.scalar(select(Project).where(Project.slug == SLUG))
    item = WorkItem(
        project_id=project.id,
        idempotency_key=str(uuid4()),
        source="api",
        original_payload={},
        title="Botón de limpiar",
        body="Añade un botón que vacía el texto.",
        status=QUEUED,
        labels=[],
    )
    db.add(item)
    db.commit()
    claims.claim(db, item.id, owner, now=now)
    return item


def test_complete_moves_owned_claim_to_pr_open_with_event(db):
    item = _claimed_item(db)
    pipeline.complete(db, item.id, DEV1, PR_URL, 7)
    db.refresh(item)
    assert item.status == pipeline.PR_OPEN
    assert item.owner == DEV1
    assert "taken by" not in " ".join(item.labels)
    kinds = [e.kind for e in db.scalars(select(WorkItemEvent).where(WorkItemEvent.work_item_id == item.id))]
    assert "pr_opened" in kinds


def test_complete_refused_for_non_owner_and_for_queued_item(db):
    item = _claimed_item(db)
    with pytest.raises(HTTPException) as exc:
        pipeline.complete(db, item.id, DEV2, PR_URL, 7)
    assert exc.value.status_code == 409
    db.rollback()
    db.refresh(item)
    assert item.status == claims.CLAIMED


def test_complete_rejects_non_https_url(db):
    item = _claimed_item(db)
    with pytest.raises(HTTPException) as exc:
        pipeline.complete(db, item.id, DEV1, "http://example.com/pr/1", 1)
    assert exc.value.status_code == 422


def test_pr_open_is_not_requeued_by_expiry(db):
    item = _claimed_item(db)
    pipeline.complete(db, item.id, DEV1, PR_URL, 7)
    expired = claims.expire_stale_claims(db, now=T0 + timedelta(seconds=TIMEOUT + 60), timeout_seconds=TIMEOUT)
    assert expired == 0
    db.refresh(item)
    assert item.status == pipeline.PR_OPEN


def test_artifact_upload_is_idempotent_by_client_key(db):
    item = _claimed_item(db)
    first, created = pipeline.add_artifact(
        db, item.id, DEV1, stage="gate", round_no=1, kind="log", client_key="gate-1", content="ok"
    )
    again, created_again = pipeline.add_artifact(
        db, item.id, DEV1, stage="gate", round_no=1, kind="log", client_key="gate-1", content="ok"
    )
    assert created and not created_again
    assert first.id == again.id
    assert len(pipeline.list_artifacts(db, item.id)) == 1


def test_artifact_refused_for_non_owner_bad_kind_and_too_big(db):
    item = _claimed_item(db)
    with pytest.raises(HTTPException) as exc:
        pipeline.add_artifact(db, item.id, DEV2, stage="gate", round_no=1, kind="log", client_key="k", content="x")
    assert exc.value.status_code == 409
    db.rollback()
    with pytest.raises(HTTPException) as exc:
        pipeline.add_artifact(db, item.id, DEV1, stage="gate", round_no=1, kind="binario", client_key="k", content="x")
    assert exc.value.status_code == 422
    db.rollback()
    with pytest.raises(ValidationError):
        ArtifactIn(
            stage="gate",
            round=1,
            kind="diff",
            client_key="k",
            content="x" * (pipeline.MAX_ARTIFACT_CHARS + 1),
        )


def test_tracker_link_is_idempotent_and_rejects_another_issue(db):
    item = _claimed_item(db)
    pipeline.link_tracker(db, item.id, DEV1, "github", "12", "https://github.com/x/y/issues/12")
    pipeline.link_tracker(db, item.id, DEV1, "github", "12", None)
    with pytest.raises(HTTPException) as exc:
        pipeline.link_tracker(db, item.id, DEV1, "github", "13", None)
    assert exc.value.status_code == 409
    detail = _detail(db, db.get(WorkItem, item.id))
    assert detail.tracker == {
        "provider": "github",
        "remote_id": "12",
        "remote_url": "https://github.com/x/y/issues/12",
    }
