"""GET /metrics: formato Prometheus. Solo admin (Bearer fct_ de un usuario admin). No va sin autenticar."""

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.routers.auth import Admin
from app.services.metrics import render_metrics

router = APIRouter(tags=["metrics"])


@router.get("/metrics", response_class=PlainTextResponse)
def metrics(_: Admin, db: Session = Depends(get_db)) -> str:
    return render_metrics(db)
