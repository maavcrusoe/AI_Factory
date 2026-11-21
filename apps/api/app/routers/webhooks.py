from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request, Response
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import WorkItem
from app.routers.inputs import InputIn, WorkItemOut, create_item
from app.security import verify_signature
from app.services.intake_model import IntakeModel
from app.services.llm_ollama import get_intake_model

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])


@router.post("/generic", response_model=WorkItemOut, status_code=201)
async def generic_webhook(
    request: Request,
    response: Response,
    background: BackgroundTasks,
    idempotency_key: Annotated[str, Header(alias="X-Idempotency-Key", min_length=1, max_length=200)],
    signature: Annotated[str | None, Header(alias="X-Hub-Signature-256")] = None,
    db: Session = Depends(get_db),
    model: IntakeModel = Depends(get_intake_model),
) -> WorkItem:
    """Entrada sin usuario: la autoridad es la firma HMAC-SHA256 del cuerpo crudo."""
    raw = await request.body()
    if not verify_signature(raw, signature, get_settings().webhook_secret):
        raise HTTPException(status_code=401, detail="Firma no válida")
    try:
        body = InputIn.model_validate_json(raw)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors(include_url=False)) from exc
    return create_item(db, background, model, body, idempotency_key, response, actor="webhook")
