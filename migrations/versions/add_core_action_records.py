"""
Create core_action_records table — COMP-012 (CTCOAMSHM-115, REQ-007, REQ-009)

Revision ID: add_core_action_records
Revises: fix_scheduling_role_nullable
Create Date: 2026-05-13
"""
from alembic import op
import sqlalchemy as sa

revision = "add_core_action_records"
down_revision = "fix_scheduling_role_nullable"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "core_action_records",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("resource_id", sa.String(36), nullable=False),
        sa.Column("section_id", sa.String(128), nullable=False),
        sa.Column("actor_user_id", sa.String(128), nullable=False),
        sa.Column(
            "status",
            sa.String(32),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("payload", sa.JSON, nullable=False),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("completed_at", sa.DateTime, nullable=True),
        sa.Column("failure_reason", sa.Text, nullable=True),
        sa.CheckConstraint(
            "status IN ('pending','completed','failed','rolled_back')",
            name="ck_core_action_records_status",
        ),
        sa.ForeignKeyConstraint(["actor_user_id"], ["user.id"], name="fk_core_action_actor"),
    )
    op.create_index(
        "ix_core_action_records_resource_id",
        "core_action_records",
        ["resource_id"],
    )
    op.create_index(
        "idx_ca_record_actor",
        "core_action_records",
        ["actor_user_id"],
    )
    op.create_index(
        "idx_ca_record_status_created",
        "core_action_records",
        ["status", "created_at"],
    )


def downgrade():
    op.drop_index("idx_ca_record_status_created", table_name="core_action_records")
    op.drop_index("idx_ca_record_actor", table_name="core_action_records")
    op.drop_index("ix_core_action_records_resource_id", table_name="core_action_records")
    op.drop_table("core_action_records")
