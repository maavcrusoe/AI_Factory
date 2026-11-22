"""Administración: usuarios (admin) y política de merge versionada (admin escribe, cualquier autenticado lee)."""

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import MergePolicy, Project, User
from app.routers.auth import Admin, UserOut, current_user
from app.security import hash_password
from app.services.merge_policy import MergePolicyBody, active_policy
from app.services.rules import find_project

router = APIRouter(tags=["admin"])


class UserIn(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=200)
    role: Literal["admin", "developer", "reviewer"]


class PolicyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    version: int
    body: dict[str, Any]


@router.post("/api/v1/users", response_model=UserOut, status_code=201)
def create_user(body: UserIn, _: Admin, db: Session = Depends(get_db)) -> User:
    if db.scalar(select(User.id).where(User.email == body.email)) is not None:
        raise HTTPException(status_code=409, detail="Ese email ya existe")
    user = User(email=body.email, password_hash=hash_password(body.password), role=body.role)
    db.add(user)
    db.commit()
    return user


@router.get("/api/v1/users", response_model=list[UserOut])
def list_users(_: Admin, db: Session = Depends(get_db)) -> list[User]:
    return list(db.scalars(select(User).order_by(User.id)).all())


@router.get("/api/v1/projects/{slug}/merge-policy", response_model=PolicyOut)
def get_merge_policy(
    slug: str,
    _: Annotated[User, Depends(current_user)],
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    version, policy = active_policy(db, find_project(db, slug).id)
    return {"version": version, "body": policy.model_dump()}


@router.put("/api/v1/projects/{slug}/merge-policy", response_model=PolicyOut, status_code=201)
def put_merge_policy(
    slug: str,
    body: MergePolicyBody,
    user: Admin,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Crea la versión siguiente. Las anteriores no se tocan: son el historial de decisiones."""
    project = db.scalar(select(Project).where(Project.slug == slug).with_for_update())
    if project is None:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    current = db.scalar(select(func.max(MergePolicy.version)).where(MergePolicy.project_id == project.id)) or 0
    row = MergePolicy(
        project_id=project.id,
        version=current + 1,
        body=body.model_dump(),
        created_by=user.email,
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Otra edición de la política ganó: recarga") from None
    return {"version": row.version, "body": row.body}
