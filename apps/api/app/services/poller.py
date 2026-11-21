"""Sondeo periódico de trackers. Un solo proceso de API (ver ceiling en decisión 008)."""

import logging
import threading
from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters import ADAPTERS
from app.db import SessionLocal
from app.models import ProjectIntegration
from app.services.intake import run_intake
from app.services.llm_ollama import get_intake_model
from app.services.tracker_sync import poll_integration

logger = logging.getLogger("factory.tracker")
TICK_SECONDS = 15


def start_intake_in_thread(item_id: int) -> None:
    # El intake tarda hasta 60 s: en hilo propio para no frenar el sondeo.
    threading.Thread(target=run_intake, args=(item_id, get_intake_model()), daemon=True).start()


def poll_due(db: Session, now: datetime, start_intake: Callable[[int], None] = start_intake_in_thread) -> int:
    """Sondea las integraciones cuyo intervalo ha vencido. Un fallo no para a las demás."""
    polled = 0
    for integration in db.scalars(select(ProjectIntegration)).all():
        adapter_cls = ADAPTERS.get(integration.provider)
        if adapter_cls is None or adapter_cls.default_poll_seconds == 0:
            continue
        interval = integration.config.get("pollSeconds", adapter_cls.default_poll_seconds)
        last = integration.last_polled_at
        if last is not None and (now - last).total_seconds() < interval:
            continue
        try:
            poll_integration(db, integration, start_intake)
            polled += 1
        except Exception as exc:  # noqa: BLE001 - un tracker caído no debe parar el bucle
            db.rollback()
            # Solo tipo de error: los mensajes pueden contener URLs y nunca el token.
            logger.warning(
                "sondeo fallido provider=%s project_id=%s error=%s",
                integration.provider,
                integration.project_id,
                type(exc).__name__,
            )
    return polled


def poll_forever(stop: threading.Event) -> None:
    while not stop.wait(TICK_SECONDS):
        try:
            with SessionLocal() as db:
                poll_due(db, datetime.now(UTC))
        except Exception as exc:  # noqa: BLE001
            logger.warning("tick de sondeo fallido error=%s", type(exc).__name__)
