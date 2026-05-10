"""
Add roster scheduler tables and scheduling_role column.

Revision ID: add_roster_scheduler_tables
Revises:
Create Date: 2026-05-06
"""
from alembic import op
import sqlalchemy as sa


def upgrade():
    # shift_coverage_requirements
    op.create_table(
        'shift_coverage_requirements',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('team_id', sa.Integer(), sa.ForeignKey('team.id'), nullable=False),
        sa.Column('account_id', sa.Integer(), sa.ForeignKey('account.id'), nullable=False),
        sa.Column('shift_code', sa.String(10), nullable=False),
        sa.Column('required_count', sa.String(4), nullable=False, server_default='1'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False,
                  server_default=sa.func.now()),
        sa.UniqueConstraint('team_id', 'shift_code', name='uq_team_shift_req'),
    )
    op.create_index('idx_coverage_req_team', 'shift_coverage_requirements',
                    ['team_id', 'is_active'])

    # public_holidays
    op.create_table(
        'public_holidays',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('account_id', sa.Integer(), sa.ForeignKey('account.id'), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('name', sa.String(128), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False,
                  server_default=sa.func.now()),
        sa.UniqueConstraint('account_id', 'date', name='uq_account_holiday'),
    )
    op.create_index('idx_public_holiday_account_date', 'public_holidays',
                    ['account_id', 'date'])

    # scheduled_shifts
    op.create_table(
        'scheduled_shifts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('team_member_id', sa.Integer(),
                  sa.ForeignKey('team_member.id'), nullable=False),
        sa.Column('team_id', sa.Integer(), sa.ForeignKey('team.id'), nullable=False),
        sa.Column('account_id', sa.Integer(), sa.ForeignKey('account.id'), nullable=False),
        sa.Column('shift_date', sa.Date(), nullable=False),
        sa.Column('shift_code', sa.String(10), nullable=False),
        sa.Column('is_protected', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('source', sa.String(16), nullable=False, server_default='auto'),
        sa.Column('created_at', sa.DateTime(), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False,
                  server_default=sa.func.now()),
        sa.UniqueConstraint('team_member_id', 'shift_date', name='uq_member_shift_date'),
    )
    op.create_index('idx_scheduled_shift_team_date', 'scheduled_shifts',
                    ['team_id', 'shift_date'])
    op.create_index('idx_scheduled_shift_account_date', 'scheduled_shifts',
                    ['account_id', 'shift_date'])

    # scheduling_role on team_member
    op.add_column('team_member',
        sa.Column('scheduling_role', sa.String(16), nullable=True, server_default='support'))


def downgrade():
    op.drop_column('team_member', 'scheduling_role')
    op.drop_index('idx_scheduled_shift_account_date', table_name='scheduled_shifts')
    op.drop_index('idx_scheduled_shift_team_date', table_name='scheduled_shifts')
    op.drop_table('scheduled_shifts')
    op.drop_index('idx_public_holiday_account_date', table_name='public_holidays')
    op.drop_table('public_holidays')
    op.drop_index('idx_coverage_req_team', table_name='shift_coverage_requirements')
    op.drop_table('shift_coverage_requirements')
