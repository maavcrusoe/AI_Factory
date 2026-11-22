"""Administración: usuarios (admin) y política de merge versionada (admin escribe, cualquier autenticado lee)."""

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
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


class UserUpdateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["admin", "developer", "reviewer"] | None = None
    is_active: bool | None = None


@router.patch("/api/v1/users/{user_id}", response_model=UserOut)
def update_user(user_id: int, body: UserUpdateIn, admin: Admin, db: Session = Depends(get_db)) -> User:
    """Cambia rol o activo. El admin no puede quitarse el rol de admin ni desactivarse a sí mismo."""
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    new_role = body.role or user.role
    new_active = user.is_active if body.is_active is None else body.is_active
    if user.id == admin.id and (new_role != "admin" or not new_active):
        raise HTTPException(status_code=422, detail="No puedes quitarte el rol de admin ni desactivarte")
    user.role = new_role
    user.is_active = new_active
    db.commit()
    return user


class SettingsOut(BaseModel):
    log_retention_days: int
    heartbeat_timeout_seconds: int


@router.get("/api/v1/settings", response_model=SettingsOut)
def platform_settings(_: Annotated[User, Depends(current_user)]) -> SettingsOut:
    """Valores de solo lectura que el dashboard necesita para mostrar y marcar el estado."""
    settings = get_settings()
    return SettingsOut(
        log_retention_days=settings.log_retention_days,
        heartbeat_timeout_seconds=settings.heartbeat_timeout_seconds,
    )


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
