"""Add check-in status tracking to team members

Revision ID: add_checkin_system
Revises: 
Create Date: 2025-12-11 19:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'add_checkin_system'
down_revision = None  # Update this with the latest revision if needed
branch_labels = None
depends_on = None

def upgrade():
    # Add check-in status fields to team_member table
    op.add_column('team_member', sa.Column('availability_status', sa.String(32), nullable=True, default='offline'))
    op.add_column('team_member', sa.Column('last_checkin', sa.DateTime(), nullable=True))
    op.add_column('team_member', sa.Column('checkin_location', sa.String(128), nullable=True))
    
    # Create checkin_log table
    op.create_table('checkin_log',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('team_member_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(32), nullable=False),
        sa.Column('checkin_time', sa.DateTime(), nullable=False),
        sa.Column('checkout_time', sa.DateTime(), nullable=True),
        sa.Column('location', sa.String(128), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(256), nullable=True),
        sa.ForeignKeyConstraint(['team_member_id'], ['team_member.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Set default availability_status to 'offline' for existing team members
    op.execute("UPDATE team_member SET availability_status = 'offline' WHERE availability_status IS NULL")

def downgrade():
    # Remove checkin_log table
    op.drop_table('checkin_log')
    
    # Remove check-in status fields from team_member table
    op.drop_column('team_member', 'checkin_location')
    op.drop_column('team_member', 'last_checkin')
    op.drop_column('team_member', 'availability_status')