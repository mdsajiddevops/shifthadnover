"""
Add resolved_at timestamp to incident table so recently-resolved incidents
can be pre-populated in the next handover form's Closed Incidents section.

Revision ID: add_resolved_at_to_incident
Revises: add_is_resolved_to_incident
Create Date: 2026-05-07
"""
from alembic import op
import sqlalchemy as sa


def upgrade():
    with op.batch_alter_table('incident') as batch_op:
        batch_op.add_column(
            sa.Column('resolved_at', sa.DateTime(), nullable=True)
        )


def downgrade():
    with op.batch_alter_table('incident') as batch_op:
        batch_op.drop_column('resolved_at')
