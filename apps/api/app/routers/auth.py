from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import User
from app.security import (
    API_TOKEN_PREFIX,
    ROLE_ADMIN,
    ROLE_DEVELOPER,
    ROLE_REVIEWER,
    create_token,
    read_token,
    verify_password,
)
from app.services.tokens import user_by_api_token

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class LoginIn(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    role: str
    is_active: bool


class LoginOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


@router.post("/login", response_model=LoginOut)
def login(body: LoginIn, db: Session = Depends(get_db)) -> dict:
    settings = get_settings()
    user = db.scalar(select(User).where(User.email == body.email, User.is_active.is_(True)))
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Credenciales no válidas")
    token = create_token(user.email, settings.app_secret_key, settings.token_ttl_seconds)
    return {"access_token": token, "user": user}


def current_user(
    authorization: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db),
) -> User:
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer":
        user = None
    elif token.startswith(API_TOKEN_PREFIX):
        user = user_by_api_token(db, token)
    else:
        email = read_token(token, get_settings().app_secret_key)
        user = db.scalar(select(User).where(User.email == email, User.is_active.is_(True))) if email else None
    if user is None:
        raise HTTPException(status_code=401, detail="No autenticado")
    return user


@router.get("/me", response_model=UserOut)
def me(user: Annotated[User, Depends(current_user)]) -> User:
    return user


def require_role(*roles: str) -> Callable[..., User]:
    """Dependencia: 401 sin sesión, 403 si el rol del usuario no está en `roles`."""

    def dependency(user: Annotated[User, Depends(current_user)]) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Tu rol no permite esta acción")
        return user

    return dependency


Developer = Annotated[User, Depends(require_role(ROLE_DEVELOPER, ROLE_ADMIN))]
Reviewer = Annotated[User, Depends(require_role(ROLE_REVIEWER, ROLE_ADMIN))]
Admin = Annotated[User, Depends(require_role(ROLE_ADMIN))]
