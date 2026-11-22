"""Resumen de proyectos para el dashboard (Fase 6): nº de items por estado, cualquier autenticado."""

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Project, User, WorkItem
from app.routers.auth import current_user

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


class ProjectSummary(BaseModel):
    slug: str
    name: str
    total: int
    by_status: dict[str, int]


@router.get("", response_model=list[ProjectSummary])
def list_projects(
    _: Annotated[User, Depends(current_user)],
    db: Session = Depends(get_db),
) -> list[ProjectSummary]:
    counts: dict[int, dict[str, int]] = {}
    rows = db.execute(
        select(WorkItem.project_id, WorkItem.status, func.count()).group_by(WorkItem.project_id, WorkItem.status)
    ).all()
    for project_id, status, count in rows:
        counts.setdefault(project_id, {})[status] = count
    return [
        ProjectSummary(
            slug=project.slug,
            name=project.name,
            total=sum(counts.get(project.id, {}).values()),
            by_status=counts.get(project.id, {}),
        )
        for project in db.scalars(select(Project).order_by(Project.slug)).all()
    ]
