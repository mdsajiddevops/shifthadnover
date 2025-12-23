from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models.models import db, Account, Team, User
from models.handover_enhanced import HandoverIncidentResponseLog
from werkzeug.security import generate_password_hash

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_user.role not in ['super_admin', 'account_admin', 'team_admin']:
            flash('Access denied. Admin privileges required.')
            return redirect(url_for('dashboard.dashboard'))
        return f(*args, **kwargs)
    return decorated

admin_bp = Blueprint('admin', __name__)

# --- Admin Dashboard - Redirect to Secrets Management ---
@admin_bp.route('/')
@login_required
@admin_required
def admin_dashboard():
    """Redirect to secrets management dashboard"""
    return redirect(url_for('admin_secrets.secrets_dashboard'))

# --- Account Management ---
@admin_bp.route('/accounts')
@login_required
@admin_required
def accounts():
    accounts = Account.query.all()
    return render_template('admin/accounts.html', accounts=accounts)

@admin_bp.route('/accounts/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_account():
    if request.method == 'POST':
        name = request.form['name']
        if Account.query.filter_by(name=name).first():
            flash('Account already exists.')
        else:
            db.session.add(Account(name=name))
            db.session.commit()
            flash('Account added.')
            return redirect(url_for('admin.accounts'))
    return render_template('admin/account_form.html', action='Add')

@admin_bp.route('/accounts/edit/<int:account_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_account(account_id):
    account = Account.query.get_or_404(account_id)
    if request.method == 'POST':
        account.name = request.form['name']
        db.session.commit()
        flash('Account updated.')
        return redirect(url_for('admin.accounts'))
    return render_template('admin/account_form.html', action='Edit', account=account)

@admin_bp.route('/accounts/delete/<int:account_id>', methods=['POST'])
@login_required
@admin_required
def delete_account(account_id):
    account = Account.query.get_or_404(account_id)
    db.session.delete(account)
    db.session.commit()
    flash('Account deleted.')
    return redirect(url_for('admin.accounts'))

# --- Team Management ---
# Team management route removed - functionality moved to user management
# @admin_bp.route('/teams')
# @login_required
# @admin_required
# def teams():
#     teams = Team.query.all()
#     return render_template('admin/teams.html', teams=teams)

# Team email configuration is now integrated into secrets management
# Route removed - functionality available at /admin/secrets/

@admin_bp.route('/api/teams-by-account/<int:account_id>')
@login_required
@admin_required  
def get_teams_by_account(account_id):
    """API endpoint to get teams for a specific account"""
    from flask import jsonify
    teams = Team.query.filter_by(account_id=account_id).all()
    return jsonify([{
        'id': team.id,
        'name': team.name,
        'email_recipients': team.email_recipients or '',
        'priority_alert_recipients': team.priority_alert_recipients or ''
    } for team in teams])

# Team add route removed - use user management interface
# @admin_bp.route('/teams/add', methods=['GET', 'POST'])
# @login_required
# @admin_required
# def add_team():
    accounts = Account.query.all()
    if request.method == 'POST':
        name = request.form['name']
        account_id = request.form['account_id']
        email_recipients = request.form.get('email_recipients', '').strip()
        priority_alert_recipients = request.form.get('priority_alert_recipients', '').strip()
        
        if Team.query.filter_by(name=name, account_id=account_id).first():
            flash('Team already exists.')
        else:
            # Validate email addresses if provided
            def validate_email_list(email_string, field_name):
                if email_string:
                    emails = [email.strip() for email in email_string.split(',')]
                    import re
                    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                    for email in emails:
                        if email and not re.match(email_pattern, email):
                            flash(f'Invalid email address in {field_name}: {email}', 'error')
                            return render_template('admin/team_form.html', action='Add', accounts=accounts)
                return None
            
            # Validate emails
            if validate_email_list(email_recipients, 'Email Recipients'):
                return render_template('admin/team_form.html', action='Add', accounts=accounts)
            if validate_email_list(priority_alert_recipients, 'Priority Alert Recipients'):
                return render_template('admin/team_form.html', action='Add', accounts=accounts)
            
            # Create team with email configuration
            team = Team(
                name=name, 
                account_id=account_id,
                email_recipients=email_recipients if email_recipients else None,
                priority_alert_recipients=priority_alert_recipients if priority_alert_recipients else None
            )
            db.session.add(team)
            db.session.commit()
            flash('Team added with email configuration.')
            return redirect(url_for('admin.teams'))
    return render_template('admin/team_form.html', action='Add', accounts=accounts)

# Team edit route removed - use user management interface
# @admin_bp.route('/teams/edit/<int:team_id>', methods=['GET', 'POST'])
# @login_required
# @admin_required
# def edit_team(team_id):
    team = Team.query.get_or_404(team_id)
    accounts = Account.query.all()
    
    if request.method == 'POST':
        try:
            # Validate input data
            name = request.form.get('name', '').strip()
            account_id = request.form.get('account_id', '')
            
            # Validation checks
            if not name:
                flash('Team name is required.', 'error')
                return render_template('admin/team_form.html', action='Edit', team=team, accounts=accounts)
            
            if len(name) < 2:
                flash('Team name must be at least 2 characters long.', 'error')
                return render_template('admin/team_form.html', action='Edit', team=team, accounts=accounts)
            
            if len(name) > 100:
                flash('Team name must be less than 100 characters.', 'error')
                return render_template('admin/team_form.html', action='Edit', team=team, accounts=accounts)
            
            if not account_id:
                flash('Account selection is required.', 'error')
                return render_template('admin/team_form.html', action='Edit', team=team, accounts=accounts)
            
            # Verify account exists
            account = Account.query.get(account_id)
            if not account:
                flash('Selected account does not exist.', 'error')
                return render_template('admin/team_form.html', action='Edit', team=team, accounts=accounts)
            
            # Check for duplicate team name in the same account (excluding current team)
            existing_team = Team.query.filter(
                Team.name == name,
                Team.account_id == account_id,
                Team.id != team_id
            ).first()
            
            if existing_team:
                flash(f'A team named "{name}" already exists in this account.', 'error')
                return render_template('admin/team_form.html', action='Edit', team=team, accounts=accounts)
            
            # Get email configuration fields
            email_recipients = request.form.get('email_recipients', '').strip()
            priority_alert_recipients = request.form.get('priority_alert_recipients', '').strip()
            
            # Validate email addresses if provided
            def validate_email_list(email_string, field_name):
                if email_string:
                    emails = [email.strip() for email in email_string.split(',')]
                    import re
                    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                    for email in emails:
                        if email and not re.match(email_pattern, email):
                            return f'Invalid email address in {field_name}: {email}'
                return None
            
            # Validate email recipients
            email_error = validate_email_list(email_recipients, 'Email Recipients')
            if email_error:
                flash(email_error, 'error')
                return render_template('admin/team_form.html', action='Edit', team=team, accounts=accounts)
            
            priority_error = validate_email_list(priority_alert_recipients, 'Priority Alert Recipients')
            if priority_error:
                flash(priority_error, 'error')
                return render_template('admin/team_form.html', action='Edit', team=team, accounts=accounts)
            
            # Update team
            old_name = team.name
            old_account = team.account.name if team.account else 'Unknown'
            
            team.name = name
            team.account_id = account_id
            team.email_recipients = email_recipients if email_recipients else None
            team.priority_alert_recipients = priority_alert_recipients if priority_alert_recipients else None
            
            db.session.commit()
            
            # Success message with details
            new_account = account.name
            if old_name != name or old_account != new_account:
                flash(f'Team updated successfully! "{old_name}" → "{name}" (Account: {new_account})', 'success')
            else:
                flash('Team updated successfully!', 'success')
            
            return redirect(url_for('admin.teams'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating team: {str(e)}', 'error')
            return render_template('admin/team_form.html', action='Edit', team=team, accounts=accounts)
    
    return render_template('admin/team_form.html', action='Edit', team=team, accounts=accounts)

# Team delete route removed - use user management interface  
# @admin_bp.route('/teams/delete/<int:team_id>', methods=['POST'])
# @login_required
# @admin_required
# def delete_team(team_id):
    team = Team.query.get_or_404(team_id)
    db.session.delete(team)
    db.session.commit()
    flash('Team deleted.')
    return redirect(url_for('admin.teams'))

# --- User Management ---
@admin_bp.route('/users')
@login_required
@admin_required
def users():
    users = User.query.all()
    return render_template('admin/users.html', users=users)

@admin_bp.route('/users/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_user():
    accounts = Account.query.all()
    teams = Team.query.all()
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        role = request.form['role']
        account_id = request.form['account_id']
        team_id = request.form['team_id'] or None
        if User.query.filter_by(username=username).first():
            flash('Username already exists.')
        else:
            db.session.add(User(username=username, email=email, password=password, role=role, account_id=account_id, team_id=team_id))
            db.session.commit()
            flash('User added.')
            return redirect(url_for('admin.users'))
    return render_template('admin/user_form.html', action='Add', accounts=accounts, teams=teams)

@admin_bp.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    accounts = Account.query.all()
    teams = Team.query.all()
    if request.method == 'POST':
        user.username = request.form['username']
        user.email = request.form['email']
        if request.form['password']:
            user.password = generate_password_hash(request.form['password'])
        user.role = request.form['role']
        user.account_id = request.form['account_id']
        user.team_id = request.form['team_id'] or None
        db.session.commit()
        flash('User updated.')
        return redirect(url_for('admin.users'))
    return render_template('admin/user_form.html', action='Edit', user=user, accounts=accounts, teams=teams)

@admin_bp.route('/users/delete/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash('User deleted.')
    return redirect(url_for('admin.users'))

# --- Handover Incident Response Logs (Admin Only) ---
@admin_bp.route('/incident-response-logs')
@login_required
@admin_required
def incident_response_logs():
    """Admin-only view for comprehensive handover incident response logs"""
    
    # Get filter parameters
    incident_search = request.args.get('incident_search', '').strip()
    status_filter = request.args.get('status_filter', '').strip()
    date_from = request.args.get('date_from', '').strip()
    date_to = request.args.get('date_to', '').strip()
    
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Build query with filters
    query = HandoverIncidentResponseLog.query
    
    # Apply filters independently
    if incident_search:
        query = query.filter(
            db.or_(
                HandoverIncidentResponseLog.incident_number.ilike(f'%{incident_search}%'),
                HandoverIncidentResponseLog.incident_title.ilike(f'%{incident_search}%')
            )
        )
        
    if status_filter:
        query = query.filter(HandoverIncidentResponseLog.response_status == status_filter)
        
    if date_from:
        try:
            from datetime import datetime
            from sqlalchemy import func
            # Try different date formats
            date_from_obj = None
            for fmt in ['%Y-%m-%d', '%d-%m-%Y', '%m/%d/%Y']:
                try:
                    date_from_obj = datetime.strptime(date_from, fmt).date()
                    break
                except ValueError:
                    continue
            
            if date_from_obj:
                query = query.filter(func.date(HandoverIncidentResponseLog.response_datetime) >= date_from_obj)
        except Exception:
            pass
            
    if date_to:
        try:
            from datetime import datetime
            from sqlalchemy import func
            # Try different date formats
            date_to_obj = None
            for fmt in ['%Y-%m-%d', '%d-%m-%Y', '%m/%d/%Y']:
                try:
                    date_to_obj = datetime.strptime(date_to, fmt).date()
                    break
                except ValueError:
                    continue
            
            if date_to_obj:
                query = query.filter(func.date(HandoverIncidentResponseLog.response_datetime) <= date_to_obj)
        except Exception:
            pass
    
    # Apply ordering and pagination
    query = query.order_by(HandoverIncidentResponseLog.response_datetime.desc())
    logs = query.paginate(page=page, per_page=per_page, error_out=False)
    
    # Get summary statistics
    total_logs = HandoverIncidentResponseLog.query.count()
    accepted_logs = HandoverIncidentResponseLog.query.filter_by(response_status='accepted').count()
    rejected_logs = HandoverIncidentResponseLog.query.filter_by(response_status='rejected').count()
    needs_clarification_logs = HandoverIncidentResponseLog.query.filter_by(response_status='needs_clarification').count()
    
    stats = {
        'total_logs': total_logs,
        'accepted_logs': accepted_logs,
        'rejected_logs': rejected_logs,
        'needs_clarification_logs': needs_clarification_logs,
        'response_rate': round((accepted_logs / total_logs * 100) if total_logs > 0 else 0, 1)
    }
    
    return render_template('admin/incident_response_logs.html', 
                         logs=logs, 
                         stats=stats,
                         title='Handover Incident Response Logs')
