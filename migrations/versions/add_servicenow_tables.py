"""Add ServiceNow integration tables

Revision ID: servicenow_integration
Revises: previous_migration
Create Date: 2025-01-08

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers
revision = 'servicenow_integration'
down_revision = None  # Will be set by alembic
branch_labels = None
depends_on = None


def upgrade():
    # Create servicenow_incidents table
    op.create_table('servicenow_incidents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('sys_id', sa.String(length=50), nullable=False),
        sa.Column('number', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('state', sa.String(length=50), nullable=False),
        sa.Column('priority', sa.String(length=20), nullable=True),
        sa.Column('urgency', sa.String(length=20), nullable=True),
        sa.Column('impact', sa.String(length=20), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('subcategory', sa.String(length=100), nullable=True),
        sa.Column('assignment_group', sa.String(length=100), nullable=True),
        sa.Column('assigned_to', sa.String(length=100), nullable=True),
        sa.Column('caller', sa.String(length=100), nullable=True),
        sa.Column('opened_by', sa.String(length=100), nullable=True),
        sa.Column('created_on', sa.DateTime(), nullable=False),
        sa.Column('updated_on', sa.DateTime(), nullable=False),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('closed_at', sa.DateTime(), nullable=True),
        sa.Column('close_notes', sa.Text(), nullable=True),
        sa.Column('work_notes', sa.Text(), nullable=True),
        sa.Column('comments', sa.Text(), nullable=True),
        sa.Column('last_synced', sa.DateTime(), nullable=False),
        sa.Column('sync_status', sa.String(length=20), nullable=False),
        sa.Column('account_id', sa.Integer(), nullable=True),
        sa.Column('team_id', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for servicenow_incidents
    op.create_index('ix_servicenow_incidents_sys_id', 'servicenow_incidents', ['sys_id'], unique=True)
    op.create_index('ix_servicenow_incidents_number', 'servicenow_incidents', ['number'], unique=True)
    op.create_index('ix_servicenow_incidents_state', 'servicenow_incidents', ['state'])
    op.create_index('ix_servicenow_incidents_priority', 'servicenow_incidents', ['priority'])
    op.create_index('ix_servicenow_incidents_assignment_group', 'servicenow_incidents', ['assignment_group'])
    op.create_index('ix_servicenow_incidents_created_on', 'servicenow_incidents', ['created_on'])
    
    # Create servicenow_assignment_groups table
    op.create_table('servicenow_assignment_groups',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('sys_id', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.Column('account_id', sa.Integer(), nullable=True),
        sa.Column('team_id', sa.Integer(), nullable=True),
        sa.Column('created_on', sa.DateTime(), nullable=False),
        sa.Column('updated_on', sa.DateTime(), nullable=False),
        sa.Column('last_synced', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for servicenow_assignment_groups
    op.create_index('ix_servicenow_assignment_groups_sys_id', 'servicenow_assignment_groups', ['sys_id'], unique=True)
    op.create_index('ix_servicenow_assignment_groups_name', 'servicenow_assignment_groups', ['name'])
    
    # Create servicenow_sync_logs table
    op.create_table('servicenow_sync_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('sync_started', sa.DateTime(), nullable=False),
        sa.Column('sync_completed', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('incidents_synced', sa.Integer(), nullable=True),
        sa.Column('incidents_updated', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('sync_type', sa.String(length=50), nullable=True),
        sa.Column('triggered_by', sa.String(length=100), nullable=True),
        sa.Column('service_groups', sa.JSON(), nullable=True),
        sa.Column('shift_start', sa.DateTime(), nullable=True),
        sa.Column('shift_end', sa.DateTime(), nullable=True),
        sa.Column('account_id', sa.Integer(), nullable=True),
        sa.Column('team_id', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    # Drop tables in reverse order
    op.drop_table('servicenow_sync_logs')
    op.drop_table('servicenow_assignment_groups')
    op.drop_table('servicenow_incidents')