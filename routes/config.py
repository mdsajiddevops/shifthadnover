from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models.app_config import AppConfig
from models.models import db, Account, Team
from models.team_feature_config import TeamFeatureConfig
from services.audit_service import log_action
import logging

logger = logging.getLogger(__name__)

config_bp = Blueprint('config', __name__)

@config_bp.route('/admin/configuration', methods=['GET', 'POST'])
@login_required
def admin_configuration():
    """Admin configuration page for super admins only"""
    if current_user.role != 'super_admin':
        flash('Access denied. Super admin privileges required.', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    if request.method == 'POST':
        # Handle configuration updates
        config_updates = []
        
        # Define all possible configuration keys that should be processed
        all_config_keys = [
            # Navigation Tabs
            'tab_kb_articles',
            'tab_vendor_details',
            'tab_applications',
            'tab_change_management',
            'tab_problem_tickets',
            'tab_post_mortems',
            'tab_shift_management',
            # Super Admin Only Tabs
            'tab_manual_roster',
            'tab_incident_response_logs',
            'tab_active_sessions',
            'tab_user_team_linking',
            'tab_email_monitoring',
            # System Features
            'feature_servicenow_integration',
            'feature_ctask_assignment',
        ]
        
        # Process each configuration key - this ensures unchecked boxes are set to 'false'
        for key in all_config_keys:
            # Check if the checkbox was checked (present in form) or unchecked (not present)
            value = 'true' if request.form.get(key) == 'on' else 'false'
            AppConfig.set_config(key, value)
            config_updates.append(f"{key}: {value}")
            log_action('Update Configuration', f'Updated {key} to {value}')
        
        if config_updates:
            flash(f'Configuration updated successfully. {len(config_updates)} settings processed.', 'success')
        else:
            flash('No configuration changes made.', 'info')
        
        # Stay on configuration page instead of redirecting to dashboard
        return redirect(url_for('config.admin_configuration'))
    
    # Get all configurations
    all_configs = AppConfig.query.filter(
        db.or_(
            AppConfig.config_key.like('tab_%'),
            AppConfig.config_key.like('feature_%')
        )
    ).all()
    
    # Organize configs by category
    configs_by_category = {}
    for config in all_configs:
        category = config.category
        if category not in configs_by_category:
            configs_by_category[category] = []
        configs_by_category[category].append(config)
    
    return render_template('admin/configuration.html', 
                         configs_by_category=configs_by_category,
                         all_configs=all_configs)

@config_bp.route('/api/config/<config_key>')
@login_required
def get_config_api(config_key):
    """API endpoint to get configuration value"""
    if current_user.role != 'super_admin':
        return jsonify({'error': 'Access denied'}), 403
    
    value = AppConfig.get_config(config_key)
    return jsonify({'key': config_key, 'value': value})

@config_bp.route('/api/config/<config_key>', methods=['POST'])
@login_required
def set_config_api(config_key):
    """API endpoint to set configuration value"""
    if current_user.role != 'super_admin':
        return jsonify({'error': 'Access denied'}), 403
    
    data = request.get_json()
    value = data.get('value', 'false')
    description = data.get('description')
    
    AppConfig.set_config(config_key, value, description)
    log_action('Update Configuration via API', f'Updated {config_key} to {value}')
    
    return jsonify({'success': True, 'key': config_key, 'value': value})

@config_bp.route('/api/servicenow/save-configuration', methods=['POST'])
@login_required
def save_servicenow_configuration():
    """API endpoint to save ServiceNow configuration"""
    if current_user.role != 'super_admin':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        from models.servicenow_config import ServiceNowConfig
        
        # Get form data
        instance_url = request.form.get('instance_url', '').strip()
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        assignment_groups = request.form.get('assignment_groups', '').strip()
        timeout = request.form.get('timeout', '30')
        auto_fetch_incidents = request.form.get('auto_fetch_incidents', 'false')
        auto_assign_ctasks = request.form.get('auto_assign_ctasks', 'false')
        
        # Validate required fields
        if not instance_url:
            return jsonify({'error': 'Instance URL is required'}), 400
        if not username:
            return jsonify({'error': 'Username is required'}), 400
        if not password:
            return jsonify({'error': 'Password is required'}), 400
        
        # Validate timeout
        try:
            timeout_int = int(timeout)
            if timeout_int < 10 or timeout_int > 120:
                return jsonify({'error': 'Timeout must be between 10 and 120 seconds'}), 400
        except ValueError:
            return jsonify({'error': 'Invalid timeout value'}), 400
        
        # Save configuration values
        ServiceNowConfig.set_config('instance_url', instance_url, 'ServiceNow instance URL')
        ServiceNowConfig.set_config('username', username, 'ServiceNow API username')
        ServiceNowConfig.set_config('password', password, 'ServiceNow API password', encrypted=True)
        ServiceNowConfig.set_config('assignment_groups', assignment_groups, 'Comma-separated assignment groups')
        ServiceNowConfig.set_config('timeout', str(timeout_int), 'API request timeout in seconds')
        ServiceNowConfig.set_config('auto_fetch_incidents', auto_fetch_incidents, 'Auto-fetch incidents for handover')
        ServiceNowConfig.set_config('auto_assign_ctasks', auto_assign_ctasks, 'Auto-assign CTasks to engineers')
        
        log_action('Update ServiceNow Configuration', f'Updated ServiceNow settings for instance: {instance_url}')
        
        return jsonify({
            'success': True,
            'message': 'ServiceNow configuration saved successfully'
        })
        
    except Exception as e:
        log_action('ServiceNow Configuration Error', f'Failed to save configuration: {str(e)}')
        return jsonify({'error': f'Failed to save configuration: {str(e)}'}), 500

@config_bp.route('/api/servicenow/test-connection-new', methods=['POST'])
@login_required
def test_servicenow_connection_new():
    """API endpoint to test ServiceNow connection with provided credentials"""
    if current_user.role != 'super_admin':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        # Get form data
        instance_url = request.form.get('instance_url', '').strip()
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        timeout = request.form.get('timeout', '30')
        
        # Validate inputs
        if not instance_url:
            return jsonify({'error': 'Instance URL is required'}), 400
        if not username:
            return jsonify({'error': 'Username is required'}), 400
        if not password:
            return jsonify({'error': 'Password is required'}), 400
        
        # Validate timeout
        try:
            timeout_int = int(timeout)
            if timeout_int < 10 or timeout_int > 120:
                timeout_int = 30
        except ValueError:
            timeout_int = 30
        
        # Ensure proper URL format
        if not instance_url.startswith('https://') and not instance_url.startswith('http://'):
            instance_url = f"https://{instance_url}"
        
        # Test connection using requests directly
        import requests
        from urllib.parse import urljoin
        
        session = requests.Session()
        session.auth = (username, password)
        session.headers.update({
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
        
        # Test with a simple API call
        test_url = urljoin(instance_url, "/api/now/table/incident")
        params = {
            'sysparm_limit': 1,
            'sysparm_fields': 'sys_id,number'
        }
        
        response = session.get(test_url, params=params, timeout=timeout_int)
        
        if response.status_code == 200:
            log_action('ServiceNow Connection Test', f'Success for {instance_url}')
            return jsonify({
                'success': True,
                'message': f'Connection successful to {instance_url}',
                'status_code': response.status_code
            })
        elif response.status_code == 401:
            log_action('ServiceNow Connection Test', f'Authentication failed for {instance_url}')
            return jsonify({
                'success': False,
                'error': 'Authentication failed - check username and password'
            }), 401
        else:
            log_action('ServiceNow Connection Test', f'Failed with status {response.status_code} for {instance_url}')
            return jsonify({
                'success': False,
                'error': f'Connection failed with status {response.status_code}'
            }), 400
            
    except requests.exceptions.Timeout:
        return jsonify({
            'success': False,
            'error': 'Connection timeout - check instance URL and network connectivity'
        }), 408
    except requests.exceptions.ConnectionError:
        return jsonify({
            'success': False,
            'error': 'Connection error - check instance URL and network connectivity'
        }), 503
    except Exception as e:
        log_action('ServiceNow Connection Test Error', f'Error: {str(e)}')
        return jsonify({
            'success': False,
            'error': f'Test failed: {str(e)}'
        }), 500

@config_bp.route('/api/servicenow/clear-configuration', methods=['POST'])
@login_required
def clear_servicenow_configuration():
    """API endpoint to clear ServiceNow configuration"""
    if current_user.role != 'super_admin':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        from models.servicenow_config import ServiceNowConfig
        
        # Clear all ServiceNow configuration
        config_keys = [
            'instance_url', 'username', 'password', 'assignment_groups', 
            'timeout', 'auto_fetch_incidents', 'auto_assign_ctasks'
        ]
        
        for key in config_keys:
            ServiceNowConfig.set_config(key, '', f'Cleared {key}')
        
        log_action('Clear ServiceNow Configuration', 'All ServiceNow settings cleared')
        
        return jsonify({
            'success': True,
            'message': 'ServiceNow configuration cleared successfully'
        })
        
    except Exception as e:
        log_action('ServiceNow Configuration Clear Error', f'Error: {str(e)}')
        return jsonify({'error': f'Failed to clear configuration: {str(e)}'}), 500

# ============================================================================
# Team/Account Feature Management Routes
# ============================================================================

@config_bp.route('/admin/feature-management')
@login_required
def feature_management():
    """Main feature management page for superadmin to control tabs per team/account"""
    if current_user.role != 'super_admin':
        flash('Access denied. Super admin privileges required.', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    try:
        # Get all accounts and teams
        accounts = Account.query.filter_by(is_active=True).order_by(Account.name).all()
        teams_by_account = {}
        
        for account in accounts:
            teams_by_account[account.id] = Team.query.filter_by(
                account_id=account.id, 
                is_active=True
            ).order_by(Team.name).all()
        
        # Get all available features
        available_features = TeamFeatureConfig.get_all_available_features()
        
        # Convert teams_by_account dict to a format that can be serialized to JSON
        # teams_by_account is already a dict with account_id as key and list of Team objects as value
        # We need to convert Team objects to dicts
        teams_by_account_dict = {}
        for account_id, teams_list in teams_by_account.items():
            teams_by_account_dict[account_id] = [
                {
                    'id': team.id,
                    'name': team.name,
                    'account_id': team.account_id,
                    'is_active': team.is_active
                }
                for team in teams_list
            ]
        
        # Convert accounts to list of dicts
        accounts_list = [
            {
                'id': acc.id,
                'name': acc.name,
                'is_active': acc.is_active
            }
            for acc in accounts
        ]
        
        return render_template('admin/feature_management.html',
                             accounts=accounts_list,
                             teams_by_account=teams_by_account_dict,
                             available_features=available_features)
    
    except Exception as e:
        logger.error(f"Error loading feature management page: {e}", exc_info=True)
        flash(f'Error loading feature management: {str(e)}', 'danger')
        return redirect(url_for('dashboard.dashboard'))

@config_bp.route('/api/feature-management/accounts')
@login_required
def api_get_accounts():
    """API endpoint to get all accounts for feature management"""
    if current_user.role != 'super_admin':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        accounts = Account.query.filter_by(is_active=True).order_by(Account.name).all()
        accounts_data = [{
            'id': acc.id,
            'name': acc.name,
            'is_active': acc.is_active
        } for acc in accounts]
        
        return jsonify({'success': True, 'accounts': accounts_data})
    
    except Exception as e:
        logger.error(f"Error getting accounts: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@config_bp.route('/api/feature-management/accounts/<int:account_id>/teams')
@login_required
def api_get_teams_by_account(account_id):
    """API endpoint to get teams for a specific account"""
    if current_user.role != 'super_admin':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        teams = Team.query.filter_by(account_id=account_id, is_active=True).order_by(Team.name).all()
        teams_data = [{
            'id': team.id,
            'name': team.name,
            'account_id': team.account_id,
            'is_active': team.is_active
        } for team in teams]
        
        return jsonify({'success': True, 'teams': teams_data})
    
    except Exception as e:
        logger.error(f"Error getting teams: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@config_bp.route('/api/feature-management/features')
@login_required
def api_get_available_features():
    """API endpoint to get all available features"""
    if current_user.role != 'super_admin':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        features = TeamFeatureConfig.get_all_available_features()
        features_data = []
        
        # Group by category
        features_by_category = {}
        for feature_key, feature_name, category in features:
            if category not in features_by_category:
                features_by_category[category] = []
            features_by_category[category].append({
                'key': feature_key,
                'name': feature_name,
                'category': category
            })
        
        return jsonify({
            'success': True,
            'features': features_data,
            'features_by_category': features_by_category
        })
    
    except Exception as e:
        logger.error(f"Error getting features: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@config_bp.route('/api/feature-management/config', methods=['GET'])
@login_required
def api_get_feature_config():
    """API endpoint to get feature configuration for a scope"""
    if current_user.role != 'super_admin':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        scope_type = request.args.get('scope_type')  # 'account' or 'team'
        scope_id = request.args.get('scope_id', type=int)
        
        if not scope_type or not scope_id:
            return jsonify({'success': False, 'error': 'Missing scope_type or scope_id'}), 400
        
        if scope_type not in ['account', 'team']:
            return jsonify({'success': False, 'error': 'Invalid scope_type'}), 400
        
        # Get all configurations for this scope
        configs = TeamFeatureConfig.query.filter_by(
            scope_type=scope_type,
            scope_id=scope_id
        ).all()
        
        config_map = {}
        for config in configs:
            config_map[config.feature_key] = {
                'is_enabled': config.is_enabled,
                'description': config.description,
                'updated_at': config.updated_at.isoformat() if config.updated_at else None,
                'updated_by': config.updated_by
            }
        
        return jsonify({'success': True, 'configs': config_map})
    
    except Exception as e:
        logger.error(f"Error getting feature config: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@config_bp.route('/api/feature-management/config', methods=['POST'])
@login_required
def api_set_feature_config():
    """API endpoint to set feature configuration for a scope"""
    if current_user.role != 'super_admin':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        data = request.get_json()
        scope_type = data.get('scope_type')  # 'account' or 'team'
        scope_id = data.get('scope_id')
        feature_key = data.get('feature_key')
        is_enabled = data.get('is_enabled', True)
        description = data.get('description')
        
        if not all([scope_type, scope_id, feature_key]):
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        if scope_type not in ['account', 'team']:
            return jsonify({'success': False, 'error': 'Invalid scope_type'}), 400
        
        # Validate scope exists
        if scope_type == 'account':
            scope_obj = Account.query.get(scope_id)
            scope_name = scope_obj.name if scope_obj else None
        else:
            scope_obj = Team.query.get(scope_id)
            scope_name = scope_obj.name if scope_obj else None
        
        if not scope_obj:
            return jsonify({'success': False, 'error': f'{scope_type.capitalize()} not found'}), 404
        
        # Set the configuration
        config = TeamFeatureConfig.set_feature_status(
            scope_type=scope_type,
            scope_id=scope_id,
            feature_key=feature_key,
            is_enabled=is_enabled,
            description=description,
            updated_by=current_user.email
        )
        
        log_action(
            'Update Feature Configuration',
            f'Updated {feature_key} for {scope_type} "{scope_name}" to {is_enabled}'
        )
        
        return jsonify({
            'success': True,
            'message': f'Feature configuration updated successfully',
            'config': {
                'id': config.id,
                'scope_type': config.scope_type,
                'scope_id': config.scope_id,
                'feature_key': config.feature_key,
                'is_enabled': config.is_enabled
            }
        })
    
    except Exception as e:
        logger.error(f"Error setting feature config: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@config_bp.route('/api/feature-management/config/bulk', methods=['POST'])
@login_required
def api_bulk_set_feature_config():
    """API endpoint to bulk update feature configurations for a scope"""
    if current_user.role != 'super_admin':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        data = request.get_json()
        scope_type = data.get('scope_type')  # 'account' or 'team'
        scope_id = data.get('scope_id')
        feature_updates = data.get('feature_updates', {})  # {feature_key: is_enabled}
        
        if not all([scope_type, scope_id]):
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        if scope_type not in ['account', 'team']:
            return jsonify({'success': False, 'error': 'Invalid scope_type'}), 400
        
        # Validate scope exists
        if scope_type == 'account':
            scope_obj = Account.query.get(scope_id)
            scope_name = scope_obj.name if scope_obj else None
        else:
            scope_obj = Team.query.get(scope_id)
            scope_name = scope_obj.name if scope_obj else None
        
        if not scope_obj:
            return jsonify({'success': False, 'error': f'{scope_type.capitalize()} not found'}), 404
        
        # Bulk update
        TeamFeatureConfig.bulk_update_features(
            scope_type=scope_type,
            scope_id=scope_id,
            feature_updates=feature_updates,
            updated_by=current_user.email
        )
        
        log_action(
            'Bulk Update Feature Configuration',
            f'Updated {len(feature_updates)} features for {scope_type} "{scope_name}"'
        )
        
        return jsonify({
            'success': True,
            'message': f'Updated {len(feature_updates)} feature configurations successfully'
        })
    
    except Exception as e:
        logger.error(f"Error bulk setting feature config: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@config_bp.route('/api/feature-management/config/<int:config_id>', methods=['DELETE'])
@login_required
def api_delete_feature_config(config_id):
    """API endpoint to delete a feature configuration (reset to default)"""
    if current_user.role != 'super_admin':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        config = TeamFeatureConfig.query.get(config_id)
        if not config:
            return jsonify({'success': False, 'error': 'Configuration not found'}), 404
        
        scope_name = f"{config.scope_type}:{config.scope_id}"
        feature_key = config.feature_key
        
        db.session.delete(config)
        db.session.commit()
        
        log_action(
            'Delete Feature Configuration',
            f'Deleted {feature_key} configuration for {scope_name}'
        )
        
        return jsonify({
            'success': True,
            'message': 'Feature configuration deleted successfully'
        })
    
    except Exception as e:
        logger.error(f"Error deleting feature config: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500