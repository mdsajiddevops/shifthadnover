"""
Create core_action_audit_entries table — COMP-017 (CTCOAMSHM-115, REQ-010)

Revision ID: add_core_action_audit_entries
Revises: add_core_action_records
Create Date: 2026-05-13
"""
from alembic import op
import sqlalchemy as sa

revision = "add_core_action_audit_entries"
down_revision = "add_core_action_records"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "core_action_audit_entries",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("core_action_id", sa.String(36), nullable=True),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("actor_user_id", sa.String(128), nullable=False),
        sa.Column("resource_id", sa.String(36), nullable=True),
        sa.Column("denied_operation", sa.String(128), nullable=True),
        sa.Column("details", sa.JSON, nullable=True),
        sa.Column(
            "recorded_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "event_type IN ('permission_denied','lock_denied','action_initiated',"
            "'action_completed','action_failed','action_rolled_back')",
            name="ck_core_action_audit_event_type",
        ),
        sa.ForeignKeyConstraint(
            ["core_action_id"],
            ["core_action_records.id"],
            name="fk_audit_core_action",
            ondelete="SET NULL",
        ),
    )
    op.create_index(
        "ix_core_action_audit_core_action_id",
        "core_action_audit_entries",
        ["core_action_id"],
    )
    op.create_index(
        "ix_core_action_audit_actor",
        "core_action_audit_entries",
        ["actor_user_id"],
    )
    op.create_index(
        "idx_ca_audit_event_type",
        "core_action_audit_entries",
        ["event_type"],
    )
    op.create_index(
        "idx_ca_audit_recorded_at",
        "core_action_audit_entries",
        ["recorded_at"],
    )


def downgrade():
    op.drop_index("idx_ca_audit_recorded_at", table_name="core_action_audit_entries")
    op.drop_index("idx_ca_audit_event_type", table_name="core_action_audit_entries")
    op.drop_index("ix_core_action_audit_actor", table_name="core_action_audit_entries")
    op.drop_index("ix_core_action_audit_core_action_id", table_name="core_action_audit_entries")
    op.drop_table("core_action_audit_entries")
