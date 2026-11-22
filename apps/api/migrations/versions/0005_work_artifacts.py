"""work_artifacts: logs y diffs por etapa del cliente (Fase 4)

Revision ID: 0005_work_artifacts
Revises: 0004_claims_y_tokens
Create Date: 2026-11-21 21:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005_work_artifacts"
down_revision: str | None = "0004_claims_y_tokens"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "work_artifacts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("work_item_id", sa.Integer(), nullable=False),
        sa.Column("client_key", sa.String(length=100), nullable=False),
        sa.Column("stage", sa.String(length=30), nullable=False),
        sa.Column("round", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["work_item_id"], ["work_items.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("work_item_id", "client_key", name="uq_work_artifacts_key"),
    )
    op.create_index(op.f("ix_work_artifacts_work_item_id"), "work_artifacts", ["work_item_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_work_artifacts_work_item_id"), table_name="work_artifacts")
    op.drop_table("work_artifacts")
