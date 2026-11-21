from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DeveloperToken, User
from app.security import hash_api_token


def user_by_api_token(db: Session, token: str) -> User | None:
    row = db.scalar(
        select(DeveloperToken).where(
            DeveloperToken.token_hash == hash_api_token(token),
            DeveloperToken.revoked_at.is_(None),
        )
    )
    if row is None:
        return None
    user = db.get(User, row.user_id)
    return user if user is not None and user.is_active else None


def revoke(db: Session, token: DeveloperToken) -> None:
    token.revoked_at = datetime.now(UTC)
    db.commit()
