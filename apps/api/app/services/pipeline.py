"""Pipeline del cliente (Fase 4): completar con PR, enlace al issue y artefactos (logs/diffs)."""

from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import TrackerLink, WorkArtifact, WorkItem
from app.services.claims import _locked, _require_owner
from app.services.intake import record
from app.services.tracker_sync import replace_taken_label

PR_OPEN = "PR_OPEN"
CLAIMED = "CLAIMED"
MAX_ARTIFACT_CHARS = 200_000
ARTIFACT_KINDS = {"log", "diff", "failure_report", "report"}


def complete(db: Session, item_id: int, user_email: str, pr_url: str, pr_number: int) -> WorkItem:
    """El dueño cierra su trabajo con un PR en borrador. Pasa a PR_OPEN: la caducidad no lo toca."""
    if not pr_url.startswith("https://"):
        raise HTTPException(status_code=422, detail="pr_url debe empezar por https://")
    item = _locked(db, item_id)
    _require_owner(item, user_email)
    item.status = PR_OPEN
    item.reason = f"PR en borrador: {pr_url}"
    replace_taken_label(item, None)
    record(db, item, "pr_opened", PR_OPEN, user_email, {"pr_url": pr_url, "pr_number": pr_number})
    return item


def link_tracker(
    db: Session, item_id: int, actor: str, provider: str, remote_id: str, remote_url: str | None
) -> TrackerLink:
    """Enlaza el item con un issue remoto (p. ej. para `Closes #N`). Idempotente para el mismo issue."""
    item = _locked(db, item_id)
    existing = db.scalar(select(TrackerLink).where(TrackerLink.work_item_id == item.id))
    if existing is not None:
        if (existing.provider, existing.remote_id) == (provider, remote_id):
            db.rollback()
            return existing
        db.rollback()
        raise HTTPException(status_code=409, detail="El item ya está enlazado a otro issue")
    link = TrackerLink(
        work_item_id=item.id,
        project_id=item.project_id,
        provider=provider,
        remote_id=remote_id,
        remote_url=remote_url,
        managed_labels=[],
    )
    db.add(link)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Ese issue ya está enlazado a otro item") from None
    record(db, item, "tracker_linked", None, actor, {"provider": provider, "remote_id": remote_id})
    return link


def add_artifact(
    db: Session,
    item_id: int,
    user_email: str,
    *,
    stage: str,
    round_no: int,
    kind: str,
    client_key: str,
    content: str,
) -> tuple[WorkArtifact, bool]:
    """Devuelve (artefacto, creado). Misma `client_key` en el item: no duplica (reintento tras corte)."""
    if kind not in ARTIFACT_KINDS:
        raise HTTPException(status_code=422, detail=f"kind no válido: {kind}")
    if len(content) > MAX_ARTIFACT_CHARS:
        raise HTTPException(status_code=422, detail=f"content supera {MAX_ARTIFACT_CHARS} caracteres")
    item = _locked(db, item_id)
    _require_owner(item, user_email)
    existing = db.scalar(
        select(WorkArtifact).where(
            WorkArtifact.work_item_id == item.id, WorkArtifact.client_key == client_key
        )
    )
    if existing is not None:
        db.rollback()
        return existing, False
    artifact = WorkArtifact(
        work_item_id=item.id,
        client_key=client_key,
        stage=stage,
        round=round_no,
        kind=kind,
        content=content,
    )
    db.add(artifact)
    db.commit()
    return artifact, True


def list_artifacts(db: Session, item_id: int) -> list[WorkArtifact]:
    return list(
        db.scalars(
            select(WorkArtifact).where(WorkArtifact.work_item_id == item_id).order_by(WorkArtifact.id)
        ).all()
    )


def artifact_out(artifact: WorkArtifact) -> dict[str, Any]:
    return {
        "id": artifact.id,
        "stage": artifact.stage,
        "round": artifact.round,
        "kind": artifact.kind,
        "client_key": artifact.client_key,
        "content": artifact.content,
        "created_at": artifact.created_at.isoformat(),
    }
