from fastapi import APIRouter, Depends, Response
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
def health(response: Response, db: Session = Depends(get_db)) -> dict[str, str]:
    try:
        db.execute(text("select 1"))
    except SQLAlchemyError:
        response.status_code = 503
        return {"status": "error", "database": "unreachable"}
    return {"status": "ok", "database": "ok"}
