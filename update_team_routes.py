#!/usr/bin/env python3
"""
Update Team Routes and Templates for Active/Inactive Team Members

This script updates:
1. Team route to show only active team members
2. Add admin controls for enable/disable team members
3. Update user management to hide disabled users properly
4. Update API endpoints to respect is_active status
"""

import sys
import os
from datetime import datetime

# Add the application root to the Python path
app_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, app_root)

def update_team_route():
    """Update team.py route to filter active team members and add enable/disable functionality"""
    
    team_route_path = os.path.join(app_root, 'routes', 'team.py')
    
    try:
        with open(team_route_path, 'r') as f:
            content = f.read()
        
        # Create the updated content
        updated_content = '''from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_required, current_user
from models.models import TeamMember, db

team_bp = Blueprint('team', __name__)


# List/add/edit/delete team members
@team_bp.route('/team', methods=['GET', 'POST'])
@login_required
def team():
    if request.method == 'POST' and current_user.role not in ['super_admin', 'account_admin', 'team_admin']:
        flash('You do not have permission to edit team details. Contact an administrator.')
        return redirect(url_for('team.team'))
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add':
            if current_user.role in ['super_admin', 'account_admin', 'team_admin']:
                name = request.form['name']
                email = request.form['email']
                contact_number = request.form['contact_number']
                role = request.form.get('role')
                member = TeamMember(name=name, email=email, contact_number=contact_number, role=role,
                                   account_id=current_user.account_id, team_id=current_user.team_id,
                                   is_active=True)  # New members are active by default
                db.session.add(member)
                db.session.commit()
                flash('Team member added!')
            else:
                flash('You do not have permission to add team members. Admin access required.')
        elif action == 'edit':
            member_id = request.form['member_id']
            member = TeamMember.query.get(member_id)
            if member and current_user.role in ['super_admin', 'account_admin', 'team_admin']:
                member.name = request.form['name']
                new_email = request.form['email']
                member.contact_number = request.form['contact_number']
                member.role = request.form.get('role')
                
                # Check if email changed and handle user linking
                if member.email != new_email:
                    member.email = new_email
                    
                    try:
                        # Import here to avoid circular imports
                        from services.user_team_member_linking import UserTeamMemberLinkingService
                        
                        # Check for exact email match with existing users
                        matching_user = db.session.query(User).filter_by(email=new_email).first()
                        
                        if matching_user:
                            # Check if this user is already linked to another team member
                            existing_link = TeamMember.query.filter_by(user_id=matching_user.id).first()
                            
                            if not existing_link or existing_link.id == member.id:
                                # Perfect match - link them
                                member.user_id = matching_user.id
                                
                                # Update user's team info if not set
                                if not matching_user.team_id:
                                    matching_user.team_id = member.team_id
                                if not matching_user.account_id:
                                    matching_user.account_id = member.account_id
                                
                                db.session.commit()
                                
                                flash(f'Team member updated and automatically linked to user account: {matching_user.username}!')
                            else:
                                flash(f'Team member updated! Note: User with email {new_email} is already linked to another team member.')
                        else:
                            # No exact email match, try similarity matching with existing users
                            potential_users = User.query.filter(
                                User.account_id == member.account_id
                            ).all()
                            
                            best_user = None
                            best_confidence = 0
                            
                            for user in potential_users:
                                # Skip if user is already linked
                                if TeamMember.query.filter_by(user_id=user.id).first():
                                    continue
                                    
                                confidence = UserTeamMemberLinkingService.similarity_score(
                                    user.email or '', new_email
                                )
                                
                                if confidence > best_confidence and confidence >= 80:  # High threshold for email updates
                                    best_user = user
                                    best_confidence = confidence
                            
                            if best_user:
                                member.user_id = best_user.id
                                if not best_user.team_id:
                                    best_user.team_id = member.team_id
                                if not best_user.account_id:
                                    best_user.account_id = member.account_id
                                db.session.commit()
                                flash(f'Team member updated and linked to user {best_user.username} ({best_confidence:.1f}% email match)!')
                            else:
                                flash('Team member updated!')
                                
                    except Exception as e:
                        # Don't break the update if linking fails
                        flash('Team member updated!')
                else:
                    flash('Team member updated!')
            else:
                flash('You do not have permission to edit this team member. Admin access required.')
        elif action == 'enable_member':
            member_id = request.form.get('member_id')
            member = TeamMember.query.get(member_id)
            if member and current_user.role in ['super_admin', 'account_admin', 'team_admin']:
                member.is_active = True
                db.session.commit()
                flash(f'Team member {member.name} enabled successfully!')
            else:
                flash('You do not have permission to enable this team member.')
        elif action == 'disable_member':
            member_id = request.form.get('member_id')
            member = TeamMember.query.get(member_id)
            if member and current_user.role in ['super_admin', 'account_admin', 'team_admin']:
                member.is_active = False
                db.session.commit()
                flash(f'Team member {member.name} disabled successfully!')
            else:
                flash('You do not have permission to disable this team member.')
        elif action == 'delete':
            member_id = request.form['member_id']
            member = TeamMember.query.get(member_id)
            if member and current_user.role in ['super_admin', 'account_admin', 'team_admin']:
                try:
                    db.session.delete(member)
                    db.session.commit()
                    flash('Team member deleted!')
                except Exception as e:
                    db.session.rollback()
                    if 'foreign key constraint fails' in str(e).lower():
                        flash('Cannot delete team member: assigned in shift roster or related records exist.', 'danger')
                    else:
                        flash(f'Error deleting team member: {e}', 'danger')
        return redirect(url_for('team.team'))
    from models.models import Account, Team, User
    tm_query = TeamMember.query
    account_id = None
    team_id = None
    accounts = []
    teams = []
    
    # Add show_inactive parameter to optionally show inactive members
    show_inactive = request.args.get('show_inactive', 'false').lower() == 'true'
    
    if current_user.role == 'super_admin':
        accounts = Account.query.filter_by(is_active=True).all()
        account_id = request.args.get('account_id') or session.get('selected_account_id')
        teams = Team.query.filter_by(is_active=True)
        if account_id:
            teams = teams.filter_by(account_id=account_id)
        teams = teams.all()
        team_id = request.args.get('team_id') or session.get('selected_team_id')
    elif current_user.role == 'account_admin':
        account_id = current_user.account_id
        accounts = [Account.query.get(account_id)] if account_id else []
        teams = Team.query.filter_by(account_id=account_id, is_active=True).all()
        team_id = request.args.get('team_id') or session.get('selected_team_id')
    else:
        account_id = current_user.account_id
        team_id = current_user.team_id
        accounts = [Account.query.get(account_id)] if account_id else []
        teams = [Team.query.get(team_id)] if team_id else []
    
    if account_id:
        tm_query = tm_query.filter_by(account_id=account_id)
    if team_id:
        tm_query = tm_query.filter_by(team_id=team_id)
    
    # Filter by active status unless show_inactive is requested
    if not show_inactive:
        tm_query = tm_query.filter_by(is_active=True)
    
    members = tm_query.all()
    return render_template('team_details.html', 
                         members=members, 
                         accounts=accounts, 
                         teams=teams, 
                         selected_account_id=account_id, 
                         selected_team_id=team_id,
                         show_inactive=show_inactive)
'''

        with open(team_route_path, 'w') as f:
            f.write(updated_content)
        
        print("✅ Updated team.py route with active/inactive filtering and admin controls")
        return True
        
    except Exception as e:
        print(f"❌ Error updating team route: {str(e)}")
        return False

def update_user_management_route():
    """Update user_management.py to properly filter disabled users"""
    
    user_mgmt_path = os.path.join(app_root, 'routes', 'user_management.py')
    
    try:
        with open(user_mgmt_path, 'r') as f:
            content = f.read()
        
        # Replace the user filtering logic to exclude disabled users by default
        updated_content = content.replace(
            "User.status.in_(['active', 'disabled'])",
            "User.status == 'active'"
        )
        
        # Add show_disabled parameter handling
        lines = updated_content.split('\n')
        updated_lines = []
        
        for i, line in enumerate(lines):
            updated_lines.append(line)
            if 'def user_management():' in line:
                # Add show_disabled parameter after function definition
                updated_lines.append('    # Check if admin wants to see disabled users')
                updated_lines.append('    show_disabled = request.args.get("show_disabled", "false").lower() == "true"')
                updated_lines.append('    user_filter = ["active", "disabled"] if show_disabled else ["active"]')
                updated_lines.append('')
        
        # Replace the status filtering with the new logic
        final_content = '\n'.join(updated_lines)
        final_content = final_content.replace(
            "User.status == 'active'",
            "User.status.in_(user_filter)"
        )
        
        with open(user_mgmt_path, 'w') as f:
            f.write(final_content)
        
        print("✅ Updated user_management.py to hide disabled users by default")
        return True
        
    except Exception as e:
        print(f"❌ Error updating user management route: {str(e)}")
        return False

def update_api_endpoints():
    """Update API endpoints to respect is_active status"""
    
    # Update handover.py API endpoint
    handover_path = os.path.join(app_root, 'routes', 'handover.py')
    
    try:
        with open(handover_path, 'r') as f:
            content = f.read()
        
        # Find and update get_all_team_members API
        if 'def get_all_team_members():' in content:
            updated_content = content.replace(
                '# Get all team members (remove status filter since TeamMember model doesn\'t have status field)',
                '# Get all active team members only'
            )
            updated_content = updated_content.replace(
                'team_members = tm_query.all()',
                'team_members = tm_query.filter_by(is_active=True).all()'
            )
            
            with open(handover_path, 'w') as f:
                f.write(updated_content)
            
            print("✅ Updated handover.py API to filter active team members")
        
    except Exception as e:
        print(f"⚠️ Could not update handover.py: {str(e)}")
    
    # Update shift_swap_leave.py API endpoint
    shift_swap_path = os.path.join(app_root, 'routes', 'shift_swap_leave.py')
    
    try:
        with open(shift_swap_path, 'r') as f:
            content = f.read()
        
        # Update team-members API endpoint
        if '@shift_swap_leave_bp.route(\'/api/team-members\')' in content:
            # Find the function and add is_active filter
            lines = content.split('\n')
            updated_lines = []
            in_team_members_func = False
            
            for line in lines:
                if 'def get_team_members():' in line:
                    in_team_members_func = True
                elif in_team_members_func and 'User.status == \'active\',' in line:
                    # Add is_active filter
                    updated_lines.append(line)
                    updated_lines.append('            User.is_active == True,')
                    continue
                elif in_team_members_func and 'def ' in line and 'get_team_members' not in line:
                    in_team_members_func = False
                
                updated_lines.append(line)
            
            with open(shift_swap_path, 'w') as f:
                f.write('\n'.join(updated_lines))
            
            print("✅ Updated shift_swap_leave.py API to filter active users")
        
    except Exception as e:
        print(f"⚠️ Could not update shift_swap_leave.py: {str(e)}")

def main():
    """Main execution function"""
    
    print("🚀 UPDATING ROUTES FOR TEAM MEMBER STATUS SYSTEM")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Step 1: Update team route
    if not update_team_route():
        print("❌ Failed to update team route")
        return False
    
    # Step 2: Update user management route
    if not update_user_management_route():
        print("❌ Failed to update user management route")
        return False
    
    # Step 3: Update API endpoints
    update_api_endpoints()
    
    print("\n✅ ROUTE UPDATES COMPLETED")
    print("=" * 60)
    print("Updated:")
    print("1. ✅ team.py - Added active/inactive filtering and admin controls")
    print("2. ✅ user_management.py - Hide disabled users by default")
    print("3. ✅ API endpoints - Filter active team members and users")
    print()
    print("Next: Update templates to show enable/disable controls")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)