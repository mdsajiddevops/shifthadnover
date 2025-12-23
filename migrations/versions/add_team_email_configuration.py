"""Add team-specific email configuration fields

Revision ID: add_team_email_config
Revises: 
Create Date: 2024-12-20 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_team_email_config'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    """Add email configuration fields to Team table"""
    try:
        # Add email_recipients column
        op.add_column('team', sa.Column('email_recipients', sa.Text(), nullable=True))
        print("Added email_recipients column to team table")
        
        # Add priority_alert_recipients column
        op.add_column('team', sa.Column('priority_alert_recipients', sa.Text(), nullable=True))
        print("Added priority_alert_recipients column to team table")
        
    except Exception as e:
        print(f"Error adding columns to team table: {e}")
        # Check if columns already exist
        conn = op.get_bind()
        inspector = sa.inspect(conn)
        columns = [col['name'] for col in inspector.get_columns('team')]
        
        if 'email_recipients' not in columns:
            op.add_column('team', sa.Column('email_recipients', sa.Text(), nullable=True))
            print("Added email_recipients column to team table")
        else:
            print("email_recipients column already exists")
            
        if 'priority_alert_recipients' not in columns:
            op.add_column('team', sa.Column('priority_alert_recipients', sa.Text(), nullable=True))
            print("Added priority_alert_recipients column to team table")
        else:
            print("priority_alert_recipients column already exists")

def downgrade():
    """Remove email configuration fields from Team table"""
    try:
        op.drop_column('team', 'priority_alert_recipients')
        print("Removed priority_alert_recipients column from team table")
        
        op.drop_column('team', 'email_recipients')
        print("Removed email_recipients column from team table")
        
    except Exception as e:
        print(f"Error removing columns from team table: {e}")