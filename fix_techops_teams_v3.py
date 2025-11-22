#!/usr/bin/env python3
"""
Fix TechOps Users Team Membership - Version 3
Adds all techops users to Operations Team with proper field population
Using direct app import instead of factory pattern
"""

import sys
sys.path.append('/app')

# Import the Flask app and models directly
from app import app, db
from models.models import User, Team, TeamMember

def fix_techops_team_memberships():
    with app.app_context():
        try:
            # Find Operations Team
            operations_team = Team.query.get(2)
            if not operations_team:
                print("❌ Operations Team not found!")
                return False
            
            print(f"🏢 Found Operations Team: {operations_team.name} (ID: {operations_team.id})")
            
            # Find all techops users
            techops_users = User.query.filter(
                User.username.like('techops%')
            ).all()
            
            print(f"👥 Found {len(techops_users)} techops users")
            
            success_count = 0
            
            for user in techops_users:
                try:
                    # Check if already a team member
                    existing_membership = TeamMember.query.filter_by(
                        user_id=user.id,
                        team_id=operations_team.id
                    ).first()
                    
                    if existing_membership:
                        print(f"⚠️ {user.username} already in Operations Team")
                        continue
                    
                    # Create new team membership with proper field population
                    team_member = TeamMember(
                        user_id=user.id,
                        name=user.username,  # Use username as name
                        email=user.email if user.email else f"{user.username}@techops.com",  # Use email or generate one
                        contact_number=user.contact_number if hasattr(user, 'contact_number') and user.contact_number else "N/A",
                        role="Team Member",  # Default role
                        account_id=1,  # TechCorp Solutions account
                        team_id=operations_team.id
                    )
                    
                    db.session.add(team_member)
                    print(f"➕ Added {user.username} (ID: {user.id}) to Operations Team")
                    success_count += 1
                    
                except Exception as e:
                    print(f"❌ Error adding {user.username}: {str(e)}")
                    db.session.rollback()
                    continue
            
            # Commit all changes
            if success_count > 0:
                db.session.commit()
                print(f"✅ Successfully added {success_count} users to Operations Team")
                
                # Verify the memberships
                print("\n🔍 Verifying new memberships:")
                for user in techops_users:
                    membership = TeamMember.query.filter_by(
                        user_id=user.id,
                        team_id=operations_team.id
                    ).first()
                    if membership:
                        print(f"✅ {user.username} → Operations Team (Member ID: {membership.id})")
                    else:
                        print(f"❌ {user.username} → NOT in Operations Team")
                        
                return True
            else:
                print("⚠️ No new memberships created")
                return False
                
        except Exception as e:
            print(f"❌ Error fixing team memberships: {str(e)}")
            db.session.rollback()
            return False

if __name__ == "__main__":
    print("🔧 Starting TechOps Team Membership Fix v3...")
    success = fix_techops_team_memberships()
    
    if success:
        print("✅ Team membership fix completed successfully!")
    else:
        print("❌ Team membership fix failed!")