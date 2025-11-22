#!/usr/bin/env python3
"""
Automated Team Membership Management
Utility script to automatically assign team memberships based on user patterns
"""

import sys
sys.path.append('/app')

from app import app, db
from models.models import User, Team, TeamMember

def auto_assign_team_membership(user_id, team_pattern_rules=None):
    """
    Automatically assign team membership based on username patterns
    
    Args:
        user_id: User ID to assign team membership
        team_pattern_rules: Dict of username patterns to team IDs
    """
    
    if team_pattern_rules is None:
        # Default team assignment rules
        team_pattern_rules = {
            'techops': 2,      # Operations Team
            'admin': 2,        # Operations Team  
            'ops': 2,          # Operations Team
            'dev': 3,          # Development Team (if exists)
            'support': 2,      # Operations Team
            'manager': 2,      # Operations Team
        }
    
    with app.app_context():
        try:
            user = User.query.get(user_id)
            if not user:
                print(f"❌ User ID {user_id} not found")
                return False
            
            # Check if user already has team membership
            existing_membership = TeamMember.query.filter_by(user_id=user_id).first()
            if existing_membership:
                print(f"⚠️ User {user.username} already has team membership")
                return True
            
            # Find matching team based on username pattern
            assigned_team_id = None
            for pattern, team_id in team_pattern_rules.items():
                if pattern.lower() in user.username.lower():
                    assigned_team_id = team_id
                    break
            
            if not assigned_team_id:
                # Default to Operations Team if no pattern match
                assigned_team_id = 2
                print(f"⚠️ No pattern match for {user.username}, defaulting to Operations Team")
            
            # Verify team exists
            team = Team.query.get(assigned_team_id)
            if not team:
                print(f"❌ Team ID {assigned_team_id} not found")
                return False
            
            # Create team membership
            team_member = TeamMember(
                user_id=user.id,
                name=user.username,
                email=user.email if user.email else f"{user.username}@company.com",
                contact_number=user.contact_number if hasattr(user, 'contact_number') and user.contact_number else "N/A",
                role="Team Member",
                account_id=1,  # Default to TechCorp Solutions
                team_id=assigned_team_id
            )
            
            db.session.add(team_member)
            db.session.commit()
            
            print(f"✅ Auto-assigned {user.username} to {team.name} (Team ID: {assigned_team_id})")
            return True
            
        except Exception as e:
            print(f"❌ Error auto-assigning team membership: {str(e)}")
            db.session.rollback()
            return False

def bulk_assign_unassigned_users():
    """
    Find all users without team memberships and auto-assign them
    """
    with app.app_context():
        try:
            # Find users without team memberships
            users_without_teams = db.session.query(User).outerjoin(
                TeamMember, User.id == TeamMember.user_id
            ).filter(TeamMember.id.is_(None)).all()
            
            print(f"🔍 Found {len(users_without_teams)} users without team memberships")
            
            success_count = 0
            for user in users_without_teams:
                if auto_assign_team_membership(user.id):
                    success_count += 1
            
            print(f"✅ Successfully assigned {success_count} users to teams")
            return success_count
            
        except Exception as e:
            print(f"❌ Error in bulk assignment: {str(e)}")
            return 0

def show_team_assignment_rules():
    """
    Display current team assignment rules
    """
    print("📋 Current Team Assignment Rules:")
    print("=" * 50)
    print("Username Pattern → Team Assignment")
    print("-" * 50)
    print("techops*         → Operations Team (ID: 2)")
    print("admin*           → Operations Team (ID: 2)")
    print("ops*             → Operations Team (ID: 2)")
    print("dev*             → Development Team (ID: 3)")
    print("support*         → Operations Team (ID: 2)")
    print("manager*         → Operations Team (ID: 2)")
    print("*default*        → Operations Team (ID: 2)")
    print("=" * 50)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "bulk":
            print("🔧 Running bulk team assignment for unassigned users...")
            bulk_assign_unassigned_users()
        elif sys.argv[1] == "rules":
            show_team_assignment_rules()
        elif sys.argv[1].isdigit():
            user_id = int(sys.argv[1])
            print(f"🔧 Auto-assigning team membership for user ID {user_id}...")
            auto_assign_team_membership(user_id)
        else:
            print("Usage:")
            print("  python auto_team_assignment.py <user_id>  - Assign team to specific user")
            print("  python auto_team_assignment.py bulk       - Assign teams to all unassigned users")
            print("  python auto_team_assignment.py rules      - Show assignment rules")
    else:
        print("🔧 Auto Team Assignment Utility")
        show_team_assignment_rules()
        print("\nUsage:")
        print("  python auto_team_assignment.py <user_id>  - Assign team to specific user")
        print("  python auto_team_assignment.py bulk       - Assign teams to all unassigned users")
        print("  python auto_team_assignment.py rules      - Show assignment rules")