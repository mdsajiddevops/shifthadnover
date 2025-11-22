#!/usr/bin/env python3

"""
Diagnostic script to find all foreign key references to team_member table
"""

import sys
import os

# Change to app directory
os.chdir('/app')
sys.path.insert(0, '/app')

# Import the Flask app and database
from app import app, db
from sqlalchemy import text

def find_all_foreign_keys():
    """Find all foreign key references to team_member table"""
    
    with app.app_context():
        print("🔍 Finding all foreign key references to team_member table")
        print("=" * 70)
        
        # Get orphaned IDs first
        orphaned_query = text("""
            SELECT id FROM team_member
            WHERE account_id = 1 AND team_id = 2 AND user_id IS NULL
        """)
        orphaned_ids = [row.id for row in db.session.execute(orphaned_query).fetchall()]
        print(f"🎯 Orphaned team_member IDs: {orphaned_ids}")
        
        # Check each table for foreign key references
        tables_to_check = [
            ('shift_roster', 'team_member_id'),
            ('current_shift_engineers', 'team_member_id'), 
            ('next_shift_engineers', 'team_member_id'),
            ('incident_assignment', 'assigned_to_id'),
            ('handover_notification', 'assigned_to_id'),
            ('shift_key_point', 'responsible_engineer_id'),
            ('shift_key_point', 'team_member_id'),  # Check both possible column names
        ]
        
        print("\n📋 Checking all possible foreign key references:")
        
        for table, column in tables_to_check:
            try:
                # First check if the column exists
                check_column_query = text(f"""
                    SELECT COUNT(*) FROM information_schema.COLUMNS 
                    WHERE TABLE_SCHEMA = DATABASE() 
                    AND TABLE_NAME = '{table}' 
                    AND COLUMN_NAME = '{column}'
                """)
                column_exists = db.session.execute(check_column_query).scalar() > 0
                
                if not column_exists:
                    print(f"   ⚠️ {table}.{column}: Column does not exist")
                    continue
                
                # Check for references to orphaned IDs
                count_query = text(f"""
                    SELECT COUNT(*) FROM {table} 
                    WHERE {column} IN :orphaned_ids
                """)
                count = db.session.execute(count_query, {
                    'orphaned_ids': tuple(orphaned_ids) if orphaned_ids else (0,)
                }).scalar()
                
                if count > 0:
                    print(f"   🔥 {table}.{column}: {count} references found")
                    
                    # Show some sample references
                    sample_query = text(f"""
                        SELECT id, {column} FROM {table} 
                        WHERE {column} IN :orphaned_ids
                        LIMIT 3
                    """)
                    samples = db.session.execute(sample_query, {
                        'orphaned_ids': tuple(orphaned_ids) if orphaned_ids else (0,)
                    }).fetchall()
                    
                    for sample in samples:
                        print(f"      Record ID {sample.id} → team_member {sample[1]}")
                else:
                    print(f"   ✅ {table}.{column}: No references")
                    
            except Exception as e:
                print(f"   ❌ {table}.{column}: Error - {str(e)[:60]}...")
        
        # Show schema of shift_key_point table specifically
        print("\n🔍 SHIFT_KEY_POINT TABLE SCHEMA:")
        try:
            schema_query = text("""
                SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_KEY
                FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'shift_key_point'
                ORDER BY ORDINAL_POSITION
            """)
            columns = db.session.execute(schema_query).fetchall()
            
            for col in columns:
                print(f"   📝 {col.COLUMN_NAME}: {col.DATA_TYPE} {'(PK)' if col.COLUMN_KEY == 'PRI' else ''} {'(FK)' if col.COLUMN_KEY == 'MUL' else ''}")
                
        except Exception as e:
            print(f"   ❌ Error getting schema: {e}")

if __name__ == "__main__":
    find_all_foreign_keys()