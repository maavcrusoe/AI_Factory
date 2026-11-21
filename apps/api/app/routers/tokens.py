from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import DeveloperToken, User
from app.routers.auth import current_user
from app.security import hash_api_token, new_api_token
from app.services.tokens import revoke

router = APIRouter(prefix="/api/v1/tokens", tags=["tokens"])


class TokenIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class TokenOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    created_at: datetime
    revoked_at: datetime | None


class TokenCreated(TokenOut):
    # Único momento en que el valor en claro existe. No se guarda ni se vuelve a mostrar.
    token: str


@router.post("", response_model=TokenCreated, status_code=201)
def create_token(
    body: TokenIn,
    user: Annotated[User, Depends(current_user)],
    db: Session = Depends(get_db),
) -> dict:
    plaintext = new_api_token()
    row = DeveloperToken(user_id=user.id, name=body.name, token_hash=hash_api_token(plaintext))
    db.add(row)
    db.commit()
    return {**TokenOut.model_validate(row).model_dump(), "token": plaintext}


@router.get("", response_model=list[TokenOut])
def list_tokens(user: Annotated[User, Depends(current_user)], db: Session = Depends(get_db)) -> list[DeveloperToken]:
    return list(db.scalars(select(DeveloperToken).where(DeveloperToken.user_id == user.id).order_by(DeveloperToken.id)).all())


@router.delete("/{token_id}", response_model=TokenOut)
def revoke_token(
    token_id: int,
    user: Annotated[User, Depends(current_user)],
    db: Session = Depends(get_db),
) -> DeveloperToken:
    row = db.get(DeveloperToken, token_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="Token no encontrado")
    revoke(db, row)
    return row
