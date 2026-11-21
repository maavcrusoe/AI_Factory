from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class WorkItem(Base):
    __tablename__ = "work_items"
    __table_args__ = (UniqueConstraint("project_id", "idempotency_key", name="uq_work_items_project_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    idempotency_key: Mapped[str] = mapped_column(String(200))
    source: Mapped[str] = mapped_column(String(20))
    original_payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    expanded_body: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), index=True)
    decision: Mapped[str | None] = mapped_column(String(20))
    confidence: Mapped[float | None] = mapped_column(Float)
    work_type: Mapped[str | None] = mapped_column(String(20))
    difficulty: Mapped[str | None] = mapped_column(String(10))
    risk: Mapped[str | None] = mapped_column(String(10))
    summary: Mapped[str | None] = mapped_column(Text)
    valuation: Mapped[str | None] = mapped_column(Text)
    labels: Mapped[list[str]] = mapped_column(JSON, default=list)
    reason: Mapped[str | None] = mapped_column(Text)
    # Claim (Fase 3): dueño = email del dev que lo cogió; nulo si está sin asignar.
    owner: Mapped[str | None] = mapped_column(String(320), index=True)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    heartbeat_state: Mapped[str | None] = mapped_column(String(30))
    heartbeat_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class WorkItemEvent(Base):
    """Registro de auditoría: cada cambio de estado o decisión deja una fila."""

    __tablename__ = "work_item_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    work_item_id: Mapped[int] = mapped_column(ForeignKey("work_items.id"), index=True)
    kind: Mapped[str] = mapped_column(String(40))
    from_status: Mapped[str | None] = mapped_column(String(30))
    to_status: Mapped[str | None] = mapped_column(String(30))
    actor: Mapped[str] = mapped_column(String(320))
    detail: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
