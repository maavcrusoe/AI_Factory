from datetime import datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters import ADAPTERS
from app.db import get_db
from app.models import ProjectIntegration, User
from app.routers.auth import current_user
from app.services.crypto import TokenCryptoError, encrypt_token
from app.services.rules import find_project

router = APIRouter(prefix="/api/v1/projects", tags=["integrations"])

Provider = Literal["github", "azuredevops", "generic"]
MIN_POLL_SECONDS = 15


class IntegrationIn(BaseModel):
    provider: Provider
    config: dict[str, Any] = Field(default_factory=dict)
    # Solo escritura: nunca se devuelve. Sin valor, se conserva el token guardado.
    token: str | None = Field(default=None, min_length=1, max_length=500)


class IntegrationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    provider: str
    config: dict[str, Any]
    has_token: bool
    last_polled_at: datetime | None

    @classmethod
    def of(cls, integration: ProjectIntegration) -> "IntegrationOut":
        return cls(
            provider=integration.provider,
            config=integration.config,
            has_token=integration.token_encrypted is not None,
            last_polled_at=integration.last_polled_at,
        )


def _validate_config(body: IntegrationIn) -> None:
    if "token" in body.config or "password" in body.config:
        raise HTTPException(status_code=422, detail="El token no va en config: usa el campo token")
    poll = body.config.get("pollSeconds")
    if poll is not None and (not isinstance(poll, int) or poll < MIN_POLL_SECONDS):
        raise HTTPException(status_code=422, detail=f"pollSeconds debe ser entero >= {MIN_POLL_SECONDS}")
    try:
        # Construir el adapter valida la config sin tocar la red.
        ADAPTERS[body.provider](body.config, "validar")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.put("/{slug}/integration", response_model=IntegrationOut)
def put_integration(
    slug: str,
    body: IntegrationIn,
    user: Annotated[User, Depends(current_user)],
    db: Session = Depends(get_db),
) -> IntegrationOut:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Solo un admin configura integraciones")
    project = find_project(db, slug)
    _validate_config(body)
    integration = db.scalar(select(ProjectIntegration).where(ProjectIntegration.project_id == project.id))
    if integration is None:
        integration = ProjectIntegration(project_id=project.id, provider=body.provider)
        db.add(integration)
    if body.provider != integration.provider and body.token is None:
        integration.token_encrypted = None
    integration.provider = body.provider
    integration.config = body.config
    if body.token is not None:
        try:
            integration.token_encrypted = encrypt_token(body.token)
        except TokenCryptoError as exc:
            db.rollback()
            raise HTTPException(status_code=503, detail=str(exc)) from exc
    if body.provider != "generic" and integration.token_encrypted is None:
        db.rollback()
        raise HTTPException(status_code=422, detail="Token requerido para este proveedor")
    db.commit()
    return IntegrationOut.of(integration)


@router.get("/{slug}/integration", response_model=IntegrationOut)
def get_integration(
    slug: str,
    _: Annotated[User, Depends(current_user)],
    db: Session = Depends(get_db),
) -> IntegrationOut:
    project = find_project(db, slug)
    integration = db.scalar(select(ProjectIntegration).where(ProjectIntegration.project_id == project.id))
    if integration is None:
        raise HTTPException(status_code=404, detail="Integración no configurada")
    return IntegrationOut.of(integration)
