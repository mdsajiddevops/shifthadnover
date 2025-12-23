from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, abort
from flask_login import login_required, current_user
from models.models import TeamMember, Account, Team, User, db
from services.team_access_service import TeamAccessService

team_bp = Blueprint('team', __name__)

@team_bp.route('/api/get_teams_for_account')
@login_required
def get_teams_for_account():
    """AJAX endpoint to get teams based on account selection for team management"""
    account_id = request.args.get('account_id')
    
    print(f"[TEAM_API] get_teams_for_account called with account_id={account_id}")
    print(f"[TEAM_API] Current user role: {current_user.role}, account_id: {current_user.account_id}")
    
    if not account_id:
        print("[TEAM_API] No account_id provided, returning empty list")
        return jsonify([])
    
    try:
        account_id = int(account_id)
    except ValueError:
        print(f"[TEAM_API] Invalid account_id format: {account_id}")
        return jsonify([])
    
    # Security check
    if current_user.role == 'super_admin':
        # Super admin can access any account
        teams = Team.query.filter_by(account_id=account_id, is_active=True).all()
        print(f"[TEAM_API] Super admin accessing account {account_id}, found {len(teams)} teams")
    elif current_user.role == 'account_admin' and current_user.account_id == account_id:
        # Account admin can only access their own account
        teams = Team.query.filter_by(account_id=account_id, is_active=True).all()
        print(f"[TEAM_API] Account admin accessing own account {account_id}, found {len(teams)} teams")
    else:
        # Regular users cannot access this endpoint or wrong account
        print(f"[TEAM_API] Access denied for user role {current_user.role} trying to access account {account_id}")
        return jsonify([])
    
    team_list = [{'id': team.id, 'name': team.name} for team in teams]
    print(f"[TEAM_API] Returning teams: {team_list}")
    return jsonify(team_list)

@team_bp.route('/team-details')
@team_bp.route('/team-details/<int:team_id>')
@login_required
def team_details(team_id=None):
    """Team details page with proper authorization"""
    try:
        print(f"[TEAM_DETAILS] Accessing team details for team_id: {team_id}")
        print(f"[TEAM_DETAILS] Current user: {current_user.username}, role: {current_user.role}")
        
        # Get team_id from URL parameter or request args
        if not team_id:
            team_id = request.args.get('team_id')
        
        if team_id:
            try:
                team_id = int(team_id)
            except (ValueError, TypeError):
                flash('Invalid team ID provided.', 'error')
                return redirect(url_for('dashboard.dashboard'))
            
            # Get the team
            team = Team.query.get(team_id)
            if not team:
                flash('Team not found.', 'error')
                return redirect(url_for('dashboard.dashboard'))
            
            # Authorization check - proper access control
            if current_user.role == 'super_admin':
                # Super admin can view any team
                pass
            elif current_user.role == 'account_admin':
                # Account admin can view teams in their account
                if team.account_id != current_user.account_id:
                    flash('Access denied. You can only view teams in your account.', 'error')
                    return redirect(url_for('dashboard.dashboard'))
            else:
                # Regular users can only view teams they belong to
                user_team_ids = TeamAccessService.get_user_team_ids()
                if team_id not in user_team_ids:
                    flash('Access denied. You can only view teams you belong to.', 'error')
                    return redirect(url_for('dashboard.dashboard'))
            
            # Get team members
            members = TeamMember.query.filter_by(team_id=team_id, is_active=True).all()
            
            print(f"[TEAM_DETAILS] Found {len(members)} active members for team {team.name}")
            
            return render_template('team_details.html',
                                 team=team,
                                 members=members,
                                 selected_team_id=team_id)
        
        # No specific team - show team selection or user's teams
        if current_user.role == 'super_admin':
            accounts = Account.query.filter_by(is_active=True).all()
            teams = Team.query.filter_by(is_active=True).all()
        elif current_user.role == 'account_admin':
            accounts = [Account.query.get(current_user.account_id)]
            teams = Team.query.filter_by(account_id=current_user.account_id, is_active=True).all()
        else:
            # Regular users see their teams
            accounts = [Account.query.get(current_user.account_id)] if current_user.account_id else []
            user_teams = TeamAccessService.get_user_teams_for_account(current_user.account_id)
            teams = user_teams
        
        return render_template('team_details.html',
                             teams=teams,
                             accounts=accounts,
                             members=[],
                             selected_team_id=None)
                             
    except Exception as e:
        print(f"[TEAM_DETAILS] Error loading team data: {str(e)}")
        flash(f'Error loading team data: {str(e)}', 'error')
        return redirect(url_for('dashboard.dashboard'))

@team_bp.route('/teams')
@login_required  
def teams_list():
    """Teams listing page with proper access control"""
    try:
        if current_user.role == 'super_admin':
            # Super admin sees all teams
            teams = Team.query.filter_by(is_active=True).all()
        elif current_user.role == 'account_admin':
            # Account admin sees teams in their account
            teams = Team.query.filter_by(account_id=current_user.account_id, is_active=True).all()
        else:
            # Regular users see their teams
            teams = TeamAccessService.get_user_teams_for_account(current_user.account_id)
        
        return render_template('teams.html', teams=teams)
        
    except Exception as e:
        flash(f'Error loading teams: {str(e)}', 'error')
        return redirect(url_for('dashboard.dashboard'))