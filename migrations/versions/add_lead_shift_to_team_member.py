"""
Add lead_shift column to team_member for configurable lead weekday shift.

Revision ID: add_lead_shift_to_team_member
Revises: add_roster_scheduler_tables
Create Date: 2026-05-07
"""
from alembic import op
import sqlalchemy as sa


def upgrade():
    with op.batch_alter_table('team_member') as batch_op:
        batch_op.add_column(
            sa.Column('lead_shift', sa.String(8), nullable=True, server_default='E')
        )


def downgrade():
    with op.batch_alter_table('team_member') as batch_op:
        batch_op.drop_column('lead_shift')
