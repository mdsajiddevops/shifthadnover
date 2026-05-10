"""
Add created_by_id audit column to scheduled_shifts.

Revision ID: add_audit_to_scheduled_shifts
Revises: add_roster_scheduler_tables
Create Date: 2026-05-07
"""
from alembic import op
import sqlalchemy as sa


def upgrade():
    with op.batch_alter_table('scheduled_shifts') as batch_op:
        batch_op.add_column(
            sa.Column('created_by_id', sa.Integer(),
                      sa.ForeignKey('user.id'), nullable=True)
        )


def downgrade():
    with op.batch_alter_table('scheduled_shifts') as batch_op:
        batch_op.drop_column('created_by_id')
