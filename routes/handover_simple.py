from flask import Blueprint, request, render_template, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from models.models import Shift, Incident, KeyPoint, TeamMember, Team, AuditLog, ShiftRoster
from models.incident_assignment import IncidentAssignment
from models.database import db
from datetime import datetime, date, timedelta, time as dt_time
import pytz
from services.servicenow_service import ServiceNowService

handover_bp = Blueprint('handover', __name__)

@handover_bp.route('/handover', methods=['GET', 'POST'])
@login_required  
def handover():
    """Simple handover form with fast processing"""
    
    # 🚨 CRITICAL: Identify which route is being used
    print("🚨🚨🚨 SIMPLE HANDOVER ROUTE FROM handover_simple.py IS BEING USED 🚨🚨🚨")
    
    # Get account and team info
    if current_user.role == 'super_admin':
        account_id = request.form.get('account_id') if request.method == 'POST' else current_user.account_id
    else:
        account_id = current_user.account_id
        
    # Ensure account_id is never None
    if not account_id:
        account_id = current_user.account_id
        
    # Final safeguard: if current_user.account_id is also None, handle gracefully
    if not account_id:
        flash('User account configuration is incomplete. Please contact administrator.', 'error')
        return redirect(url_for('dashboard.dashboard'))
        
    if current_user.role in ['super_admin', 'account_admin']:
        team_id_raw = request.form.get('team_id') if request.method == 'POST' else current_user.team_id
    else:
        team_id_raw = current_user.team_id
        
    try:
        team_id = int(team_id_raw) if team_id_raw not in (None, '', 'None') else None
    except (TypeError, ValueError):
        team_id = None
    
    # Get teams for the dropdown
    if current_user.role == 'super_admin':
        teams = Team.query.filter_by(status='active').all()
    elif current_user.role == 'account_admin':
        teams = Team.query.filter_by(account_id=current_user.account_id, status='active').all()
    else:
        teams = Team.query.filter_by(account_id=current_user.account_id, id=current_user.team_id, status='active').all()
    
    # Set default team selection
    default_team_id = None
    if current_user.role in ['user', 'team_admin'] and current_user.team_id:
        default_team_id = current_user.team_id
    elif team_id:
        default_team_id = team_id
    
    # Get team members
    tm_query = TeamMember.query
    if current_user.role == 'super_admin':
        if account_id:
            tm_query = tm_query.filter_by(account_id=account_id)
        if team_id:
            tm_query = tm_query.filter_by(team_id=team_id)
    elif current_user.role == 'account_admin':
        tm_query = tm_query.filter_by(account_id=current_user.account_id)
        if team_id:
            tm_query = tm_query.filter_by(team_id=team_id)
    else:
        tm_query = tm_query.filter_by(account_id=current_user.account_id, team_id=current_user.team_id)
    
    team_members = tm_query.all()
    
    # Get current date and time
    ist_now = datetime.now(pytz.timezone('Asia/Kolkata'))
    default_date = ist_now.date()
    
    # Handle POST request - form submission
    if request.method == 'POST':
        try:
            handover_date_str = request.form.get('handover_date')
            if not handover_date_str:
                flash('Handover date is required.', 'error')
                return redirect(url_for('handover.handover'))
            date = datetime.strptime(handover_date_str, '%Y-%m-%d').date()
        except ValueError as e:
            flash(f'Invalid date format: {e}', 'error')
            return redirect(url_for('handover.handover'))
            
        current_shift_type = request.form.get('current_shift_type')
        next_shift_type = request.form.get('next_shift_type')
        
        # Normalize shift types
        if current_shift_type:
            current_shift_type = current_shift_type.capitalize()
        if next_shift_type:
            next_shift_type = next_shift_type.capitalize()
        
        if not current_shift_type or not next_shift_type:
            flash('Please select both current and next shift types.', 'error')
            return redirect(url_for('handover.handover'))
            
        action = request.form.get('action', 'submit')
        
        # ⚠️ DUPLICATE PREVENTION CHECK
        # Check if a handover already exists for this shift date + type + team combination
        existing_handover = Shift.query.filter_by(
            date=date,
            current_shift_type=current_shift_type,
            next_shift_type=next_shift_type,
            team_id=team_id,
            account_id=account_id
        ).first()
        
        if existing_handover:
            # Super Admin bypass capability
            if current_user.role == 'super_admin':
                print(f"[SUPER_ADMIN_BYPASS] Allowing duplicate handover creation for Super Admin")
                flash(f'⚠️ Super Admin Override: Creating duplicate handover for {date.strftime("%d-%m-%Y")} {current_shift_type} → {next_shift_type}', 'warning')
            else:
                # Format the date in DD-MM-YYYY format for user-friendly display
                formatted_date = date.strftime("%d-%m-%Y")
                error_message = f'⚠️ A handover for this shift ({formatted_date} {current_shift_type} → {next_shift_type}) has already been submitted by your team.'
                flash(error_message, 'error')
                print(f"[DUPLICATE_PREVENTION] Blocking duplicate handover - {error_message}")
                return redirect(url_for('handover.handover'))
        
        print(f"[FAST_PATH] Creating handover - Date: {date}, Current: {current_shift_type}, Next: {next_shift_type}, Action: {action}")
        
        # Create minimal shift record
        shift = Shift(
            date=date,
            current_shift_type=current_shift_type,
            next_shift_type=next_shift_type,
            status='draft' if action == 'draft' else 'sent',
            submitted_at=datetime.now() if action == 'submit' else None,  # Set submission timestamp
            account_id=account_id,
            team_id=team_id
        )
        db.session.add(shift)
        db.session.commit()
        
        print(f"[FAST_PATH] Handover created with ID: {shift.id} - redirecting")
        
        if action == 'submit':
            flash('Shift handover submitted successfully!', 'success')
        else:
            flash('Draft saved successfully!', 'success')
            
        return redirect(url_for('reports.handover_reports'))
    
    # Handle GET request - show form
    show_team_error = not Team.query.get(team_id) if team_id else False
    
    # Set default shift types based on current time
    current_time = ist_now.time()
    if current_time >= dt_time(7, 0) and current_time < dt_time(15, 0):
        current_shift_type = 'Morning'
        next_shift_type = 'Evening'
    elif current_time >= dt_time(15, 0) and current_time < dt_time(23, 0):
        current_shift_type = 'Evening'
        next_shift_type = 'Night'
    else:
        current_shift_type = 'Night'
        next_shift_type = 'Morning'
    
    return render_template('handover_form.html',
        team_members=team_members,
        teams=teams,
        default_team_id=default_team_id,
        current_engineers=[],
        next_engineers=[],
        current_shift_type=current_shift_type,
        next_shift_type=next_shift_type,
        open_key_points=[],
        current_time=datetime.now(),
        shift=None,
        open_incidents=[],
        closed_incidents=[],
        priority_incidents=[],
        handover_incidents=[],
        today=default_date.strftime('%Y-%m-%d'),
        show_team_error=show_team_error,
        assignment_groups_filter=[],
        assignment_groups_filtered=False
    )