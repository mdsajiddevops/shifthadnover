"""
Shift Time Configuration Routes
Dedicated module for managing team-specific shift timing configurations
"""

from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from functools import wraps
from datetime import datetime, time
import logging

from models.models import db, Account, Team, User
from models.team_shift_timing_config import TeamShiftTimingConfig
from services.shift_timing_service import ShiftTimingService

# Set up logger
logger = logging.getLogger(__name__)

# Create blueprint
shift_config_bp = Blueprint('shift_config', __name__, url_prefix='/admin/shift-config')

def role_required(*allowed_roles):
    """Decorator to check if user has required role for shift configuration management"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return jsonify({'success': False, 'error': 'Authentication required'}), 401
            
            user_role = getattr(current_user, 'role', None)
            if user_role not in allowed_roles:
                return jsonify({'success': False, 'error': 'Insufficient permissions'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def can_manage_shifts():
    """Check if current user can manage shift configurations"""
    if not current_user.is_authenticated:
        return False
    
    allowed_roles = ['super_admin', 'account_admin', 'team_admin']
    return getattr(current_user, 'role', None) in allowed_roles

def can_view_shifts():
    """Check if current user can view shift configurations"""
    if not current_user.is_authenticated:
        return False
    
    # All authenticated users can view shift configurations
    return True

# Main shift configuration page
@shift_config_bp.route('/')
@login_required
def shift_config_dashboard():
    """Main Shift Time Configuration dashboard"""
    try:
        if not can_view_shifts():
            return render_template('errors/403.html'), 403
        
        # Fetch fresh user data from the database to avoid stale session data
        fresh_user = User.query.get(current_user.id)
        user_role = fresh_user.role if fresh_user else getattr(current_user, 'role', None)
        user_account_id = fresh_user.account_id if fresh_user else getattr(current_user, 'account_id', None)
        
        # Get accounts and teams for dropdowns
        accounts = Account.query.filter_by(is_active=True).all()
        
        # Filter accounts based on user role
        if user_role == 'account_admin':
            # Account admins can only see their own account
            if user_account_id:
                accounts = [acc for acc in accounts if acc.id == user_account_id]
        elif user_role == 'team_admin':
            # Team admins can only see their team's account
            if user_account_id:
                accounts = [acc for acc in accounts if acc.id == user_account_id]
        
        return render_template('admin/shift_config.html', 
                             user=current_user,
                             accounts=accounts,
                             can_manage=can_manage_shifts(),
                             can_view=can_view_shifts())
        
    except Exception as e:
        logger.error(f"Error in shift config dashboard: {e}", exc_info=True)
        return render_template('errors/500.html'), 500

# API Routes
@shift_config_bp.route('/api/accounts')
@login_required
def get_accounts():
    """Get accounts based on user role"""
    try:
        if not can_view_shifts():
            return jsonify({'success': False, 'error': 'Insufficient permissions'}), 403
        
        accounts = Account.query.filter_by(is_active=True).all()
        
        # Fetch fresh user data from the database to avoid stale session data
        fresh_user = User.query.get(current_user.id)
        user_role = fresh_user.role if fresh_user else getattr(current_user, 'role', None)
        user_account_id = fresh_user.account_id if fresh_user else getattr(current_user, 'account_id', None)
        
        # Filter based on user role
        if user_role == 'account_admin' or user_role == 'team_admin':
            if user_account_id:
                accounts = [acc for acc in accounts if acc.id == user_account_id]
        
        accounts_data = [
            {
                'id': acc.id,
                'name': acc.name,
                'is_active': acc.is_active
            }
            for acc in accounts
        ]
        
        return jsonify({
            'success': True,
            'accounts': accounts_data
        })
        
    except Exception as e:
        logger.error(f"Error getting accounts: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@shift_config_bp.route('/api/accounts/<int:account_id>/teams')
@login_required
def get_teams_by_account(account_id):
    """Get teams for a specific account"""
    try:
        if not can_view_shifts():
            return jsonify({'success': False, 'error': 'Insufficient permissions'}), 403
        
        # Fetch fresh user data from the database to avoid stale session data
        fresh_user = User.query.get(current_user.id)
        user_role = fresh_user.role if fresh_user else getattr(current_user, 'role', None)
        user_account_id = fresh_user.account_id if fresh_user else getattr(current_user, 'account_id', None)
        user_team_id = fresh_user.team_id if fresh_user else getattr(current_user, 'team_id', None)
        
        logger.info(f"[SHIFT CONFIG] User {current_user.email}: session team_id={getattr(current_user, 'team_id', None)}, fresh team_id={user_team_id}")
        
        # Check if user has access to this account
        if user_role in ['account_admin', 'team_admin']:
            if user_account_id and user_account_id != account_id:
                return jsonify({'success': False, 'error': 'Access denied to this account'}), 403
        
        teams = Team.query.filter_by(account_id=account_id, is_active=True).all()
        
        # If team admin, filter to their specific team
        if user_role == 'team_admin':
            if user_team_id:
                teams = [team for team in teams if team.id == user_team_id]
        
        teams_data = [
            {
                'id': team.id,
                'name': team.name,
                'is_active': team.is_active
            }
            for team in teams
        ]
        
        return jsonify({
            'success': True,
            'teams': teams_data
        })
        
    except Exception as e:
        logger.error(f"Error getting teams: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@shift_config_bp.route('/api/shifts/<int:account_id>/<int:team_id>')
@login_required
def get_shift_configurations(account_id, team_id):
    """Get shift configurations for account and team"""
    try:
        if not can_view_shifts():
            return jsonify({'success': False, 'error': 'Insufficient permissions'}), 403
        
        # Validate access permissions
        user_role = getattr(current_user, 'role', None)
        if user_role in ['account_admin', 'team_admin']:
            user_account_id = getattr(current_user, 'account_id', None)
            if user_account_id and user_account_id != account_id:
                return jsonify({'success': False, 'error': 'Access denied to this account'}), 403
        
        if user_role == 'team_admin':
            user_team_id = getattr(current_user, 'team_id', None)
            if user_team_id and user_team_id != team_id:
                return jsonify({'success': False, 'error': 'Access denied to this team'}), 403
        
        # Get shift configurations
        service = ShiftTimingService()
        result = service.get_team_configurations(account_id, team_id)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error getting shift configurations: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@shift_config_bp.route('/api/shifts', methods=['POST'])
@login_required
@role_required('super_admin', 'account_admin', 'team_admin')
def create_shift_configuration():
    """Create a new shift configuration"""
    try:
        data = request.get_json()
        logger.info(f"Creating shift configuration with data: {data}")
        
        if not data:
            return jsonify({'success': False, 'error': 'No JSON data received'}), 400
        
        # Validate required fields
        required_fields = ['account_id', 'team_id', 'shift_code', 'shift_name', 'start_time', 'end_time']
        for field in required_fields:
            if field not in data:
                logger.error(f'Missing required field: {field}. Received data: {data}')
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
        
        # Validate access permissions
        user_role = getattr(current_user, 'role', None)
        if user_role in ['account_admin', 'team_admin']:
            user_account_id = getattr(current_user, 'account_id', None)
            if user_account_id and user_account_id != data['account_id']:
                return jsonify({'success': False, 'error': 'Access denied to this account'}), 403
        
        if user_role == 'team_admin':
            user_team_id = getattr(current_user, 'team_id', None)
            if user_team_id and user_team_id != data['team_id']:
                return jsonify({'success': False, 'error': 'Access denied to this team'}), 403
        
        # Create configuration
        service = ShiftTimingService()
        result = service.create_configuration(data, current_user.username)
        
        return jsonify(result), 201 if result['success'] else 400
        
    except Exception as e:
        logger.error(f"Error creating shift configuration: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@shift_config_bp.route('/api/shifts/<int:config_id>', methods=['PUT'])
@login_required
@role_required('super_admin', 'account_admin', 'team_admin')
def update_shift_configuration(config_id):
    """Update an existing shift configuration"""
    try:
        data = request.get_json()
        
        # Get existing configuration to validate access
        config = TeamShiftTimingConfig.query.get(config_id)
        if not config:
            return jsonify({'success': False, 'error': 'Configuration not found'}), 404
        
        # Validate access permissions
        user_role = getattr(current_user, 'role', None)
        if user_role in ['account_admin', 'team_admin']:
            user_account_id = getattr(current_user, 'account_id', None)
            if user_account_id and user_account_id != config.account_id:
                return jsonify({'success': False, 'error': 'Access denied to this account'}), 403
        
        if user_role == 'team_admin':
            user_team_id = getattr(current_user, 'team_id', None)
            if user_team_id and user_team_id != config.team_id:
                return jsonify({'success': False, 'error': 'Access denied to this team'}), 403
        
        # Update configuration
        service = ShiftTimingService()
        result = service.update_configuration(config_id, data, current_user.username)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error updating shift configuration: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@shift_config_bp.route('/api/shifts/<int:config_id>', methods=['DELETE'])
@login_required
@role_required('super_admin', 'account_admin', 'team_admin')
def delete_shift_configuration(config_id):
    """Delete a shift configuration"""
    try:
        # Get existing configuration to validate access
        config = TeamShiftTimingConfig.query.get(config_id)
        if not config:
            return jsonify({'success': False, 'error': 'Configuration not found'}), 404
        
        # Validate access permissions
        user_role = getattr(current_user, 'role', None)
        if user_role in ['account_admin', 'team_admin']:
            user_account_id = getattr(current_user, 'account_id', None)
            if user_account_id and user_account_id != config.account_id:
                return jsonify({'success': False, 'error': 'Access denied to this account'}), 403
        
        if user_role == 'team_admin':
            user_team_id = getattr(current_user, 'team_id', None)
            if user_team_id and user_team_id != config.team_id:
                return jsonify({'success': False, 'error': 'Access denied to this team'}), 403
        
        # Delete configuration
        service = ShiftTimingService()
        result = service.delete_configuration(config_id, current_user.username)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error deleting shift configuration: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@shift_config_bp.route('/api/shifts/create-defaults', methods=['POST'])
@login_required
@role_required('super_admin', 'account_admin', 'team_admin')
def create_default_shifts():
    """Create default shift patterns for a team"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if 'account_id' not in data or 'team_id' not in data:
            return jsonify({'success': False, 'error': 'Missing account_id or team_id'}), 400
        
        # Validate access permissions
        user_role = getattr(current_user, 'role', None)
        if user_role in ['account_admin', 'team_admin']:
            user_account_id = getattr(current_user, 'account_id', None)
            if user_account_id and user_account_id != data['account_id']:
                return jsonify({'success': False, 'error': 'Access denied to this account'}), 403
        
        if user_role == 'team_admin':
            user_team_id = getattr(current_user, 'team_id', None)
            if user_team_id and user_team_id != data['team_id']:
                return jsonify({'success': False, 'error': 'Access denied to this team'}), 403
        
        # Create default configurations
        service = ShiftTimingService()
        pattern = data.get('pattern', 'standard')
        result = service.create_default_configurations(data['account_id'], data['team_id'], pattern, current_user.username)
        
        return jsonify(result), 201 if result['success'] else 400
        
    except Exception as e:
        logger.error(f"Error creating default shifts: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500