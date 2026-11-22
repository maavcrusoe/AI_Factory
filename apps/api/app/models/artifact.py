"""Logs y diffs que el cliente sube por etapa (Fase 4). El contenido vive en Postgres."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class WorkArtifact(Base):
    __tablename__ = "work_artifacts"
    __table_args__ = (UniqueConstraint("work_item_id", "client_key", name="uq_work_artifacts_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    work_item_id: Mapped[int] = mapped_column(ForeignKey("work_items.id"), index=True)
    # Clave que genera el cliente: un reintento tras corte de red no duplica la fila.
    client_key: Mapped[str] = mapped_column(String(100))
    stage: Mapped[str] = mapped_column(String(30))
    round: Mapped[int] = mapped_column(Integer, default=0)
    kind: Mapped[str] = mapped_column(String(20))  # log | diff | failure_report | report
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
