"""Claim, heartbeat, release, eventos y caducidad de trabajo (Fase 3).

Regla de bloqueo: cada operación toma `SELECT ... FOR UPDATE` sobre la fila, decide en Python,
muta sin commit y hace un único commit (`record` o `db.commit`). Así el perdedor de una carrera
espera y ve el estado ya cambiado.
"""

import logging
import threading
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import SessionLocal
from app.models import WorkItem, WorkItemEvent
from app.services.intake import QUEUED, record
from app.services.tracker_sync import replace_taken_label

CLAIMED = "CLAIMED"
EXPIRY_TICK_SECONDS = 30
logger = logging.getLogger("factory.claims")


def handle(email: str) -> str:
    """Nombre corto para etiquetas y mensajes: la parte local del email, máximo 40 caracteres."""
    return email.split("@", 1)[0][:40]


def _now() -> datetime:
    return datetime.now(UTC)


def _locked(db: Session, item_id: int) -> WorkItem:
    item = db.scalar(
        select(WorkItem)
        .where(WorkItem.id == item_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Trabajo no encontrado")
    return item


def _require_owner(item: WorkItem, user_email: str) -> None:
    if item.status != CLAIMED or item.owner != user_email:
        raise HTTPException(status_code=409, detail=f"No tienes este trabajo (estado {item.status})")


def check_version(item: WorkItem, expected_version: int) -> None:
    """Bloqueo optimista: la decisión sobre una versión vieja del item se rechaza (Fase 5)."""
    if item.approval_version != expected_version:
        raise HTTPException(
            status_code=409,
            detail=f"El item cambió (versión {item.approval_version}, esperada {expected_version}): recarga antes de decidir",
        )


def _unassign(item: WorkItem) -> None:
    item.owner = None
    item.claimed_at = None
    item.last_heartbeat_at = None
    item.heartbeat_state = None
    item.heartbeat_message = None
    replace_taken_label(item, None)


def claim(db: Session, item_id: int, user_email: str, now: datetime | None = None) -> WorkItem:
    item = _locked(db, item_id)
    if item.status == CLAIMED:
        raise HTTPException(status_code=409, detail=f"ya cogido por {handle(item.owner or '')}")
    if item.status != QUEUED:
        raise HTTPException(status_code=409, detail=f"No está en cola (estado {item.status})")
    now = now or _now()
    item.owner = user_email
    item.claimed_at = now
    item.last_heartbeat_at = None
    item.reason = None  # el motivo de una liberación anterior ya no aplica
    replace_taken_label(item, handle(user_email))
    record(db, item, "claimed", CLAIMED, user_email, {"user": handle(user_email)})
    return item


def heartbeat(
    db: Session,
    item_id: int,
    user_email: str,
    state: str,
    message: str | None,
    now: datetime | None = None,
) -> WorkItem:
    item = _locked(db, item_id)
    _require_owner(item, user_email)
    item.last_heartbeat_at = now or _now()
    item.heartbeat_state = state
    item.heartbeat_message = message
    db.commit()  # Sin evento por latido: el estado vive en la fila, no en la auditoría.
    return item


def release(db: Session, item_id: int, user_email: str, reason: str) -> WorkItem:
    item = _locked(db, item_id)
    _require_owner(item, user_email)
    item.reason = f"Liberado por {handle(user_email)}: {reason}"
    _unassign(item)
    record(db, item, "released", QUEUED, user_email, {"reason": reason})
    return item


def add_event(
    db: Session,
    item_id: int,
    user_email: str,
    kind: str,
    message: str,
    detail: dict[str, Any] | None,
) -> WorkItemEvent:
    item = _locked(db, item_id)
    _require_owner(item, user_email)
    event = WorkItemEvent(
        work_item_id=item.id,
        kind=kind,
        actor=user_email,
        detail={"message": message, **(detail or {})},
    )
    db.add(event)
    db.commit()
    return event


def expire_stale_claims(
    db: Session,
    now: datetime | None = None,
    timeout_seconds: int | None = None,
) -> int:
    """Devuelve a QUEUED los claims sin heartbeat desde hace `timeout_seconds`. Reloj inyectable para tests."""
    now = now or _now()
    timeout = timedelta(seconds=timeout_seconds or get_settings().heartbeat_timeout_seconds)
    cutoff = now - timeout
    last_seen = func.coalesce(WorkItem.last_heartbeat_at, WorkItem.claimed_at)
    candidate_ids = db.scalars(
        select(WorkItem.id).where(WorkItem.status == CLAIMED, last_seen < cutoff)
    ).all()
    expired = 0
    for item_id in candidate_ids:
        # skip_locked: si un latido o una liberación tiene la fila, no esperamos; la siguiente vuelta lo verá.
        item = db.scalar(
            select(WorkItem)
            .where(WorkItem.id == item_id, WorkItem.status == CLAIMED)
            .with_for_update(skip_locked=True)
            .execution_options(populate_existing=True)
        )
        if item is None:
            db.rollback()
            continue
        # Recomprobar con la fila bloqueada: pudo llegar un latido entre la lista y el bloqueo.
        if (item.last_heartbeat_at or item.claimed_at) >= cutoff:
            db.rollback()
            continue
        previous = item.owner or ""
        item.reason = "Heartbeat caducado: vuelve a la cola"
        _unassign(item)
        record(db, item, "heartbeat_expired", QUEUED, "system", {"previous": handle(previous)})
        expired += 1
    return expired


def expire_forever(stop: threading.Event) -> None:
    while not stop.wait(EXPIRY_TICK_SECONDS):
        try:
            with SessionLocal() as db:
                expired = expire_stale_claims(db)
            if expired:
                logger.warning("claims caducados y devueltos a la cola: %d", expired)
        except Exception as exc:  # noqa: BLE001 - el job no debe morir por un fallo puntual
            logger.warning("job de caducidad fallido error=%s", type(exc).__name__)
