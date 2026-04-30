"""Add ServiceNow configuration table

Revision ID: add_servicenow_config_table
Revises: add_app_config_table
Create Date: 2025-10-15 16:50:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_servicenow_config_table'
down_revision = 'add_app_config_table'
branch_labels = None
depends_on = None

def upgrade():
    # Create servicenow_config table
    op.create_table('servicenow_config',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('config_key', sa.String(length=128), nullable=False),
        sa.Column('config_value', sa.Text(), nullable=True),
        sa.Column('encrypted', sa.Boolean(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('config_key')
    )

def downgrade():
    op.drop_table('servicenow_config')