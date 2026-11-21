"""Alta idempotente de WorkItem, compartida por la API, el webhook y el sondeo de trackers."""

from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Project, TrackerLink, WorkItem, WorkItemEvent
from app.services.intake import RECEIVED
from app.services.rules import find_duplicate


def ingest(
    db: Session,
    project: Project,
    *,
    source: str,
    title: str,
    body: str,
    payload: dict[str, Any],
    idempotency_key: str,
    actor: str,
    link: dict[str, str | None] | None = None,
) -> tuple[WorkItem, bool]:
    """Devuelve (item, creado). Misma clave en el proyecto = item existente, sin duplicar.

    `link` (provider, remote_id, remote_url) se guarda en la misma transacción que el item.
    """
    existing = find_duplicate(db, project.id, idempotency_key)
    if existing is not None:
        return existing, False

    item = WorkItem(
        project_id=project.id,
        idempotency_key=idempotency_key,
        source=source,
        original_payload={**payload, "projectId": project.slug},
        title=title.strip(),
        body=body.strip(),
        status=RECEIVED,
        labels=[],
    )
    db.add(item)
    try:
        db.flush()
        db.add(WorkItemEvent(work_item_id=item.id, kind="received", to_status=RECEIVED, actor=actor))
        if link is not None:
            db.add(
                TrackerLink(
                    work_item_id=item.id,
                    project_id=project.id,
                    provider=link["provider"],
                    remote_id=link["remote_id"],
                    remote_url=link.get("remote_url"),
                    managed_labels=[],
                )
            )
        db.commit()
    except IntegrityError:
        # Carrera: otra petición o sondeo con la misma clave ganó; se revierten item y enlace juntos.
        db.rollback()
        existing = find_duplicate(db, project.id, idempotency_key)
        if existing is None:
            raise
        return existing, False
    return item, True
