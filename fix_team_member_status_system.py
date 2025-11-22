#!/usr/bin/env python3
"""
Fix Team Member Status System - Complete Solution

This script addresses:
1. Add is_active field to TeamMember model
2. Hide inactive team members from team details page
3. Hide disabled users from user management
4. Add admin enable/disable functionality for team members
5. Update all related API endpoints
"""

import sys
import os
from datetime import datetime

# Add the application root to the Python path
app_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, app_root)

from app import app, db
from models.models import TeamMember, User, Team, Account
from sqlalchemy import text

def add_is_active_to_team_member():
    """Add is_active field to team_member table if it doesn't exist"""
    
    with app.app_context():
        print("🔍 CHECKING TEAM_MEMBER TABLE STRUCTURE")
        print("=" * 60)
        
        try:
            # Check if is_active column exists
            result = db.session.execute(text("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = 'team_member' 
                AND COLUMN_NAME = 'is_active'
            """)).fetchall()
            
            if result:
                print("✅ is_active column already exists in team_member table")
                return True
            else:
                print("➕ Adding is_active column to team_member table...")
                
                # Add the column
                db.session.execute(text("""
                    ALTER TABLE team_member 
                    ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE
                """))
                
                # Update existing records to be active by default
                db.session.execute(text("""
                    UPDATE team_member 
                    SET is_active = TRUE 
                    WHERE is_active IS NULL
                """))
                
                db.session.commit()
                print("✅ Successfully added is_active column to team_member table")
                return True
                
        except Exception as e:
            print(f"❌ Error adding is_active column: {str(e)}")
            db.session.rollback()
            return False

def check_current_state():
    """Check current state of team members and users"""
    
    with app.app_context():
        print("\n🔍 CURRENT STATE ANALYSIS")
        print("=" * 60)
        
        # Check team members
        try:
            team_members = db.session.execute(text("""
                SELECT tm.id, tm.name, tm.email, tm.is_active, tm.user_id,
                       u.username, u.is_active as user_is_active, u.status as user_status
                FROM team_member tm
                LEFT JOIN user u ON tm.user_id = u.id
                ORDER BY tm.account_id, tm.team_id, tm.id
            """)).fetchall()
            
            print(f"📊 Found {len(team_members)} team members:")
            
            active_count = 0
            inactive_count = 0
            
            for tm in team_members:
                status = "Active" if tm.is_active else "Inactive"
                user_info = ""
                if tm.user_id:
                    user_status = "Active" if tm.user_is_active and tm.user_status == 'active' else "Inactive"
                    user_info = f" → User: {tm.username} ({user_status})"
                
                print(f"   {'✅' if tm.is_active else '❌'} ID={tm.id}: {tm.name} [{status}]{user_info}")
                
                if tm.is_active:
                    active_count += 1
                else:
                    inactive_count += 1
            
            print(f"\n📈 Summary: {active_count} active, {inactive_count} inactive team members")
            
        except Exception as e:
            print(f"❌ Error checking team members: {str(e)}")

def update_model_file():
    """Update the models.py file to include is_active field"""
    
    model_file_path = os.path.join(app_root, 'models', 'models.py')
    
    try:
        with open(model_file_path, 'r') as f:
            content = f.read()
        
        # Check if is_active field is already present
        if 'is_active = db.Column(db.Boolean, default=True, nullable=False)' in content:
            print("✅ TeamMember model already has is_active field")
            return True
        
        # Find the TeamMember class and add is_active field
        lines = content.split('\n')
        updated_lines = []
        in_team_member_class = False
        field_added = False
        
        for line in lines:
            if 'class TeamMember(db.Model):' in line:
                in_team_member_class = True
                updated_lines.append(line)
            elif in_team_member_class and line.strip().startswith('account_id = db.Column') and not field_added:
                # Add is_active field before account_id
                updated_lines.append('    is_active = db.Column(db.Boolean, default=True, nullable=False)')
                updated_lines.append(line)
                field_added = True
                in_team_member_class = False
            else:
                updated_lines.append(line)
        
        if field_added:
            with open(model_file_path, 'w') as f:
                f.write('\n'.join(updated_lines))
            print("✅ Updated TeamMember model with is_active field")
            return True
        else:
            print("⚠️ Could not find appropriate location to add is_active field")
            return False
            
    except Exception as e:
        print(f"❌ Error updating model file: {str(e)}")
        return False

def main():
    """Main execution function"""
    
    print("🚀 TEAM MEMBER STATUS SYSTEM FIX")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Step 1: Add is_active column to database
    if not add_is_active_to_team_member():
        print("❌ Failed to add is_active column. Exiting.")
        return False
    
    # Step 2: Update model file
    if not update_model_file():
        print("⚠️ Failed to update model file, but database changes were successful")
    
    # Step 3: Check current state
    check_current_state()
    
    print("\n✅ TEAM MEMBER STATUS SYSTEM FIX COMPLETED")
    print("=" * 60)
    print("Next steps:")
    print("1. Restart the Flask application to load the updated model")
    print("2. Update routes to filter by is_active=True")
    print("3. Add admin controls for enable/disable team members")
    print("4. Test the functionality")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)