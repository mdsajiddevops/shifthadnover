"""
Revision ID: add_failed_tasks_table
Revises: add_user_role_column
Create Date: 2026-05-02

Add failed_tasks dead-letter queue table (ADR-005, REQ-006).
Written exclusively by tasks/dlq_handler.py when a Celery task exhausts retries.
"""
from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'failed_tasks',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('celery_task_id', sa.String(length=255), nullable=False),
        sa.Column('task_name', sa.String(length=255), nullable=False),
        sa.Column('task_args', sa.Text(), nullable=True),
        sa.Column('task_kwargs', sa.Text(), nullable=True),
        sa.Column('error_message', sa.String(length=1000), nullable=True),
        sa.Column('error_trace', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='failed'),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('max_retries', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('alert_dispatched', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('alert_dispatched_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('celery_task_id', name='uq_failed_tasks_celery_task_id'),
    )
    op.create_index('ix_failed_tasks_celery_task_id', 'failed_tasks', ['celery_task_id'], unique=True)
    op.create_index('ix_failed_tasks_task_name', 'failed_tasks', ['task_name'], unique=False)
    op.create_index('ix_failed_tasks_status', 'failed_tasks', ['status'], unique=False)


def downgrade():
    op.drop_index('ix_failed_tasks_status', table_name='failed_tasks')
    op.drop_index('ix_failed_tasks_task_name', table_name='failed_tasks')
    op.drop_index('ix_failed_tasks_celery_task_id', table_name='failed_tasks')
    op.drop_table('failed_tasks')
