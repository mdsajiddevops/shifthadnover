#!/usr/bin/env python3
"""
Enhanced Team Membership Service
Service to automatically handle team assignments during user creation
"""

import os
import sys
sys.path.append('/app')

from app import app, db
from models.models import User, Team, TeamMember
from flask import current_app

class TeamAssignmentService:
    """Service class for automatic team assignment"""
    
    # Default team assignment rules
    DEFAULT_ASSIGNMENT_RULES = {
        'techops': 2,      # Operations Team
        'admin': 2,        # Operations Team  
        'ops': 2,          # Operations Team
        'dev': 3,          # Development Team (if exists)
        'support': 2,      # Operations Team
        'manager': 2,      # Operations Team
        'engineer': 2,     # Operations Team
        'analyst': 2,      # Operations Team
        'lead': 2,         # Operations Team
    }
    
    @staticmethod
    def get_team_assignment_rules():
        """Get team assignment rules from config or use defaults"""
        # You can extend this to read from database config or environment variables
        return TeamAssignmentService.DEFAULT_ASSIGNMENT_RULES
    
    @staticmethod
    def auto_assign_team_membership(user_id, force_reassign=False):
        """
        Automatically assign team membership based on username patterns
        
        Args:
            user_id: User ID to assign team membership
            force_reassign: Whether to reassign if user already has team membership
            
        Returns:
            tuple: (success: bool, team_name: str, message: str)
        """
        try:
            user = User.query.get(user_id)
            if not user:
                return False, None, f"User ID {user_id} not found"
            
            # Check if user already has team membership
            existing_membership = TeamMember.query.filter_by(user_id=user_id).first()
            if existing_membership and not force_reassign:
                team = Team.query.get(existing_membership.team_id)
                team_name = team.name if team else "Unknown Team"
                return True, team_name, f"User {user.username} already has team membership in {team_name}"
            
            # Get assignment rules
            team_pattern_rules = TeamAssignmentService.get_team_assignment_rules()
            
            # Find matching team based on username pattern
            assigned_team_id = None
            matched_pattern = None
            
            for pattern, team_id in team_pattern_rules.items():
                if pattern.lower() in user.username.lower():
                    assigned_team_id = team_id
                    matched_pattern = pattern
                    break
            
            if not assigned_team_id:
                # Default to Operations Team if no pattern match
                assigned_team_id = 2
                matched_pattern = "default"
            
            # Verify team exists
            team = Team.query.get(assigned_team_id)
            if not team:
                return False, None, f"Team ID {assigned_team_id} not found"
            
            # Remove existing membership if force reassign
            if existing_membership and force_reassign:
                db.session.delete(existing_membership)
            
            # Create team membership
            team_member = TeamMember(
                user_id=user.id,
                name=user.username,
                email=user.email if user.email else f"{user.username}@company.com",
                contact_number=getattr(user, 'contact_number', None) or "N/A",
                role="Team Member",
                account_id=user.account_id or 1,  # Use user's account or default to TechCorp
                team_id=assigned_team_id
            )
            
            db.session.add(team_member)
            db.session.commit()
            
            message = f"Auto-assigned {user.username} to {team.name} (pattern: {matched_pattern})"
            
            # Log the assignment
            if current_app:
                current_app.logger.info(f"✅ {message}")
            
            return True, team.name, message
            
        except Exception as e:
            db.session.rollback()
            error_msg = f"Error auto-assigning team membership: {str(e)}"
            if current_app:
                current_app.logger.error(f"❌ {error_msg}")
            return False, None, error_msg
    
    @staticmethod
    def bulk_assign_unassigned_users():
        """
        Find all users without team memberships and auto-assign them
        
        Returns:
            dict: Summary of assignments made
        """
        try:
            # Find users without team memberships
            users_without_teams = db.session.query(User).outerjoin(
                TeamMember, User.id == TeamMember.user_id
            ).filter(TeamMember.id.is_(None)).all()
            
            results = {
                'total_found': len(users_without_teams),
                'successful_assignments': 0,
                'failed_assignments': 0,
                'assignments': []
            }
            
            for user in users_without_teams:
                success, team_name, message = TeamAssignmentService.auto_assign_team_membership(user.id)
                
                assignment_result = {
                    'user_id': user.id,
                    'username': user.username,
                    'success': success,
                    'team_name': team_name,
                    'message': message
                }
                
                results['assignments'].append(assignment_result)
                
                if success:
                    results['successful_assignments'] += 1
                else:
                    results['failed_assignments'] += 1
            
            return results
            
        except Exception as e:
            if current_app:
                current_app.logger.error(f"❌ Error in bulk assignment: {str(e)}")
            return {
                'error': str(e),
                'total_found': 0,
                'successful_assignments': 0,
                'failed_assignments': 0,
                'assignments': []
            }

# Standalone execution functions for command line usage
def main():
    """Main function for command line usage"""
    with app.app_context():
        if len(sys.argv) > 1:
            if sys.argv[1] == "bulk":
                print("🔧 Running bulk team assignment for unassigned users...")
                results = TeamAssignmentService.bulk_assign_unassigned_users()
                
                print(f"🔍 Found {results['total_found']} users without team memberships")
                print(f"✅ Successfully assigned {results['successful_assignments']} users")
                print(f"❌ Failed to assign {results['failed_assignments']} users")
                
                for assignment in results['assignments']:
                    status = "✅" if assignment['success'] else "❌"
                    print(f"{status} {assignment['username']}: {assignment['message']}")
                    
            elif sys.argv[1] == "rules":
                print("📋 Current Team Assignment Rules:")
                print("=" * 50)
                print("Username Pattern → Team Assignment")
                print("-" * 50)
                rules = TeamAssignmentService.get_team_assignment_rules()
                for pattern, team_id in rules.items():
                    try:
                        team = Team.query.get(team_id)
                        team_name = team.name if team else f"Team ID {team_id}"
                    except:
                        team_name = f"Team ID {team_id}"
                    print(f"{pattern}* → {team_name}")
                print("*default* → Operations Team (ID: 2)")
                print("=" * 50)
                
            elif sys.argv[1].isdigit():
                user_id = int(sys.argv[1])
                print(f"🔧 Auto-assigning team membership for user ID {user_id}...")
                success, team_name, message = TeamAssignmentService.auto_assign_team_membership(user_id)
                status = "✅" if success else "❌"
                print(f"{status} {message}")
                
            else:
                show_usage()
        else:
            show_usage()

def show_usage():
    """Show usage instructions"""
    print("🔧 Enhanced Team Assignment Service")
    print("=" * 50)
    print("Usage:")
    print("  python enhanced_team_service.py <user_id>  - Assign team to specific user")
    print("  python enhanced_team_service.py bulk       - Assign teams to all unassigned users")
    print("  python enhanced_team_service.py rules      - Show assignment rules")

if __name__ == "__main__":
    main()