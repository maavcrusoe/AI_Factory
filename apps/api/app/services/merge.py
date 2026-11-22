"""Controlador de merge (Fase 5). Único sitio que mergea; usa la credencial de merge, no la del cliente.

Orden: bloqueo y paso a MERGING (commit) -> llamadas al remoto fuera del bloqueo -> MERGED o vuelta atrás.
Antes de mergear comprueba que el head del PR sigue siendo el SHA del gate. Si no, vuelve a PR_OPEN.
"""

import logging

import httpx
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters import ADAPTERS
from app.adapters.base import RepoAdapter
from app.models import ProjectIntegration, WorkItem
from app.services.claims import _locked, check_version, handle
from app.services.crypto import decrypt_token
from app.services.intake import record

PR_OPEN = "PR_OPEN"
READY_TO_MERGE = "READY_TO_MERGE"
MERGING = "MERGING"
MERGED = "MERGED"
logger = logging.getLogger("factory.merge")


def _controller(db: Session, item: WorkItem) -> RepoAdapter:
    integration = db.scalar(select(ProjectIntegration).where(ProjectIntegration.project_id == item.project_id))
    if integration is None or integration.merge_token_encrypted is None:
        raise HTTPException(status_code=422, detail="Sin credencial de merge configurada para el proyecto")
    token = decrypt_token(integration.merge_token_encrypted)
    return ADAPTERS[integration.provider](integration.config, token)


def merge_item(db: Session, item_id: int, actor: str, expected_version: int | None) -> WorkItem:
    item = _locked(db, item_id)
    if expected_version is not None:
        check_version(item, expected_version)
    if item.status != READY_TO_MERGE:
        raise HTTPException(status_code=409, detail=f"No está listo para mergear (estado {item.status})")
    if item.pr_number is None or item.gate_sha is None:
        raise HTTPException(status_code=409, detail="Falta el PR o el informe del gate")
    controller = _controller(db, item)
    pr_id = str(item.pr_number)
    sha = item.gate_sha
    item.status = MERGING
    item.approval_version += 1
    record(db, item, "merge_started", MERGING, actor, {"pr_number": item.pr_number, "gate_sha": sha})

    try:
        head = controller.get_head_sha(pr_id)
        if head != sha:
            # El PR cambió después del gate: el informe ya no vale para este código.
            item.gate_result = None
            record(
                db,
                item,
                "merge_rejected_sha",
                PR_OPEN,
                actor,
                {"gate_sha": sha, "head_sha": head},
            )
            raise HTTPException(status_code=409, detail="El PR cambió desde el gate: hace falta un nuevo informe")
        controller.mark_ready(pr_id)
        controller.merge_pr(pr_id, sha)
    except HTTPException:
        raise
    except (httpx.HTTPError, ValueError, NotImplementedError) as exc:
        logger.warning("Merge del item %s fallido: %s", item.id, exc)
        record(db, item, "merge_failed", READY_TO_MERGE, actor, {"reason": str(exc)})
        raise HTTPException(status_code=502, detail="El remoto rechazó el merge") from exc

    record(db, item, "merged", MERGED, actor, {"pr_number": item.pr_number, "sha": sha, "by": handle(actor)})
    return item
