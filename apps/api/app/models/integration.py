from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ProjectIntegration(Base):
    """Conexión de un proyecto con su tracker/repo. El token va cifrado; nunca en claro."""

    __tablename__ = "project_integrations"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), unique=True)
    provider: Mapped[str] = mapped_column(String(20))
    config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    token_encrypted: Mapped[str | None] = mapped_column(Text)
    # Credencial separada: solo la usa el controlador de merge (Fase 5). Nunca la ven el cliente ni el tracker.
    merge_token_encrypted: Mapped[str | None] = mapped_column(Text)
    last_polled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"ProjectIntegration(id={self.id}, provider={self.provider!r}, has_token={self.token_encrypted is not None})"


class TrackerLink(Base):
    """Enlace WorkItem <-> issue/work item remoto. `managed_labels` es el marcador de origen:
    última lista de etiquetas gestionadas que escribió el hub."""

    __tablename__ = "tracker_links"
    __table_args__ = (UniqueConstraint("project_id", "provider", "remote_id", name="uq_tracker_links_remote"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    work_item_id: Mapped[int] = mapped_column(ForeignKey("work_items.id"), unique=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    provider: Mapped[str] = mapped_column(String(20))
    remote_id: Mapped[str] = mapped_column(String(100))
    remote_url: Mapped[str | None] = mapped_column(String(500))
    managed_labels: Mapped[list[str]] = mapped_column(JSON, default=list)
    synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
