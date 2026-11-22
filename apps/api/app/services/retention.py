"""Retención de logs (Fase 6). Borra artefactos `log` más antiguos que `log_retention_days`.

Solo se tocan los `log`: diffs e informes son la base de las aprobaciones y de la auditoría,
así que se conservan. Configuración: `LOG_RETENTION_DAYS` (por defecto 30).
"""

import logging
import threading
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import SessionLocal
from app.models import WorkArtifact

LOG_KIND = "log"
# ponytail: una pasada por hora; si hay muchos logs, lotes por id en vez de un DELETE grande.
CLEANUP_TICK_SECONDS = 3600
logger = logging.getLogger("factory.retention")


def purge_old_logs(db: Session, days: int, now: datetime | None = None) -> int:
    """Borra los logs creados antes de `now - days`. Devuelve cuántas filas borró."""
    cutoff = (now or datetime.now(UTC)) - timedelta(days=days)
    result = db.execute(
        delete(WorkArtifact)
        .where(WorkArtifact.kind == LOG_KIND, WorkArtifact.created_at < cutoff)
        .execution_options(synchronize_session=False)
    )
    db.commit()
    return result.rowcount or 0


def cleanup_once() -> int:
    settings = get_settings()
    with SessionLocal() as db:
        return purge_old_logs(db, settings.log_retention_days)


def purge_forever(stop: threading.Event) -> None:
    """Hilo de fondo: una pasada al arrancar y luego cada hora hasta `stop`."""
    while True:
        try:
            removed = cleanup_once()
            if removed:
                logger.info("Retención: %d logs borrados", removed)
        except SQLAlchemyError:
            logger.exception("Retención: fallo al limpiar logs; se reintenta en la siguiente pasada")
        if stop.wait(CLEANUP_TICK_SECONDS):
            return
