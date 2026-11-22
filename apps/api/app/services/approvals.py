"""Informe del gate final, veredicto de política y decisiones de revisor (Fase 5).

Cada decisión deja un WorkItemEvent. Toda decisión pasa por `_locked` (FOR UPDATE) y, si lleva
`expected_version`, por `check_version`: una decisión sobre una versión vieja da 409.
"""

from typing import Literal

from fastapi import HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.models import WorkItem
from app.services.claims import _locked, check_version, handle
from app.services.intake import record
from app.services.merge import READY_TO_MERGE, merge_item
from app.services.merge_policy import MergeFacts, active_policy, evaluate

PR_OPEN = "PR_OPEN"
FIXING = "FIXING"
WAITING_HUMAN_MERGE = "WAITING_HUMAN_MERGE"
REPORTABLE = (PR_OPEN, FIXING)
MAX_PATHS = 500
MAX_FINDINGS = 50


class GateReport(BaseModel):
    """Lo que el cliente informa tras el gate final de un SHA concreto."""

    sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    result: Literal["passed", "failed"]
    meaning_change: Literal["none", "minor", "major", "dubious"]
    planned: bool
    touched_paths: list[str] = Field(max_length=MAX_PATHS)
    review_findings: list[str] = Field(default_factory=list, max_length=MAX_FINDINGS)


def report_gate(db: Session, item_id: int, actor: str, report: GateReport) -> WorkItem:
    item = _locked(db, item_id)
    if item.owner != actor or item.status not in REPORTABLE:
        raise HTTPException(status_code=409, detail=f"No tienes este PR en revisión (estado {item.status})")
    if item.pr_number is None:
        raise HTTPException(status_code=409, detail="El item no tiene PR abierto")

    # Un informe nuevo sustituye al anterior y vuelve a exigir decisión: lo aprobado queda obsoleto.
    item.gate_sha = report.sha
    item.gate_result = report.result
    item.meaning_change = report.meaning_change
    item.planned = report.planned
    item.touched_paths = report.touched_paths
    item.review_findings = report.review_findings
    item.approval_version += 1
    record(
        db,
        item,
        "gate_reported",
        None,
        actor,
        {"sha": report.sha, "result": report.result, "approval_version": item.approval_version},
    )
    if report.result == "failed":
        return item

    version, policy = active_policy(db, item.project_id)
    facts = MergeFacts(
        difficulty=item.difficulty,
        touched_paths=report.touched_paths,
        planned=report.planned,
        meaning_change=report.meaning_change,
        gate_result=report.result,
        gate_sha=report.sha,
    )
    verdict = evaluate(policy, facts)
    item.policy_version = version
    item.policy_reasons = verdict.reasons
    detail = {"policy_version": version, "reasons": verdict.reasons, "sha": report.sha}
    if verdict.human_required:
        item.reason = "Espera aprobación humana"
        record(db, item, "policy_evaluated", WAITING_HUMAN_MERGE, "system:policy", detail)
        return item

    item.reason = "Sin revisión humana según la política"
    record(db, item, "policy_evaluated", READY_TO_MERGE, "system:policy", detail)
    try:
        merge_item(db, item.id, "system:policy", None)
    except HTTPException:
        # El fallo ya queda en auditoría dentro de merge_item; el item se queda en READY_TO_MERGE.
        pass
    return item


def _decide(
    db: Session,
    item_id: int,
    actor: str,
    expected_version: int,
    *,
    kind: str,
    to_status: str,
    reason: str | None,
) -> WorkItem:
    item = _locked(db, item_id)
    check_version(item, expected_version)
    if item.status != WAITING_HUMAN_MERGE:
        raise HTTPException(status_code=409, detail=f"No espera aprobación (estado {item.status})")
    item.approval_version += 1
    item.reason = reason or f"Decidido por {handle(actor)}"
    record(
        db,
        item,
        kind,
        to_status,
        actor,
        {"gate_sha": item.gate_sha, "approval_version": item.approval_version, "reason": reason},
    )
    return item


def approve(db: Session, item_id: int, actor: str, expected_version: int) -> WorkItem:
    return _decide(
        db,
        item_id,
        actor,
        expected_version,
        kind="approved",
        to_status=READY_TO_MERGE,
        reason=f"Aprobado por {handle(actor)}",
    )


def request_changes(db: Session, item_id: int, actor: str, expected_version: int, reason: str) -> WorkItem:
    return _decide(
        db,
        item_id,
        actor,
        expected_version,
        kind="changes_requested",
        to_status=FIXING,
        reason=f"Cambios pedidos por {handle(actor)}: {reason}",
    )
