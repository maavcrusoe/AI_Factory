"""Enlace con trackers: ingesta por sondeo y sincronización de etiquetas. Gana el hub.

Etiquetas gestionadas: la de fábrica y "taken by <usuario>". Cualquier otra etiqueta del remoto
se respeta. El marcador de origen es `TrackerLink.managed_labels`: lo último que escribió el hub.
Así un cambio manual en el remoto se distingue de un cambio del hub y no se generan bucles.
"""

import logging
from collections.abc import Callable
from datetime import UTC, datetime
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters import ADAPTERS
from app.adapters.base import TrackerAdapter
from app.models import Project, ProjectIntegration, TrackerLink, WorkItem
from app.services.crypto import decrypt_token
from app.services.ingest import ingest
from app.services.intake import record

TAKEN_PREFIX = "taken by "
HUB_MARKER = "<!-- factory:origin=hub -->"

StartIntake = Callable[[int], None]
logger = logging.getLogger("factory.tracker")


def is_managed(label: str, factory_label: str) -> bool:
    return label == factory_label or label.startswith(TAKEN_PREFIX)


def desired_managed(item: WorkItem, factory_label: str) -> list[str]:
    taken = sorted(label for label in item.labels if label.startswith(TAKEN_PREFIX))
    return [factory_label, *taken]


def replace_taken_label(item: WorkItem, user: str | None) -> None:
    """Cambia la etiqueta "taken by" en memoria, sin commit. user=None la quita."""
    labels = [label for label in item.labels if not label.startswith(TAKEN_PREFIX)]
    if user is not None:
        labels = [*labels, f"{TAKEN_PREFIX}{user}"]
    item.labels = labels


def set_taken_by(db: Session, item: WorkItem, user: str, actor: str) -> None:
    """El hub marca quién atiende el item. La sincronización la copia al remoto."""
    replace_taken_label(item, user)
    record(db, item, "taken_by_set", None, actor, {"user": user})


def build_adapter(integration: ProjectIntegration) -> TrackerAdapter:
    token = decrypt_token(integration.token_encrypted) if integration.token_encrypted else None
    return ADAPTERS[integration.provider](integration.config, token)


def post_hub_comment(adapter: TrackerAdapter, remote_id: str, text: str) -> None:
    """Comentario del hub con marcador de origen oculto."""
    adapter.comment(remote_id, f"{text}\n\n{HUB_MARKER}")


def poll_integration(db: Session, integration: ProjectIntegration, start_intake: StartIntake) -> None:
    adapter = build_adapter(integration)
    project = db.get(Project, integration.project_id)
    for remote in adapter.fetch_new_items():
        item, created = ingest(
            db,
            project,
            source=integration.provider,
            title=remote.title,
            body=remote.body,
            payload={"title": remote.title, "body": remote.body, "source": integration.provider},
            idempotency_key=f"{integration.provider}:{remote.remote_id}",
            actor=f"{integration.provider}-poll",
            link={"provider": integration.provider, "remote_id": remote.remote_id, "remote_url": remote.url},
        )
        if created:
            start_intake(item.id)
    integration.last_polled_at = datetime.now(UTC)
    db.commit()
    reconcile_labels(db, integration, adapter)


def reconcile_labels(db: Session, integration: ProjectIntegration, adapter: TrackerAdapter) -> int:
    """Hace que las etiquetas gestionadas del remoto igualen las del hub. Devuelve reversiones/empujes."""
    factory_label = integration.config.get("label", "factory")
    links = db.scalars(
        select(TrackerLink).where(
            TrackerLink.project_id == integration.project_id, TrackerLink.provider == integration.provider
        )
    ).all()
    changed = 0
    for link in links:
        # Un enlace roto (404, movido, sin permiso) no debe frenar al resto del proyecto.
        try:
            changed += _reconcile_link(db, adapter, link, factory_label)
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            logger.warning(
                "sincronización de etiquetas fallida provider=%s link_id=%s error=%s",
                integration.provider,
                link.id,
                type(exc).__name__,
            )
    return changed


def _reconcile_link(db: Session, adapter: TrackerAdapter, link: TrackerLink, factory_label: str) -> int:
    item = db.get(WorkItem, link.work_item_id)
    desired = desired_managed(item, factory_label)
    hub_changed = desired != link.managed_labels
    remote = adapter.get_item(link.remote_id)
    remote_managed = sorted(label for label in remote.labels if is_managed(label, factory_label))
    if remote_managed == sorted(desired):
        if hub_changed:
            link.managed_labels = desired
            link.synced_at = datetime.now(UTC)
            db.commit()
        return 0
    # Solo se tocan las gestionadas; el resto de etiquetas del remoto se conservan.
    kept = [label for label in remote.labels if not is_managed(label, factory_label)]
    adapter.set_labels(link.remote_id, [*kept, *desired])
    kind = "labels_pushed" if hub_changed else "label_reverted"
    record(db, item, kind, None, "hub-sync", {"remote": remote_managed, "hub": desired})
    link.managed_labels = desired
    link.synced_at = datetime.now(UTC)
    db.commit()
    return 1
