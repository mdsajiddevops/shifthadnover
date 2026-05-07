
from flask import Blueprint, render_template, request, flash, session
from flask_login import login_required, current_user
from models.models import Incident, TeamMember, ShiftRoster, ShiftKeyPoint, Shift, Account, Team, User, db
from services.team_access_service import TeamAccessService
from services.multi_team_service import apply_team_filtering
import plotly.graph_objs as go
import plotly
import json
from datetime import datetime, timedelta, time as dt_time
import pytz
from sqlalchemy import func, or_, and_
import logging

# Module logger
logger = logging.getLogger(__name__)

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/get_teams_for_account')
@login_required
def get_teams_for_account():
    """AJAX endpoint to get teams based on account selection"""
    from flask import jsonify
    account_id = request.args.get('account_id')
    
    if not account_id:
        return jsonify([])
    
    # Security check
    if current_user.role == 'super_admin':
        # Super admin can access any account
        teams = Team.query.filter_by(account_id=account_id, is_active=True).all()
    elif current_user.role == 'account_admin' and current_user.account_id == int(account_id):
        # Account admin can only access their own account
        teams = Team.query.filter_by(account_id=account_id, is_active=True).all()
    else:
        # Regular users cannot access this endpoint
        return jsonify([])
    
    team_list = [{'id': team.id, 'name': team.name} for team in teams]
    return jsonify(team_list)

def get_ist_now():
    utc_now = datetime.utcnow()
    ist = pytz.timezone('Asia/Kolkata')
    return utc_now.replace(tzinfo=pytz.utc).astimezone(ist)

def get_shift_type_and_next(now):
    # Shift timings (IST):
    # Morning: 6:30-15:30, Evening: 14:45-23:45, Night: 21:45-6:45 (next day)
    t = now.time()
    if dt_time(6,30) <= t < dt_time(15,30):
        return 'Morning', 'Evening'
    elif dt_time(14,45) <= t < dt_time(23,45):
        return 'Evening', 'Night'
    else:
        # Night shift covers 21:45-6:45 (next day)
        return 'Night', 'Morning'

def get_engineers_for_shift(date, shift_code, account_id=None, team_id=None):
    # shift_code: 'E' (Evening), 'D' (Day/Morning), 'N' (Night)
    logger.debug(f"[DEBUG] *** GET_ENGINEERS_FOR_SHIFT CALLED ***")
    logger.debug(f"[DEBUG] Parameters: date={date}, shift_code={shift_code}, account_id={account_id}, team_id={team_id}")
    
    query = ShiftRoster.query.filter_by(date=date, shift_code=shift_code)
    
    # Apply team-based filtering using the new service
    if account_id and team_id:
        # When specific account/team provided (admin filtering)
        logger.debug(f"[DEBUG] Applying admin filtering: account_id={account_id}, team_id={team_id}")
        query = query.filter_by(account_id=account_id, team_id=team_id)
    elif current_user.is_authenticated:
        # Use TeamAccessService for proper multi-team filtering
        query = TeamAccessService.apply_team_filter(query, ShiftRoster)
        logger.debug(f"[DEBUG] Applied team filter for user {current_user.username}")
        
        # Debug: show effective team IDs
        effective_teams = TeamAccessService.get_effective_team_ids()
        effective_account = TeamAccessService.get_effective_account_id()
        logger.debug(f"[DEBUG] Effective teams: {effective_teams}, account: {effective_account}")
    else:
        logger.debug(f"[DEBUG] User not authenticated - returning empty results")
        return []
    
    entries = query.all()
    logger.debug(f"[DEBUG] ShiftRoster query found {len(entries)} entries")
    for i, entry in enumerate(entries):
        logger.debug(f"[DEBUG] Entry {i+1}: team_member_id={entry.team_member_id}, account_id={entry.account_id}, team_id={entry.team_id}")
    
    member_ids = [e.team_member_id for e in entries]
    
    if not member_ids:
        logger.debug(f"[DEBUG] No member_ids found - returning empty list")
        return []
    
    # Apply same security filtering to TeamMember query
    tm_query = TeamMember.query.filter(TeamMember.id.in_(member_ids))
    logger.debug(f"[DEBUG] TeamMember base query for member_ids: {member_ids}")
    
    if account_id and team_id:
        # When specific account/team provided (admin filtering)
        logger.debug(f"[DEBUG] Applying TeamMember admin filtering: account_id={account_id}, team_id={team_id}")
        tm_query = tm_query.filter_by(account_id=account_id, team_id=team_id)
    elif current_user.is_authenticated:
        # Use TeamAccessService for consistent multi-team filtering
        tm_query = TeamAccessService.apply_team_filter(tm_query, TeamMember)
        logger.debug(f"[DEBUG] Applied team filter to TeamMember query for user {current_user.username}")
    
    final_members = tm_query.all()
    logger.debug(f"[DEBUG] Final TeamMember query returned {len(final_members)} members")
    for i, member in enumerate(final_members):
        team_name = member.team.name if member.team else 'Unknown'
        logger.debug(f"[DEBUG] Final member {i+1}: {member.name} (Team: {team_name}, Account: {member.account_id})")
    
    return final_members

def get_incident_trends_data(range_type, start_date=None, end_date=None):
    """Generate incident trends data for charts"""
    ist_now = get_ist_now()
    
    if range_type == '1d':
        start_date = ist_now.date()
        end_date = start_date
    elif range_type == '7d':
        start_date = ist_now.date() - timedelta(days=6)
        end_date = ist_now.date()
    elif range_type == '30d':
        start_date = ist_now.date() - timedelta(days=29)
        end_date = ist_now.date()
    elif range_type == '1y':
        start_date = ist_now.date() - timedelta(days=364)
        end_date = ist_now.date()
    
    # Query incidents within date range
    query = db.session.query(
        func.date(Incident.created_at).label('date'),
        func.count(Incident.id).label('count')
    ).filter(
        func.date(Incident.created_at).between(start_date, end_date)
    )
    
    # Apply team-based filtering for incident trends
    if current_user.is_authenticated:
        # Use TeamAccessService for consistent multi-team filtering
        query = TeamAccessService.apply_team_filter(query, Incident)
    
    results = query.group_by(func.date(Incident.created_at)).all()
    
    # Create date range and fill missing dates with 0
    date_range = []
    current_date = start_date
    while current_date <= end_date:
        date_range.append(current_date)
        current_date += timedelta(days=1)
    
    # Create data dictionary
    data_dict = {result.date: result.count for result in results}
    
    # Fill in missing dates
    dates = []
    counts = []
    for date in date_range:
        dates.append(date.strftime('%Y-%m-%d'))
        counts.append(data_dict.get(date, 0))
    
    return dates, counts

@dashboard_bp.route('/')
@login_required
def dashboard():
    logger.debug(f"[DEBUG] Dashboard: Starting dashboard route execution...")
    
    # Check if user just completed onboarding
    if request.args.get('onboarding_complete') == 'true':
        # Get user's account and team info for personalized welcome
        account_name = current_user.account.name if current_user.account else "the application"
        team_name = current_user.team.name if current_user.team else ""
        
        if team_name:
            welcome_msg = f"Welcome to the Shift Handover Application! You're now part of {account_name} - {team_name}."
        else:
            welcome_msg = f"Welcome to the Shift Handover Application! You're now part of {account_name}."
        
        flash(welcome_msg, 'success')
    
    ist_now = get_ist_now()
    today = ist_now.date()
    # Enhanced shift mapping to support additional shift codes
    shift_map = {'Morning': 'D', 'Evening': 'E', 'Late Evening': 'LE', 'Night': 'N', 'General': 'G', 'OnShore': 'OS', 'OffShore': 'OF'}
    
    # Additional shift codes mapping (bidirectional relationships)
    additional_shift_codes = {
        'Morning': ['G', 'OS'],      # Morning also shows General and OnShore engineers
        'Evening': [],               # No additional codes for Evening
        'Late Evening': ['N'],       # Late Evening also shows Night engineers
        'Night': ['LE', 'OF'],       # Night also shows Late Evening and OffShore engineers
        'General': ['D'],            # General also shows Morning (Day) engineers
        'OnShore': ['D'],            # OnShore also shows Morning (Day) engineers
        'OffShore': ['N']            # OffShore also shows Night engineers
    }
    
    current_shift_type, next_shift_type = get_shift_type_and_next(ist_now)
    current_shift_code = shift_map[current_shift_type]
    next_shift_code = shift_map[next_shift_type]
    next_date = today + timedelta(days=1)

    from flask import session
    logger.debug(f"[DEBUG] Dashboard: current_user.is_authenticated={getattr(current_user, 'is_authenticated', None)}, id={getattr(current_user, 'id', None)}, username={getattr(current_user, 'username', None)}")
    
    # 🆕 ENHANCED DASHBOARD FILTERING - Handle filter parameters and session storage
    accounts = []
    teams = []
    selected_account_id = None
    selected_team_id = None
    team_filter_context = None  # Initialize for all user roles
    
    # Update session with filter values if provided in URL
    if request.args.get('account_id'):
        session['dashboard_selected_account_id'] = request.args.get('account_id')
    if request.args.get('team_id'):
        session['dashboard_selected_team_id'] = request.args.get('team_id')
        # Also update the TeamAccessService session key for multi-team users
        try:
            team_id_int = int(request.args.get('team_id'))
            # Validate user has access to this team before setting in session
            user_team_ids = TeamAccessService.get_user_team_ids()
            if team_id_int in user_team_ids:
                session['selected_team_id'] = team_id_int
                logger.debug(f"[DASHBOARD] Updated selected_team_id in session to {team_id_int}")
        except (ValueError, TypeError):
            pass
    
    if current_user.role == 'super_admin':
        # Super Admin: Can filter by any account and team
        accounts = Account.query.filter_by(is_active=True).all()
        selected_account_id = request.args.get('account_id') or session.get('dashboard_selected_account_id')
        
        teams = Team.query.filter_by(is_active=True)
        if selected_account_id:
            teams = teams.filter_by(account_id=selected_account_id)
        teams = teams.all()
        
        selected_team_id = request.args.get('team_id') or session.get('dashboard_selected_team_id')
        
        # For filtering data
        filter_account_id = selected_account_id
        filter_team_id = selected_team_id
        # Super admin doesn't need team filter context (they have full access)
        team_filter_context = None
        
    elif current_user.role == 'account_admin':
        # Account Admin: Can filter by teams within their account
        filter_account_id = current_user.account_id
        accounts = [Account.query.get(filter_account_id)] if filter_account_id else []
        teams = Team.query.filter_by(account_id=filter_account_id, is_active=True).all()
        
        selected_team_id = request.args.get('team_id') or session.get('dashboard_selected_team_id')
        
        # If no team selected, default to show all teams in the account (None means all)
        filter_team_id = selected_team_id
        # Account admin doesn't need team filter context (they have full account access)
        team_filter_context = None
        
    else:
        # Regular users and team admins: Use multi-team service
        filter_account_id = current_user.account_id
        accounts = [Account.query.get(filter_account_id)] if filter_account_id else []
        
        # Check if URL explicitly requests a team
        url_team_id = request.args.get('team_id')
        if url_team_id:
            try:
                url_team_id_int = int(url_team_id)
                user_team_ids = TeamAccessService.get_user_team_ids()
                if url_team_id_int in user_team_ids:
                    # Force update session before getting team_filter_context
                    session['selected_team_id'] = url_team_id_int
                    logger.debug(f"[DASHBOARD] Regular user explicitly selected team_id={url_team_id_int} from URL")
            except (ValueError, TypeError):
                pass
        
        # Get team filter context using team access service
        url_team_id = request.args.get('team_id', type=int)
        team_filter_context = TeamAccessService.get_team_filter_context(url_team_id=url_team_id)
        
        teams = team_filter_context['user_teams']
        selected_account_id = filter_account_id
        selected_team_id = team_filter_context['selected_team_id']
        
        logger.debug(f"[DASHBOARD] Regular user {current_user.username}: selected_team_id={selected_team_id}, primary_team_id={team_filter_context.get('primary_team_id')}")
        
        # Set filter team ID - None means show all user's teams
        filter_team_id = selected_team_id

    # Get incidents handed over TO the current shift from the previous shift
    # This shows only incidents that were specifically handed over, not all incidents
    
    # 🔧 FIXED LOGIC: Find ONLY the PREVIOUS SHIFT handover (not old handovers from previous days)
    # Show only the immediately previous shift handover details
    logger.debug(f"[DEBUG] Dashboard: Looking for PREVIOUS SHIFT handover TO {current_shift_type} shift")
    
    def get_previous_shift_handover(current_shift, today_date, account_id, team_id):
        """Get the previous shift handover based on current shift and date"""
        # 🔧 FIXED: Night shift logic to handle day boundaries correctly
        # Night shift spans midnight, so we need to check if we're looking for yesterday's Evening handover
        if current_shift == 'Night':
            # Check if we're in early Night shift (00:00-06:30) looking for yesterday's Evening handover
            ist_now = get_ist_now()
            if ist_now.time() < dt_time(6, 30):
                # Early night shift - look for yesterday's Evening→Night handover
                search_date = today_date - timedelta(days=1)
            else:
                # Late night shift (21:45-23:59) - look for today's Evening→Night handover
                search_date = today_date
            previous_shift_map = {
                'Night': ('Evening', search_date)
            }
        else:
            previous_shift_map = {
                'Morning': ('Night', today_date - timedelta(days=1)),  # Morning comes after Night (previous day)
                'Evening': ('Morning', today_date),                    # Evening comes after Morning (same day)
            }
        
        if current_shift not in previous_shift_map:
            return None
            
        prev_shift_type, search_date = previous_shift_map[current_shift]
        
        logger.debug(f"[DEBUG] Looking for {prev_shift_type} → {current_shift} handover on {search_date}")
        
        # Look for handover FROM previous shift TO current shift on the correct date
        handover = Shift.query.filter_by(
            current_shift_type=prev_shift_type,
            next_shift_type=current_shift,
            date=search_date,
            account_id=account_id,
            team_id=team_id,
            status='sent'
        ).order_by(Shift.id.desc()).first()
        
        if handover:
            logger.debug(f"[DEBUG] Found previous shift handover: ID={handover.id}, {handover.current_shift_type}→{handover.next_shift_type}, date={handover.date}")
        else:
            logger.debug(f"[DEBUG] No previous shift handover found for {prev_shift_type}→{current_shift} on {search_date}")
            
        return handover
    
    if filter_account_id and filter_team_id:
        # Get the previous shift handover (not any old handover)
        target_handover = get_previous_shift_handover(current_shift_type, today, filter_account_id, filter_team_id)
        
        if target_handover:
            logger.debug(f"[DEBUG] Dashboard: Found target handover ID={target_handover.id}, {target_handover.current_shift_type}→{target_handover.next_shift_type}, date={target_handover.date}")
            
            # Get only Open incidents and Handover incidents from the target shift
            # 🔧 FIXED: Only show Open and Handover incidents in "Recent Handover Incidents"
            # Priority and Escalated incidents have their own separate sections
            raw_incidents = Incident.query.filter(
                Incident.shift_id == target_handover.id,
                Incident.account_id == filter_account_id,
                Incident.team_id == filter_team_id,
                Incident.type.in_(['Open', 'Handover']),  # Only Open and Handover incidents
                Incident.status != 'Closed'  # Exclude closed incidents
            ).all()
            
            logger.debug(f"[DEBUG] Dashboard: Found {len(raw_incidents)} raw incidents from handover")
            
            # 🔧 ENHANCED LOGIC: Filter out incidents that were closed in newer handovers
            open_incidents = []
            for incident in raw_incidents:
                # Check if this incident was closed in any newer shift
                newer_closed_incident = Incident.query.filter(
                    Incident.account_id == filter_account_id,
                    Incident.team_id == filter_team_id,
                    Incident.shift_id > target_handover.id,  # Only newer shifts
                    Incident.title == incident.title,  # Same incident
                    Incident.type == 'Closed',  # Closed type
                    Incident.status == 'Resolved'  # Resolved status
                ).first()
                
                if not newer_closed_incident:
                    # This incident was not closed in a newer handover, so show it
                    open_incidents.append(incident)
                    logger.debug(f"[DEBUG] Dashboard: Including incident '{incident.title}' (type: {incident.type}, priority: {incident.priority})")
                else:
                    logger.debug(f"[DEBUG] Dashboard: Incident '{incident.title}' was closed in shift {newer_closed_incident.shift_id}, not showing")
        else:
            logger.debug(f"[DEBUG] Dashboard: No handover found TO {current_shift_type} shift")
            open_incidents = []
            
    elif filter_account_id:
        # Account admin logic - get previous shift handover for the account
        def get_account_previous_shift_handover(current_shift, today_date, account_id):
            """Get previous shift handover for account admin (across all teams in account)"""
            # 🔧 FIXED: Night shift logic for account admin too
            if current_shift == 'Night':
                ist_now = get_ist_now()
                if ist_now.time() < dt_time(6, 30):
                    search_date = today_date - timedelta(days=1)
                else:
                    search_date = today_date
                previous_shift_map = {
                    'Night': ('Evening', search_date)
                }
            else:
                previous_shift_map = {
                    'Morning': ('Night', today_date - timedelta(days=1)),
                    'Evening': ('Morning', today_date),
                }
            
            if current_shift not in previous_shift_map:
                return None
                
            prev_shift_type, search_date = previous_shift_map[current_shift]
            
            # Look for most recent handover in the account on the correct date
            handover = Shift.query.filter_by(
                current_shift_type=prev_shift_type,
                next_shift_type=current_shift,
                date=search_date,
                account_id=account_id,
                status='sent'
            ).order_by(Shift.id.desc()).first()
            
            return handover
            
        target_handover = get_account_previous_shift_handover(current_shift_type, today, filter_account_id)
            
        if target_handover:
            # 🔧 FIXED: Only include Open and Handover incidents for account admin recent handover section
            raw_incidents = Incident.query.filter(
                Incident.shift_id == target_handover.id,
                Incident.account_id == filter_account_id,
                Incident.type.in_(['Open', 'Handover']),  # Only Open and Handover incidents
                Incident.status != 'Closed'
            ).all()
            
            open_incidents = []
            for incident in raw_incidents:
                newer_closed_incident = Incident.query.filter(
                    Incident.account_id == filter_account_id,
                    Incident.shift_id > target_handover.id,
                    Incident.title == incident.title,
                    Incident.type == 'Closed',
                    Incident.status == 'Resolved'
                ).first()
                
                if not newer_closed_incident:
                    open_incidents.append(incident)
        else:
            open_incidents = []
            
    else:
        # For super admin, get previous shift handovers from all accounts/teams (not old handovers)
        def get_super_admin_previous_shift_handovers(current_shift, today_date):
            """Get previous shift handovers for super admin"""
            # 🔧 FIXED: Night shift logic for super admin too
            if current_shift == 'Night':
                ist_now = get_ist_now()
                if ist_now.time() < dt_time(6, 30):
                    search_date = today_date - timedelta(days=1)
                else:
                    search_date = today_date
                previous_shift_map = {
                    'Night': ('Evening', search_date)
                }
            else:
                previous_shift_map = {
                    'Morning': ('Night', today_date - timedelta(days=1)),
                    'Evening': ('Morning', today_date),
                }
            
            if current_shift not in previous_shift_map:
                return []
                
            prev_shift_type, search_date = previous_shift_map[current_shift]
            
            # Get handovers from the previous shift on the correct date
            handovers = Shift.query.filter_by(
                current_shift_type=prev_shift_type,
                next_shift_type=current_shift,
                date=search_date,
                status='sent'
            ).order_by(Shift.id.desc()).limit(20).all()  # Limit to prevent too many results
            
            return handovers
            
        target_handovers = get_super_admin_previous_shift_handovers(current_shift_type, today)
        
        open_incidents = []
        for shift in target_handovers:
            # 🔧 FIXED: Only include Open and Handover incidents for super admin recent handover section
            raw_incidents = Incident.query.filter(
                Incident.shift_id == shift.id,
                Incident.type.in_(['Open', 'Handover']),  # Only Open and Handover incidents
                Incident.status != 'Closed'
            ).all()
            
            for incident in raw_incidents:
                newer_closed_incident = Incident.query.filter(
                    Incident.account_id == incident.account_id,
                    Incident.team_id == incident.team_id,
                    Incident.shift_id > shift.id,
                    Incident.title == incident.title,
                    Incident.type == 'Closed',
                    Incident.status == 'Resolved'
                ).first()
                
                if not newer_closed_incident:
                    open_incidents.append(incident)
    # Enhanced current shift engineers with multiple shift codes
    logger.debug(f"[DEBUG] *** ENHANCED CURRENT SHIFT ENGINEERS CALCULATION ***")
    logger.debug(f"[DEBUG] Current shift type: {current_shift_type}, Primary shift code: {current_shift_code}")
    logger.debug(f"[DEBUG] Additional shift codes for {current_shift_type}: {additional_shift_codes.get(current_shift_type, [])}")
    logger.debug(f"[DEBUG] Filter account_id: {filter_account_id}, Filter team_id: {filter_team_id}")
    
    current_engineers = []
    
    # Get engineers for primary shift code
    if current_shift_type == 'Night' and ist_now.time() < dt_time(6,45):
        night_date = today - timedelta(days=1)
        primary_engineers = get_engineers_for_shift(night_date, current_shift_code, filter_account_id, filter_team_id)
        logger.debug(f"[DEBUG] Using night date: {night_date} for primary current shift")
    else:
        primary_engineers = get_engineers_for_shift(today, current_shift_code, filter_account_id, filter_team_id)
        logger.debug(f"[DEBUG] Using today date: {today} for primary current shift")
    
    # Add shift code info to engineers
    for engineer in primary_engineers:
        engineer.display_shift_code = current_shift_code
        engineer.is_primary_shift = True
    current_engineers.extend(primary_engineers)
    
    # Get engineers for additional shift codes in this category
    for add_shift_code in additional_shift_codes.get(current_shift_type, []):
        if current_shift_type == 'Night' and ist_now.time() < dt_time(6,45):
            add_engineers = get_engineers_for_shift(night_date, add_shift_code, filter_account_id, filter_team_id)
        else:
            add_engineers = get_engineers_for_shift(today, add_shift_code, filter_account_id, filter_team_id)
        
        # Add shift code info to engineers
        for engineer in add_engineers:
            engineer.display_shift_code = add_shift_code
            engineer.is_primary_shift = False
        current_engineers.extend(add_engineers)
        logger.debug(f"[DEBUG] Added {len(add_engineers)} engineers from shift code {add_shift_code}")
    
    logger.debug(f"[DEBUG] ENHANCED DASHBOARD RESULT: Found {len(current_engineers)} total engineers for current shift")
    for i, engineer in enumerate(current_engineers):
        team_name = engineer.team.name if engineer.team else 'Unknown'
        shift_display = f" ({engineer.display_shift_code})" if not engineer.is_primary_shift else ""
        logger.debug(f"[DEBUG] Current Engineer {i+1}: {engineer.name}{shift_display} (Team: {team_name}, Account: {engineer.account_id})")
    # Enhanced next shift engineers with multiple shift codes
    logger.debug(f"[DEBUG] *** ENHANCED NEXT SHIFT ENGINEERS CALCULATION ***")
    logger.debug(f"[DEBUG] Current time: {ist_now.strftime('%H:%M:%S')}")
    logger.debug(f"[DEBUG] Next shift type: {next_shift_type}, Primary shift code: {next_shift_code}")
    logger.debug(f"[DEBUG] Additional shift codes for {next_shift_type}: {additional_shift_codes.get(next_shift_type, [])}")
    logger.debug(f"[DEBUG] Current user: {current_user.username}, Role: {current_user.role}")
    user_teams = current_user.get_teams()
    user_team_ids = [team.id for team in user_teams] if user_teams else []
    logger.debug(f"[DEBUG] User account_id: {current_user.account_id}, team_ids: {user_team_ids}")
    logger.debug(f"[DEBUG] Filter account_id: {filter_account_id}, Filter team_id: {filter_team_id}")
    
    next_shift_engineers = []
    
    # Get engineers for primary next shift code
    logger.debug(f"[DEBUG] Using TODAY date for {next_shift_type} shift: {today}")
    primary_next_engineers = get_engineers_for_shift(today, next_shift_code, filter_account_id, filter_team_id)
    
    # Add shift code info to engineers
    for engineer in primary_next_engineers:
        engineer.display_shift_code = next_shift_code
        engineer.is_primary_shift = True
    next_shift_engineers.extend(primary_next_engineers)
    
    # Get engineers for additional shift codes in this category
    for add_shift_code in additional_shift_codes.get(next_shift_type, []):
        add_next_engineers = get_engineers_for_shift(today, add_shift_code, filter_account_id, filter_team_id)
        
        # Add shift code info to engineers
        for engineer in add_next_engineers:
            engineer.display_shift_code = add_shift_code
            engineer.is_primary_shift = False
        next_shift_engineers.extend(add_next_engineers)
        logger.debug(f"[DEBUG] Added {len(add_next_engineers)} engineers from next shift code {add_shift_code}")
    
    logger.debug(f"[DEBUG] ENHANCED DASHBOARD RESULT: Found {len(next_shift_engineers)} total engineers for next shift")
    for i, engineer in enumerate(next_shift_engineers):
        team_name = engineer.team.name if engineer.team else 'Unknown'
        shift_display = f" ({engineer.display_shift_code})" if not engineer.is_primary_shift else ""
        logger.debug(f"[DEBUG] Next Engineer {i+1}: {engineer.name}{shift_display} (Team: {team_name}, Account: {engineer.account_id})")
    if filter_account_id and filter_team_id:
        # 🔧 ENHANCED KEY POINT FILTERING: Use same logic as new handover form for consistency
        # Get all key points, then apply intelligent filtering
        all_kps_query = ShiftKeyPoint.query.filter(
            ShiftKeyPoint.account_id == filter_account_id,
            ShiftKeyPoint.team_id == filter_team_id
        ).order_by(ShiftKeyPoint.id.desc())
        
        logger.debug(f"[DASHBOARD DEBUG] Total key points for team: {all_kps_query.count()}")
        
        # Filter to only Open/In Progress status
        all_prev_kps = all_kps_query.filter(
            ShiftKeyPoint.status.in_(['Open', 'In Progress'])
        ).all()
        
        logger.debug(f"[DASHBOARD DEBUG] Open/In Progress key points: {len(all_prev_kps)}")
        
        # Additional check: exclude key points from shifts that have been submitted with 'Closed' status
        filtered_kps = []
        for kp in all_prev_kps:
            # Check if this key point's shift was submitted and this key point was marked closed
            shift = Shift.query.get(kp.shift_id)
            if shift and shift.status == 'sent':
                # This is from a submitted handover - check if there's a newer version that closed this key point (CASE-INSENSITIVE)
                newer_closed = ShiftKeyPoint.query.filter(
                    func.lower(ShiftKeyPoint.description) == kp.description.lower(),
                    ShiftKeyPoint.jira_id == kp.jira_id,
                    ShiftKeyPoint.status == 'Closed',
                    ShiftKeyPoint.id > kp.id
                ).first()
                if newer_closed:
                    logger.debug(f"[DASHBOARD DEBUG] Excluding key point ID {kp.id} - found newer closed version ID {newer_closed.id}")
                    continue
            filtered_kps.append(kp)
        
        all_prev_kps = filtered_kps
        logger.debug(f"[DASHBOARD DEBUG] After submission filtering: {len(all_prev_kps)} key points remain")
        
        # Deduplicate: keep only the latest (by id) for each (description, normalized_jira_id) pair
        kp_map = {}
        for kp in all_prev_kps:
            if kp.status == 'Closed':
                continue
            # Normalize JIRA ID: treat None, NULL, empty string, and 'None' as equivalent
            normalized_jira = kp.jira_id if kp.jira_id and kp.jira_id.lower() not in ['none', 'null', ''] else None
            key = (kp.description, normalized_jira)
            if key not in kp_map or kp.id > kp_map[key].id:
                kp_map[key] = kp
        
        logger.debug(f"[DASHBOARD DEBUG] After deduplication: {len(kp_map)} unique key points")
        
        # Attach assigned user info to each key point
        open_key_points = []
        from models.models import TeamMember, User
        for kp in kp_map.values():
            assigned_user = None
            logger.debug(f"[DASHBOARD DEBUG] Processing key point ID {kp.id}: {kp.description[:30]}...")
            logger.debug(f"[DASHBOARD DEBUG] responsible_engineer_id: {kp.responsible_engineer_id}")
            
            if kp.responsible_engineer_id:
                team_member = TeamMember.query.get(kp.responsible_engineer_id)
                logger.debug(f"[DASHBOARD DEBUG] Team member found: {team_member.name if team_member else 'None'}")
                
                if team_member:
                    # Prefer linked user if available, else fallback to team member name
                    if team_member.user_id:
                        user = User.query.get(team_member.user_id)
                        assigned_user = user.username if user else team_member.name
                        logger.debug(f"[DASHBOARD DEBUG] Using user: {assigned_user}")
                    else:
                        assigned_user = team_member.name
                        logger.debug(f"[DASHBOARD DEBUG] Using team member name: {assigned_user}")
            
            kp.assigned_to_display = assigned_user or "Unassigned"
            logger.debug(f"[DASHBOARD DEBUG] Final assigned_to_display: {kp.assigned_to_display}")
            open_key_points.append(kp)
        
        # Get priority incidents ONLY Priority type from the target handover
        # 🔧 FIXED: Only show Priority incidents in "Priority Incidents" section
        # Escalated incidents will be shown separately if needed
        if target_handover:
            priority_incidents = Incident.query.filter(
                Incident.shift_id == target_handover.id,
                Incident.account_id == filter_account_id,
                Incident.team_id == filter_team_id,
                Incident.type == 'Priority',  # Only Priority incidents
                Incident.status != 'Closed'
            ).all()
            
            # Apply same closure filtering logic
            filtered_priority_incidents = []
            for incident in priority_incidents:
                newer_closed_incident = Incident.query.filter(
                    Incident.account_id == filter_account_id,
                    Incident.team_id == filter_team_id,
                    Incident.shift_id > target_handover.id,
                    Incident.title == incident.title,
                    Incident.type == 'Closed',
                    Incident.status == 'Resolved'
                ).first()
                
                if not newer_closed_incident:
                    filtered_priority_incidents.append(incident)
            
            priority_incidents = filtered_priority_incidents
        else:
            priority_incidents = []
            
    elif filter_account_id:
        # 🔧 ENHANCED: Check if regular user should get team-level filtering
        if current_user.role not in ['super_admin', 'account_admin'] and filter_team_id:
            # Regular users should get team-level filtering like the first branch
            all_kps_query = ShiftKeyPoint.query.filter(
                ShiftKeyPoint.account_id == filter_account_id,
                ShiftKeyPoint.team_id == filter_team_id
            ).order_by(ShiftKeyPoint.id.desc())
            
            logger.debug(f"[DASHBOARD DEBUG] Team-level filtering for regular user - Total key points for team: {all_kps_query.count()}")
            
            # Filter to only Open/In Progress status
            all_prev_kps = all_kps_query.filter(
                ShiftKeyPoint.status.in_(['Open', 'In Progress'])
            ).all()
            
            logger.debug(f"[DASHBOARD DEBUG] Open/In Progress key points: {len(all_prev_kps)}")
            
            # Additional check: exclude key points from shifts that have been submitted with 'Closed' status
            filtered_kps = []
            for kp in all_prev_kps:
                # Check if this key point's shift was submitted and this key point was marked closed
                shift = Shift.query.get(kp.shift_id)
                if shift and shift.status == 'sent':
                    # This is from a submitted handover - check if there's a newer version that closed this key point
                    newer_closed = ShiftKeyPoint.query.filter(
                        ShiftKeyPoint.description == kp.description,
                        ShiftKeyPoint.jira_id == kp.jira_id,
                        ShiftKeyPoint.status == 'Closed',
                        ShiftKeyPoint.id > kp.id
                    ).first()
                    if newer_closed:
                        logger.debug(f"[DASHBOARD DEBUG] Excluding key point ID {kp.id} - found newer closed version ID {newer_closed.id}")
                        continue
                filtered_kps.append(kp)
            
            all_prev_kps = filtered_kps
            logger.debug(f"[DASHBOARD DEBUG] After submission filtering: {len(all_prev_kps)} key points remain")
            
            # Deduplicate: keep only the latest (by id) for each (description, normalized_jira_id) pair
            kp_map = {}
            for kp in all_prev_kps:
                if kp.status == 'Closed':
                    continue
                # Normalize JIRA ID: treat None, NULL, empty string, and 'None' as equivalent
                normalized_jira = kp.jira_id if kp.jira_id and kp.jira_id.lower() not in ['none', 'null', ''] else None
                key = (kp.description, normalized_jira)
                if key not in kp_map or kp.id > kp_map[key].id:
                    kp_map[key] = kp
            
            # Convert to list and attach assigned user info
            open_key_points = []
            from models.models import TeamMember, User
            for kp in kp_map.values():
                assigned_user = None
                if kp.responsible_engineer_id:
                    team_member = TeamMember.query.get(kp.responsible_engineer_id)
                    if team_member:
                        if team_member.user_id:
                            user = User.query.get(team_member.user_id)
                            assigned_user = user.username if user else team_member.name
                        else:
                            assigned_user = team_member.name
                kp.assigned_to_display = assigned_user or "Unassigned"
                open_key_points.append(kp)
                
            logger.debug(f"[DASHBOARD DEBUG] Final deduplicated key points for team: {len(open_key_points)}")
        else:
            # Account admin or super admin - show account-level filtering
            # 🔧 FIXED: Get ALL key points first, then deduplicate, then filter by status
            # This ensures we find the latest key point even if it's closed
            all_key_points = ShiftKeyPoint.query.filter_by(account_id=filter_account_id).all()
            
            # Apply deduplication logic: keep only the latest (by id) for each (description, jira_id) pair
            kp_map = {}
            for kp in all_key_points:
                key = (kp.description, kp.jira_id)
                if key not in kp_map or kp.id > kp_map[key].id:
                    kp_map[key] = kp
            
            # Filter to only show Open and In Progress after deduplication
            # Attach assigned user info to each key point
            open_key_points = []
            from models.models import TeamMember, User
            for kp in kp_map.values():
                if kp.status in ['Open', 'In Progress']:
                    assigned_user = None
                    if kp.responsible_engineer_id:
                        team_member = TeamMember.query.get(kp.responsible_engineer_id)
                        if team_member:
                            # Prefer linked user if available, else fallback to team member name
                            if team_member.user_id:
                                user = User.query.get(team_member.user_id)
                                assigned_user = user.username if user else team_member.name
                            else:
                                assigned_user = team_member.name
                    kp.assigned_to_display = assigned_user or "Unassigned"
                    open_key_points.append(kp)
        
        # Get priority incidents for account-level filtering (both cases need this)
        # 🔧 FIXED: Only show Priority incidents in account admin view
        if target_handover:
            priority_incidents = Incident.query.filter(
                Incident.shift_id == target_handover.id,
                Incident.account_id == filter_account_id,
                Incident.type == 'Priority',  # Only Priority incidents
                Incident.status != 'Closed'
            ).all()
            
            # Apply same closure filtering logic
            filtered_priority_incidents = []
            for incident in priority_incidents:
                newer_closed_incident = Incident.query.filter(
                    Incident.account_id == filter_account_id,
                    Incident.shift_id > target_handover.id,
                    Incident.title == incident.title,
                    Incident.type == 'Closed',
                    Incident.status == 'Resolved'
                ).first()
                
                if not newer_closed_incident:
                    filtered_priority_incidents.append(incident)
            
            priority_incidents = filtered_priority_incidents
        else:
            priority_incidents = []
    else:
        # 🔧 FIXED: For super admin without filters, get ALL key points first, then deduplicate, then filter
        all_key_points = ShiftKeyPoint.query.all()
        
        # Apply deduplication logic: keep only the latest (by id) for each (description, jira_id) pair
        kp_map = {}
        for kp in all_key_points:
            key = (kp.description, kp.jira_id)
            if key not in kp_map or kp.id > kp_map[key].id:
                kp_map[key] = kp
        
        # Filter to only show Open and In Progress after deduplication
        # Attach assigned user info to each key point
        open_key_points = []
        from models.models import TeamMember, User
        for kp in kp_map.values():
            if kp.status in ['Open', 'In Progress']:
                assigned_user = None
                if kp.responsible_engineer_id:
                    team_member = TeamMember.query.get(kp.responsible_engineer_id)
                    if team_member:
                        # Prefer linked user if available, else fallback to team member name
                        if team_member.user_id:
                            user = User.query.get(team_member.user_id)
                            assigned_user = user.username if user else team_member.name
                        else:
                            assigned_user = team_member.name
                kp.assigned_to_display = assigned_user or "Unassigned"
                open_key_points.append(kp)
        
        # Get priority incidents ONLY from target handovers (not all active incidents)
        priority_incidents = []
        for shift in target_handovers:
            # 🔧 FIXED: Get only Priority incidents from each target handover for super admin
            shift_priority_incidents = Incident.query.filter(
                Incident.shift_id == shift.id,
                Incident.type == 'Priority',  # Only Priority incidents
                Incident.status != 'Closed'
            ).all()
            
            # Apply closure filtering
            for incident in shift_priority_incidents:
                newer_closed_incident = Incident.query.filter(
                    Incident.account_id == incident.account_id,
                    Incident.team_id == incident.team_id,
                    Incident.shift_id > shift.id,
                    Incident.title == incident.title,
                    Incident.type == 'Closed',
                    Incident.status == 'Resolved'
                ).first()
                
                if not newer_closed_incident:
                    priority_incidents.append(incident)

    # Chart logic
    range_opt = request.args.get('range', '7d')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    if range_opt == '1d':
        from_date = today - timedelta(days=1)
        to_date = today
    elif range_opt == '7d':
        from_date = today - timedelta(days=7)
        to_date = today
    elif range_opt == '30d':
        from_date = today - timedelta(days=30)
        to_date = today
    elif range_opt == '1y':
        from_date = today - timedelta(days=365)
        to_date = today
    elif range_opt == 'custom' and start_date and end_date:
        from_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        to_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    else:
        from_date = today - timedelta(days=7)
        to_date = today

    date_list = [(from_date + timedelta(days=i)) for i in range((to_date - from_date).days + 1)]
    open_counts = []
    closed_counts = []
    handover_counts = []
    priority_counts = []
    for d in date_list:
        base_incident_query = db.session.query(Incident).join(Shift, Incident.shift_id == Shift.id)
        if current_user.role not in ['super_admin', 'admin']:
            if current_user.role == 'account_admin':
                base_incident_query = base_incident_query.filter(Incident.account_id == current_user.account_id)
            else:
                # Regular users - use multi-team filtering
                base_incident_query = apply_team_filtering(
                    base_incident_query,
                    Incident,
                    current_user,
                    selected_team_id=filter_team_id,
                    account_id=current_user.account_id
                )
        open_c = base_incident_query.filter(Incident.type=='Open', Shift.date==d).count()
        closed_c = base_incident_query.filter(Incident.type=='Closed', Shift.date==d).count()
        handover_c = base_incident_query.filter(Incident.type=='Handover', Shift.date==d).count()
        priority_c = base_incident_query.filter(Incident.type=='Priority', Shift.date==d).count()
        open_counts.append(open_c)
        closed_counts.append(closed_c)
        handover_counts.append(handover_c)
        priority_counts.append(priority_c)

    x_dates = [d.strftime('%Y-%m-%d') for d in date_list]
    trace_open = go.Bar(x=x_dates, y=open_counts, name='Open Incidents', marker_color='#3498db')
    trace_closed = go.Bar(x=x_dates, y=closed_counts, name='Closed Incidents', marker_color='#2ecc71')
    trace_handover = go.Bar(x=x_dates, y=handover_counts, name='Handover Incidents', marker_color='#f39c12')
    trace_priority = go.Bar(x=x_dates, y=priority_counts, name='Priority Incidents', marker_color='#e74c3c')
    data = [trace_open, trace_closed, trace_handover, trace_priority]
    layout = go.Layout(
        barmode='group', 
        xaxis={'title': 'Date'}, 
        yaxis={'title': 'Count'}, 
        title='Incident Trends Over Time',
        height=400,
        margin=dict(l=50, r=50, t=80, b=50)
    )
    graphJSON = json.dumps({'data': data, 'layout': layout}, cls=plotly.utils.PlotlyJSONEncoder)

    # Calculate priority distribution for pie chart
    logger.debug(f"[DEBUG] Dashboard: Starting priority distribution calculation...")
    priority_distribution = {
        'critical': 0,
        'high': 0, 
        'medium': 0,
        'low': 0
    }
    
    logger.debug(f"[DEBUG] Dashboard: Processing {len(open_incidents)} open incidents for priority distribution...")
    for incident in open_incidents:
        if hasattr(incident, 'priority') and incident.priority:
            priority_lower = incident.priority.lower()
            if priority_lower in priority_distribution:
                priority_distribution[priority_lower] += 1
            elif priority_lower == 'urgent':  # Handle alternate naming
                priority_distribution['critical'] += 1

    logger.debug(f"[DEBUG] Dashboard: Priority distribution completed: {priority_distribution}")

    logger.debug(f"[DEBUG] Dashboard: *** NOTIFICATION SECTION REACHED ***")
    logger.debug(f"[DEBUG] Dashboard: About to query notifications...")
    # Get pending notifications for the current user
    pending_notifications = []
    pending_count = 0
    try:
        logger.debug(f"[DEBUG] Dashboard: Importing HandoverNotification model...")
        from models.handover_enhanced import HandoverNotification
        from models.models import User  # Ensure User import is available
        logger.debug(f"[DEBUG] Dashboard: Model imported successfully")
        
        logger.debug(f"[DEBUG] Dashboard: Querying notifications for user_id={current_user.id}")
        pending_notifications = HandoverNotification.query.filter_by(
            recipient_id=current_user.id,
            is_read=False
        ).order_by(HandoverNotification.created_at.desc()).all()
        
        pending_count = len(pending_notifications)
        logger.debug(f"[DEBUG] Dashboard: Found {pending_count} unread notifications for user {current_user.id} ({current_user.username})")
        
        for notif in pending_notifications:
            logger.debug(f"[DEBUG] Dashboard: Notification ID {notif.id}: {notif.title}")
            
    except ImportError as e:
        logger.error(f"[ERROR] Dashboard: Import error for HandoverNotification: {e}")
        pending_notifications = []
        pending_count = 0
    except Exception as e:
        logger.error(f"[ERROR] Dashboard: Error getting pending notifications: {e}")
        import traceback
        traceback.print_exc()
        pending_notifications = []
        pending_count = 0

    return render_template(
        'dashboard.html',
        accounts=accounts,
        teams=teams,
        selected_account_id=selected_account_id,
        selected_team_id=selected_team_id,
        filter_account_id=filter_account_id,
        filter_team_id=filter_team_id,
        open_incidents=open_incidents,
        current_engineers=current_engineers,
        next_shift_engineers=next_shift_engineers,
        open_key_points=open_key_points,
        priority_incidents=priority_incidents,
        priority_distribution=priority_distribution,
        current_shift_type=current_shift_type,
        next_shift_type=next_shift_type,
        today=today,
        next_date=next_date,
        graphJSON=graphJSON,
        selected_range=range_opt,
        start_date=start_date or from_date.strftime('%Y-%m-%d'),
        end_date=end_date or to_date.strftime('%Y-%m-%d'),
        pending_count=pending_count,
        pending_notifications=pending_notifications,
        team_filter_context=team_filter_context
    )


@dashboard_bp.route('/api/incidents/<int:incident_id>/resolve', methods=['POST'])
@login_required
def resolve_incident(incident_id):
    """Mark an incident as resolved so it stops carrying forward into new handover forms."""
    from flask import jsonify
    incident = Incident.query.get_or_404(incident_id)
    if incident.account_id != current_user.account_id and current_user.role != 'super_admin':
        return jsonify({'error': 'Forbidden'}), 403
    incident.is_resolved = True
    incident.resolved_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'status': 'resolved', 'id': incident_id})


@dashboard_bp.route('/api/incidents/<int:incident_id>/unresolve', methods=['POST'])
@login_required
def unresolve_incident(incident_id):
    """Reopen a resolved incident so it carries forward again."""
    from flask import jsonify
    incident = Incident.query.get_or_404(incident_id)
    if incident.account_id != current_user.account_id and current_user.role != 'super_admin':
        return jsonify({'error': 'Forbidden'}), 403
    incident.is_resolved = False
    db.session.commit()
    return jsonify({'status': 'unresolved', 'id': incident_id})
