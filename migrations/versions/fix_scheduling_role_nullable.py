"""
Backfill NULL scheduling_role values and make column NOT NULL.

Revision ID: fix_scheduling_role_nullable
Revises: add_roster_scheduler_tables
Create Date: 2026-05-07
"""
from alembic import op
import sqlalchemy as sa


def upgrade():
    # Backfill any existing NULL rows to 'support' before enforcing NOT NULL
    op.execute("UPDATE team_member SET scheduling_role = 'support' WHERE scheduling_role IS NULL")

    with op.batch_alter_table('team_member') as batch_op:
        batch_op.alter_column(
            'scheduling_role',
            existing_type=sa.String(16),
            nullable=False,
            server_default='support',
        )


def downgrade():
    with op.batch_alter_table('team_member') as batch_op:
        batch_op.alter_column(
            'scheduling_role',
            existing_type=sa.String(16),
            nullable=True,
            server_default='support',
        )
