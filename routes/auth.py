
from flask import Blueprint, render_template, redirect, url_for, request, flash, session, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from models.models import User, Account, Team, db
from models.password_reset import PasswordResetToken
from services.password_reset_service import PasswordResetService
from services.team_access_service import TeamAccessService
from werkzeug.security import check_password_hash, generate_password_hash


def initialize_user_team_session(user):
    """Initialize user's team session on login - set primary team as default"""
    try:
        # Get user's primary team and set it in session
        primary_team_id = TeamAccessService.get_primary_team_id(user=user, account_id=user.account_id)
        if primary_team_id:
            session['selected_team_id'] = primary_team_id
            print(f"✅ [AUTH] Initialized session with primary team {primary_team_id} for user {user.username}")
        else:
            # If no primary team, get first available team
            user_teams = user.get_teams(account_id=user.account_id, active_only=True)
            if user_teams:
                session['selected_team_id'] = user_teams[0].team_id
                print(f"✅ [AUTH] Initialized session with first team {user_teams[0].team_id} for user {user.username}")
            else:
                # Fallback to legacy team_id
                if user.team_id:
                    session['selected_team_id'] = user.team_id
                    print(f"✅ [AUTH] Initialized session with legacy team_id {user.team_id} for user {user.username}")
        
        # Set account in session too
        if user.account_id:
            session['selected_account_id'] = user.account_id
    except Exception as e:
        print(f"⚠️ [AUTH] Error initializing team session: {e}")

auth_bp = Blueprint('auth', __name__)

# Add route to set account/team selection in session
@auth_bp.route('/set_selection', methods=['POST'])
@login_required
def set_selection():
    account_id = request.form.get('account_id', type=int)
    team_id = request.form.get('team_id', type=int)
    if current_user.role == 'super_admin':
        session['selected_account_id'] = account_id
        session['selected_team_id'] = team_id
    elif current_user.role == 'account_admin':
        session['selected_account_id'] = current_user.account_id
        session['selected_team_id'] = team_id
    # Team admin/user: do not allow changing
    return redirect(request.referrer or url_for('dashboard.dashboard'))

# Route for multi-team filtering
@auth_bp.route('/set_team_filter', methods=['POST'])
@auth_bp.route('/auth/set_team_filter', methods=['POST'])  # Add prefixed route for frontend compatibility
@login_required
def set_team_filter():
    """Set the active team filter for multi-team users"""
    from services.team_access_service import TeamAccessService
    
    try:
        data = request.get_json()
        if not data:
            return {'success': False, 'message': 'No data provided'}, 400
            
        team_id = data.get('team_id')
        
        print(f"🔄 [AUTH] Team filter change request: {team_id}")
        
        # Convert 'all' to None for all teams
        if team_id == 'all':
            team_id = None
        else:
            team_id = int(team_id) if team_id and str(team_id).isdigit() else None
        
        # Validate and set the team filter
        if TeamAccessService.set_selected_team(team_id):
            print(f"✅ [AUTH] Team filter updated to: {team_id}")
            return {'success': True, 'message': 'Team filter updated', 'team_id': team_id}
        else:
            print(f"❌ [AUTH] Invalid team selection: {team_id}")
            return {'success': False, 'message': 'Invalid team selection'}, 400
            
    except Exception as e:
        print(f"❌ [AUTH] Error setting team filter: {e}")
        return {'success': False, 'message': f'Error: {str(e)}'}, 500

# Make accounts/teams available in all templates
@auth_bp.app_context_processor
def inject_accounts_teams():
    from services.team_access_service import TeamAccessService
    
    try:
        # Check if current_user is available and authenticated
        if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated and current_user.role in ['super_admin', 'account_admin']:
            accounts = Account.query.filter_by(is_active=True).all()
        else:
            accounts = []
    except:
        # If current_user is not available, return empty lists
        accounts = []
    
    try:
        selected_account_id = session.get('selected_account_id')
        teams = Team.query.filter_by(account_id=selected_account_id, is_active=True).all() if selected_account_id else []
    except:
        teams = []
    
    # Add team filter context for multi-team users
    team_filter_context = {}
    try:
        if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
            team_filter_context = TeamAccessService.get_team_filter_context()
    except:
        pass
    
    return dict(accounts=accounts, teams=teams, team_filter_context=team_filter_context)

from flask import jsonify

# AJAX endpoint to get teams for a selected account
@auth_bp.route('/get_teams')
def get_teams():
    account_id = request.args.get('account_id')
    teams = []
    if account_id:
        teams = Team.query.filter_by(account_id=account_id, is_active=True).all()
    return jsonify({
        'teams': [{'id': t.id, 'name': t.name} for t in teams]
    })


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    accounts = Account.query.filter_by(is_active=True).all()
    selected_account_id = request.form.get('account_id')
    selected_team_id = request.form.get('team_id')
    # Convert to int if present, else None
    selected_account_id_int = int(selected_account_id) if selected_account_id and selected_account_id.isdigit() else None
    selected_team_id_int = int(selected_team_id) if selected_team_id and selected_team_id.isdigit() else None
    teams = []
    if selected_account_id_int:
        teams = Team.query.filter_by(account_id=selected_account_id_int, is_active=True).all()

    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and user.role == 'super_admin':
            # Super Admin: no account/team required, skip onboarding
            if check_password_hash(user.password, password):
                # Update last login time
                from datetime import datetime
                user.last_login = datetime.now()
                user.first_login = False
                user.onboarding_completed = True  # Super admins always considered onboarded
                db.session.commit()
                
                login_user(user)
                initialize_user_team_session(user)
                return redirect(url_for('dashboard.dashboard'))
            else:
                flash('Invalid credentials')
        elif user and user.role in ['account_admin', 'team_admin', 'user', 'engineer']:
            # Check if user needs onboarding (first-time login or no account/team assigned)
            if user.needs_onboarding:
                # For first-time users, just verify password and redirect to onboarding
                if check_password_hash(user.password, password):
                    login_user(user)
                    flash('Welcome! Please select your account and team to continue.', 'info')
                    return redirect(url_for('onboarding.index'))
                else:
                    flash('Invalid credentials')
            else:
                # Existing logic for users with account/team already assigned
                if user.role == 'account_admin':
                    # Account Admin: must match username/account, team optional
                    if selected_account_id_int == user.account_id and check_password_hash(user.password, password):
                        # Update last login time
                        from datetime import datetime
                        user.last_login = datetime.now()
                        user.first_login = False
                        db.session.commit()
                        
                        login_user(user)
                        initialize_user_team_session(user)
                        return redirect(url_for('dashboard.dashboard'))
                    else:
                        flash('Invalid credentials or account mismatch')
                elif user.role == 'team_admin':
                    # Team Admin: must match username/account/team
                    if selected_account_id_int == user.account_id and selected_team_id_int == user.team_id and check_password_hash(user.password, password):
                        # Update last login time
                        from datetime import datetime
                        user.last_login = datetime.now()
                        user.first_login = False
                        db.session.commit()
                        
                        login_user(user)
                        initialize_user_team_session(user)
                        return redirect(url_for('dashboard.dashboard'))
                    else:
                        flash('Invalid credentials or team/account mismatch')
                elif user.role in ['user', 'engineer']:
                    # Regular User/Engineer: must match username/account/team
                    if selected_account_id_int == user.account_id and selected_team_id_int == user.team_id and check_password_hash(user.password, password):
                        # Update last login time
                        from datetime import datetime
                        user.last_login = datetime.now()
                        user.first_login = False
                        db.session.commit()
                        
                        login_user(user)
                        initialize_user_team_session(user)
                        return redirect(url_for('dashboard.dashboard'))
                    else:
                        flash('Invalid credentials or team/account mismatch')
        else:
            flash('Invalid credentials or role')
    return render_template('login.html', 
                          accounts=accounts, 
                          teams=teams, 
                          selected_account_id=selected_account_id_int, 
                          selected_team_id=selected_team_id_int,
                          pending_count=0,
                          pending_assignments=[])

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Forgot password page - initiate password reset"""
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        
        if not email:
            flash('Email address is required.', 'error')
            return render_template('auth/forgot_password.html')
        
        # Get client information for security logging
        ip_address = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR'))
        user_agent = request.environ.get('HTTP_USER_AGENT', '')
        
        # Initiate password reset
        result = PasswordResetService.initiate_password_reset(
            email=email,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        if result['success']:
            flash(result['message'], 'success')
            return redirect(url_for('auth.login'))
        else:
            flash(result['message'], 'error')
    
    return render_template('auth/forgot_password.html')

@auth_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    """Reset password page - complete password reset with token"""
    token = request.args.get('token') or request.form.get('token')
    
    if not token:
        flash('Invalid or missing reset token.', 'error')
        return redirect(url_for('auth.forgot_password'))
    
    if request.method == 'GET':
        # Validate token for GET request
        result = PasswordResetService.validate_reset_token(token)
        if not result['success']:
            flash(result['message'], 'error')
            return redirect(url_for('auth.forgot_password'))
        
        # Show reset form with valid token
        return render_template('auth/reset_password.html', token=token, user=result['user'])
    
    elif request.method == 'POST':
        # Process password reset
        new_password = request.form.get('new_password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        
        if not new_password or not confirm_password:
            flash('Both password fields are required.', 'error')
            return render_template('auth/reset_password.html', token=token)
        
        # Reset password
        result = PasswordResetService.reset_password(
            token_string=token,
            new_password=new_password,
            confirm_password=confirm_password
        )
        
        if result['success']:
            flash(result['message'], 'success')
            return redirect(url_for('auth.login'))
        else:
            flash(result['message'], 'error')
            # Re-validate token to get user info for template
            token_result = PasswordResetService.validate_reset_token(token)
            user = token_result.get('user') if token_result['success'] else None
            return render_template('auth/reset_password.html', token=token, user=user)

@auth_bp.route('/api/check-reset-token', methods=['POST'])
def check_reset_token():
    """API endpoint to validate reset token"""
    data = request.get_json()
    token = data.get('token') if data else None
    
    if not token:
        return jsonify({'success': False, 'message': 'Token is required'})
    
    result = PasswordResetService.validate_reset_token(token)
    
    if result['success']:
        return jsonify({
            'success': True,
            'message': 'Valid token',
            'user': {
                'username': result['user'].username,
                'email': result['user'].email,
                'first_name': result['user'].first_name,
                'last_name': result['user'].last_name
            }
        })
    else:
        return jsonify({
            'success': False,
            'message': result['message']
        })

