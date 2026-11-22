"""Métricas por proyecto en formato Prometheus. Se calculan desde Postgres: sobreviven a reinicios."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Project, WorkItem, WorkItemEvent
from app.services.claims import CLAIMED
from app.services.intake import QUEUED

EXPIRY_KIND = "heartbeat_expired"
ERROR_KINDS = ("intake_failed", "merge_failed", "startup_sweep")

Labels = dict[str, str]


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


def _sample(name: str, labels: Labels, value: int) -> str:
    inner = ",".join(f'{key}="{_escape(val)}"' for key, val in labels.items())
    return f"{name}{{{inner}}} {value}"


def render_metrics(db: Session) -> str:
    out: list[str] = []

    def family(name: str, kind: str, help_text: str, samples: list[str]) -> None:
        out.append(f"# HELP {name} {help_text}")
        out.append(f"# TYPE {name} {kind}")
        out.extend(samples)

    slugs = list(db.scalars(select(Project.slug).order_by(Project.slug)).all())

    status_rows = db.execute(
        select(Project.slug, WorkItem.status, func.count(WorkItem.id))
        .join(WorkItem, WorkItem.project_id == Project.id)
        .group_by(Project.slug, WorkItem.status)
    ).all()
    by_status = {(slug, status): count for slug, status, count in status_rows}

    family(
        "factory_work_items",
        "gauge",
        "Items por proyecto y estado.",
        [_sample("factory_work_items", {"project": s, "status": st}, n) for s, st, n in status_rows],
    )
    family(
        "factory_queue_size",
        "gauge",
        "Items en cola (QUEUED) por proyecto.",
        [_sample("factory_queue_size", {"project": s}, by_status.get((s, QUEUED), 0)) for s in slugs],
    )
    family(
        "factory_claims_active",
        "gauge",
        "Items con claim activo (CLAIMED) por proyecto.",
        [_sample("factory_claims_active", {"project": s}, by_status.get((s, CLAIMED), 0)) for s in slugs],
    )

    event_rows = db.execute(
        select(Project.slug, WorkItemEvent.kind, func.count(WorkItemEvent.id))
        .join(WorkItem, WorkItem.id == WorkItemEvent.work_item_id)
        .join(Project, Project.id == WorkItem.project_id)
        .where(WorkItemEvent.kind.in_((EXPIRY_KIND, *ERROR_KINDS)))
        .group_by(Project.slug, WorkItemEvent.kind)
    ).all()
    expiries = {sl: n for sl, k, n in event_rows if k == EXPIRY_KIND}
    family(
        "factory_heartbeat_expiries_total",
        "counter",
        "Claims caducados por falta de latido, desde el inicio de la base de datos.",
        [_sample("factory_heartbeat_expiries_total", {"project": s}, expiries.get(s, 0)) for s in slugs],
    )
    family(
        "factory_errors_total",
        "counter",
        "Eventos de error operativo (intake fallido, merge fallido, reinicio con items colgados).",
        [_sample("factory_errors_total", {"project": s, "kind": k}, n) for s, k, n in event_rows if k in ERROR_KINDS],
    )

    decision_rows = db.execute(
        select(Project.slug, WorkItem.decision, func.count(WorkItem.id))
        .join(WorkItem, WorkItem.project_id == Project.id)
        .where(WorkItem.decision.is_not(None))
        .group_by(Project.slug, WorkItem.decision)
    ).all()
    family(
        "factory_intake_decisions",
        "gauge",
        "Items por decisión actual del intake (ACCEPT, REJECT, ...).",
        [_sample("factory_intake_decisions", {"project": s, "decision": d}, n) for s, d, n in decision_rows],
    )

    return "\n".join(out) + "\n"
