from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models.models import db, Account, Team, User
from models.handover_enhanced import HandoverIncidentResponseLog
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta

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

# --- Active Sessions Management ---
@admin_bp.route('/active-sessions')
@login_required
@admin_required
def active_sessions():
    """View currently active users and their session information"""
    
    # Get time thresholds
    now = datetime.now()
    online_threshold = now - timedelta(minutes=5)  # Online: active in last 5 minutes
    recently_active_threshold = now - timedelta(minutes=30)  # Recently active: last 30 minutes
    today_threshold = now - timedelta(hours=24)  # Active today: last 24 hours
    
    # Role-based filtering
    if current_user.role == 'super_admin':
        base_query = User.query.filter(User.status == 'active')
    elif current_user.role == 'account_admin':
        base_query = User.query.filter(User.account_id == current_user.account_id, User.status == 'active')
    else:  # team_admin
        base_query = User.query.filter(
            User.account_id == current_user.account_id,
            User.team_id == current_user.team_id,
            User.status == 'active'
        )
    
    # Get users by activity status
    online_users = base_query.filter(User.last_activity >= online_threshold).order_by(User.last_activity.desc()).all()
    recently_active_users = base_query.filter(
        User.last_activity >= recently_active_threshold,
        User.last_activity < online_threshold
    ).order_by(User.last_activity.desc()).all()
    active_today_users = base_query.filter(
        User.last_activity >= today_threshold,
        User.last_activity < recently_active_threshold
    ).order_by(User.last_activity.desc()).all()
    
    # Get users who logged in but no recent activity
    inactive_users = base_query.filter(
        db.or_(
            User.last_activity.is_(None),
            User.last_activity < today_threshold
        )
    ).order_by(User.last_login.desc()).limit(50).all()
    
    # Statistics
    stats = {
        'online_count': len(online_users),
        'recently_active_count': len(recently_active_users),
        'active_today_count': len(active_today_users),
        'total_users': base_query.count()
    }
    
    return render_template('admin/active_sessions.html',
                         online_users=online_users,
                         recently_active_users=recently_active_users,
                         active_today_users=active_today_users,
                         inactive_users=inactive_users,
                         stats=stats,
                         now=now)

@admin_bp.route('/api/active-sessions')
@login_required
@admin_required
def active_sessions_api():
    """API endpoint for real-time active session updates"""
    now = datetime.now()
    online_threshold = now - timedelta(minutes=5)
    
    # Role-based filtering
    if current_user.role == 'super_admin':
        base_query = User.query.filter(User.status == 'active')
    elif current_user.role == 'account_admin':
        base_query = User.query.filter(User.account_id == current_user.account_id, User.status == 'active')
    else:
        base_query = User.query.filter(
            User.account_id == current_user.account_id,
            User.team_id == current_user.team_id,
            User.status == 'active'
        )
    
    online_users = base_query.filter(User.last_activity >= online_threshold).all()
    
    return jsonify({
        'online_count': len(online_users),
        'users': [{
            'id': u.id,
            'name': u.display_name,
            'email': u.email,
            'role': u.role,
            'team': u.team.name if u.team else 'N/A',
            'last_activity': u.last_activity.strftime('%Y-%m-%d %H:%M:%S') if u.last_activity else None
        } for u in online_users]
    })

# --- Session Management (Terminate Sessions) ---
@admin_bp.route('/terminate-session/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def terminate_session(user_id):
    """Terminate a specific user's session (force logout)"""
    # Only super_admin can terminate sessions
    if current_user.role != 'super_admin':
        flash('Only Super Admins can terminate user sessions.', 'error')
        return redirect(url_for('admin.active_sessions'))
    
    # Cannot terminate own session
    if user_id == current_user.id:
        flash('You cannot terminate your own session.', 'warning')
        return redirect(url_for('admin.active_sessions'))
    
    user = User.query.get(user_id)
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('admin.active_sessions'))
    
    try:
        # Clear session token to invalidate their session
        user.session_token = None
        user.sessions_terminated_at = datetime.now()
        db.session.commit()
        
        # Log the action
        from services.audit_service import log_action
        log_action(
            action='SESSION_TERMINATED',
            details=f'Admin {current_user.username} terminated session for user {user.username} ({user.email})'
        )
        
        flash(f'Session terminated for user: {user.display_name}', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error terminating session: {str(e)}', 'error')
    
    return redirect(url_for('admin.active_sessions'))

@admin_bp.route('/terminate-all-sessions/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def terminate_all_user_sessions(user_id):
    """Terminate all sessions for a specific user"""
    # Only super_admin can terminate sessions
    if current_user.role != 'super_admin':
        return jsonify({'success': False, 'error': 'Only Super Admins can terminate sessions'}), 403
    
    # Cannot terminate own sessions
    if user_id == current_user.id:
        return jsonify({'success': False, 'error': 'Cannot terminate your own sessions'}), 400
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'error': 'User not found'}), 404
    
    try:
        user.session_token = None
        user.sessions_terminated_at = datetime.now()
        db.session.commit()
        
        from services.audit_service import log_action
        log_action(
            action='ALL_SESSIONS_TERMINATED',
            details=f'Admin {current_user.username} terminated all sessions for user {user.username}'
        )
        
        return jsonify({
            'success': True, 
            'message': f'All sessions terminated for {user.display_name}'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/terminate-bulk-sessions', methods=['POST'])
@login_required
@admin_required
def terminate_bulk_sessions():
    """Terminate sessions for multiple users (emergency bulk logout)"""
    # Only super_admin can bulk terminate
    if current_user.role != 'super_admin':
        return jsonify({'success': False, 'error': 'Only Super Admins can perform bulk termination'}), 403
    
    data = request.get_json()
    user_ids = data.get('user_ids', [])
    
    if not user_ids:
        return jsonify({'success': False, 'error': 'No users specified'}), 400
    
    # Remove current user from list if present
    user_ids = [uid for uid in user_ids if uid != current_user.id]
    
    if not user_ids:
        return jsonify({'success': False, 'error': 'No valid users to terminate'}), 400
    
    try:
        terminated_count = 0
        for user_id in user_ids:
            user = User.query.get(user_id)
            if user:
                user.session_token = None
                user.sessions_terminated_at = datetime.now()
                terminated_count += 1
        
        db.session.commit()
        
        from services.audit_service import log_action
        log_action(
            action='BULK_SESSIONS_TERMINATED',
            details=f'Admin {current_user.username} terminated {terminated_count} user sessions'
        )
        
        return jsonify({
            'success': True,
            'message': f'Terminated {terminated_count} user sessions',
            'count': terminated_count
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/session-info/<int:user_id>')
@login_required
@admin_required
def get_session_info(user_id):
    """Get detailed session information for a user"""
    if current_user.role != 'super_admin':
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'error': 'User not found'}), 404
    
    return jsonify({
        'success': True,
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'display_name': user.display_name,
            'role': user.role,
            'team': user.team.name if user.team else 'N/A',
            'account': user.account.name if user.account else 'N/A',
            'last_login': user.last_login.strftime('%Y-%m-%d %H:%M:%S') if user.last_login else None,
            'last_activity': user.last_activity.strftime('%Y-%m-%d %H:%M:%S') if user.last_activity else None,
            'session_created_at': user.session_created_at.strftime('%Y-%m-%d %H:%M:%S') if user.session_created_at else None,
            'has_active_session': user.session_token is not None,
            'is_online': user.is_online,
            'is_recently_active': user.is_recently_active
        }
    })

# --- Email Delivery Monitoring ---
@admin_bp.route('/email-monitoring')
@login_required
@admin_required
def email_monitoring():
    """View email delivery logs and statistics"""
    from models.email_delivery_log import EmailDeliveryLog
    
    # Get filter parameters
    status_filter = request.args.get('status', '')
    source_filter = request.args.get('source', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    page = request.args.get('page', 1, type=int)
    per_page = 25
    
    # Build query with role-based filtering
    query = EmailDeliveryLog.query
    
    if current_user.role == 'account_admin':
        query = query.filter(EmailDeliveryLog.account_id == current_user.account_id)
    elif current_user.role == 'team_admin':
        query = query.filter(
            EmailDeliveryLog.account_id == current_user.account_id,
            EmailDeliveryLog.team_id == current_user.team_id
        )
    # super_admin sees all
    
    # Apply filters
    if status_filter:
        query = query.filter(EmailDeliveryLog.status == status_filter)
    if source_filter:
        query = query.filter(EmailDeliveryLog.source_type == source_filter)
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(EmailDeliveryLog.created_at >= date_from_obj)
        except ValueError:
            pass
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(EmailDeliveryLog.created_at < date_to_obj)
        except ValueError:
            pass
    
    # Order by most recent first
    query = query.order_by(EmailDeliveryLog.created_at.desc())
    
    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    email_logs = pagination.items
    
    # Calculate statistics
    stats_query = EmailDeliveryLog.query
    if current_user.role == 'account_admin':
        stats_query = stats_query.filter(EmailDeliveryLog.account_id == current_user.account_id)
    elif current_user.role == 'team_admin':
        stats_query = stats_query.filter(
            EmailDeliveryLog.account_id == current_user.account_id,
            EmailDeliveryLog.team_id == current_user.team_id
        )
    
    # Get stats for last 24 hours
    last_24h = datetime.now() - timedelta(hours=24)
    stats = {
        'total_sent': stats_query.filter(EmailDeliveryLog.status == 'sent').count(),
        'total_failed': stats_query.filter(EmailDeliveryLog.status == 'failed').count(),
        'total_pending': stats_query.filter(EmailDeliveryLog.status == 'pending').count(),
        'total_skipped': stats_query.filter(EmailDeliveryLog.status == 'skipped').count(),
        'sent_24h': stats_query.filter(EmailDeliveryLog.status == 'sent', EmailDeliveryLog.created_at >= last_24h).count(),
        'failed_24h': stats_query.filter(EmailDeliveryLog.status == 'failed', EmailDeliveryLog.created_at >= last_24h).count(),
    }
    stats['total'] = stats['total_sent'] + stats['total_failed'] + stats['total_pending'] + stats['total_skipped']
    stats['success_rate'] = round((stats['total_sent'] / stats['total'] * 100), 1) if stats['total'] > 0 else 0
    
    # Get unique source types for filter dropdown
    source_types = db.session.query(EmailDeliveryLog.source_type).distinct().all()
    source_types = [s[0] for s in source_types if s[0]]
    
    return render_template('admin/email_monitoring.html',
                         email_logs=email_logs,
                         pagination=pagination,
                         stats=stats,
                         source_types=source_types,
                         status_filter=status_filter,
                         source_filter=source_filter,
                         date_from=date_from,
                         date_to=date_to)

@admin_bp.route('/api/email-monitoring/stats')
@login_required
@admin_required
def email_monitoring_stats_api():
    """API endpoint for real-time email stats"""
    from models.email_delivery_log import EmailDeliveryLog
    
    stats_query = EmailDeliveryLog.query
    if current_user.role == 'account_admin':
        stats_query = stats_query.filter(EmailDeliveryLog.account_id == current_user.account_id)
    elif current_user.role == 'team_admin':
        stats_query = stats_query.filter(
            EmailDeliveryLog.account_id == current_user.account_id,
            EmailDeliveryLog.team_id == current_user.team_id
        )
    
    last_24h = datetime.now() - timedelta(hours=24)
    
    return jsonify({
        'sent_24h': stats_query.filter(EmailDeliveryLog.status == 'sent', EmailDeliveryLog.created_at >= last_24h).count(),
        'failed_24h': stats_query.filter(EmailDeliveryLog.status == 'failed', EmailDeliveryLog.created_at >= last_24h).count(),
        'pending': stats_query.filter(EmailDeliveryLog.status == 'pending').count()
    })

@admin_bp.route('/email-monitoring/<int:log_id>')
@login_required
@admin_required
def email_log_detail(log_id):
    """View detailed information about a specific email delivery"""
    from models.email_delivery_log import EmailDeliveryLog
    
    log = EmailDeliveryLog.query.get_or_404(log_id)
    
    # Check access permissions
    if current_user.role == 'account_admin' and log.account_id != current_user.account_id:
        flash('Access denied.')
        return redirect(url_for('admin.email_monitoring'))
    elif current_user.role == 'team_admin' and (log.account_id != current_user.account_id or log.team_id != current_user.team_id):
        flash('Access denied.')
        return redirect(url_for('admin.email_monitoring'))
    
    return jsonify({
        'id': log.id,
        'uns_event_id': log.uns_event_id,
        'subject': log.subject,
        'recipients': log.get_recipients_list(),
        'cc_recipients': log.get_cc_list(),
        'sender': log.sender,
        'source_type': log.source_type,
        'source_id': log.source_id,
        'status': log.status,
        'error_message': log.error_message,
        'smtp_server': log.smtp_server,
        'smtp_port': log.smtp_port,
        'created_at': log.created_at.strftime('%Y-%m-%d %H:%M:%S') if log.created_at else None,
        'sent_at': log.sent_at.strftime('%Y-%m-%d %H:%M:%S') if log.sent_at else None,
        'duration_seconds': log.duration_seconds,
        'account': log.account.name if log.account else 'N/A',
        'team': log.team.name if log.team else 'N/A',
        'recipient_count': log.recipient_count
    })

# --- Handover Incident Response Logs (Admin Only) ---
@admin_bp.route('/incident-response-logs')
@login_required
@admin_required
def incident_response_logs():
    """Admin-only view for comprehensive handover incident response logs with access control"""
    
    # Get filter parameters
    incident_search = request.args.get('incident_search', '').strip()
    status_filter = request.args.get('status_filter', '').strip()
    date_from = request.args.get('date_from', '').strip()
    date_to = request.args.get('date_to', '').strip()
    
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Build query with access control
    query = HandoverIncidentResponseLog.query
    
    # Apply access control based on user role
    if current_user.role == 'super_admin':
        # Super admin can see all logs
        pass
    elif current_user.role == 'account_admin':
        # Account admin can only see logs from their account
        if current_user.account_id:
            query = query.filter(HandoverIncidentResponseLog.account_id == current_user.account_id)
        else:
            query = query.filter(db.literal(False))
    elif current_user.role == 'team_admin':
        # Team admin can only see logs from their team(s)
        from services.team_access_service import TeamAccessService
        user_team_ids = TeamAccessService.get_user_team_ids()
        if user_team_ids:
            query = query.filter(HandoverIncidentResponseLog.team_id.in_(user_team_ids))
        else:
            query = query.filter(db.literal(False))
    
    # Apply search/filter parameters independently
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
    
    # Get summary statistics with same access control
    stats_base_query = HandoverIncidentResponseLog.query
    
    # Apply same access control to stats
    if current_user.role == 'super_admin':
        pass
    elif current_user.role == 'account_admin':
        if current_user.account_id:
            stats_base_query = stats_base_query.filter(HandoverIncidentResponseLog.account_id == current_user.account_id)
        else:
            stats_base_query = stats_base_query.filter(db.literal(False))
    elif current_user.role == 'team_admin':
        from services.team_access_service import TeamAccessService
        user_team_ids = TeamAccessService.get_user_team_ids()
        if user_team_ids:
            stats_base_query = stats_base_query.filter(HandoverIncidentResponseLog.team_id.in_(user_team_ids))
        else:
            stats_base_query = stats_base_query.filter(db.literal(False))
    
    total_logs = stats_base_query.count()
    accepted_logs = stats_base_query.filter(HandoverIncidentResponseLog.response_status == 'accepted').count()
    rejected_logs = stats_base_query.filter(HandoverIncidentResponseLog.response_status == 'rejected').count()
    needs_clarification_logs = stats_base_query.filter(HandoverIncidentResponseLog.response_status == 'needs_clarification').count()
    
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
