"""
Email Configuration Routes

API endpoints for managing team-based email configurations.
Provides CRUD operations with role-based access control.
"""

from flask import Blueprint, request, jsonify, render_template, session, redirect, url_for, flash
from flask_login import login_required, current_user
from functools import wraps
import logging

from services.email_config_service import EmailConfigService
from models.models import db, Account, Team, User
from models.email_config import TeamEmailConfig

# Create blueprint
email_config_bp = Blueprint('email_config', __name__, url_prefix='/api/email-config')
logger = logging.getLogger(__name__)

# Initialize service
email_service = EmailConfigService()

def role_required(*allowed_roles):
    """Decorator to check if user has required role."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return jsonify({'error': 'Authentication required'}), 401
            
            if current_user.role not in allowed_roles:
                return jsonify({'error': 'Insufficient permissions'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def can_access_account(account_id):
    """Check if current user can access the specified account."""
    if current_user.role == 'super_admin':
        return True
    
    if current_user.role in ['account_admin', 'team_admin']:
        return current_user.account_id == account_id
    
    return False

def can_access_team(account_id, team_id):
    """Check if current user can access the specified team."""
    if current_user.role == 'super_admin':
        return True
    
    if current_user.role == 'account_admin':
        return current_user.account_id == account_id
    
    if current_user.role == 'team_admin':
        return (current_user.account_id == account_id and 
               current_user.team_id == team_id)
    
    return False

@email_config_bp.route('/configs', methods=['GET'])
@login_required
@role_required('super_admin', 'account_admin', 'team_admin')
def get_configs():
    """Get email configurations based on user's role and permissions."""
    try:
        account_id = request.args.get('account_id', type=int)
        team_id = request.args.get('team_id', type=int)
        
        # Super admin can see all configurations
        if current_user.role == 'super_admin':
            if account_id:
                result = email_service.get_configs_for_account(account_id)
            else:
                # Get all configurations
                configs = TeamEmailConfig.query.filter_by(is_active=True).all()
                result = {
                    'success': True,
                    'data': [email_service._serialize_config(config) for config in configs]
                }
        
        # Account admin can see configurations for their account
        elif current_user.role == 'account_admin':
            target_account_id = account_id or current_user.account_id
            if not can_access_account(target_account_id):
                return jsonify({'error': 'Cannot access this account'}), 403
            
            result = email_service.get_configs_for_account(target_account_id)
        
        # Team admin can see configurations for their team
        elif current_user.role == 'team_admin':
            target_account_id = account_id or current_user.account_id
            target_team_id = team_id or current_user.team_id
            
            if not can_access_team(target_account_id, target_team_id):
                return jsonify({'error': 'Cannot access this team'}), 403
            
            config = TeamEmailConfig.get_config_for_team(target_account_id, target_team_id)
            if config:
                result = {
                    'success': True,
                    'data': [email_service._serialize_config(config)]
                }
            else:
                result = {'success': True, 'data': []}
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify({'error': result['message']}), 400
            
    except Exception as e:
        logger.error(f"Error getting email configurations: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@email_config_bp.route('/config/<int:config_id>', methods=['GET'])
@login_required
@role_required('super_admin', 'account_admin', 'team_admin')
def get_config(config_id):
    """Get a specific email configuration."""
    try:
        result = email_service.get_config(config_id)
        
        if not result['success']:
            return jsonify({'error': result['message']}), 404
        
        config_data = result['data']
        
        # Check permissions
        if not can_access_team(config_data['account_id'], config_data['team_id']):
            return jsonify({'error': 'Cannot access this configuration'}), 403
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error getting email configuration: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@email_config_bp.route('/config', methods=['POST'])
@login_required
@role_required('super_admin', 'account_admin', 'team_admin')
def create_config():
    """Create a new email configuration."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        account_id = data.get('account_id')
        team_id = data.get('team_id')
        
        if not account_id or not team_id:
            return jsonify({'error': 'account_id and team_id are required'}), 400
        
        # Check permissions
        if not can_access_team(account_id, team_id):
            return jsonify({'error': 'Cannot create configuration for this team'}), 403
        
        result = email_service.create_config(
            account_id=account_id,
            team_id=team_id,
            to_recipients=data.get('to_recipients'),
            cc_recipients=data.get('cc_recipients'),
            priority_recipients=data.get('priority_recipients'),
            is_default=data.get('is_default', False)
        )
        
        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify({'error': result['message']}), 400
            
    except Exception as e:
        logger.error(f"Error creating email configuration: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@email_config_bp.route('/config/<int:config_id>', methods=['PUT'])
@login_required
@role_required('super_admin', 'account_admin', 'team_admin')
def update_config(config_id):
    """Update an existing email configuration."""
    try:
        # First get the config to check permissions
        config = TeamEmailConfig.query.get(config_id)
        if not config or not config.is_active:
            return jsonify({'error': 'Configuration not found'}), 404
        
        # Check permissions
        if not can_access_team(config.account_id, config.team_id):
            return jsonify({'error': 'Cannot modify this configuration'}), 403
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        result = email_service.update_config(
            config_id=config_id,
            to_recipients=data.get('to_recipients'),
            cc_recipients=data.get('cc_recipients'),
            priority_recipients=data.get('priority_recipients'),
            is_default=data.get('is_default')
        )
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify({'error': result['message']}), 400
            
    except Exception as e:
        logger.error(f"Error updating email configuration: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@email_config_bp.route('/config/<int:config_id>', methods=['DELETE'])
@login_required
@role_required('super_admin', 'account_admin', 'team_admin')
def delete_config(config_id):
    """Delete (deactivate) an email configuration."""
    try:
        # First get the config to check permissions
        config = TeamEmailConfig.query.get(config_id)
        if not config or not config.is_active:
            return jsonify({'error': 'Configuration not found'}), 404
        
        # Check permissions
        if not can_access_team(config.account_id, config.team_id):
            return jsonify({'error': 'Cannot delete this configuration'}), 403
        
        result = email_service.delete_config(config_id)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify({'error': result['message']}), 400
            
    except Exception as e:
        logger.error(f"Error deleting email configuration: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@email_config_bp.route('/accounts', methods=['GET'])
@login_required
@role_required('super_admin', 'account_admin', 'team_admin')
def get_accounts():
    """Get accounts that the user can access."""
    try:
        if current_user.role == 'super_admin':
            # Only show active accounts
            accounts = Account.query.filter_by(is_active=True).order_by(Account.name).all()
        else:
            accounts = Account.query.filter_by(id=current_user.account_id, is_active=True).all()
        
        return jsonify({
            'success': True,
            'data': [{'id': acc.id, 'name': acc.name} for acc in accounts]
        })
        
    except Exception as e:
        logger.error(f"Error getting accounts: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@email_config_bp.route('/accounts/<int:account_id>/teams', methods=['GET'])
@login_required
@role_required('super_admin', 'account_admin', 'team_admin')
def get_teams_for_account(account_id):
    """Get teams for a specific account."""
    try:
        # Check permissions
        if not can_access_account(account_id):
            return jsonify({'error': 'Cannot access this account'}), 403
        
        if current_user.role == 'team_admin':
            # Team admin can only see their own team
            teams = Team.query.filter_by(
                account_id=account_id,
                id=current_user.team_id
            ).all()
        else:
            # Account admin and super admin can see all teams for the account
            teams = Team.query.filter_by(account_id=account_id).all()
        
        return jsonify({
            'success': True,
            'data': [{'id': team.id, 'name': team.name} for team in teams]
        })
        
    except Exception as e:
        logger.error(f"Error getting teams for account: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@email_config_bp.route('/recipients/<int:user_id>/<int:account_id>/<int:team_id>', methods=['GET'])
@login_required
def get_handover_recipients(user_id, account_id, team_id):
    """
    Get email recipients for handover notifications.
    This endpoint is called by the handover notification service.
    """
    try:
        is_priority = request.args.get('priority', 'false').lower() == 'true'
        
        result = email_service.get_recipients_for_handover(
            user_id=user_id,
            account_id=account_id,
            team_id=team_id,
            is_priority=is_priority
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error getting handover recipients: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Internal server error',
            'to_recipients': [],
            'cc_recipients': [],
            'priority_recipients': []
        }), 500

# Admin UI Routes (for the management interface)
@email_config_bp.route('/admin', methods=['GET'])
@login_required
@role_required('super_admin', 'account_admin', 'team_admin')
def admin_page():
    """Render the email configuration management page."""
    return render_template('admin/email_config.html')

@email_config_bp.route('/debug', methods=['GET'])
@login_required
@role_required('super_admin', 'account_admin', 'team_admin')  
def debug_page():
    """Render the debug email configuration page."""
    return render_template('admin/email_config_debug.html')

# Error handlers
@email_config_bp.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@email_config_bp.errorhandler(405)
def method_not_allowed(error):
    return jsonify({'error': 'Method not allowed'}), 405

@email_config_bp.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {str(error)}")
    return jsonify({'error': 'Internal server error'}), 500