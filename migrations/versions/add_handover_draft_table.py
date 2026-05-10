"""
Add handover_draft table for Yjs document persistence (CTCOAMSHM-7).

Stores the serialized Yjs document state for each shift's collaborative draft.
Auto-saved by the WebSocket relay on every sync-step-2 received from a client.
Cleaned up by the draft_cleanup_stale_drafts Celery task after 24 hours.
"""
from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'handover_draft',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('shift_id', sa.Integer(), nullable=False),
        sa.Column('ydoc_state', sa.LargeBinary(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['shift_id'], ['shift.id']),
        sa.UniqueConstraint('shift_id', name='uq_handover_draft_shift_id'),
    )
    op.create_index('ix_handover_draft_shift_id', 'handover_draft', ['shift_id'], unique=True)
    op.create_index('ix_handover_draft_updated_at', 'handover_draft', ['updated_at'])


def downgrade():
    op.drop_index('ix_handover_draft_updated_at', table_name='handover_draft')
    op.drop_index('ix_handover_draft_shift_id', table_name='handover_draft')
    op.drop_table('handover_draft')
