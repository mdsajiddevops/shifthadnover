#!/usr/bin/env python3
"""
Fix script to add techops users to Operations Team (ID: 2)
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the Flask app and database
from app import app, db
from models.models import User, Team, TeamMember
from sqlalchemy import text

def fix_techops_team_memberships():
    """Add all techops users to the Operations Team"""
    
    with app.app_context():
        try:
            # Get Operations Team (ID: 2)
            operations_team = Team.query.get(2)
            if not operations_team:
                print("❌ Operations Team (ID: 2) not found!")
                return
            
            print(f"🏢 Found Operations Team: {operations_team.name} (ID: {operations_team.id})")
            
            # Get all techops users
            techops_users = User.query.filter(User.username.like('techops%')).all()
            
            print(f"👥 Found {len(techops_users)} techops users")
            
            added_count = 0
            
            for user in techops_users:
                # Check if user already has team membership
                existing_membership = TeamMember.query.filter(
                    TeamMember.user_id == user.id,
                    TeamMember.team_id == operations_team.id
                ).first()
                
                if existing_membership:
                    print(f"✅ {user.username} already in Operations Team")
                else:
                    # Add user to Operations Team
                    team_member = TeamMember(
                        user_id=user.id,
                        team_id=operations_team.id
                    )
                    db.session.add(team_member)
                    print(f"➕ Added {user.username} to Operations Team")
                    added_count += 1
            
            # Commit all changes
            db.session.commit()
            
            print(f"\n✅ Successfully added {added_count} users to Operations Team")
            
            # Verify the changes
            print("\n🔍 Verification - Users now in Operations Team:")
            print("=" * 50)
            
            team_members = db.session.execute(
                text("SELECT u.id, u.username, u.email FROM user u JOIN team_member tm ON u.id = tm.user_id WHERE tm.team_id = :team_id ORDER BY u.username"),
                {"team_id": operations_team.id}
            ).fetchall()
            
            for member in team_members:
                print(f"👤 {member[1]} (ID: {member[0]}) - {member[2]}")
            
            print(f"\n🎉 Team membership fix completed! {len(team_members)} total members in Operations Team.")
                    
        except Exception as e:
            print(f"❌ Error fixing team memberships: {e}")
            db.session.rollback()
            raise

if __name__ == "__main__":
    fix_techops_team_memberships()