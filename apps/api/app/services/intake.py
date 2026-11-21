"""Máquina de estados del intake y decisiones manuales. Cada cambio deja un WorkItemEvent."""

from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import SessionLocal
from app.models import WorkItem, WorkItemEvent
from app.services.intake_model import IntakeAssessment, IntakeInput, IntakeModel, IntakeModelError

RECEIVED = "RECEIVED"
NORMALIZING = "NORMALIZING"
TRIAGE = "TRIAGE"
QUEUED = "QUEUED"
NEEDS_INFO = "NEEDS_INFO"
WAITING_HUMAN_TRIAGE = "WAITING_HUMAN_TRIAGE"
REJECTED = "REJECTED"

# Umbral de automatismo (propuesta de specs/02). Por debajo, siempre decide un humano.
ACCEPT_THRESHOLD = 0.80
# Solo cambia el motivo que se muestra al humano; el destino es el mismo.
REVIEW_THRESHOLD = 0.65

MANUAL_FROM = {WAITING_HUMAN_TRIAGE, NEEDS_INFO}
STUCK_FROM = (RECEIVED, NORMALIZING, TRIAGE)


def assess_with_deadline(model: IntakeModel, item: IntakeInput, deadline: float) -> IntakeAssessment:
    """Plazo total duro: el timeout de httpx no basta (no cubre toda la espera)."""
    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(model.assess, item)
    try:
        return future.result(timeout=deadline)
    except FutureTimeout as exc:
        raise IntakeModelError(f"plazo de {deadline:g} s superado") from exc
    finally:
        # No esperar: la llamada colgada termina sola por el timeout de httpx.
        executor.shutdown(wait=False, cancel_futures=True)


def sweep_stuck_items(db: Session) -> int:
    """Al arrancar: lo que quedó a medias por un reinicio pasa a revisión humana."""
    items = db.scalars(select(WorkItem).where(WorkItem.status.in_(STUCK_FROM))).all()
    for item in items:
        previous = item.status
        item.reason = "Interrumpido por reinicio del hub: decide un humano"
        record(db, item, "startup_sweep", WAITING_HUMAN_TRIAGE, "system", {"previous": previous})
    return len(items)


def plan_outcome(assessment: IntakeAssessment) -> tuple[str, str | None]:
    """Devuelve (estado destino, motivo). Solo acepta con confianza alta; el resto va a humano."""
    if assessment.confidence < ACCEPT_THRESHOLD:
        level = "baja" if assessment.confidence < REVIEW_THRESHOLD else "media"
        return WAITING_HUMAN_TRIAGE, f"Confianza {level} ({assessment.confidence:.2f}): decide un humano"
    if assessment.decision == "accept":
        return QUEUED, None
    if assessment.decision == "needs_info":
        return NEEDS_INFO, "El modelo pide más información"
    return REJECTED, "El modelo recomienda rechazar"


def record(
    db: Session,
    item: WorkItem,
    kind: str,
    to_status: str | None,
    actor: str,
    detail: dict | None = None,
) -> None:
    """Guarda evento de auditoría y el estado nuevo, en una sola transacción."""
    from_status = item.status if to_status is not None else None
    if to_status is not None:
        item.status = to_status
    db.add(
        WorkItemEvent(
            work_item_id=item.id,
            kind=kind,
            from_status=from_status,
            to_status=to_status,
            actor=actor,
            detail=detail,
        )
    )
    db.commit()


def run_intake(work_item_id: int, model: IntakeModel) -> None:
    """Corre tras la respuesta HTTP. Cualquier fallo del modelo deja el item en revisión humana."""
    with SessionLocal() as db:
        item = db.get(WorkItem, work_item_id)
        if item is None or item.status != RECEIVED:
            return
        record(db, item, "normalized", NORMALIZING, "system")
        item.title = item.title.strip()
        # Leer antes del commit: después no se toca la BD hasta tener la valoración,
        # así la transacción no queda abierta durante la llamada al modelo.
        intake_input = IntakeInput(item.original_payload["projectId"], item.title, item.body)
        record(db, item, "triage_started", TRIAGE, "intake")

        try:
            deadline = get_settings().intake_deadline_seconds
            assessment = assess_with_deadline(model, intake_input, deadline)
        except Exception as exc:  # noqa: BLE001 - cualquier fallo del modelo va a humano, nunca auto-acepta
            item.reason = f"Intake fallido: {exc}"
            record(db, item, "intake_failed", WAITING_HUMAN_TRIAGE, "intake", {"reason": str(exc)})
            return

        item.decision = assessment.decision
        item.confidence = assessment.confidence
        item.work_type = assessment.work_type
        item.difficulty = assessment.difficulty
        item.risk = assessment.risk
        item.summary = assessment.summary
        item.valuation = assessment.valuation
        item.expanded_body = assessment.expanded_body
        item.labels = list(dict.fromkeys(assessment.suggested_labels))
        status, reason = plan_outcome(assessment)
        if status == QUEUED:
            item.labels = [*item.labels, "factory:auto"]
        item.reason = reason
        record(
            db,
            item,
            "intake_assessed",
            status,
            "intake",
            assessment.model_dump(by_alias=True),
        )


def apply_manual_decision(
    db: Session,
    item: WorkItem,
    action: str,
    actor: str,
    reason: str | None,
    label: str | None,
) -> None:
    if item.status not in MANUAL_FROM:
        raise HTTPException(status_code=409, detail=f"No se puede decidir en estado {item.status}")
    if action == "accept":
        status, decision = QUEUED, "accept"
        item.labels = list(dict.fromkeys([*item.labels, label or "factory:human"]))
    elif action == "reject":
        status, decision = REJECTED, "reject"
    else:
        status, decision = NEEDS_INFO, "needs_info"
    item.decision = decision
    item.reason = reason
    record(
        db,
        item,
        "manual_decision",
        status,
        actor,
        {"action": action, "reason": reason, "label": label},
    )
