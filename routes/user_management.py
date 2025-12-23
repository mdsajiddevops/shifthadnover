
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models.models import db, User, Account, Team, UserTeamMembership
from werkzeug.security import generate_password_hash
from services.audit_service import log_action

user_mgmt_bp = Blueprint('user_mgmt', __name__)

@user_mgmt_bp.route('/api/user/<int:user_id>/teams')
@login_required
def get_user_teams(user_id):
    """API endpoint to get user's team memberships"""
    # Allow super_admin and account_admin to manage teams
    if current_user.role not in ['super_admin', 'account_admin']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    user = User.query.get_or_404(user_id)
    
    try:
        # Use direct UserTeamMembership query instead of user.get_teams() which may be failing
        memberships = UserTeamMembership.query.filter_by(
            user_id=user_id, 
            is_active=True
        ).all()
        teams_data = []
        
        for membership in memberships:
            team = db.session.get(Team, membership.team_id)
            account = db.session.get(Account, membership.account_id)
            
            if team and account:
                teams_data.append({
                    'membership_id': membership.id,
                    'team_id': membership.team_id,
                    'team_name': team.name,
                    'account_id': membership.account_id,
                    'account_name': account.name,
                    'is_primary': membership.is_primary,
                    'role': membership.role or '',
                    'created_at': membership.created_at.strftime('%Y-%m-%d %H:%M:%S') if membership.created_at else ''
                })
        
        return jsonify({
            'success': True,
            'user_id': user_id,
            'username': user.username,
            'teams': teams_data
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@user_mgmt_bp.route('/api/teams-not-assigned/<int:user_id>')
@login_required 
def get_teams_not_assigned_to_user(user_id):
    """API endpoint to get teams that user is not a member of"""
    # Allow super_admin and account_admin to manage teams
    if current_user.role not in ['super_admin', 'account_admin']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    user = User.query.get_or_404(user_id)
    
    try:
        # Get user's current team IDs
        current_team_ids = []
        if hasattr(user, 'get_teams'):
            memberships = user.get_teams()
            current_team_ids = [m.team_id for m in memberships]
        
        # Get teams user is not a member of (within same account for account admins)
        query = Team.query.filter(
            ~Team.id.in_(current_team_ids),
            Team.is_active == True,
            Team.status == 'active'
        )
        
        # Account admins can only add users to teams in their account
        if current_user.role == 'account_admin':
            query = query.filter(Team.account_id == current_user.account_id)
            
        available_teams = query.all()
        
        teams_data = []
        for team in available_teams:
            account = Account.query.get(team.account_id)
            teams_data.append({
                'team_id': team.id,
                'team_name': team.name,
                'account_id': team.account_id,
                'account_name': account.name if account else 'Unknown'
            })
        
        return jsonify({
            'success': True,
            'available_teams': teams_data
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@user_mgmt_bp.route('/api/user/<int:user_id>/add-team', methods=['POST'])
@login_required
def add_user_to_team_api(user_id):
    """API endpoint to add a user to a team"""
    if current_user.role not in ['super_admin', 'account_admin']:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        team_id = data.get('team_id')
        role = data.get('role', 'member')
        is_primary = data.get('is_primary', False)
        
        user = User.query.get_or_404(user_id)
        team = Team.query.get_or_404(team_id)
        
        # Check permission
        if current_user.role == 'account_admin' and team.account_id != current_user.account_id:
            return jsonify({'success': False, 'error': 'You can only assign users to teams in your account'}), 403
        
        # Add team membership
        membership = user.add_team_membership(
            team_id=team_id,
            account_id=team.account_id,
            is_primary=is_primary,
            role=role,
            added_by=current_user
        )
        
        if is_primary:
            # Update user's primary team_id for backward compatibility
            user.team_id = team_id
        
        db.session.commit()
        log_action('Add User to Team (API)', f'User: {user.username}, Team: {team.name}, Role: {role}, Primary: {is_primary}')
        
        return jsonify({
            'success': True,
            'message': f'Successfully added {user.username} to {team.name}',
            'membership_id': membership.id
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] add_user_to_team_api: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@user_mgmt_bp.route('/api/user/<int:user_id>/remove-team/<int:team_id>', methods=['DELETE'])
@login_required
def remove_user_from_team_api(user_id, team_id):
    """API endpoint to remove a user from a team"""
    if current_user.role not in ['super_admin', 'account_admin']:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    try:
        user = User.query.get_or_404(user_id)
        team = Team.query.get_or_404(team_id)
        
        # Check permission
        if current_user.role == 'account_admin' and team.account_id != current_user.account_id:
            return jsonify({'success': False, 'error': 'You can only manage teams in your account'}), 403
        
        # Remove team membership
        success = user.remove_team_membership(team_id, team.account_id)
        
        if success:
            db.session.commit()
            log_action('Remove User from Team (API)', f'User: {user.username}, Team: {team.name}')
            return jsonify({
                'success': True,
                'message': f'Successfully removed {user.username} from {team.name}'
            })
        else:
            return jsonify({
                'success': False,
                'error': f'{user.username} is not a member of {team.name}'
            }), 400
            
    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] remove_user_from_team_api: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@user_mgmt_bp.route('/user-management', methods=['GET', 'POST'])
@login_required
def user_management():
    # Check if admin wants to see disabled users
    show_disabled = request.args.get("show_disabled", "false").lower() == "true"
    user_filter = ["active", "disabled"] if show_disabled else ["active"]

    # Role-based filtering
    # Only show active users, teams, and accounts by default
    if current_user.role == 'super_admin':
        users = User.query.filter(User.status.in_(user_filter)).all()
        accounts = Account.query.filter(Account.status.in_(['active', 'disabled'])).all()
        teams = Team.query.filter(Team.status.in_(['active', 'disabled'])).all()
    elif current_user.role == 'account_admin':
        users = User.query.filter(User.account_id==current_user.account_id, User.status.in_(user_filter)).all()
        acc = Account.query.get(current_user.account_id)
        accounts = [acc] if acc and acc.status in ['active', 'disabled'] else []
        teams = Team.query.filter(Team.account_id==current_user.account_id, Team.status.in_(['active', 'disabled'])).all()
    elif current_user.role == 'team_admin':
        users = User.query.filter(User.account_id==current_user.account_id, User.team_id==current_user.team_id, User.status.in_(user_filter)).all()
        acc = Account.query.get(current_user.account_id)
        accounts = [acc] if acc and acc.status in ['active', 'disabled'] else []
        t = Team.query.get(current_user.team_id)
        teams = [t] if t and t.status in ['active', 'disabled'] else []
    else:
        flash('You do not have permission to access user management.')
        return redirect(url_for('dashboard.dashboard'))

    if request.method == 'POST':
        print(f"[POST RECEIVED] user_management: user={getattr(current_user, 'username', None)}, action={request.form.get('action')}, form={dict(request.form)}")
        action = request.form.get('action')
        # Enable/disable user
        if action in ['enable_user', 'disable_user']:
            user_id = request.form.get('user_id', type=int)
            user = User.query.get(user_id)
            if user:
                # Only allow within scope
                if current_user.role == 'super_admin' or \
                   (current_user.role == 'account_admin' and user.account_id == current_user.account_id and user.role != 'super_admin') or \
                   (current_user.role == 'team_admin' and user.account_id == current_user.account_id and user.team_id == current_user.team_id and user.role == 'user'):
                    user.is_active = (action == 'enable_user')
                    user.status = 'active' if action == 'enable_user' else 'disabled'
                    db.session.commit()
                    log_action('Enable/Disable User', f'User ID: {user_id}, Status: {user.status}')
                    flash(f"User {'enabled' if action == 'enable_user' else 'disabled'} successfully.")
                else:
                    flash('You do not have permission to enable/disable this user.')
            else:
                flash('User not found.')
            return redirect(url_for('user_mgmt.user_management'))
        # Enable/disable team
        elif action in ['enable_team', 'disable_team']:
            team_id = request.form.get('team_id', type=int)
            team = Team.query.get(team_id)
            if team:
                if current_user.role == 'super_admin' or \
                   (current_user.role == 'account_admin' and team.account_id == current_user.account_id):
                    team.is_active = (action == 'enable_team')
                    team.status = 'active' if action == 'enable_team' else 'disabled'
                    db.session.commit()
                    log_action('Enable/Disable Team', f'Team ID: {team_id}, Status: {team.status}')
                    flash(f"Team {'enabled' if action == 'enable_team' else 'disabled'} successfully.")
                else:
                    flash('You do not have permission to enable/disable this team.')
            else:
                flash('Team not found.')
            return redirect(url_for('user_mgmt.user_management'))
        # Enable/disable account
        elif action in ['enable_account', 'disable_account']:
            account_id = request.form.get('account_id', type=int)
            account = Account.query.get(account_id)
            if account:
                if current_user.role == 'super_admin':
                    account.is_active = (action == 'enable_account')
                    account.status = 'active' if action == 'enable_account' else 'disabled'
                    db.session.commit()
                    log_action('Enable/Disable Account', f'Account ID: {account_id}, Status: {account.status}')
                    flash(f"Account {'enabled' if action == 'enable_account' else 'disabled'} successfully.")
                else:
                    flash('You do not have permission to enable/disable this account.')
            else:
                flash('Account not found.')
            return redirect(url_for('user_mgmt.user_management'))
        elif action == 'add_account' and current_user.role == 'super_admin':
            account_name = request.form.get('account_name')
            print(f"[DEBUG] Add Account: account_name={account_name}")
            
            if account_name:
                existing_account = Account.query.filter_by(name=account_name).first()
                if existing_account:
                    flash('Account name already exists.')
                else:
                    try:
                        account = Account(
                            name=account_name,
                            status='active',
                            is_active=True
                        )
                        db.session.add(account)
                        db.session.commit()
                        log_action('Add Account', f'Account: {account_name}')
                        flash('Account added successfully.')
                        print(f"[SUCCESS] Account created: {account}")
                    except Exception as e:
                        db.session.rollback()
                        print(f"[ERROR] Failed to create account: {e}")
                        flash('Failed to add account.')
            else:
                flash('Account name is required.')
            return redirect(url_for('user_mgmt.user_management'))
            
        elif action == 'add_team' and (current_user.role == 'super_admin' or current_user.role == 'account_admin'):
            team_name = request.form.get('team_name')
            account_id = request.form.get('account_id', type=int)
            print(f"[DEBUG] Add Team: team_name={team_name}, account_id={account_id}")
            
            if team_name and account_id:
                # Check permission
                if current_user.role == 'account_admin' and account_id != current_user.account_id:
                    flash('You can only add teams to your own account.')
                    return redirect(url_for('user_mgmt.user_management'))
                
                existing_team = Team.query.filter_by(name=team_name, account_id=account_id).first()
                if existing_team:
                    flash('Team name already exists in this account.')
                else:
                    try:
                        team = Team(
                            name=team_name,
                            account_id=account_id,
                            status='active',
                            is_active=True
                        )
                        db.session.add(team)
                        db.session.commit()
                        log_action('Add Team', f'Team: {team_name}, Account ID: {account_id}')
                        flash('Team added successfully.')
                        print(f"[SUCCESS] Team created: {team}")
                    except Exception as e:
                        db.session.rollback()
                        print(f"[ERROR] Failed to create team: {e}")
                        flash('Failed to add team.')
            else:
                flash('Team name and account are required.')
            return redirect(url_for('user_mgmt.user_management'))
        
        elif action == 'edit_user':
            user_id = request.form.get('user_id', type=int)
            user = User.query.get(user_id)
            print(f"[DEBUG] Edit User: user_id={user_id}, user={user}")
            
            if user:
                # Check permission to edit this user
                can_edit = False
                if current_user.role == 'super_admin':
                    can_edit = True
                elif current_user.role == 'account_admin' and user.account_id == current_user.account_id and user.role != 'super_admin':
                    can_edit = True
                elif current_user.role == 'team_admin' and user.account_id == current_user.account_id and user.team_id == current_user.team_id and user.role == 'user':
                    can_edit = True
                
                if can_edit:
                    try:
                        # Get form data
                        new_username = request.form.get('username')
                        new_email = request.form.get('email')
                        new_role = request.form.get('role')
                        new_account_id = request.form.get('account_id', type=int)
                        new_team_id = request.form.get('team_id', type=int) if request.form.get('team_id') else None
                        new_password = request.form.get('new_password')  # Fixed: was 'password', now 'new_password'
                        new_first_name = request.form.get('first_name', '').strip()
                        new_last_name = request.form.get('last_name', '').strip()
                        
                        print(f"[DEBUG] Edit form data: username={new_username}, email={new_email}, role={new_role}, account_id={new_account_id}, team_id={new_team_id}, first_name={new_first_name}, last_name={new_last_name}, password={'***' if new_password else 'None'}")
                        print(f"[DEBUG] Current user values: team_id={user.team_id}, account_id={user.account_id}")
                        
                        # Validate required fields
                        if not new_username:
                            flash('Username is required.')
                            return redirect(url_for('user_mgmt.user_management'))
                        
                        # Check username uniqueness (if changed)
                        if new_username != user.username:
                            existing_user = User.query.filter_by(username=new_username).first()
                            if existing_user:
                                flash('Username already exists.')
                                return redirect(url_for('user_mgmt.user_management'))
                        
                        # Validate role permissions
                        if current_user.role == 'account_admin' and new_role == 'super_admin':
                            flash('Account admins cannot assign super admin role.')
                            return redirect(url_for('user_mgmt.user_management'))
                        elif current_user.role == 'team_admin' and new_role != 'user':
                            flash('Team admins can only assign user role.')
                            return redirect(url_for('user_mgmt.user_management'))
                        
                        # Validate account/team permissions
                        if current_user.role == 'account_admin' and new_account_id != current_user.account_id:
                            flash('You can only assign users to your own account.')
                            return redirect(url_for('user_mgmt.user_management'))
                        elif current_user.role == 'team_admin' and (new_account_id != current_user.account_id or new_team_id != current_user.team_id):
                            flash('You can only assign users to your own account and team.')
                            return redirect(url_for('user_mgmt.user_management'))
                        
                        # Update user fields
                        user.username = new_username
                        if new_email:
                            user.email = new_email
                        user.role = new_role
                        user.account_id = new_account_id
                        
                        # Handle team assignment properly through UserTeamMembership
                        if new_team_id and new_team_id != user.team_id:
                            # Get the team to validate account
                            team = Team.query.get(new_team_id)
                            if team and team.account_id == new_account_id:
                                # Check if user already has membership to this team
                                existing_membership = UserTeamMembership.query.filter_by(
                                    user_id=user.id,
                                    team_id=new_team_id,
                                    account_id=new_account_id
                                ).first()
                                
                                if existing_membership:
                                    # Reactivate existing membership and make it primary
                                    existing_membership.is_active = True
                                    existing_membership.is_primary = True
                                    # Remove primary from other teams in same account
                                    UserTeamMembership.query.filter_by(
                                        user_id=user.id,
                                        account_id=new_account_id,
                                        is_primary=True
                                    ).filter(UserTeamMembership.id != existing_membership.id).update({'is_primary': False})
                                else:
                                    # Create new team membership
                                    user.add_team_membership(
                                        team_id=new_team_id,
                                        account_id=new_account_id,
                                        is_primary=True,
                                        role='member',
                                        added_by=current_user
                                    )
                                
                                # Update user's primary team_id (for backward compatibility)
                                user.team_id = new_team_id
                            else:
                                flash('Invalid team selection for the specified account.')
                                return redirect(url_for('user_mgmt.user_management'))
                        elif new_team_id is None:
                            # If no team selected, keep existing primary team
                            pass
                        else:
                            # Update team_id for backward compatibility
                            user.team_id = new_team_id
                        
                        user.first_name = new_first_name if new_first_name else None
                        user.last_name = new_last_name if new_last_name else None
                        
                        # Update password if provided
                        if new_password:
                            user.password = generate_password_hash(new_password)
                        
                        db.session.commit()
                        print(f"[DEBUG] After update - User: id={user.id}, username={user.username}, team_id={user.team_id}, account_id={user.account_id}")
                        log_action('Edit User', f'User ID: {user_id}, Username: {new_username}, Role: {new_role}, Account: {new_account_id}, Team: {new_team_id}')
                        flash('User updated successfully.')
                        print(f"[SUCCESS] User updated: {user}")
                        
                    except Exception as e:
                        db.session.rollback()
                        print(f"[ERROR] Failed to update user: {e}")
                        flash('Failed to update user.')
                else:
                    flash('You do not have permission to edit this user.')
            else:
                flash('User not found.')
            
            return redirect(url_for('user_mgmt.user_management'))
        
        elif action == 'add':
            username = request.form.get('username')
            password = request.form.get('password')
            email = request.form.get('email')
            role = request.form.get('role')
            account_id = request.form.get('account_id', type=int)
            team_id = request.form.get('team_id', type=int)
            first_name = request.form.get('first_name', '').strip()
            last_name = request.form.get('last_name', '').strip()
            debug_msgs = []
            debug_msgs.append(f"[DEBUG] Add User: username={username}, email={email}, role={role}, account_id={account_id}, team_id={team_id}, first_name={first_name}, last_name={last_name}")
            try:
                if username and password and email and role and account_id:
                    existing_user = User.query.filter_by(username=username).first()
                    existing_email = User.query.filter_by(email=email).first()
                    debug_msgs.append(f"[DEBUG] Existing user: {existing_user}")
                    debug_msgs.append(f"[DEBUG] Existing email: {existing_email}")
                    if existing_user:
                        flash('Username already exists.')
                        debug_msgs.append("[ERROR] Username already exists.")
                        for msg in debug_msgs:
                            print(msg)
                        return redirect(url_for('user_mgmt.user_management'))
                    elif existing_email:
                        flash('Email already exists.')
                        debug_msgs.append("[ERROR] Email already exists.")
                        for msg in debug_msgs:
                            print(msg)
                        return redirect(url_for('user_mgmt.user_management'))
                    else:
                        # Only allow adding within scope
                        if current_user.role == 'super_admin' or \
                           (current_user.role == 'account_admin' and account_id == current_user.account_id) or \
                           (current_user.role == 'team_admin' and account_id == current_user.account_id and team_id == current_user.team_id):
                            user = User(
                                username=username, 
                                email=email,
                                password=generate_password_hash(password), 
                                role=role, 
                                account_id=account_id, 
                                team_id=team_id if team_id else None, 
                                status='active', 
                                is_active=True,
                                first_name=first_name if first_name else None,
                                last_name=last_name if last_name else None
                            )
                            db.session.add(user)
                            db.session.flush()  # Get the user ID
                            debug_msgs.append(f"[DEBUG] User (before commit): id={user.id}, username={user.username}, email={user.email}")
                            
                            # Create team membership if team is assigned
                            if team_id:
                                user.add_team_membership(
                                    team_id=team_id,
                                    account_id=account_id,
                                    is_primary=True,
                                    role='member',
                                    added_by=current_user
                                )
                                debug_msgs.append(f"[DEBUG] Created team membership: user_id={user.id}, team_id={team_id}")
                            
                            db.session.commit()
                            log_action('Add User', f'User: {username}, Email: {email}, Role: {role}, Account: {account_id}, Team: {team_id}')
                            debug_msgs.append(f"[DEBUG] User created: {user}")
                            flash('User added successfully.')
                            # Log debug messages for successful creation
                            for msg in debug_msgs:
                                print(msg)
                            return redirect(url_for('user_mgmt.user_management'))
                        else:
                            flash('You do not have permission to add user to this account/team.')
                            debug_msgs.append("[ERROR] Permission denied for user add.")
                            for msg in debug_msgs:
                                print(msg)
                            return redirect(url_for('user_mgmt.user_management'))
                else:
                    flash('Username, password, email, role, and account are required.')
                    debug_msgs.append("[ERROR] Missing required fields for user add.")
                    for msg in debug_msgs:
                        print(msg)
                    return redirect(url_for('user_mgmt.user_management'))
            except Exception as e:
                db.session.rollback()
                debug_msgs.append(f"[ERROR] Exception: {e}")
                flash('Failed to add user.')
                print(f"[ERROR] User creation failed: {e}")
            finally:
                # Log debug messages instead of flashing them to avoid UI issues
                for msg in debug_msgs:
                    print(msg)
        elif action == 'delete':
            user_id = request.form.get('user_id', type=int)
            user = User.query.get(user_id)
            print(f"[DELETE] Attempting to soft delete user_id={user_id}, found={user}")
            if user and user.username != 'admin':
                # Only allow deleting within scope
                if current_user.role == 'super_admin' or \
                   (current_user.role == 'account_admin' and user.account_id == current_user.account_id) or \
                   (current_user.role == 'team_admin' and user.account_id == current_user.account_id and user.team_id == current_user.team_id):
                    user.status = 'deleted'
                    user.is_active = False
                    db.session.commit()
                    log_action('Delete User', f'User ID: {user_id}, Username: {getattr(user, "username", None)}')
                    print(f"[DELETE] User soft deleted: {user}")
                    flash('User deleted successfully.')
                else:
                    print(f"[DELETE] Permission denied for user_id={user_id}")
                    flash('You do not have permission to delete this user.')
            else:
                print(f"[DELETE] Cannot delete user_id={user_id}, user={user}")
                flash('Cannot delete this user.')
            return redirect(url_for('user_mgmt.user_management'))
        elif action == 'delete_team':
            team_id = request.form.get('team_id', type=int)
            team = Team.query.get(team_id)
            if team:
                if current_user.role == 'super_admin' or (current_user.role == 'account_admin' and team.account_id == current_user.account_id):
                    team.status = 'deleted'
                    team.is_active = False
                    db.session.commit()
                    log_action('Delete Team', f'Team ID: {team_id}, Name: {getattr(team, "name", None)}')
                    flash('Team deleted successfully.')
                else:
                    flash('You do not have permission to delete this team.')
            else:
                flash('Team not found.')
            return redirect(url_for('user_mgmt.user_management'))
        elif action == 'delete_account':
            account_id = request.form.get('account_id', type=int)
            account = Account.query.get(account_id)
            if account:
                if current_user.role == 'super_admin':
                    account.status = 'deleted'
                    account.is_active = False
                    db.session.commit()
                    log_action('Delete Account', f'Account ID: {account_id}, Name: {getattr(account, "name", None)}')
                    flash('Account deleted successfully.')
                else:
                    flash('You do not have permission to delete this account.')
            else:
                flash('Account not found.')
            return redirect(url_for('user_mgmt.user_management'))
        elif action == 'update':
            user_id = request.form.get('user_id', type=int)
            role = request.form.get('role')
            user = User.query.get(user_id)
            if user:
                # Only allow updating within scope
                if current_user.role == 'super_admin':
                    users = User.query.filter(User.status.in_(user_filter)).all()
                    accounts = Account.query.all()
                    teams = Team.query.all()
                elif current_user.role == 'account_admin':
                    users = User.query.filter(User.account_id==current_user.account_id, User.status.in_(user_filter)).all()
                    acc = Account.query.get(current_user.account_id)
                    accounts = [acc] if acc else []
                    teams = Team.query.filter_by(account_id=current_user.account_id).all()
                elif current_user.role == 'team_admin':
                    users = User.query.filter(User.account_id==current_user.account_id, User.team_id==current_user.team_id, User.status.in_(user_filter)).all()
                    acc = Account.query.get(current_user.account_id)
                    accounts = [acc] if acc else []
                    t = Team.query.get(current_user.team_id)
                    teams = [t] if t else []
        
        # Handle multiple team management actions
        elif action == 'add_user_to_team':
            if current_user.role not in ['super_admin', 'account_admin']:
                flash('You do not have permission to manage team memberships.')
                return redirect(url_for('user_mgmt.user_management'))
            
            user_id = request.form.get('user_id', type=int)
            team_id = request.form.get('new_team_id', type=int)
            role = request.form.get('team_role', 'member')
            is_primary = request.form.get('is_primary') == 'on'
            
            user = User.query.get(user_id)
            team = Team.query.get(team_id)
            
            if user and team:
                try:
                    membership = user.add_team_membership(
                        team_id=team_id,
                        account_id=team.account_id,
                        is_primary=is_primary,
                        role=role,
                        added_by=current_user
                    )
                    db.session.commit()
                    
                    primary_text = " as primary team" if is_primary else ""
                    flash(f'Successfully added {user.username} to {team.name}{primary_text}.')
                    log_action('Add User to Team', f'User: {user.username}, Team: {team.name}, Role: {role}, Primary: {is_primary}')
                    
                except Exception as e:
                    db.session.rollback()
                    flash(f'Error adding user to team: {str(e)}')
            else:
                flash('Invalid user or team selection.')
            
            return redirect(url_for('user_mgmt.user_management'))
        
        elif action == 'remove_user_from_team':
            if current_user.role not in ['super_admin', 'account_admin']:
                flash('You do not have permission to manage team memberships.')
                return redirect(url_for('user_mgmt.user_management'))
            
            user_id = request.form.get('user_id', type=int)
            team_id = request.form.get('team_id', type=int)
            
            user = User.query.get(user_id)
            team = Team.query.get(team_id)
            
            if user and team:
                try:
                    success = user.remove_team_membership(team_id, team.account_id)
                    if success:
                        db.session.commit()
                        flash(f'Successfully removed {user.username} from {team.name}.')
                        log_action('Remove User from Team', f'User: {user.username}, Team: {team.name}')
                    else:
                        flash(f'{user.username} is not a member of {team.name}.')
                        
                except Exception as e:
                    db.session.rollback()
                    flash(f'Error removing user from team: {str(e)}')
            else:
                flash('Invalid user or team selection.')
            
            return redirect(url_for('user_mgmt.user_management'))
        
        elif action == 'set_primary_team':
            if current_user.role != 'super_admin':
                flash('Only super admins can manage primary team assignments.')
                return redirect(url_for('user_mgmt.user_management'))
            
            user_id = request.form.get('user_id', type=int)
            team_id = request.form.get('team_id', type=int)
            
            user = User.query.get(user_id)
            team = Team.query.get(team_id)
            
            if user and team:
                try:
                    # Check if user is member of this team
                    membership = UserTeamMembership.query.filter_by(
                        user_id=user_id,
                        team_id=team_id,
                        account_id=team.account_id,
                        is_active=True
                    ).first()
                    
                    if membership:
                        # Remove primary from other teams in same account
                        UserTeamMembership.query.filter_by(
                            user_id=user_id,
                            account_id=team.account_id,
                            is_primary=True
                        ).update({'is_primary': False})
                        
                        # Set this team as primary
                        membership.is_primary = True
                        user.team_id = team_id  # Update user's primary team reference
                        
                        db.session.commit()
                        flash(f'Successfully set {team.name} as primary team for {user.username}.')
                        log_action('Set Primary Team', f'User: {user.username}, Team: {team.name}')
                        
                    else:
                        flash(f'{user.username} is not a member of {team.name}.')
                        
                except Exception as e:
                    db.session.rollback()
                    flash(f'Error setting primary team: {str(e)}')
            else:
                flash('Invalid user or team selection.')
            
            return redirect(url_for('user_mgmt.user_management'))
    
    # Enhanced user data with team memberships for display
    users_with_teams = []
    for user in users:
        # Use direct UserTeamMembership query instead of problematic user.get_teams()
        team_memberships = UserTeamMembership.query.filter_by(
            user_id=user.id, 
            is_active=True
        ).all()
        
        # Build display string manually since all_teams_display might also be broken
        teams_display_list = []
        for membership in team_memberships:
            team = db.session.get(Team, membership.team_id)
            if team:
                team_str = team.name
                if membership.is_primary:
                    team_str += " (Primary)"
                teams_display_list.append(team_str)
        
        teams_display = "; ".join(teams_display_list) if teams_display_list else "No Teams"
        
        user_data = {
            'user': user,
            'team_memberships': team_memberships,
            'all_teams_display': teams_display
        }
        users_with_teams.append(user_data)
    
    return render_template('user_management.html', 
                         users=users,
                         users_with_teams=users_with_teams, 
                         accounts=accounts, 
                         teams=teams,
                         current_engineers=[],
                         next_shift_engineers=[])
