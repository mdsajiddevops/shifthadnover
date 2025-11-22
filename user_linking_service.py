#!/usr/bin/env python3
"""
User-TeamMember Automatic Linking Service
Automatically links User table entries with TeamMember table entries
during various workflows (SSO, admin creation, roster upload)
"""

import sys
sys.path.append('/app')

from app import app, db
from models.models import User, Team, TeamMember
from flask import current_app
import re
from difflib import SequenceMatcher

class UserTeamMemberLinkingService:
    """Service to automatically link Users with TeamMembers"""
    
    @staticmethod
    def similarity_score(a, b):
        """Calculate similarity score between two strings"""
        if not a or not b:
            return 0
        return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio() * 100
    
    @staticmethod
    def normalize_name(name):
        """Normalize name for comparison"""
        if not name:
            return ""
        # Remove extra spaces, convert to lowercase
        normalized = re.sub(r'\s+', ' ', str(name).strip().lower())
        return normalized
    
    @staticmethod
    def extract_username_from_email(email):
        """Extract username from email"""
        if not email or '@' not in email:
            return email
        return email.split('@')[0].lower()
    
    @staticmethod
    def find_matching_teammember(user, min_confidence=70):
        """
        Find matching TeamMember for a User
        
        Args:
            user: User object
            min_confidence: Minimum confidence percentage for match
            
        Returns:
            tuple: (team_member, confidence, match_reason)
        """
        if not user:
            return None, 0, "No user provided"
        
        # Get all team members (scope by account if user has one)
        query = TeamMember.query
        if user.account_id:
            query = query.filter_by(account_id=user.account_id)
        
        team_members = query.all()
        
        best_match = None
        best_confidence = 0
        best_reason = ""
        
        for tm in team_members:
            confidence = 0
            reasons = []
            
            # Skip if already linked to another user
            if tm.user_id and tm.user_id != user.id:
                continue
            
            # Exact email match (highest priority)
            if user.email and tm.email and user.email.lower() == tm.email.lower():
                confidence = 100
                reasons.append("exact email match")
            
            # Username match with email
            elif user.email and tm.email:
                user_username = UserTeamMemberLinkingService.extract_username_from_email(user.email)
                tm_username = UserTeamMemberLinkingService.extract_username_from_email(tm.email)
                if user_username == tm_username:
                    confidence = 90
                    reasons.append("username from email match")
            
            # Username match with name
            if user.username and tm.name:
                username_similarity = UserTeamMemberLinkingService.similarity_score(user.username, tm.name)
                if username_similarity >= 80:
                    confidence = max(confidence, username_similarity)
                    reasons.append(f"username-name similarity ({username_similarity:.1f}%)")
            
            # Full name match
            if hasattr(user, 'first_name') and hasattr(user, 'last_name'):
                user_full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
                if user_full_name and tm.name:
                    name_similarity = UserTeamMemberLinkingService.similarity_score(user_full_name, tm.name)
                    if name_similarity >= 70:
                        confidence = max(confidence, name_similarity)
                        reasons.append(f"full name similarity ({name_similarity:.1f}%)")
            
            # Email local part with name similarity
            if user.email and tm.name:
                email_local = user.email.split('@')[0].replace('.', ' ').replace('_', ' ')
                email_name_similarity = UserTeamMemberLinkingService.similarity_score(email_local, tm.name)
                if email_name_similarity >= 60:
                    confidence = max(confidence, email_name_similarity * 0.8)  # Slightly lower weight
                    reasons.append(f"email-name similarity ({email_name_similarity:.1f}%)")
            
            # Update best match if this is better
            if confidence > best_confidence and confidence >= min_confidence:
                best_match = tm
                best_confidence = confidence
                best_reason = "; ".join(reasons)
        
        return best_match, best_confidence, best_reason
    
    @staticmethod
    def link_user_to_teammember(user_id, team_member_id=None, auto_link=True):
        """
        Link a User to a TeamMember
        
        Args:
            user_id: User ID to link
            team_member_id: Specific TeamMember ID to link to (optional)
            auto_link: Whether to automatically find best match if team_member_id not provided
            
        Returns:
            tuple: (success, team_member, confidence, message)
        """
        try:
            user = User.query.get(user_id)
            if not user:
                return False, None, 0, f"User ID {user_id} not found"
            
            team_member = None
            confidence = 0
            message = ""
            
            if team_member_id:
                # Link to specific team member
                team_member = TeamMember.query.get(team_member_id)
                if not team_member:
                    return False, None, 0, f"TeamMember ID {team_member_id} not found"
                
                # Check if team member is already linked to another user
                if team_member.user_id and team_member.user_id != user_id:
                    existing_user = User.query.get(team_member.user_id)
                    existing_username = existing_user.username if existing_user else f"User ID {team_member.user_id}"
                    return False, None, 0, f"TeamMember already linked to {existing_username}"
                
                confidence = 100
                message = "Manual link"
                
            elif auto_link:
                # Automatically find best match
                team_member, confidence, reason = UserTeamMemberLinkingService.find_matching_teammember(user)
                message = reason or "No suitable match found"
                
                if not team_member:
                    return False, None, confidence, message
            
            else:
                return False, None, 0, "No team member specified and auto-link disabled"
            
            # Perform the linking
            team_member.user_id = user_id
            
            # Update user's team info if not set
            if not user.team_id:
                user.team_id = team_member.team_id
            if not user.account_id:
                user.account_id = team_member.account_id
            
            db.session.commit()
            
            success_message = f"Linked {user.username} to TeamMember '{team_member.name}' ({confidence:.1f}%)"
            if current_app:
                current_app.logger.info(f"✅ USER-TEAMMEMBER LINK: {success_message}")
            
            return True, team_member, confidence, success_message
            
        except Exception as e:
            db.session.rollback()
            error_msg = f"Error linking user to team member: {str(e)}"
            if current_app:
                current_app.logger.error(f"❌ USER-TEAMMEMBER LINK ERROR: {error_msg}")
            return False, None, 0, error_msg
    
    @staticmethod
    def bulk_link_users_to_teammembers(min_confidence=70, dry_run=False):
        """
        Bulk link all unlinked users to team members
        
        Args:
            min_confidence: Minimum confidence for auto-linking
            dry_run: If True, don't actually make changes
            
        Returns:
            dict: Summary of linking results
        """
        try:
            # Find users without team member links
            unlinked_users = User.query.outerjoin(
                TeamMember, User.id == TeamMember.user_id
            ).filter(TeamMember.user_id.is_(None)).all()
            
            results = {
                'total_unlinked_users': len(unlinked_users),
                'successful_links': 0,
                'potential_matches': 0,
                'no_matches': 0,
                'links': []
            }
            
            for user in unlinked_users:
                team_member, confidence, reason = UserTeamMemberLinkingService.find_matching_teammember(user, min_confidence)
                
                link_result = {
                    'user_id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'team_member_id': team_member.id if team_member else None,
                    'team_member_name': team_member.name if team_member else None,
                    'confidence': confidence,
                    'reason': reason,
                    'action': 'none'
                }
                
                if team_member and confidence >= min_confidence:
                    if not dry_run:
                        success, _, _, message = UserTeamMemberLinkingService.link_user_to_teammember(
                            user.id, team_member.id, auto_link=False
                        )
                        if success:
                            results['successful_links'] += 1
                            link_result['action'] = 'linked'
                        else:
                            link_result['action'] = 'failed'
                            link_result['error'] = message
                    else:
                        results['successful_links'] += 1
                        link_result['action'] = 'would_link'
                        
                elif team_member and confidence >= 50:
                    results['potential_matches'] += 1
                    link_result['action'] = 'potential_match'
                    
                else:
                    results['no_matches'] += 1
                    link_result['action'] = 'no_match'
                
                results['links'].append(link_result)
            
            return results
            
        except Exception as e:
            error_msg = f"Error in bulk linking: {str(e)}"
            if current_app:
                current_app.logger.error(f"❌ BULK LINK ERROR: {error_msg}")
            return {'error': error_msg}
    
    @staticmethod
    def create_teammember_for_user(user_id, team_id=None, account_id=None):
        """
        Create a TeamMember entry for an existing User
        
        Args:
            user_id: User ID to create TeamMember for
            team_id: Team ID (will try to determine if not provided)
            account_id: Account ID (will try to determine if not provided)
            
        Returns:
            tuple: (success, team_member, message)
        """
        try:
            user = User.query.get(user_id)
            if not user:
                return False, None, f"User ID {user_id} not found"
            
            # Check if user already has a linked team member
            existing_tm = TeamMember.query.filter_by(user_id=user_id).first()
            if existing_tm:
                return True, existing_tm, f"User already has TeamMember: {existing_tm.name}"
            
            # Determine team_id and account_id
            if not team_id:
                team_id = user.team_id or 2  # Default to Operations Team
            
            if not account_id:
                account_id = user.account_id or 1  # Default to TechCorp Solutions
            
            # Verify team and account exist
            team = Team.query.get(team_id)
            if not team:
                return False, None, f"Team ID {team_id} not found"
            
            # Create team member
            team_member = TeamMember(
                user_id=user_id,
                name=user.username,
                email=user.email or f"{user.username}@company.com",
                contact_number=getattr(user, 'contact_number', None) or "N/A",
                role="Team Member",
                account_id=account_id,
                team_id=team_id
            )
            
            db.session.add(team_member)
            
            # Update user's team info if not set
            if not user.team_id:
                user.team_id = team_id
            if not user.account_id:
                user.account_id = account_id
            
            db.session.commit()
            
            message = f"Created TeamMember for {user.username} in {team.name}"
            if current_app:
                current_app.logger.info(f"✅ TEAMMEMBER CREATION: {message}")
            
            return True, team_member, message
            
        except Exception as e:
            db.session.rollback()
            error_msg = f"Error creating TeamMember for user: {str(e)}"
            if current_app:
                current_app.logger.error(f"❌ TEAMMEMBER CREATION ERROR: {error_msg}")
            return False, None, error_msg

# Command line interface functions
def main():
    """Main function for command line usage"""
    with app.app_context():
        if len(sys.argv) > 1:
            command = sys.argv[1]
            
            if command == "link":
                if len(sys.argv) >= 3:
                    user_id = int(sys.argv[2])
                    team_member_id = int(sys.argv[3]) if len(sys.argv) >= 4 else None
                    
                    success, tm, confidence, message = UserTeamMemberLinkingService.link_user_to_teammember(
                        user_id, team_member_id
                    )
                    status = "✅" if success else "❌"
                    print(f"{status} {message}")
                else:
                    print("Usage: python user_linking_service.py link <user_id> [team_member_id]")
                    
            elif command == "bulk":
                dry_run = "--dry-run" in sys.argv
                min_confidence = 70
                
                if "--confidence" in sys.argv:
                    conf_idx = sys.argv.index("--confidence")
                    if conf_idx + 1 < len(sys.argv):
                        min_confidence = int(sys.argv[conf_idx + 1])
                
                print(f"🔧 Running bulk user-teammember linking (min confidence: {min_confidence}%)...")
                if dry_run:
                    print("🔍 DRY RUN MODE - No changes will be made")
                
                results = UserTeamMemberLinkingService.bulk_link_users_to_teammembers(
                    min_confidence=min_confidence, dry_run=dry_run
                )
                
                print(f"📊 Results:")
                print(f"   Total unlinked users: {results['total_unlinked_users']}")
                print(f"   Successful links: {results['successful_links']}")
                print(f"   Potential matches: {results['potential_matches']}")
                print(f"   No matches: {results['no_matches']}")
                
                # Show details
                for link in results['links']:
                    action_icons = {
                        'linked': '✅',
                        'would_link': '🔗',
                        'potential_match': '⚠️',
                        'no_match': '❌',
                        'failed': '💥'
                    }
                    icon = action_icons.get(link['action'], '❓')
                    
                    if link['team_member_name']:
                        print(f"   {icon} {link['username']} → {link['team_member_name']} ({link['confidence']:.1f}%)")
                    else:
                        print(f"   {icon} {link['username']} → No match found")
                        
            elif command == "create":
                if len(sys.argv) >= 3:
                    user_id = int(sys.argv[2])
                    team_id = int(sys.argv[3]) if len(sys.argv) >= 4 else None
                    account_id = int(sys.argv[4]) if len(sys.argv) >= 5 else None
                    
                    success, tm, message = UserTeamMemberLinkingService.create_teammember_for_user(
                        user_id, team_id, account_id
                    )
                    status = "✅" if success else "❌"
                    print(f"{status} {message}")
                else:
                    print("Usage: python user_linking_service.py create <user_id> [team_id] [account_id]")
                    
            else:
                show_usage()
        else:
            show_usage()

def show_usage():
    """Show usage instructions"""
    print("🔧 User-TeamMember Linking Service")
    print("=" * 50)
    print("Commands:")
    print("  link <user_id> [team_member_id]     - Link user to team member")
    print("  bulk [--dry-run] [--confidence N]   - Bulk link users to team members")
    print("  create <user_id> [team_id] [acc_id] - Create team member for user")
    print("")
    print("Examples:")
    print("  python user_linking_service.py link 42")
    print("  python user_linking_service.py bulk --dry-run --confidence 80")
    print("  python user_linking_service.py create 42 2 1")

if __name__ == "__main__":
    main()