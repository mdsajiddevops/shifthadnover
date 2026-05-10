"""
Create email_delivery_log table for email monitoring.

Revision ID: create_email_delivery_log
Revises:
Create Date: 2026-05-07
"""
from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'email_delivery_log',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('subject', sa.String(500), nullable=False),
        sa.Column('recipients', sa.Text(), nullable=False),
        sa.Column('cc_recipients', sa.Text(), nullable=True),
        sa.Column('sender', sa.String(255), nullable=True),
        sa.Column('source_type', sa.String(50), nullable=False),
        sa.Column('source_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('smtp_server', sa.String(255), nullable=True),
        sa.Column('smtp_port', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('duration_seconds', sa.Float(), nullable=True),
        sa.Column('account_id', sa.Integer(), sa.ForeignKey('account.id'), nullable=True),
        sa.Column('team_id', sa.Integer(), sa.ForeignKey('team.id'), nullable=True),
        sa.Column('triggered_by_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=True),
        sa.Column('recipient_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('retry_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('uns_event_id', sa.String(100), nullable=True),
    )
    op.create_index('ix_email_delivery_log_uns_event_id', 'email_delivery_log', ['uns_event_id'])
    op.create_index('ix_email_delivery_log_status', 'email_delivery_log', ['status'])
    op.create_index('ix_email_delivery_log_created_at', 'email_delivery_log', ['created_at'])


def downgrade():
    op.drop_index('ix_email_delivery_log_created_at', table_name='email_delivery_log')
    op.drop_index('ix_email_delivery_log_status', table_name='email_delivery_log')
    op.drop_index('ix_email_delivery_log_uns_event_id', table_name='email_delivery_log')
    op.drop_table('email_delivery_log')
