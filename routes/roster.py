from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from flask import session
from models.models import TeamMember, ShiftRoster, Team, Account, db
from datetime import datetime

roster_bp = Blueprint('roster', __name__)



# Shift Roster View with Month/Year filters
@roster_bp.route('/roster', methods=['GET', 'POST'])
@login_required
def roster():
    if request.method == 'POST' and current_user.role == 'viewer':
        flash('You do not have permission to edit shift roster.')
        return redirect(url_for('roster.roster'))
    # Get filter values from query params
    import calendar
    month_str = request.args.get('month')
    year = request.args.get('year', default=None, type=int)
    now = datetime.now()
    month = None
    if month_str:
        try:
            month = list(calendar.month_name).index(month_str)
        except ValueError:
            month = None
    if not month:
        month = now.month
    if not year:
        year = now.year
    filter_date = request.args.get('filter_date')
    filter_shift = request.args.get('filter_shift')

    query = db.session.query(ShiftRoster)
    account_id = None
    team_id = None
    accounts = []
    teams = []
    if current_user.role == 'super_admin':
        accounts = Account.query.filter_by(is_active=True).all()
        account_id = request.args.get('account_id')
        team_id = request.args.get('team_id')
        # Update session with selected values for consistent filtering
        if account_id:
            session['selected_account_id'] = account_id
        else:
            account_id = session.get('selected_account_id')
        if team_id:
            try:
                team_id = int(team_id)
                session['selected_team_id'] = team_id
            except (TypeError, ValueError):
                team_id = None
        else:
            team_id = session.get('selected_team_id')
        teams = Team.query.filter_by(is_active=True)
        if account_id:
            teams = teams.filter_by(account_id=account_id)
        teams = teams.all()
        if account_id:
            query = query.filter(ShiftRoster.account_id==account_id)
        if team_id:
            query = query.filter(ShiftRoster.team_id==team_id)
        # Ensure team_id is int for team_members query as well
        tm_query = TeamMember.query
        if account_id:
            tm_query = tm_query.filter_by(account_id=account_id)
        if team_id:
            tm_query = tm_query.filter_by(team_id=team_id)
    elif current_user.role == 'account_admin':
        account_id = current_user.account_id
        if not account_id:
            flash('Access denied: No account assigned.', 'error')
            return redirect(url_for('main.dashboard'))
            
        accounts = [Account.query.get(account_id)] if account_id else []
        teams = Team.query.filter_by(account_id=account_id, is_active=True).all()
        team_id = request.args.get('team_id')
        
        # SECURITY FIX: Validate team belongs to admin's account
        if team_id:
            try:
                team_id = int(team_id)
                # Verify the team belongs to the admin's account
                team_exists = Team.query.filter_by(id=team_id, account_id=account_id).first()
                if not team_exists:
                    flash('Access denied: Team not found in your account.', 'error')
                    team_id = None
            except (TypeError, ValueError):
                team_id = None
        
        query = query.filter(ShiftRoster.account_id==account_id)
        if team_id:
            query = query.filter(ShiftRoster.team_id==team_id)
        else:
            # If no team selected, show all teams for account
            team_ids = [t.id for t in teams]
            if team_ids:
                query = query.filter(ShiftRoster.team_id.in_(team_ids))
            else:
                query = query.filter(ShiftRoster.team_id.in_([-1]))  # No teams = no results
    else:
        # SECURITY FIX: Regular users (team_admin, user) see ONLY their own team data
        if not current_user.team_id:
            flash('Access denied: No team assigned to your account.', 'error')
            return redirect(url_for('main.dashboard'))
        
        account_id = current_user.account_id
        team_id = current_user.team_id
        
        # Strict validation: ensure user can only access their own team
        accounts = []  # No account dropdown for regular users
        teams = []     # No team dropdown for regular users
        
        # Filter strictly by user's team only
        query = query.filter(ShiftRoster.account_id==account_id)
        query = query.filter(ShiftRoster.team_id==team_id)
        
        # Log access for security monitoring
        from flask import current_app
        current_app.logger.info(f"User {current_user.username} (role: {current_user.role}) accessed roster - restricted to team {team_id}")
    # Removed debug flash
    if month:
        query = query.filter(db.extract('month', ShiftRoster.date) == month)
    if year:
        query = query.filter(db.extract('year', ShiftRoster.date) == year)
    roster_entries = query.order_by(ShiftRoster.date).all()
    if not roster_entries:
        pass
    tm_query = TeamMember.query
    if current_user.role == 'super_admin':
        account_id = session.get('selected_account_id')
        team_id = session.get('selected_team_id')
        if account_id:
            tm_query = tm_query.filter_by(account_id=account_id)
        if team_id:
            tm_query = tm_query.filter_by(team_id=team_id)
    elif current_user.role == 'account_admin':
        account_id = current_user.account_id
        team_id = request.args.get('team_id')
        
        # SECURITY FIX: Validate team belongs to admin's account (same as above)
        if team_id:
            try:
                team_id = int(team_id)
                # Verify the team belongs to the admin's account
                team_exists = Team.query.filter_by(id=team_id, account_id=account_id).first()
                if not team_exists:
                    team_id = None
            except (TypeError, ValueError):
                team_id = None
        
        tm_query = tm_query.filter_by(account_id=account_id)
        if team_id:
            tm_query = tm_query.filter_by(team_id=team_id)
        else:
            # If no team selected, show all team members for account
            team_ids = [t.id for t in teams]
            if team_ids:
                tm_query = tm_query.filter(TeamMember.team_id.in_(team_ids))
            else:
                tm_query = tm_query.filter(TeamMember.team_id.in_([-1]))  # No teams = no results
    else:
        # SECURITY FIX: Regular users see only their team members
        if not current_user.team_id:
            # This should already be caught above, but double-check for security
            tm_query = tm_query.filter_by(id=-1)  # Return no results
        else:
            tm_query = tm_query.filter_by(account_id=current_user.account_id, team_id=current_user.team_id)
    all_members_all = tm_query.all()
    # Only include members with at least one shift entry
    member_ids_with_shifts = {entry.team_member_id for entry in roster_entries}
    all_members = [m for m in all_members_all if m.id in member_ids_with_shifts]
    # Debug: Show roster_entries and all_members
    # Removed debug flash
    # Build a set of all dates in the filtered result
    all_dates = sorted({entry.date for entry in roster_entries})
    # Build roster data: {member_name: {date: shift_code}}
    roster_data = {member.name: {date: '' for date in all_dates} for member in all_members}
    for entry in roster_entries:
        member = next((m for m in all_members if m.id == entry.team_member_id), None)
        if member:
            roster_data[member.name][entry.date] = entry.shift_code
    # For dropdowns
    months = [calendar.month_name[i] for i in range(1, 13)]
    # Show current year and next 10 years
    current_year = now.year
    years = [current_year + i for i in range(11)]

    # SECURITY FIX: Team Availability Filter with role-based access control
    present_members = []
    present_members_by_shift = {}
    if filter_date:
        date_obj = datetime.strptime(filter_date, '%Y-%m-%d').date()
        
        # Build base query with role-based security restrictions
        if current_user.role == 'super_admin':
            # Super admin can filter by any account/team
            base_roster_query = ShiftRoster.query.filter(ShiftRoster.date == date_obj)
            if account_id:
                base_roster_query = base_roster_query.filter(ShiftRoster.account_id == account_id)
            if team_id:
                base_roster_query = base_roster_query.filter(ShiftRoster.team_id == team_id)
                
        elif current_user.role == 'account_admin':
            # Account admin restricted to their account only
            base_roster_query = ShiftRoster.query.filter(
                ShiftRoster.date == date_obj,
                ShiftRoster.account_id == current_user.account_id
            )
            if team_id and team_id in [t.id for t in teams]:  # Validate team belongs to account
                base_roster_query = base_roster_query.filter(ShiftRoster.team_id == team_id)
                
        else:
            # Regular users and team admins - ONLY their own team
            if not current_user.team_id:
                # No team assigned = no results
                base_roster_query = ShiftRoster.query.filter(ShiftRoster.id == -1)
            else:
                base_roster_query = ShiftRoster.query.filter(
                    ShiftRoster.date == date_obj,
                    ShiftRoster.account_id == current_user.account_id,
                    ShiftRoster.team_id == current_user.team_id
                )
        
        if filter_shift is not None and filter_shift != '':
            # Single shift filter with security
            present_entries = base_roster_query.filter(ShiftRoster.shift_code == filter_shift).all()
            present_member_ids = [e.team_member_id for e in present_entries]
            
            if present_member_ids:
                # Additional security: ensure team members belong to allowed teams
                allowed_team_ids = []
                if current_user.role == 'super_admin':
                    allowed_team_ids = [t.id for t in Team.query.all()] if not team_id else [team_id]
                elif current_user.role == 'account_admin':
                    allowed_team_ids = [t.id for t in teams]
                else:
                    allowed_team_ids = [current_user.team_id] if current_user.team_id else []
                
                present_members = TeamMember.query.filter(
                    TeamMember.id.in_(present_member_ids),
                    TeamMember.team_id.in_(allowed_team_ids)
                ).all() if allowed_team_ids else []
            else:
                present_members = []
        else:
            # Group by shift_code with security restrictions
            shift_codes = ['D', 'E', 'N', 'LE', 'G']
            for code in shift_codes:
                entries = base_roster_query.filter(ShiftRoster.shift_code == code).all()
                member_ids = [e.team_member_id for e in entries]
                
                if member_ids:
                    # Apply same team security as above
                    allowed_team_ids = []
                    if current_user.role == 'super_admin':
                        allowed_team_ids = [t.id for t in Team.query.all()] if not team_id else [team_id]
                    elif current_user.role == 'account_admin':
                        allowed_team_ids = [t.id for t in teams]
                    else:
                        allowed_team_ids = [current_user.team_id] if current_user.team_id else []
                    
                    members = TeamMember.query.filter(
                        TeamMember.id.in_(member_ids),
                        TeamMember.team_id.in_(allowed_team_ids)
                    ).all() if allowed_team_ids else []
                else:
                    members = []
                    
                present_members_by_shift[code] = members
            
            # Ensure all shift codes are present in the dict, even if empty
            for code in shift_codes:
                if code not in present_members_by_shift:
                    present_members_by_shift[code] = []
        
        # Security logging for team availability filter access
        from flask import current_app
        if filter_shift:
            current_app.logger.info(f"User {current_user.username} (role: {current_user.role}) filtered team availability - Date: {filter_date}, Shift: {filter_shift}, Results: {len(present_members)} members")
        else:
            total_members = sum(len(members) for members in present_members_by_shift.values())
            current_app.logger.info(f"User {current_user.username} (role: {current_user.role}) viewed team availability - Date: {filter_date}, All shifts, Results: {total_members} members")

    return render_template(
        'shift_roster.html',
        all_dates=all_dates,
        all_members=all_members,
        roster_data=roster_data,
        months=months,
        years=years,
        selected_month=month,
        selected_year=year,
        filter_date=filter_date,
        filter_shift=filter_shift,
        present_members=present_members,
        present_members_by_shift=present_members_by_shift if 'present_members_by_shift' in locals() else {},
        accounts=accounts,
        teams=teams
    )

