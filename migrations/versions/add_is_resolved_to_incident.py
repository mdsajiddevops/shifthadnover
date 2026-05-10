"""
Add is_resolved flag to incident table for cross-shift carryforward tracking.

Revision ID: add_is_resolved_to_incident
Revises: create_email_delivery_log
Create Date: 2026-05-07
"""
from alembic import op
import sqlalchemy as sa


def upgrade():
    with op.batch_alter_table('incident') as batch_op:
        batch_op.add_column(
            sa.Column('is_resolved', sa.Boolean(), nullable=False, server_default='0')
        )


def downgrade():
    with op.batch_alter_table('incident') as batch_op:
        batch_op.drop_column('is_resolved')
