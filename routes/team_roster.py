from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session
from flask_login import login_required, current_user
from models.models import Team, Account, User, ShiftRoster, TeamMember, db
from models.team_roster_models import TeamShiftConfig, RosterAssignment
from models.team_shift_timing_config import TeamShiftTimingConfig
from datetime import datetime, date, time as dt_time, timedelta
from sqlalchemy.orm import joinedload
import pytz

team_roster_bp = Blueprint('team_roster', __name__)

def get_ist_now():
    """Get current time in IST timezone"""
    utc_now = datetime.utcnow()
    ist = pytz.timezone('Asia/Kolkata')
    return utc_now.replace(tzinfo=pytz.utc).astimezone(ist)

def get_engineers_for_shift(date, shift_code, account_id=None, team_id=None):
    """Get engineers assigned to a specific shift on a given date"""
    print(f"[TEAM_ROSTER DEBUG] Getting engineers for date={date}, shift_code={shift_code}, account_id={account_id}, team_id={team_id}")
    
    query = ShiftRoster.query.filter_by(date=date, shift_code=shift_code)
    
    # Apply filtering based on user role or provided parameters
    if account_id and team_id:
        # When specific account/team provided - allow if user belongs to same account
        if (current_user.role in ['super_admin', 'account_admin'] or 
            current_user.account_id == account_id):
            query = query.filter_by(account_id=account_id, team_id=team_id)
        else:
            # User doesn't have access to this account
            return []
    elif current_user.is_authenticated:
        if current_user.role == 'super_admin':
            # Super admin sees all data (no additional filtering)
            pass
        elif current_user.role == 'account_admin':
            # Account admin sees only their account data
            if current_user.account_id:
                query = query.filter_by(account_id=current_user.account_id)
        else:
            # Regular users - filter by their team memberships
            user_teams = current_user.get_teams()
            if user_teams:
                user_team_ids = [team.id for team in user_teams]
                query = query.filter(
                    ShiftRoster.account_id == current_user.account_id,
                    ShiftRoster.team_id.in_(user_team_ids)
                )
            elif current_user.account_id and current_user.team_id:
                # Fallback for users with account/team IDs
                query = query.filter_by(account_id=current_user.account_id, team_id=current_user.team_id)
    
    entries = query.all()
    member_ids = [e.team_member_id for e in entries]
    
    if not member_ids:
        print(f"[TEAM_ROSTER DEBUG] No members found for shift")
        return []
    
    # Get TeamMember objects with same filtering
    tm_query = TeamMember.query.filter(TeamMember.id.in_(member_ids))
    
    if account_id and team_id:
        # Allow access if user belongs to same account
        if (current_user.role in ['super_admin', 'account_admin'] or 
            current_user.account_id == account_id):
            tm_query = tm_query.filter_by(account_id=account_id, team_id=team_id)
        else:
            return []
    elif current_user.is_authenticated:
        if current_user.role == 'super_admin':
            pass
        elif current_user.role == 'account_admin':
            if current_user.account_id:
                tm_query = tm_query.filter_by(account_id=current_user.account_id)
        else:
            user_teams = current_user.get_teams()
            if user_teams:
                user_team_ids = [team.id for team in user_teams]
                tm_query = tm_query.filter(
                    TeamMember.account_id == current_user.account_id,
                    TeamMember.team_id.in_(user_team_ids)
                )
            elif current_user.account_id and current_user.team_id:
                tm_query = tm_query.filter_by(account_id=current_user.account_id, team_id=current_user.team_id)
    
    final_members = tm_query.all()
    print(f"[TEAM_ROSTER DEBUG] Found {len(final_members)} team members")
    return final_members

def get_current_shift_type_and_next(now=None):
    """Get current and next shift types using same logic as dashboard"""
    if now is None:
        now = datetime.now()
    
    # Use same shift timings as dashboard
    # Morning: 6:30-15:30, Evening: 14:45-23:45, Night: 21:45-6:45 (next day)
    t = now.time()
    if dt_time(6,30) <= t < dt_time(15,30):
        return 'Morning', 'Evening'
    elif dt_time(14,45) <= t < dt_time(23,45):
        return 'Evening', 'Night'
    else:
        # Night shift covers 21:45-6:45 (next day)
        return 'Night', 'Morning'

def get_shift_code_from_config(shift_config):
    """Map shift configuration to shift code based on shift name or timing"""
    if not shift_config:
        return None
    
    # Direct mapping from shift_code attribute if available
    if hasattr(shift_config, 'shift_code') and shift_config.shift_code:
        return shift_config.shift_code
    
    # Fallback: map based on shift name
    shift_name_lower = shift_config.shift_name.lower()
    if 'day' in shift_name_lower or 'morning' in shift_name_lower:
        return 'D'
    elif 'evening' in shift_name_lower:
        return 'E'  
    elif 'night' in shift_name_lower:
        return 'N'
    elif 'late evening' in shift_name_lower:
        return 'LE'
    elif 'general' in shift_name_lower:
        return 'G'
    elif 'onshore' in shift_name_lower:
        return 'OS'
    elif 'offshore' in shift_name_lower:
        return 'OF'
    
    # Default fallback
    return 'D'

@team_roster_bp.route('/teams-roster')
@login_required
def teams_roster():
    """Main teams roster page showing account-wise team cards"""
    from services.team_access_service import TeamAccessService
    
    # Get team filter context using team access service (SAME AS DASHBOARD)
    team_filter_context = TeamAccessService.get_team_filter_context()
    
    # Get accounts based on user role
    if current_user.role == 'super_admin':
        accounts = Account.query.filter_by(is_active=True).order_by(Account.name).all()
    else:
        # For non-admin users, show only their account
        accounts = [current_user.account] if current_user.account else []
    
    # Get teams and their roster data for each account
    accounts_data = []
    ist_now = get_ist_now()
    today = ist_now.date()
    
    # Get team filtering from session/request like dashboard
    selected_team_id = request.args.get('team_id') or session.get('filter_team_id')
    
    for account in accounts:
        # Get teams for this account based on user permissions and filtering
        if current_user.role == 'super_admin':
            teams = Team.query.filter_by(
                account_id=account.id, 
                is_active=True
            ).order_by(Team.name).all()
        elif current_user.role == 'account_admin':
            teams = Team.query.filter_by(
                account_id=account.id, 
                is_active=True
            ).order_by(Team.name).all()
        else:
            # Regular users: show ALL teams from their account (not just their own team)
            teams = Team.query.filter_by(
                account_id=account.id,
                is_active=True
            ).order_by(Team.name).all()
            
            # If specific team selected, filter to just that team
            if selected_team_id:
                try:
                    teams = [team for team in teams if team.id == int(selected_team_id)]
                except (TypeError, ValueError):
                    pass
        
        teams_data = []
        for team in teams:
            # Get current and next shift using dashboard logic with IST time
            current_time = ist_now
            print(f"[ROSTER DEBUG] Getting shifts for team {team.name} at {current_time.strftime('%H:%M:%S')} IST")
            
            # Use dashboard's shift timing logic
            current_shift_type, next_shift_type = get_current_shift_type_and_next(current_time)
            print(f"[ROSTER DEBUG] Dashboard logic: Current={current_shift_type}, Next={next_shift_type}")
            
            # Enhanced shift mapping to support additional shift codes like dashboard
            shift_map = {'Morning': 'D', 'Evening': 'E', 'Night': 'N'}
            current_shift_code = shift_map.get(current_shift_type, 'D')
            next_shift_code = shift_map.get(next_shift_type, 'E')
            
            # Additional shift codes mapping (same as dashboard)
            additional_shift_codes = {
                'Morning': ['G', 'OS'],  # General and Onshore show in Morning section
                'Evening': [],           # No additional codes for Evening currently
                'Night': ['LE', 'OF']   # Late Evening and Offshore show in Night section
            }
            
            # Get shift configurations from database for display purposes only
            all_shifts = TeamShiftTimingConfig.get_team_shifts(team.id)
            current_shift_config = None
            next_shift_config = None
            
            # Find configs that match the current shift codes
            for shift_config in all_shifts:
                config_code = get_shift_code_from_config(shift_config)
                if config_code == current_shift_code:
                    current_shift_config = shift_config
                elif config_code == next_shift_code:
                    next_shift_config = shift_config
            
            # Get members using enhanced dashboard's multi-shift logic
            print(f"[ROSTER DEBUG] Current shift: {current_shift_type} -> primary code: {current_shift_code}")
            
            # Get current shift members (primary + additional codes)
            current_shift_members = []
            
            # Primary shift code
            primary_current = get_engineers_for_shift(today, current_shift_code, team.account_id, team.id)
            for member in primary_current:
                member.display_shift_code = current_shift_code
                member.is_primary_shift = True
            current_shift_members.extend(primary_current)
            
            # Additional shift codes for current shift
            for add_shift_code in additional_shift_codes.get(current_shift_type, []):
                add_current = get_engineers_for_shift(today, add_shift_code, team.account_id, team.id)
                for member in add_current:
                    member.display_shift_code = add_shift_code
                    member.is_primary_shift = False
                current_shift_members.extend(add_current)
                print(f"[ROSTER DEBUG] Added {len(add_current)} members from current shift code {add_shift_code}")
            
            # Sort current shift members by availability status: oncall -> online -> offline
            def sort_by_availability(member):
                status = getattr(member, 'availability_status', 'offline') or 'offline'
                if status == 'oncall':
                    return 0  # First priority
                elif status == 'online':
                    return 1  # Second priority  
                else:  # offline or None
                    return 2  # Third priority
            
            current_shift_members.sort(key=sort_by_availability)
            
            print(f"[ROSTER DEBUG] Next shift: {next_shift_type} -> primary code: {next_shift_code}")
            
            # Get next shift members (primary + additional codes)
            next_shift_members = []
            
            # For next shift date calculation using IST
            next_shift_date = today
            if next_shift_type == 'Night' and ist_now.time() >= dt_time(21, 45):
                # Night shift starts after 21:45, use tomorrow
                next_shift_date = today + timedelta(days=1)
            
            # Primary next shift code
            primary_next = get_engineers_for_shift(next_shift_date, next_shift_code, team.account_id, team.id)
            for member in primary_next:
                member.display_shift_code = next_shift_code
                member.is_primary_shift = True
            next_shift_members.extend(primary_next)
            
            # Additional shift codes for next shift
            for add_shift_code in additional_shift_codes.get(next_shift_type, []):
                add_next = get_engineers_for_shift(next_shift_date, add_shift_code, team.account_id, team.id)
                for member in add_next:
                    member.display_shift_code = add_shift_code
                    member.is_primary_shift = False
                next_shift_members.extend(add_next)
                print(f"[ROSTER DEBUG] Added {len(add_next)} members from next shift code {add_shift_code}")
            
            # Sort next shift members by availability status: oncall -> online -> offline
            def sort_by_availability_next(member):
                status = getattr(member, 'availability_status', 'offline') or 'offline'
                if status == 'oncall':
                    return 0  # First priority
                elif status == 'online':
                    return 1  # Second priority  
                else:  # offline or None
                    return 2  # Third priority
            
            next_shift_members.sort(key=sort_by_availability_next)
            
            # Get all shift configurations for this team to show shift pattern
            all_shifts = TeamShiftTimingConfig.get_team_shifts(team.id)
            
            team_data = {
                'team': team,
                'current_shift': {
                    'config': current_shift_config,
                    'members': current_shift_members
                },
                'next_shift': {
                    'config': next_shift_config,
                    'members': next_shift_members
                },
                'all_shifts': all_shifts,
                'total_members': len(team.get_users())
            }
            teams_data.append(team_data)
        
        account_data = {
            'account': account,
            'teams': teams_data,
            'team_count': len(teams_data)
        }
        accounts_data.append(account_data)
    
    # Create serializable debug data for JavaScript
    debug_accounts_data = []
    for account_info in accounts_data:
        debug_teams = []
        for team_info in account_info['teams']:
            debug_team = {
                'id': team_info['team'].id,
                'name': team_info['team'].name,
                'account_id': team_info['team'].account_id,
                'total_members': team_info['total_members'],
                'current_shift': {
                    'config': {
                        'id': team_info['current_shift']['config'].id if team_info['current_shift']['config'] else None,
                        'shift_name': team_info['current_shift']['config'].shift_name if team_info['current_shift']['config'] else None,
                        'start_time': str(team_info['current_shift']['config'].start_time) if team_info['current_shift']['config'] else None,
                        'end_time': str(team_info['current_shift']['config'].end_time) if team_info['current_shift']['config'] else None
                    } if team_info['current_shift']['config'] else None,
                    'members_count': len(team_info['current_shift']['members'])
                },
                'next_shift': {
                    'config': {
                        'id': team_info['next_shift']['config'].id if team_info['next_shift']['config'] else None,
                        'shift_name': team_info['next_shift']['config'].shift_name if team_info['next_shift']['config'] else None,
                        'start_time': str(team_info['next_shift']['config'].start_time) if team_info['next_shift']['config'] else None,
                        'end_time': str(team_info['next_shift']['config'].end_time) if team_info['next_shift']['config'] else None
                    } if team_info['next_shift']['config'] else None,
                    'members_count': len(team_info['next_shift']['members'])
                },
                'all_shifts_count': len(team_info['all_shifts'])
            }
            debug_teams.append(debug_team)
        
        debug_account = {
            'id': account_info['account'].id,
            'name': account_info['account'].name,
            'teams': debug_teams,
            'team_count': account_info['team_count']
        }
        debug_accounts_data.append(debug_account)
    
    return render_template('teams_roster.html', 
                         accounts_data=accounts_data,
                         debug_accounts_data=debug_accounts_data,
                         current_time=ist_now,
                         team_filter_context=team_filter_context)

@team_roster_bp.route('/api/team-roster/<int:team_id>')
@login_required
def get_team_roster_api(team_id):
    """API endpoint to get detailed roster information for a team"""
    
    # Check user permissions
    team = Team.query.get_or_404(team_id)
    
    # Authorization check
    if current_user.role != 'super_admin' and current_user.account_id != team.account_id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    today = date.today()
    
    # Get all shifts for the team
    shifts = TeamShiftTimingConfig.get_team_shifts(team_id)
    
    # Get current and next shifts
    current_shift = TeamShiftTimingConfig.get_current_shift_for_team(team_id)
    next_shift = TeamShiftTimingConfig.get_next_shift_for_team(team_id)
    
    shifts_data = []
    for shift in shifts:
        members = RosterAssignment.get_shift_members(shift.id, today)
        
        shift_data = {
            'id': shift.id,
            'name': shift.shift_name,
            'start_time': shift.start_time.strftime('%H:%M'),
            'end_time': shift.end_time.strftime('%H:%M'),
            'is_current': shift.id == (current_shift.id if current_shift else None),
            'is_next': shift.id == (next_shift.id if next_shift else None),
            'members': [{
                'id': member.id,
                'name': member.display_name,
                'email': member.email,
                'initials': member.initials
            } for member in members]
        }
        shifts_data.append(shift_data)
    
    return jsonify({
        'team_id': team.id,
        'team_name': team.name,
        'account_name': team.account.name,
        'current_time': datetime.now().strftime('%H:%M'),
        'shifts': shifts_data
    })

@team_roster_bp.route('/teams-roster/manage/<int:team_id>')
@login_required
def manage_team_roster(team_id):
    """Management page for team roster configuration"""
    
    # Check permissions - only admins can manage rosters
    if current_user.role not in ['super_admin', 'account_admin', 'team_admin']:
        return redirect(url_for('team_roster.teams_roster'))
    
    team = Team.query.get_or_404(team_id)
    
    # Authorization check
    if (current_user.role != 'super_admin' and 
        current_user.account_id != team.account_id):
        return redirect(url_for('team_roster.teams_roster'))
    
    # Get all shift configurations for this team
    shifts = TeamShiftTimingConfig.get_team_shifts(team_id, active_only=False)
    
    # Get all team members
    team_members = team.get_users()
    
    # Get recent roster assignments
    recent_assignments = RosterAssignment.query.filter_by(
        team_id=team_id,
        is_active=True
    ).filter(
        RosterAssignment.assignment_date >= date.today()
    ).order_by(RosterAssignment.assignment_date.desc()).limit(50).all()
    
    return render_template('manage_team_roster.html',
                         team=team,
                         shifts=shifts,
                         team_members=team_members,
                         recent_assignments=recent_assignments)