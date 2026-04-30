"""
Add collaborative handover tables for real-time multi-user editing.

Creates the following tables:
- handover_session: Tracks active editing sessions
- section_lock: Manages soft locks for sections
- handover_change: Audit trail for all changes
- draft_incident: Temporary storage for incidents being edited
- draft_key_point: Temporary storage for keypoints being edited
"""

from alembic import op
import sqlalchemy as sa
from datetime import datetime


def upgrade():
    """Create collaborative handover tables."""
    
    # Create handover_session table
    op.create_table(
        'handover_session',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('shift_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('session_token', sa.String(64), nullable=False),
        sa.Column('started_at', sa.DateTime(), default=datetime.utcnow),
        sa.Column('last_heartbeat', sa.DateTime(), default=datetime.utcnow),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('current_section', sa.String(64), nullable=True),
        sa.Column('current_item_id', sa.String(64), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['shift_id'], ['shift.id']),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
    )
    op.create_index('idx_active_sessions', 'handover_session', ['shift_id', 'is_active'])
    op.create_index('idx_session_heartbeat', 'handover_session', ['is_active', 'last_heartbeat'])
    op.create_index('ix_handover_session_session_token', 'handover_session', ['session_token'], unique=True)
    op.create_index('ix_handover_session_shift_id', 'handover_session', ['shift_id'])
    op.create_index('ix_handover_session_last_heartbeat', 'handover_session', ['last_heartbeat'])
    op.create_index('ix_handover_session_is_active', 'handover_session', ['is_active'])

    # Create section_lock table
    op.create_table(
        'section_lock',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('shift_id', sa.Integer(), nullable=False),
        sa.Column('section_type', sa.String(32), nullable=False),
        sa.Column('item_id', sa.String(64), nullable=True),
        sa.Column('locked_by_user_id', sa.Integer(), nullable=False),
        sa.Column('locked_at', sa.DateTime(), default=datetime.utcnow),
        sa.Column('lock_expires_at', sa.DateTime(), nullable=False),
        sa.Column('version', sa.Integer(), default=1),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['shift_id'], ['shift.id']),
        sa.ForeignKeyConstraint(['locked_by_user_id'], ['user.id']),
    )
    op.create_index('idx_section_lock_unique', 'section_lock', ['shift_id', 'section_type', 'item_id'], unique=True)
    op.create_index('idx_lock_expiry', 'section_lock', ['lock_expires_at'])
    op.create_index('ix_section_lock_shift_id', 'section_lock', ['shift_id'])

    # Create handover_change table
    op.create_table(
        'handover_change',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('shift_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('change_type', sa.String(32), nullable=False),
        sa.Column('section_type', sa.String(32), nullable=False),
        sa.Column('item_id', sa.String(64), nullable=True),
        sa.Column('field_name', sa.String(64), nullable=True),
        sa.Column('old_value', sa.Text(), nullable=True),
        sa.Column('new_value', sa.Text(), nullable=True),
        sa.Column('changed_at', sa.DateTime(), default=datetime.utcnow),
        sa.Column('version', sa.Integer(), default=1),
        sa.Column('is_conflict', sa.Boolean(), default=False),
        sa.Column('conflict_resolved', sa.Boolean(), nullable=True),
        sa.Column('resolution_type', sa.String(32), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['shift_id'], ['shift.id']),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
    )
    op.create_index('idx_changes_by_shift', 'handover_change', ['shift_id', 'changed_at'])
    op.create_index('idx_changes_by_section', 'handover_change', ['shift_id', 'section_type', 'item_id'])
    op.create_index('ix_handover_change_shift_id', 'handover_change', ['shift_id'])
    op.create_index('ix_handover_change_changed_at', 'handover_change', ['changed_at'])

    # Create draft_incident table
    op.create_table(
        'draft_incident',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('shift_id', sa.Integer(), nullable=False),
        sa.Column('temp_id', sa.String(64), nullable=False),
        sa.Column('incident_number', sa.String(64), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(32), nullable=True),
        sa.Column('priority', sa.String(32), nullable=True),
        sa.Column('assigned_to', sa.String(128), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_by_user_id', sa.Integer(), nullable=False),
        sa.Column('last_modified_by_user_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), default=datetime.utcnow),
        sa.Column('modified_at', sa.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow),
        sa.Column('version', sa.Integer(), default=1),
        sa.Column('is_deleted', sa.Boolean(), default=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['shift_id'], ['shift.id']),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['user.id']),
        sa.ForeignKeyConstraint(['last_modified_by_user_id'], ['user.id']),
    )
    op.create_index('idx_draft_incidents', 'draft_incident', ['shift_id', 'is_deleted'])
    op.create_index('ix_draft_incident_shift_id', 'draft_incident', ['shift_id'])
    op.create_index('ix_draft_incident_temp_id', 'draft_incident', ['temp_id'])

    # Create draft_key_point table
    op.create_table(
        'draft_key_point',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('shift_id', sa.Integer(), nullable=False),
        sa.Column('temp_id', sa.String(64), nullable=False),
        sa.Column('title', sa.String(256), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(64), nullable=True),
        sa.Column('priority', sa.String(32), nullable=True),
        sa.Column('action_required', sa.Boolean(), default=False),
        sa.Column('action_owner', sa.String(128), nullable=True),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('created_by_user_id', sa.Integer(), nullable=False),
        sa.Column('last_modified_by_user_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), default=datetime.utcnow),
        sa.Column('modified_at', sa.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow),
        sa.Column('version', sa.Integer(), default=1),
        sa.Column('is_deleted', sa.Boolean(), default=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['shift_id'], ['shift.id']),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['user.id']),
        sa.ForeignKeyConstraint(['last_modified_by_user_id'], ['user.id']),
    )
    op.create_index('idx_draft_keypoints', 'draft_key_point', ['shift_id', 'is_deleted'])
    op.create_index('ix_draft_key_point_shift_id', 'draft_key_point', ['shift_id'])
    op.create_index('ix_draft_key_point_temp_id', 'draft_key_point', ['temp_id'])


def downgrade():
    """Remove collaborative handover tables."""
    
    # Drop draft_key_point table
    op.drop_index('ix_draft_key_point_temp_id', table_name='draft_key_point')
    op.drop_index('ix_draft_key_point_shift_id', table_name='draft_key_point')
    op.drop_index('idx_draft_keypoints', table_name='draft_key_point')
    op.drop_table('draft_key_point')
    
    # Drop draft_incident table
    op.drop_index('ix_draft_incident_temp_id', table_name='draft_incident')
    op.drop_index('ix_draft_incident_shift_id', table_name='draft_incident')
    op.drop_index('idx_draft_incidents', table_name='draft_incident')
    op.drop_table('draft_incident')
    
    # Drop handover_change table
    op.drop_index('ix_handover_change_changed_at', table_name='handover_change')
    op.drop_index('ix_handover_change_shift_id', table_name='handover_change')
    op.drop_index('idx_changes_by_section', table_name='handover_change')
    op.drop_index('idx_changes_by_shift', table_name='handover_change')
    op.drop_table('handover_change')
    
    # Drop section_lock table
    op.drop_index('ix_section_lock_shift_id', table_name='section_lock')
    op.drop_index('idx_lock_expiry', table_name='section_lock')
    op.drop_index('idx_section_lock_unique', table_name='section_lock')
    op.drop_table('section_lock')
    
    # Drop handover_session table
    op.drop_index('ix_handover_session_is_active', table_name='handover_session')
    op.drop_index('ix_handover_session_last_heartbeat', table_name='handover_session')
    op.drop_index('ix_handover_session_shift_id', table_name='handover_session')
    op.drop_index('ix_handover_session_session_token', table_name='handover_session')
    op.drop_index('idx_session_heartbeat', table_name='handover_session')
    op.drop_index('idx_active_sessions', table_name='handover_session')
    op.drop_table('handover_session')
