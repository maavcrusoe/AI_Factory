import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User, WorkItem
from app.routers.auth import current_user
from app.routers.inputs import WorkItemDetail, WorkItemOut, _detail
from app.services import claims
from app.services.intake import QUEUED
from app.services.rules import find_project

router = APIRouter(tags=["work"])

MAX_DETAIL_CHARS = 4000


class HeartbeatIn(BaseModel):
    state: str = Field(min_length=1, max_length=30)
    message: str | None = Field(default=None, max_length=1000)


class ReleaseIn(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


class EventIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: str = Field(min_length=1, max_length=40)
    message: str = Field(min_length=1, max_length=2000)
    detail: dict[str, Any] | None = None


@router.get("/api/v1/projects/{project_id}/queue", response_model=list[WorkItemOut])
def queue(
    project_id: str,
    _: Annotated[User, Depends(current_user)],
    db: Session = Depends(get_db),
) -> list[WorkItem]:
    """`project_id` es el slug del proyecto (el `projectId` de `.factory/config.yaml`)."""
    project = find_project(db, project_id)
    query = (
        select(WorkItem)
        .where(WorkItem.project_id == project.id, WorkItem.status == QUEUED)
        .order_by(WorkItem.id)
        .limit(200)
    )
    return list(db.scalars(query).all())


@router.post("/api/v1/work/{item_id}/claim", response_model=WorkItemDetail)
def claim(
    item_id: int,
    user: Annotated[User, Depends(current_user)],
    db: Session = Depends(get_db),
) -> WorkItemDetail:
    return _detail(db, claims.claim(db, item_id, user.email))


@router.post("/api/v1/work/{item_id}/heartbeat", response_model=WorkItemDetail)
def heartbeat(
    item_id: int,
    body: HeartbeatIn,
    user: Annotated[User, Depends(current_user)],
    db: Session = Depends(get_db),
) -> WorkItemDetail:
    return _detail(db, claims.heartbeat(db, item_id, user.email, body.state, body.message))


@router.post("/api/v1/work/{item_id}/release", response_model=WorkItemDetail)
def release(
    item_id: int,
    body: ReleaseIn,
    user: Annotated[User, Depends(current_user)],
    db: Session = Depends(get_db),
) -> WorkItemDetail:
    return _detail(db, claims.release(db, item_id, user.email, body.reason))


@router.post("/api/v1/work/{item_id}/events", status_code=201)
def add_event(
    item_id: int,
    body: EventIn,
    user: Annotated[User, Depends(current_user)],
    db: Session = Depends(get_db),
) -> dict[str, int]:
    if body.detail is not None and len(json.dumps(body.detail)) > MAX_DETAIL_CHARS:
        raise HTTPException(status_code=422, detail=f"detail supera {MAX_DETAIL_CHARS} caracteres")
    event = claims.add_event(db, item_id, user.email, body.kind, body.message, body.detail)
    return {"eventId": event.id}
