"""Reglas deterministas previas al LLM: proyecto existe y no es duplicado."""

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Project, WorkItem


def find_project(db: Session, slug: str) -> Project:
    project = db.scalar(select(Project).where(Project.slug == slug))
    if project is None:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    return project


def find_duplicate(db: Session, project_id: int, idempotency_key: str) -> WorkItem | None:
    return db.scalar(
        select(WorkItem).where(
            WorkItem.project_id == project_id, WorkItem.idempotency_key == idempotency_key
        )
    )
