"""Add enhanced fields to incident table

Revision ID: add_incident_fields
Revises: add_jira_id_to_keypoint
Create Date: 2024-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_incident_fields'
down_revision = 'add_jira_id_to_keypoint'
branch_labels = None
depends_on = None

def upgrade():
    # Add new fields to incident table
    op.add_column('incident', sa.Column('description', sa.Text(), nullable=True))
    op.add_column('incident', sa.Column('assigned_to', sa.String(128), nullable=True))
    op.add_column('incident', sa.Column('escalated_to', sa.String(128), nullable=True))

def downgrade():
    # Remove the added fields
    op.drop_column('incident', 'escalated_to')
    op.drop_column('incident', 'assigned_to')
    op.drop_column('incident', 'description')