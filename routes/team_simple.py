from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, abort
from flask_login import login_required, current_user
from models.models import TeamMember, Account, Team, User, db
from services.team_access_service import TeamAccessService
from services.multi_team_service import MultiTeamService

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
    """Team details page with robust error handling"""
    print(f"🔍 [TEAM_DETAILS] Route accessed - team_id: {team_id}")
    print(f"🔍 [TEAM_DETAILS] Current user: {getattr(current_user, 'username', 'Unknown')}")
    print(f"🔍 [TEAM_DETAILS] Current user role: {getattr(current_user, 'role', 'Unknown')}")
    
    try:
        # Get team filter context using team access service
        team_filter_context = TeamAccessService.get_team_filter_context()
        
        # Use team filtering logic - check request args FIRST, then URL param, then session
        if not team_id:
            # Check for team selection from request args (form submission)
            team_id = request.args.get('team_id')
            if team_id:
                print(f"🔍 [TEAM_DETAILS] Got team_id from request args: {team_id}")
            else:
                # Fall back to session
                team_id = session.get('filter_team_id') or team_filter_context.get('selected_team_id')
                print(f"🔍 [TEAM_DETAILS] Got team_id from session/context: {team_id}")
            
            # If still no team_id and user has multiple teams, show team selection
            if not team_id and team_filter_context.get('show_team_filter'):
                print(f"🔍 [TEAM_DETAILS] Multi-team user, showing team selection")
                # Show all user teams for selection
                return render_template('team_details.html',
                                     teams=team_filter_context['user_teams'],
                                     accounts=[current_user.account] if current_user.account else [],
                                     members=[],
                                     selected_team_id=None,
                                     team_filter_context=team_filter_context,
                                     selected_account_id=current_user.account_id,
                                     show_inactive=False)
            elif not team_id:
                # Use primary team or user's default team
                team_id = team_filter_context.get('primary_team_id') or current_user.team_id
        
        # Update team_filter_context with the selected team for template display
        if team_id:
            team_filter_context['selected_team_id'] = int(team_id) if isinstance(team_id, str) else team_id
        
        # For now, let's create a simple response that definitely works
        if team_id:
            try:
                team_id = int(team_id)
                print(f"🔍 [TEAM_DETAILS] Converted team_id to int: {team_id}")
                
                # Try to get the team
                team = Team.query.get(team_id)
                if not team:
                    print(f"❌ [TEAM_DETAILS] Team {team_id} not found")
                    return render_template('team_details.html', 
                                         error_message=f"Team {team_id} not found",
                                         teams=[], accounts=[], members=[])
                
                # Check if show_inactive filter is enabled
                show_inactive = request.args.get('show_inactive', 'false').lower() == 'true'
                
                # Get members - optionally filter by active status
                # Use try/except to handle case where is_active column doesn't exist yet
                try:
                    if show_inactive:
                        members = TeamMember.query.filter_by(team_id=team_id).all()
                    else:
                        members = TeamMember.query.filter_by(team_id=team_id, is_active=True).all()
                except Exception as filter_error:
                    print(f"⚠️ [TEAM_DETAILS] Error filtering by is_active (column may not exist): {filter_error}")
                    # Fallback: get all members without is_active filter
                    members = TeamMember.query.filter_by(team_id=team_id).all()
                print(f"✅ [TEAM_DETAILS] Found team: {team.name}, {len(members)} members (show_inactive={show_inactive})")
                
                # Update team_filter_context with the currently selected team
                team_filter_context['selected_team_id'] = team_id
                
                # Get user teams and accounts for the template
                user_teams = team_filter_context.get('user_teams', [])
                accounts = team_filter_context.get('accounts', [])
                
                return render_template('team_details.html',
                                     team=team,
                                     members=members,
                                     selected_team_id=team_id,
                                     team_filter_context=team_filter_context,
                                     teams=user_teams,
                                     accounts=accounts,
                                     selected_account_id=current_user.account_id,
                                     show_inactive=show_inactive)
                
            except Exception as e:
                print(f"❌ [TEAM_DETAILS] Error processing team_id {team_id}: {e}")
                return render_template('team_details.html', 
                                     error_message=f"Error loading team {team_id}: {str(e)}",
                                     teams=[], accounts=[], members=[],
                                     show_inactive=False,
                                     selected_account_id=None,
                                     team_filter_context={'show_team_filter': False, 'user_teams': [], 'selected_team_id': None})
        
        # No specific team - show available teams
        print(f"🔍 [TEAM_DETAILS] No team_id provided, showing team list")
        
        try:
            if hasattr(current_user, 'role') and current_user.role == 'super_admin':
                teams = Team.query.filter_by(is_active=True).all()
                accounts = Account.query.filter_by(is_active=True).all()
            elif hasattr(current_user, 'role') and current_user.role == 'account_admin':
                teams = Team.query.filter_by(account_id=current_user.account_id, is_active=True).all()
                accounts = [Account.query.get(current_user.account_id)] if current_user.account_id else []
            else:
                # Regular users - simplified approach for now
                teams = Team.query.filter_by(account_id=getattr(current_user, 'account_id', 1), is_active=True).all()
                accounts = [Account.query.get(getattr(current_user, 'account_id', 1))]
                
            print(f"✅ [TEAM_DETAILS] Found {len(teams)} teams, {len(accounts)} accounts")
            
            # Get team filter context using team access service (SAME AS DASHBOARD)
            team_filter_context = TeamAccessService.get_team_filter_context()
            
            return render_template('team_details.html',
                                 teams=teams,
                                 accounts=accounts,
                                 members=[],
                                 selected_team_id=None,
                                 team_filter_context=team_filter_context,
                                 selected_account_id=current_user.account_id,
                                 show_inactive=False)
                                     
        except Exception as e:
            print(f"❌ [TEAM_DETAILS] Error loading teams list: {e}")
            return render_template('team_details.html', 
                                 error_message=f"Error loading teams: {str(e)}",
                                 teams=[], accounts=[], members=[],
                                 show_inactive=False,
                                 selected_account_id=None,
                                 team_filter_context={'show_team_filter': False, 'user_teams': [], 'selected_team_id': None})
                             
    except Exception as e:
        print(f"❌ [TEAM_DETAILS] Critical error: {e}")
        # Last resort - return a simple HTML response
        return f"""
        <html><head><title>Team Details</title></head><body>
        <h1>Team Details</h1>
        <p><strong>Error:</strong> {str(e)}</p>
        <p>Please contact administrator.</p>
        <a href="/">← Back to Home</a>
        </body></html>
        """, 200

@team_bp.route('/team')
@login_required
def team():
    """Main team page - redirect to team details with primary team"""
    print(f"🔍 [TEAM] Main team route accessed by {getattr(current_user, 'username', 'Unknown')}")
    
    # Get user's primary team and redirect to it
    from services.team_access_service import TeamAccessService
    primary_team_id = TeamAccessService.get_primary_team_id()
    
    if primary_team_id:
        return redirect(url_for('team.team_details', team_id=primary_team_id))
    else:
        # If no primary team, redirect to teams list
        return redirect(url_for('team.teams_list'))

@team_bp.route('/teams')
@login_required  
def teams_list():
    """Teams listing page - simplified version"""
    try:
        print(f"🔍 [TEAMS_LIST] Route accessed by {getattr(current_user, 'username', 'Unknown')}")
        
        teams = Team.query.filter_by(is_active=True).all()
        print(f"✅ [TEAMS_LIST] Found {len(teams)} active teams")
        
        # Get member counts for each team
        team_member_counts = {}
        for team in teams:
            count = TeamMember.query.filter_by(team_id=team.id, is_active=True).count()
            team_member_counts[team.id] = count
        
        return render_template('teams.html', teams=teams, team_member_counts=team_member_counts)
        
    except Exception as e:
        print(f"❌ [TEAMS_LIST] Error: {e}")
        return f"<h1>Teams List</h1><p>Error: {str(e)}</p><a href='/'>← Back to Home</a>", 200