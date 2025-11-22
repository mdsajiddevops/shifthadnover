
from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from models.models import Incident, TeamMember, ShiftRoster, ShiftKeyPoint, Shift, Account, Team, User, db
import plotly.graph_objs as go
import plotly
import json
from datetime import datetime, timedelta, time as dt_time
import pytz
from sqlalchemy import func, or_, and_

dashboard_bp = Blueprint('dashboard', __name__)

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
    query = ShiftRoster.query.filter_by(date=date, shift_code=shift_code)
    
    # Apply account/team filtering based on user role or provided parameters
    if account_id and team_id:
        query = query.filter_by(account_id=account_id, team_id=team_id)
    elif current_user.is_authenticated and current_user.role != 'super_admin':
        query = query.filter_by(account_id=current_user.account_id, team_id=current_user.team_id)
    
    entries = query.all()
    member_ids = [e.team_member_id for e in entries]
    
    if not member_ids:
        return []
    
    tm_query = TeamMember.query.filter(TeamMember.id.in_(member_ids))
    
    # Apply same filtering to TeamMember query
    if account_id and team_id:
        tm_query = tm_query.filter_by(account_id=account_id, team_id=team_id)
    elif current_user.is_authenticated and current_user.role != 'super_admin':
        tm_query = tm_query.filter_by(account_id=current_user.account_id, team_id=current_user.team_id)
    
    return tm_query.all()

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
    
    if current_user.role not in ['super_admin']:
        query = query.filter_by(account_id=current_user.account_id, team_id=current_user.team_id)
    
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
    ist_now = get_ist_now()
    today = ist_now.date()
    shift_map = {'Morning': 'D', 'Evening': 'E', 'Night': 'N'}
    current_shift_type, next_shift_type = get_shift_type_and_next(ist_now)
    current_shift_code = shift_map[current_shift_type]
    next_shift_code = shift_map[next_shift_type]
    next_shift_code = shift_map[next_shift_type]
    next_date = today + timedelta(days=1)

    from flask import session
    print(f"[DEBUG] Dashboard: current_user.is_authenticated={getattr(current_user, 'is_authenticated', None)}, id={getattr(current_user, 'id', None)}, username={getattr(current_user, 'username', None)}")
    accounts = []
    teams = []
    selected_account_id = None
    selected_team_id = None
    if current_user.role == 'super_admin':
        accounts = Account.query.filter_by(is_active=True).all()
        selected_account_id = request.args.get('account_id') or session.get('selected_account_id')
        teams = Team.query.filter_by(is_active=True)
        if selected_account_id:
            teams = teams.filter_by(account_id=selected_account_id)
        teams = teams.all()
        selected_team_id = request.args.get('team_id') or session.get('selected_team_id')
        filter_account_id = selected_account_id
        filter_team_id = selected_team_id
    elif current_user.role == 'account_admin':
        filter_account_id = current_user.account_id
        accounts = [Account.query.get(filter_account_id)] if filter_account_id else []
        teams = Team.query.filter_by(account_id=filter_account_id, is_active=True).all()
        selected_team_id = request.args.get('team_id') or session.get('selected_team_id')
        filter_team_id = selected_team_id if selected_team_id else (teams[0].id if teams else None)
    else:
        filter_account_id = current_user.account_id
        filter_team_id = current_user.team_id
        accounts = [Account.query.get(filter_account_id)] if filter_account_id else []
        teams = [Team.query.get(filter_team_id)] if filter_team_id else []

    # Get incidents handed over TO the current shift from the previous shift
    # This shows only incidents that were specifically handed over, not all incidents
    
    # Determine previous shift based on current shift
    shift_map_reverse = {'D': 'Morning', 'E': 'Evening', 'N': 'Night'}
    previous_shift_type = None
    if current_shift_type == 'Evening':
        previous_shift_type = 'Morning'
        previous_shift_date = today  # Morning to Evening handover on same day
    elif current_shift_type == 'Night':
        previous_shift_type = 'Evening'
        previous_shift_date = today  # Evening to Night handover on same day
    elif current_shift_type == 'Morning':
        previous_shift_type = 'Night'
        previous_shift_date = today - timedelta(days=1)  # Night to Morning handover (previous day night)
    
    # Get the specific shift record for the previous shift
    if filter_account_id and filter_team_id:
        previous_shift = Shift.query.filter_by(
            date=previous_shift_date,
            current_shift_type=previous_shift_type,
            account_id=filter_account_id,
            team_id=filter_team_id
        ).first()
        
        if previous_shift:
            print(f"DEBUG Dashboard: Found previous shift ID = {previous_shift.id}")
            
            # Get only Open incidents and Handover incidents from the previous shift
            # Filter for: (type='Active' AND status='Open') OR (type='Handover')
            
            # Get Open incidents and Handover incidents from the previous shift
            open_incidents = Incident.query.filter(
                Incident.shift_id == previous_shift.id,
                Incident.account_id == filter_account_id,
                Incident.team_id == filter_team_id,
                or_(
                    and_(Incident.type == 'Open', Incident.status == 'Active'),
                    Incident.type == 'Handover'
                )
            ).all()
        else:
            open_incidents = []
            
    elif filter_account_id:
        previous_shift = Shift.query.filter_by(
            date=previous_shift_date,
            current_shift_type=previous_shift_type,
            account_id=filter_account_id
        ).first()
        
        if previous_shift:
            # Get only Open incidents and Handover incidents from the previous shift
            open_incidents = Incident.query.filter(
                Incident.shift_id == previous_shift.id,
                Incident.account_id == filter_account_id,
                or_(
                    and_(Incident.type == 'Open', Incident.status == 'Active'),
                    Incident.type == 'Handover'
                )
            ).all()
        else:
            open_incidents = []
            
    else:
        # For super admin, get all incidents from previous shifts
        previous_shifts = Shift.query.filter_by(
            date=previous_shift_date,
            current_shift_type=previous_shift_type
        ).all()
        
        open_incidents = []
        for shift in previous_shifts:
            # Get only Open incidents and Handover incidents from each previous shift
            shift_incidents = Incident.query.filter(
                Incident.shift_id == shift.id,
                or_(
                    and_(Incident.type == 'Open', Incident.status == 'Active'),
                    Incident.type == 'Handover'
                )
            ).all()
            open_incidents.extend(shift_incidents)
    # Current shift engineers
    if current_shift_type == 'Night' and ist_now.time() < dt_time(6,45):
        night_date = today - timedelta(days=1)
        current_engineers = get_engineers_for_shift(night_date, current_shift_code, filter_account_id, filter_team_id)
    else:
        current_engineers = get_engineers_for_shift(today, current_shift_code, filter_account_id, filter_team_id)
    # Next shift engineers
    if next_shift_type == 'Night' and ist_now.time() >= dt_time(21,45):
        next_date_for_engineers = today + timedelta(days=1)
        next_shift_engineers = get_engineers_for_shift(next_date_for_engineers, next_shift_code, filter_account_id, filter_team_id)
    else:
        next_shift_engineers = get_engineers_for_shift(today, next_shift_code, filter_account_id, filter_team_id)
    if filter_account_id and filter_team_id:
        open_key_points = ShiftKeyPoint.query.filter_by(account_id=filter_account_id, team_id=filter_team_id).filter(
            ShiftKeyPoint.status.in_(['Open', 'In Progress'])
        ).all()
        # Get priority incidents (High and Critical priority incidents that are still active)
        priority_incidents = Incident.query.filter_by(
            account_id=filter_account_id, 
            team_id=filter_team_id,
            status='Active'
        ).filter(
            or_(Incident.type == 'Priority', Incident.priority.in_(['High', 'Critical']))
        ).all()
    elif filter_account_id:
        open_key_points = ShiftKeyPoint.query.filter_by(account_id=filter_account_id).filter(
            ShiftKeyPoint.status.in_(['Open', 'In Progress'])
        ).all()
        # Get priority incidents for the account
        priority_incidents = Incident.query.filter_by(
            account_id=filter_account_id,
            status='Active'
        ).filter(
            or_(Incident.type == 'Priority', Incident.priority.in_(['High', 'Critical']))
        ).all()
    else:
        # For super admin without filters, show all open and in progress key points
        open_key_points = ShiftKeyPoint.query.filter(ShiftKeyPoint.status.in_(['Open', 'In Progress'])).all()
        # Get all priority incidents
        priority_incidents = Incident.query.filter_by(status='Active').filter(
            or_(Incident.type == 'Priority', Incident.priority.in_(['High', 'Critical']))
        ).all()

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
        if current_user.role != 'admin':
            base_incident_query = base_incident_query.filter(Incident.account_id==current_user.account_id, Incident.team_id==current_user.team_id)
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
    priority_distribution = {
        'critical': 0,
        'high': 0, 
        'medium': 0,
        'low': 0
    }
    
    for incident in open_incidents:
        if hasattr(incident, 'priority') and incident.priority:
            priority_lower = incident.priority.lower()
            if priority_lower in priority_distribution:
                priority_distribution[priority_lower] += 1
            elif priority_lower == 'urgent':  # Handle alternate naming
                priority_distribution['critical'] += 1

    return render_template(
        'dashboard.html',
        accounts=accounts,
        teams=teams,
        selected_account_id=filter_account_id,
        selected_team_id=filter_team_id,
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
        end_date=end_date or to_date.strftime('%Y-%m-%d')
    )
