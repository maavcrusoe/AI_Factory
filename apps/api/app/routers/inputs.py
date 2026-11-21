import json
import time
from collections.abc import Iterator
from datetime import datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import SessionLocal, get_db
from app.models import User, WorkItem, WorkItemEvent
from app.routers.auth import current_user
from app.services.intake import RECEIVED, apply_manual_decision, record, run_intake
from app.services.intake_model import IntakeModel
from app.services.llm_ollama import get_intake_model
from app.services.rules import find_duplicate, find_project

router = APIRouter(prefix="/api/v1/inputs", tags=["inputs"])

Source = Literal["form", "api", "app", "github", "azuredevops"]


class InputIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    project_slug: str = Field(alias="projectId", min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=20000)
    source: Source = "api"


class ManualDecisionIn(BaseModel):
    action: Literal["accept", "reject", "request_info"]
    reason: str | None = Field(default=None, max_length=1000)
    label: str | None = Field(default=None, min_length=1, max_length=40)


class WorkItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source: str
    title: str
    status: str
    decision: str | None
    confidence: float | None
    work_type: str | None
    labels: list[str]
    created_at: datetime
    updated_at: datetime


class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kind: str
    from_status: str | None
    to_status: str | None
    actor: str
    detail: dict[str, Any] | None
    created_at: datetime


class WorkItemDetail(WorkItemOut):
    body: str
    expanded_body: str | None
    summary: str | None
    valuation: str | None
    difficulty: str | None
    risk: str | None
    reason: str | None
    original_payload: dict[str, Any]
    events: list[EventOut]


def _detail(db: Session, item: WorkItem) -> WorkItemDetail:
    events = db.scalars(
        select(WorkItemEvent).where(WorkItemEvent.work_item_id == item.id).order_by(WorkItemEvent.id)
    ).all()
    return WorkItemDetail(
        **WorkItemOut.model_validate(item).model_dump(),
        body=item.body,
        expanded_body=item.expanded_body,
        summary=item.summary,
        valuation=item.valuation,
        difficulty=item.difficulty,
        risk=item.risk,
        reason=item.reason,
        original_payload=item.original_payload,
        events=[EventOut.model_validate(e) for e in events],
    )


def _get_item(db: Session, item_id: int) -> WorkItem:
    item = db.get(WorkItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Petición no encontrada")
    return item


@router.get("/stream")
def stream(
    _: Annotated[User, Depends(current_user)],
    after: int | None = Query(default=None, ge=0),
) -> StreamingResponse:
    if after is None:
        with SessionLocal() as db:
            after = db.scalar(select(func.coalesce(func.max(WorkItemEvent.id), 0))) or 0
    return StreamingResponse(
        event_frames(after),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def event_frames(after_id: int, poll_seconds: float = 1.0) -> Iterator[str]:
    """Sondea WorkItemEvent y emite un frame SSE por evento nuevo. Ping cada ~15 s sin novedades."""
    last = after_id
    idle = 0
    while True:
        with SessionLocal() as db:
            rows = db.scalars(
                select(WorkItemEvent)
                .where(WorkItemEvent.id > last)
                .order_by(WorkItemEvent.id)
                .limit(100)
            ).all()
        for row in rows:
            last = row.id
            payload = {"eventId": row.id, "workItemId": row.work_item_id, "kind": row.kind}
            yield f"event: change\nid: {row.id}\ndata: {json.dumps(payload)}\n\n"
        if rows:
            idle = 0
            continue
        idle += 1
        if idle % 15 == 0:
            yield ": ping\n\n"
        time.sleep(poll_seconds)


@router.post("", response_model=WorkItemOut, status_code=201)
def create_input(
    body: InputIn,
    response: Response,
    background: BackgroundTasks,
    idempotency_key: Annotated[str, Header(alias="X-Idempotency-Key", min_length=1, max_length=200)],
    _: Annotated[User, Depends(current_user)],
    db: Session = Depends(get_db),
    model: IntakeModel = Depends(get_intake_model),
) -> WorkItem:
    project = find_project(db, body.project_slug)
    existing = find_duplicate(db, project.id, idempotency_key)
    if existing is not None:
        response.status_code = 200
        return existing

    item = WorkItem(
        project_id=project.id,
        idempotency_key=idempotency_key,
        source=body.source,
        original_payload=body.model_dump(by_alias=True),
        title=body.title.strip(),
        body=body.body.strip(),
        status=RECEIVED,
        labels=[],
    )
    db.add(item)
    try:
        db.flush()
        db.add(WorkItemEvent(work_item_id=item.id, kind="received", to_status=RECEIVED, actor=body.source))
        db.commit()
    except IntegrityError:
        # Carrera: otra petición con la misma clave ganó la inserción.
        db.rollback()
        existing = find_duplicate(db, project.id, idempotency_key)
        if existing is None:
            raise
        response.status_code = 200
        return existing

    background.add_task(run_intake, item.id, model)
    return item


@router.get("", response_model=list[WorkItemOut])
def list_inputs(
    _: Annotated[User, Depends(current_user)],
    db: Session = Depends(get_db),
    status: str | None = Query(default=None, max_length=30),
) -> list[WorkItem]:
    query = select(WorkItem).order_by(WorkItem.id.desc()).limit(200)
    if status:
        query = query.where(WorkItem.status == status)
    return list(db.scalars(query).all())


@router.get("/{item_id}", response_model=WorkItemDetail)
def get_input(
    item_id: int,
    _: Annotated[User, Depends(current_user)],
    db: Session = Depends(get_db),
) -> WorkItemDetail:
    return _detail(db, _get_item(db, item_id))


@router.post("/{item_id}/decision", response_model=WorkItemDetail)
def decide(
    item_id: int,
    body: ManualDecisionIn,
    user: Annotated[User, Depends(current_user)],
    db: Session = Depends(get_db),
) -> WorkItemDetail:
    item = _get_item(db, item_id)
    apply_manual_decision(db, item, body.action, user.email, body.reason, body.label)
    return _detail(db, item)
