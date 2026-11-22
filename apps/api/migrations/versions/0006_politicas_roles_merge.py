"""politicas, roles y merge (Fase 5)

Revision ID: 0006_politicas_roles_merge
Revises: 0005_work_artifacts
Create Date: 2026-11-22 10:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006_politicas_roles_merge"
down_revision: str | None = "0005_work_artifacts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Roles: el antiguo "member" pasa a "developer" (usa /factory).
    op.execute("UPDATE users SET role = 'developer' WHERE role = 'member'")
    op.alter_column("users", "role", server_default="developer")

    op.create_table(
        "merge_policies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("body", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.String(length=320), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "version", name="uq_merge_policies_version"),
    )
    op.create_index(op.f("ix_merge_policies_project_id"), "merge_policies", ["project_id"], unique=False)

    op.add_column("project_integrations", sa.Column("merge_token_encrypted", sa.Text(), nullable=True))

    op.add_column("work_items", sa.Column("pr_number", sa.Integer(), nullable=True))
    op.add_column("work_items", sa.Column("pr_url", sa.String(length=500), nullable=True))
    op.add_column("work_items", sa.Column("gate_sha", sa.String(length=40), nullable=True))
    op.add_column("work_items", sa.Column("gate_result", sa.String(length=10), nullable=True))
    op.add_column("work_items", sa.Column("meaning_change", sa.String(length=10), nullable=True))
    op.add_column("work_items", sa.Column("planned", sa.Boolean(), nullable=True))
    op.add_column("work_items", sa.Column("touched_paths", sa.JSON(), nullable=True))
    op.add_column("work_items", sa.Column("review_findings", sa.JSON(), nullable=True))
    op.add_column(
        "work_items",
        sa.Column("approval_version", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column("work_items", sa.Column("policy_version", sa.Integer(), nullable=True))
    op.add_column("work_items", sa.Column("policy_reasons", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("work_items", "policy_reasons")
    op.drop_column("work_items", "policy_version")
    op.drop_column("work_items", "approval_version")
    op.drop_column("work_items", "review_findings")
    op.drop_column("work_items", "touched_paths")
    op.drop_column("work_items", "planned")
    op.drop_column("work_items", "meaning_change")
    op.drop_column("work_items", "gate_result")
    op.drop_column("work_items", "gate_sha")
    op.drop_column("work_items", "pr_url")
    op.drop_column("work_items", "pr_number")
    op.drop_column("project_integrations", "merge_token_encrypted")
    op.drop_index(op.f("ix_merge_policies_project_id"), table_name="merge_policies")
    op.drop_table("merge_policies")
    op.alter_column("users", "role", server_default="member")
    op.execute("UPDATE users SET role = 'member' WHERE role = 'developer'")
