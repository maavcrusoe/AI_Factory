from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User, WorkItem
from app.routers.auth import Reviewer, current_user
from app.routers.inputs import WorkItemDetail, WorkItemOut, _detail
from app.services import approvals
from app.services.merge import MERGING, READY_TO_MERGE, merge_item

router = APIRouter(tags=["approvals"])
WAITING_HUMAN_MERGE = approvals.WAITING_HUMAN_MERGE


class DecisionIn(BaseModel):
    # Versión que el revisor vio. Si el item cambió después, la decisión da 409.
    expected_version: int = Field(ge=0)


class ChangesIn(DecisionIn):
    reason: str = Field(min_length=1, max_length=2000)


@router.get("/api/v1/approvals", response_model=list[WorkItemOut])
def approvals_queue(
    _: Annotated[User, Depends(current_user)],
    db: Session = Depends(get_db),
) -> list[WorkItem]:
    query = (
        select(WorkItem)
        .where(WorkItem.status.in_([WAITING_HUMAN_MERGE, READY_TO_MERGE, MERGING]))
        .order_by(WorkItem.id)
        .limit(200)
    )
    return list(db.scalars(query).all())


@router.post("/api/v1/work/{item_id}/approve", response_model=WorkItemDetail)
def approve(
    item_id: int,
    body: DecisionIn,
    user: Reviewer,
    db: Session = Depends(get_db),
) -> WorkItemDetail:
    return _detail(db, approvals.approve(db, item_id, user.email, body.expected_version))


@router.post("/api/v1/work/{item_id}/request-changes", response_model=WorkItemDetail)
def request_changes(
    item_id: int,
    body: ChangesIn,
    user: Reviewer,
    db: Session = Depends(get_db),
) -> WorkItemDetail:
    item = approvals.request_changes(db, item_id, user.email, body.expected_version, body.reason)
    return _detail(db, item)


@router.post("/api/v1/work/{item_id}/merge", response_model=WorkItemDetail)
def merge(
    item_id: int,
    body: DecisionIn,
    user: Reviewer,
    db: Session = Depends(get_db),
) -> WorkItemDetail:
    return _detail(db, merge_item(db, item_id, user.email, body.expected_version))
