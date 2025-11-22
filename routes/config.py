from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models.app_config import AppConfig
from models.models import db
from services.audit_service import log_action

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
            'tab_kb_articles',
            'tab_vendor_details', 
            'tab_applications',
            'tab_change_management',
            'tab_problem_tickets',
            'tab_post_mortems',
            'feature_servicenow_integration',
            'feature_ctask_assignment'
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