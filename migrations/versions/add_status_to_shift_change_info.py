"""Add status column to shift_change_info table

Revision ID: add_status_to_shift_change_info
Revises: 
Create Date: 2024-12-19 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_status_to_shift_change_info'
down_revision = None
depends_on = None

def upgrade():
    # Add status column to shift_change_info table with default value 'New'
    op.add_column('shift_change_info', sa.Column('status', sa.String(16), nullable=False, server_default='New'))
    print("✅ Added status column to shift_change_info table")

def downgrade():
    # Remove status column from shift_change_info table
    op.drop_column('shift_change_info', 'status')
    print("✅ Removed status column from shift_change_info table")