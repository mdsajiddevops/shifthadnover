"""
Expand shift_roster.shift_code from String(8) to String(10) to support combined codes like E/OCN.

Revision ID: expand_shift_roster_code_column
Revises: add_roster_scheduler_tables
Create Date: 2026-05-07
"""
from alembic import op
import sqlalchemy as sa


def upgrade():
    with op.batch_alter_table('shift_roster') as batch_op:
        batch_op.alter_column(
            'shift_code',
            existing_type=sa.String(8),
            type_=sa.String(10),
            nullable=True,
        )


def downgrade():
    with op.batch_alter_table('shift_roster') as batch_op:
        batch_op.alter_column(
            'shift_code',
            existing_type=sa.String(10),
            type_=sa.String(8),
            nullable=True,
        )
