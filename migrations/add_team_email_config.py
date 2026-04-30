#!/usr/bin/env python3
"""
Migration script to add team-specific email configuration fields
Run this script to add email_recipients and priority_alert_recipients columns to the team table
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from models.models import db
import sqlalchemy as sa
from sqlalchemy import text

def add_team_email_columns():
    """Add email configuration columns to team table"""
    with app.app_context():
        try:
            # Check if columns already exist
            inspector = sa.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('team')]
            
            if 'email_recipients' not in columns:
                db.engine.execute(text("ALTER TABLE team ADD COLUMN email_recipients TEXT"))
                print("✓ Added email_recipients column to team table")
            else:
                print("✓ email_recipients column already exists")
                
            if 'priority_alert_recipients' not in columns:
                db.engine.execute(text("ALTER TABLE team ADD COLUMN priority_alert_recipients TEXT"))
                print("✓ Added priority_alert_recipients column to team table")
            else:
                print("✓ priority_alert_recipients column already exists")
                
            print("\n✅ Team email configuration migration completed successfully!")
            print("Teams can now have their own email distribution lists.")
            
        except Exception as e:
            print(f"❌ Error during migration: {e}")
            raise

if __name__ == "__main__":
    print("🔄 Starting team email configuration migration...")
    add_team_email_columns()