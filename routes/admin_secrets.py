"""
Admin routes for secure secrets management
Only accessible by superadmin users
"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, current_app, make_response
from flask_login import login_required, current_user
from functools import wraps
from datetime import datetime
import logging
import os
from sqlalchemy import text

from models.secrets_manager import secrets_manager, SecretCategory, SecretStore, SecretAuditLog, init_secrets_manager
from models.models import db
from models.smtp_config import SMTPConfig
from models.servicenow_config import ServiceNowConfig

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        if not hasattr(current_user, 'role') or current_user.role not in ['super_admin', 'account_admin']:
            return jsonify({'success': False, 'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated

admin_secrets_bp = Blueprint('admin_secrets', __name__, url_prefix='/admin/secrets')
logger = logging.getLogger(__name__)

def get_secrets_manager():
    """Get the secrets manager instance from app context or initialize it."""
    # Try to get from app context first
    if hasattr(current_app, 'secrets_manager') and current_app.secrets_manager is not None:
        logger.info("Using existing secrets manager from app context")
        return current_app.secrets_manager
    
    # If not in app context, try to initialize
    try:
        from models.secrets_manager import HybridSecretsManager
        
        # Try multiple ways to get the master key
        master_key = os.environ.get('SECRETS_MASTER_KEY')
        
        # If not in environment, try to load from .env file directly
        if not master_key:
            logger.warning("SECRETS_MASTER_KEY not found in environment, attempting to load from .env file")
            from dotenv import load_dotenv
            load_dotenv(override=True)
            master_key = os.environ.get('SECRETS_MASTER_KEY')
        
        # If still not found, try config
        if not master_key:
            try:
                from config import SecureConfigManager
                master_key = SecureConfigManager.get_secret('SECRETS_MASTER_KEY')
                logger.info("Got master key from SecureConfigManager")
            except Exception as config_e:
                logger.warning(f"Could not get master key from config: {config_e}")
        
        if not master_key:
            logger.error("SECRETS_MASTER_KEY not available from any source. Available env vars: %s", 
                        [k for k in os.environ.keys() if 'SECRET' in k.upper()])
            return None
            
        if not db.session:
            logger.error("Database session not available")
            return None
            
        logger.info("Initializing secrets manager for admin route...")
        secrets_manager = HybridSecretsManager(db.session, master_key)
        
        # Store in app context for future use
        current_app.secrets_manager = secrets_manager
        logger.info("✅ Secrets manager initialized successfully for admin routes")
        return secrets_manager
        
    except Exception as e:
        logger.error(f"Error initializing secrets manager in admin route: {e}", exc_info=True)
        return None

def superadmin_required(f):
    """Decorator to ensure only superadmin can access secrets management"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        logger.info(f"Checking superadmin access for user: {current_user.email if current_user.is_authenticated else 'Not authenticated'}")
        
        if not current_user.is_authenticated:
            logger.warning("User not authenticated")
            # Check if this is an API route (contains '/api/')
            if '/api/' in request.path:
                return jsonify({'success': False, 'error': 'Authentication required'}), 401
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('auth.login'))
        
        # Check if user is superadmin using role field or specific email
        user_role = getattr(current_user, 'role', None)
        user_email = getattr(current_user, 'email', None)
        
        logger.info(f"User role: {user_role}, User email: {user_email}")
        
        is_superadmin = (
            hasattr(current_user, 'role') and current_user.role == 'super_admin'
        ) or (
            hasattr(current_user, 'email') and current_user.email in [
                'mdsajid020@gmail.com',  # Your admin email
                'admin@yourcompany.com', # Add other admin emails as needed
                'admin@acme.com'         # Admin user from database
            ]
        )
        
        logger.info(f"Is superadmin: {is_superadmin}")
        
        if not is_superadmin:
            # Check if this is an API route (contains '/api/')
            if '/api/' in request.path:
                return jsonify({'success': False, 'error': 'Superadmin access required'}), 403
            flash('Access denied. Superadmin privileges required for secrets management.', 'error')
            logger.warning(f"Unauthorized secrets access attempt by {current_user.email}")
            return redirect(url_for('dashboard.dashboard'))
        
        return f(*args, **kwargs)
    return decorated_function

@admin_secrets_bp.route('/')
@login_required
@superadmin_required
def secrets_dashboard():
    """Enhanced secrets management dashboard v2"""
    try:
        # Debug logging
        logger.info(f"User accessing secrets dashboard: {current_user.email}, Role: {current_user.role}")
        
        # Check if environment variables are available
        env_secrets_key = os.environ.get('SECRETS_MASTER_KEY')
        logger.info(f"Environment SECRETS_MASTER_KEY available: {bool(env_secrets_key)}")
        
        # Safely get the secrets manager
        current_secrets_manager = get_secrets_manager()
        if not current_secrets_manager:
            logger.error("Secrets manager not available - could not initialize")
            # Instead of redirecting, show a helpful error message
            error_message = """
            Secrets management system is not properly configured. This could be due to:
            <br>• Missing SECRETS_MASTER_KEY environment variable
            <br>• Database connection issues
            <br>• Encryption system initialization failure
            <br><br>Please contact your system administrator to resolve this issue.
            """
            flash(error_message, 'error')
            
            # Provide minimal dashboard with error state
            return render_template('admin/secrets_dashboard.html', 
                                 secrets_by_category={},
                                 total_secrets=0,
                                 active_secrets=0,
                                 categories_count=0,
                                 servicenow_configured=False,
                                 smtp_configured=False,
                                 smtp_configs={},
                                 smtp_configured_count=0,
                                 smtp_total_required=5,
                                 smtp_completion_percentage=0,
                                 smtp_server_configured=False,
                                 smtp_auth_configured=False,
                                 smtp_email_configured=False,
                                 oauth_configured=False,
                                 last_updated="Error",
                                 secrets_status={'configured': False, 'error': True})
        
        # Get all secrets
        all_secrets = current_secrets_manager.list_secrets(include_values=False)
        
        # Group secrets by category and format dates safely
        secrets_by_category = {}
        for secret in all_secrets:
            # Safely format the updated_at field
            if 'updated_at' in secret and secret['updated_at']:
                try:
                    from datetime import datetime
                    updated_at_value = secret['updated_at']
                    if isinstance(updated_at_value, datetime):
                        secret['updated_at'] = updated_at_value.strftime('%Y-%m-%d %H:%M')
                    elif isinstance(updated_at_value, str):
                        # Already a string, keep as is
                        pass
                    else:
                        secret['updated_at'] = str(updated_at_value)
                except Exception as e:
                    logger.warning(f"Error formatting updated_at for secret {secret.get('name', 'unknown')}: {e}")
                    secret['updated_at'] = 'Unknown'
            else:
                secret['updated_at'] = 'Never'
            
            # Also handle last_accessed field
            if 'last_accessed' in secret and secret['last_accessed']:
                try:
                    from datetime import datetime
                    last_accessed_value = secret['last_accessed']
                    if isinstance(last_accessed_value, datetime):
                        secret['last_accessed'] = last_accessed_value.strftime('%Y-%m-%d %H:%M')
                    elif isinstance(last_accessed_value, str):
                        # Already a string, keep as is
                        pass
                    else:
                        secret['last_accessed'] = str(last_accessed_value)
                except Exception as e:
                    logger.warning(f"Error formatting last_accessed for secret {secret.get('name', 'unknown')}: {e}")
                    secret['last_accessed'] = 'Unknown'
            else:
                secret['last_accessed'] = 'Never'
            
            # Map secrets to our 4 main categories for better organization
            secret_name = secret.get('name', '').lower()  # Using lowercase for easier matching
            secret_description = secret.get('description', '').lower()
            
            # More comprehensive categorization based on screenshot analysis
            # ServiceNow category
            if (any(keyword in secret_name for keyword in [
                'servicenow', 'service now', 'snow'
            ]) or any(keyword in secret_description for keyword in [
                'servicenow', 'service now', 'snow'
            ])):
                category = 'ServiceNow'
            
            # SMTP/Email category - be more aggressive with email-related terms
            elif (any(keyword in secret_name for keyword in [
                'smtp', 'mail', 'email', 'team email', 'email username', 'email password', 
                'email address', 'smtp username', 'smtp password', 'mail username', 
                'mail password', 'team email address'
            ]) or any(keyword in secret_description for keyword in [
                'smtp', 'mail', 'email', 'email server', 'mail server'
            ])):
                category = 'SMTP'
            
            # OAuth/Google category
            elif (any(keyword in secret_name for keyword in [
                'oauth', 'google oauth', 'client id', 'client secret', 'google', 'sso', 
                'single sign', 'authentication'
            ]) or any(keyword in secret_description for keyword in [
                'oauth', 'google', 'authentication', 'sso', 'single sign'
            ])):
                category = 'OAuth'
            
            # Application category - everything else including shift timings, timezone, etc.
            else:
                category = 'Application'
                
            if category not in secrets_by_category:
                secrets_by_category[category] = []
            secrets_by_category[category].append(secret)
        
        # Get basic statistics
        total_secrets = len(all_secrets)
        active_secrets = len([s for s in all_secrets if s.get('is_active', True)])
        categories_count = len(secrets_by_category)
        
        # Check configuration status for different sections with flexible matching
        servicenow_configured = any(
            secret.get('name', '').upper().startswith('SERVICENOW_') or 
            'SERVICENOW' in secret.get('name', '').upper() or
            'SERVICENOW' in secret.get('description', '').upper()
            for secret in all_secrets
        )
        smtp_configured = any(
            secret.get('name', '').upper().startswith('SMTP_') or 
            secret.get('name', '').upper().startswith('MAIL_') or
            'SMTP' in secret.get('name', '').upper() or
            'MAIL' in secret.get('name', '').upper()
            for secret in all_secrets
        )
        oauth_configured = any(
            secret.get('name', '').upper().startswith('GOOGLE_OAUTH_') or 
            secret.get('name', '').upper().startswith('OAUTH_') or
            'OAUTH' in secret.get('name', '').upper() or
            'GOOGLE' in secret.get('name', '').upper()
            for secret in all_secrets
        )
        
        # Mock some data for development
        if not all_secrets:
            from datetime import datetime, timedelta
            mock_time = datetime.now() - timedelta(days=1)
            formatted_time = mock_time.strftime('%Y-%m-%d %H:%M')
            
            secrets_by_category = {
                'ServiceNow': [
                    {'id': 1, 'name': 'SERVICENOW_INSTANCE', 'description': 'ServiceNow instance endpoint', 'value': None, 'updated_at': formatted_time, 'last_accessed': 'Never'},
                    {'id': 2, 'name': 'SERVICENOW_USERNAME', 'description': 'ServiceNow authentication username', 'value': None, 'updated_at': formatted_time, 'last_accessed': 'Never'},
                ],
                'SMTP': [
                    {'id': 3, 'name': 'SMTP_SERVER', 'description': 'SMTP server hostname', 'value': None, 'updated_at': formatted_time, 'last_accessed': 'Never'},
                    {'id': 4, 'name': 'SMTP_USERNAME', 'description': 'SMTP authentication username', 'value': None, 'updated_at': formatted_time, 'last_accessed': 'Never'},
                ],
                'Application': [
                    {'id': 5, 'name': 'TEAM_EMAIL', 'description': 'Team contact email address', 'value': None, 'updated_at': formatted_time, 'last_accessed': 'Never'},
                    {'id': 6, 'name': 'DATABASE_URL', 'description': 'Application database connection', 'value': None, 'updated_at': formatted_time, 'last_accessed': 'Never'},
                ],
                'OAuth': [
                    {'id': 7, 'name': 'GOOGLE_OAUTH_CLIENT_ID', 'description': 'Google OAuth application client identifier', 'value': None, 'updated_at': formatted_time, 'last_accessed': 'Never'},
                    {'id': 8, 'name': 'GOOGLE_OAUTH_CLIENT_SECRET', 'description': 'Google OAuth application client secret', 'value': None, 'updated_at': formatted_time, 'last_accessed': 'Never'},
                ]
            }
            total_secrets = 8
            active_secrets = 8
            categories_count = 4
            # Set mock configuration statuses
            servicenow_configured = False
            smtp_configured = False
            oauth_configured = False
        
        # Calculate SMTP configuration status
        smtp_configs = {}
        smtp_required_fields = ['SMTP_SERVER', 'SMTP_PORT', 'SMTP_USERNAME', 'SMTP_PASSWORD', 'MAIL_FROM_ADDRESS']
        smtp_configured_count = 0
        
        for field in ['SMTP_SERVER', 'SMTP_PORT', 'SMTP_USERNAME', 'SMTP_PASSWORD', 'SMTP_USE_TLS', 'SMTP_USE_SSL', 'MAIL_FROM_NAME', 'MAIL_FROM_ADDRESS']:
            try:
                value = SMTPConfig.get_config(field)
                smtp_configs[field] = value
                if field in smtp_required_fields and value:
                    smtp_configured_count += 1
            except Exception as e:
                logger.warning(f"Could not get SMTP config {field}: {e}")
                smtp_configs[field] = None
        
        smtp_total_required = len(smtp_required_fields)
        smtp_completion_percentage = round((smtp_configured_count / smtp_total_required) * 100) if smtp_total_required > 0 else 0
        smtp_configured = smtp_configured_count == smtp_total_required
        
        # Check individual section completion
        smtp_server_configured = bool(smtp_configs.get('SMTP_SERVER') and smtp_configs.get('SMTP_PORT'))
        smtp_auth_configured = bool(smtp_configs.get('SMTP_USERNAME') and smtp_configs.get('SMTP_PASSWORD'))
        smtp_email_configured = bool(smtp_configs.get('MAIL_FROM_ADDRESS'))
        
        # Get application configuration values
        app_config = {
            'session_timeout': current_secrets_manager.get_secret('session_timeout', '3600'),
            'max_workers': current_secrets_manager.get_secret('max_workers', '4'),
            'log_level': current_secrets_manager.get_secret('log_level', 'INFO'),
            'app_timezone': current_secrets_manager.get_secret('app_timezone', 'Asia/Kolkata'),
            'day_shift_start': current_secrets_manager.get_secret('day_shift_start', '06:30'),
            'day_shift_end': current_secrets_manager.get_secret('day_shift_end', '15:30'),
            'evening_shift_start': current_secrets_manager.get_secret('evening_shift_start', '14:45'),
            'evening_shift_end': current_secrets_manager.get_secret('evening_shift_end', '23:45'),
            'night_shift_start': current_secrets_manager.get_secret('night_shift_start', '21:45'),
            'night_shift_end': current_secrets_manager.get_secret('night_shift_end', '06:45')
        }
        
        response = make_response(render_template('admin/secrets_dashboard.html', 
                             secrets_by_category=secrets_by_category,
                             total_secrets=total_secrets,
                             active_secrets=active_secrets,
                             categories_count=categories_count,
                             servicenow_configured=servicenow_configured,
                             smtp_configured=smtp_configured,
                             smtp_configs=smtp_configs,
                             smtp_configured_count=smtp_configured_count,
                             smtp_total_required=smtp_total_required,
                             smtp_completion_percentage=smtp_completion_percentage,
                             smtp_server_configured=smtp_server_configured,
                             smtp_auth_configured=smtp_auth_configured,
                             smtp_email_configured=smtp_email_configured,
                             oauth_configured=oauth_configured,
                             app_config=app_config,
                             last_updated="7:08:58 am",
                             secrets_status={'configured': True}))
        
        # Add cache-busting headers
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        
        return response
    
    except Exception as e:
        logger.error(f"Error loading secrets dashboard: {e}", exc_info=True)
        
        # Provide more detailed error information
        error_details = str(e)
        if "SECRETS_MASTER_KEY" in error_details:
            error_message = "Secrets encryption key is not properly configured. Please check your environment configuration."
        elif "database" in error_details.lower():
            error_message = "Database connection error. Please check your database configuration."
        else:
            error_message = f"System error: {error_details}"
        
        flash(f'Error loading secrets dashboard: {error_message}', 'error')
        
        # Return minimal dashboard instead of redirecting
        return render_template('admin/secrets_dashboard.html', 
                             secrets_by_category={},
                             total_secrets=0,
                             active_secrets=0,
                             categories_count=0,
                             servicenow_configured=False,
                             smtp_configured=False,
                             smtp_configs={},
                             smtp_configured_count=0,
                             smtp_total_required=5,
                             smtp_completion_percentage=0,
                             smtp_server_configured=False,
                             smtp_auth_configured=False,
                             smtp_email_configured=False,
                             oauth_configured=False,
                             app_config={},
                             last_updated="Error",
                             secrets_status={'configured': False, 'error': True})

@admin_secrets_bp.route('/api/secrets')
@login_required
@superadmin_required
def api_list_secrets():
    """API endpoint to list secrets"""
    try:
        current_secrets_manager = get_secrets_manager()
        if not current_secrets_manager:
            return jsonify({
                'success': False,
                'error': 'Secrets manager not available'
            }), 500
            
        category = request.args.get('category')
        include_values = request.args.get('include_values', 'false').lower() == 'true'
        
        secrets = current_secrets_manager.list_secrets(category=category, include_values=include_values)
        
        return jsonify({
            'success': True,
            'secrets': secrets,
            'count': len(secrets)
        })
    
    except Exception as e:
        logger.error(f"Error listing secrets: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@admin_secrets_bp.route('/api/secrets/<key_name>', methods=['POST'])
@login_required
@superadmin_required
def api_update_secret(key_name):
    """API endpoint to update a secret"""
    try:
        current_secrets_manager = get_secrets_manager()
        if not current_secrets_manager:
            return jsonify({
                'success': False,
                'error': 'Secrets manager not available'
            }), 500
        
        data = request.get_json()
        
        # Get current secret to preserve value if not provided
        current_value = None
        if 'value' not in data or not data['value']:
            current_value = current_secrets_manager.get_secret(key_name)
            if current_value is None:
                return jsonify({
                    'success': False,
                    'error': 'Secret not found and no new value provided'
                }), 404
        
        # Update the secret
        success = current_secrets_manager.set_secret(
            key=key_name,
            value=data.get('value', current_value),
            category=data.get('category', 'external_apis'),
            description=data.get('description'),
            is_active=data.get('is_active', True)
        )
        
        if success:
            logger.info(f"Secret {key_name} updated by {current_user.email}")
            return jsonify({
                'success': True,
                'message': f"Secret '{key_name}' updated successfully"
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to update secret'
            }), 500
            
    except Exception as e:
        logger.error(f"Error updating secret {key_name}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@admin_secrets_bp.route('/api/secrets/<key_name>')
@login_required
@superadmin_required
def api_get_secret(key_name):
    """API endpoint to get a specific secret"""
    try:
        current_secrets_manager = get_secrets_manager()
        if not current_secrets_manager:
            return jsonify({
                'success': False,
                'error': 'Secrets manager not available'
            }), 500
            
        value = current_secrets_manager.get_secret(key_name)
        
        if value is not None:
            return jsonify({
                'success': True,
                'key_name': key_name,
                'value': value
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Secret not found'
            }), 404
    
    except Exception as e:
        logger.error(f"Error getting secret {key_name}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@admin_secrets_bp.route('/api/secrets', methods=['POST'])
@login_required
@superadmin_required
def api_create_secret():
    """API endpoint to create/update a secret"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['key_name', 'value', 'category']
        if not all(field in data for field in required_fields):
            return jsonify({
                'success': False,
                'error': 'Missing required fields: key_name, value, category'
            }), 400
        
        # Validate category
        valid_categories = [SecretCategory.EXTERNAL, SecretCategory.APPLICATION, SecretCategory.FEATURE]
        if data['category'] not in valid_categories:
            return jsonify({
                'success': False,
                'error': f'Invalid category. Must be one of: {valid_categories}'
            }), 400
        
        # Set the secret
        success = secrets_manager.set_secret(
            key_name=data['key_name'],
            value=data['value'],
            category=data['category'],
            description=data.get('description'),
            requires_restart=data.get('requires_restart', False),
            expires_in_days=data.get('expires_in_days')
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': f"Secret '{data['key_name']}' saved successfully"
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to save secret'
            }), 500
    
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    except Exception as e:
        logger.error(f"Error creating secret: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@admin_secrets_bp.route('/api/secrets/<key_name>', methods=['DELETE'])
@login_required
@superadmin_required
def api_delete_secret(key_name):
    """API endpoint to delete a secret"""
    try:
        success = secrets_manager.delete_secret(key_name)
        
        if success:
            return jsonify({
                'success': True,
                'message': f"Secret '{key_name}' deleted successfully"
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to delete secret or secret not found'
            }), 404
    
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    except Exception as e:
        logger.error(f"Error deleting secret {key_name}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@admin_secrets_bp.route('/api/secrets/<key_name>/toggle', methods=['POST'])
@login_required
@superadmin_required
def api_toggle_secret(key_name):
    """API endpoint to activate/deactivate a secret"""
    try:
        secret = db.session.query(SecretStore).filter_by(key_name=key_name).first()
        
        if not secret:
            return jsonify({
                'success': False,
                'error': 'Secret not found'
            }), 404
        
        secret.is_active = not secret.is_active
        secret.updated_by = current_user.email
        secret.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        action = "activated" if secret.is_active else "deactivated"
        return jsonify({
            'success': True,
            'message': f"Secret '{key_name}' {action} successfully",
            'is_active': secret.is_active
        })
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error toggling secret {key_name}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@admin_secrets_bp.route('/audit')
@login_required
@superadmin_required
def audit_logs():
    """View audit logs for secrets"""
    try:
        secret_key = request.args.get('secret_key')
        limit = int(request.args.get('limit', 100))
        
        logs = secrets_manager.get_audit_log(secret_key=secret_key, limit=limit)
        
        return render_template('admin/secrets_audit.html', 
                             audit_logs=logs,
                             secret_key=secret_key)
    
    except Exception as e:
        logger.error(f"Error loading audit logs: {e}")
        flash('Error loading audit logs', 'error')
        return redirect(url_for('admin_secrets.secrets_dashboard'))

@admin_secrets_bp.route('/export')
@login_required
@superadmin_required
def export_secrets():
    """Export secrets (encrypted) for backup purposes"""
    try:
        secrets = secrets_manager.list_secrets(include_values=False)  # Never export actual values
        
        export_data = {
            'export_timestamp': datetime.utcnow().isoformat(),
            'exported_by': current_user.email,
            'secrets_count': len(secrets),
            'secrets': secrets
        }
        
        # Log the export
        logger.info(f"Secrets exported by {current_user.email}")
        
        return jsonify(export_data), 200, {
            'Content-Disposition': f'attachment; filename=secrets_export_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.json'
        }
    
    except Exception as e:
        logger.error(f"Error exporting secrets: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@admin_secrets_bp.route('/test/<key_name>')
@login_required
@superadmin_required
def test_secret(key_name):
    """Test if a secret can be retrieved successfully"""
    try:
        value = secrets_manager.get_secret(key_name)
        
        if value is not None:
            # Don't log the actual value for security
            value_info = {
                'length': len(str(value)),
                'type': type(value).__name__,
                'is_empty': len(str(value)) == 0,
                'starts_with': str(value)[:3] + '...' if len(str(value)) > 3 else str(value)
            }
            
            return jsonify({
                'success': True,
                'message': f"Secret '{key_name}' retrieved successfully",
                'value_info': value_info
            })
        else:
            return jsonify({
                'success': False,
                'error': f"Secret '{key_name}' not found or is empty"
            }), 404
    
    except Exception as e:
        logger.error(f"Error testing secret {key_name}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ===========================
# SMTP Configuration Routes
# ===========================

@admin_secrets_bp.route('/smtp')
@login_required
@superadmin_required
def smtp_config():
    """SMTP configuration management page"""
    try:
        smtp_configs = SMTPConfig.query.all()
        smtp_status = SMTPConfig.is_configured()
        
        # Group configs for better display
        config_groups = {
            'Server Settings': ['smtp_server', 'smtp_port', 'smtp_use_tls', 'smtp_use_ssl'],
            'Authentication': ['smtp_username', 'smtp_password'],
            'Email Settings': ['mail_default_sender', 'mail_reply_to', 'team_email'],
            'System': ['smtp_enabled']
        }
        
        return render_template('admin/smtp_config.html',
                             smtp_configs=smtp_configs,
                             smtp_status=smtp_status,
                             config_groups=config_groups)
    
    except Exception as e:
        logger.error(f"Error loading SMTP config: {e}")
        flash('Error loading SMTP configuration', 'error')
        return redirect(url_for('admin_secrets.secrets_dashboard'))

@admin_secrets_bp.route('/api/smtp/config', methods=['GET'])
@login_required
@superadmin_required
def api_get_smtp_configs():
    """API endpoint to get all SMTP configurations"""
    try:
        # Define SMTP configuration fields with their descriptions
        smtp_fields = {
            'SMTP_SERVER': {
                'label': 'SMTP Server',
                'description': 'SMTP server hostname (e.g., smtp.gmail.com)',
                'type': 'text',
                'required': True,
                'placeholder': 'smtp.gmail.com'
            },
            'SMTP_PORT': {
                'label': 'SMTP Port',
                'description': 'SMTP server port (usually 587 for TLS or 465 for SSL)',
                'type': 'number',
                'required': True,
                'placeholder': '587'
            },
            'SMTP_USERNAME': {
                'label': 'SMTP Username',
                'description': 'SMTP authentication username (usually your email)',
                'type': 'email',
                'required': True,
                'placeholder': 'your-email@company.com'
            },
            'SMTP_PASSWORD': {
                'label': 'SMTP Password',
                'description': 'SMTP authentication password or app password',
                'type': 'password',
                'required': True,
                'placeholder': '••••••••••••'
            },
            'SMTP_USE_TLS': {
                'label': 'Use TLS',
                'description': 'Enable TLS encryption for secure email transmission',
                'type': 'boolean',
                'required': False,
                'default': True
            },
            'SMTP_USE_SSL': {
                'label': 'Use SSL',
                'description': 'Enable SSL encryption (alternative to TLS)',
                'type': 'boolean',
                'required': False,
                'default': False
            },
            'MAIL_FROM_NAME': {
                'label': 'Sender Name',
                'description': 'Display name for outgoing emails',
                'type': 'text',
                'required': False,
                'placeholder': 'Shift Handover System'
            },
            'MAIL_FROM_ADDRESS': {
                'label': 'From Email Address',
                'description': 'Email address for outgoing emails',
                'type': 'email',
                'required': True,
                'placeholder': 'noreply@company.com'
            }
        }
        
        # Get current values for all SMTP fields from database
        smtp_config = {}
        for field_name, field_info in smtp_fields.items():
            try:
                config_value = SMTPConfig.get_config(field_name)
                smtp_config[field_name] = {
                    'value': config_value if config_value is not None else '',
                    'configured': config_value is not None,
                    **field_info
                }
            except Exception as e:
                logger.warning(f"Could not get SMTP config {field_name}: {e}")
                smtp_config[field_name] = {
                    'value': '',
                    'configured': False,
                    **field_info
                }
        
        # Calculate configuration status
        required_fields = [name for name, info in smtp_fields.items() if info.get('required', False)]
        configured_count = sum(1 for field in required_fields if smtp_config[field]['configured'])
        total_required = len(required_fields)
        
        config_status = 'complete' if configured_count == total_required else 'partial' if configured_count > 0 else 'none'
        
        return jsonify({
            'success': True,
            'smtp_config': smtp_config,
            'status': {
                'configured_count': configured_count,
                'total_required': total_required,
                'config_status': config_status,
                'percentage': round((configured_count / total_required) * 100) if total_required > 0 else 0
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting SMTP configs: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@admin_secrets_bp.route('/api/smtp/config', methods=['POST'])
@login_required
@superadmin_required
def api_set_smtp_config():
    """API endpoint to set SMTP configuration"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        updated_fields = []
        errors = []
        
        # Valid SMTP configuration fields
        valid_fields = {
            'SMTP_SERVER', 'SMTP_PORT', 'SMTP_USERNAME', 'SMTP_PASSWORD',
            'SMTP_USE_TLS', 'SMTP_USE_SSL', 'MAIL_FROM_NAME', 'MAIL_FROM_ADDRESS', 'smtp_enabled'
        }
        
        for field_name, field_value in data.items():
            if field_name not in valid_fields:
                continue
                
            try:
                # Convert boolean values to string for database storage
                if field_name in ['SMTP_USE_TLS', 'SMTP_USE_SSL', 'smtp_enabled']:
                    if isinstance(field_value, bool):
                        field_value = str(field_value).lower()
                    elif isinstance(field_value, str):
                        field_value = field_value.lower() in ['true', '1', 'yes', 'on']
                        field_value = str(field_value).lower()
                
                # Determine if field should be encrypted (passwords)
                encrypted = field_name == 'SMTP_PASSWORD'
                
                # Store the configuration
                success = SMTPConfig.set_config(
                    key=field_name,
                    value=str(field_value),
                    description=f"SMTP configuration: {field_name.replace('_', ' ').title()}",
                    encrypted=encrypted
                )
                
                if success:
                    updated_fields.append(field_name)
                else:
                    errors.append(f"Failed to update {field_name}")
                
            except Exception as e:
                logger.error(f"Error updating SMTP config {field_name}: {e}")
                errors.append(f"Failed to update {field_name}: {str(e)}")
        
        # Commit changes to database
        try:
            db.session.commit()
        except Exception as e:
            logger.error(f"Error committing SMTP config changes: {e}")
            db.session.rollback()
            return jsonify({
                'success': False,
                'error': f'Database error: {str(e)}'
            }), 500
        
        if errors:
            return jsonify({
                'success': False,
                'error': 'Some fields failed to update',
                'errors': errors,
                'updated_fields': updated_fields
            }), 400
        
        return jsonify({
            'success': True,
            'message': f'Updated {len(updated_fields)} SMTP configuration fields',
            'updated_fields': updated_fields
        })
        
    except Exception as e:
        logger.error(f"Error updating SMTP config: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_secrets_bp.route('/api/smtp/config/<config_key>', methods=['DELETE'])
@login_required
@superadmin_required
def api_delete_smtp_config(config_key):
    """API endpoint to delete SMTP configuration"""
    try:
        success = SMTPConfig.delete_config(config_key)
        
        if success:
            logger.info(f"SMTP config {config_key} deleted by {current_user.email}")
            return jsonify({
                'success': True,
                'message': f"SMTP configuration '{config_key}' deleted successfully"
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to delete SMTP configuration or configuration not found'
            }), 404
    
    except Exception as e:
        logger.error(f"Error deleting SMTP config {config_key}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@admin_secrets_bp.route('/api/smtp/test', methods=['POST'])
@login_required
@superadmin_required
def api_test_smtp():
    """API endpoint to test SMTP connection"""
    try:
        success, message = SMTPConfig.test_connection()
        
        logger.info(f"SMTP connection test by {current_user.email}: {message}")
        
        return jsonify({
            'success': success,
            'message': message
        })
    
    except Exception as e:
        logger.error(f"Error testing SMTP connection: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@admin_secrets_bp.route('/api/smtp/initialize', methods=['POST'])
@login_required
@superadmin_required
def api_initialize_smtp():
    """API endpoint to initialize SMTP default configurations"""
    try:
        success = SMTPConfig.initialize_default_configs()
        
        if success:
            logger.info(f"SMTP default configs initialized by {current_user.email}")
            return jsonify({
                'success': True,
                'message': 'SMTP default configurations initialized successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to initialize SMTP default configurations'
            }), 500
    
    except Exception as e:
        logger.error(f"Error initializing SMTP configs: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@admin_secrets_bp.route('/api/unified')
@login_required
@superadmin_required
def get_unified_secrets():
    """Get all secrets organized by sections for unified dashboard"""
    try:
        # Define section mapping
        section_mapping = {
            'external_apis': {
                'display_name': 'External APIs & Services',
                'description': 'Third-party service credentials and API keys',
                'icon': '🌐'
            },
            'application_config': {
                'display_name': 'Application Configuration', 
                'description': 'Application-specific settings and configurations',
                'icon': '⚙️'
            },
            'feature_controls': {
                'display_name': 'Feature Controls',
                'description': 'Feature flags and service enablement toggles', 
                'icon': '🎛️'
            }
        }
        
        # Get all secrets from database
        with db.engine.connect() as connection:
            result = connection.execute(text("""
                SELECT key_name, category, encrypted_value, is_active, description, 
                       created_at, updated_at 
                FROM secret_store 
                ORDER BY category, key_name
            """))
            all_secrets = result.fetchall()
        
        # Organize secrets by section
        sections = {}
        for section_key, section_info in section_mapping.items():
            sections[section_key] = {
                'info': section_info,
                'secrets': []
            }
        
        for secret in all_secrets:
            key_name, category, encrypted_value, is_active, description, created_at, updated_at = secret
            
            # Find the section for this category
            if category in sections:
                secret_info = {
                    'key_name': key_name,
                    'category': category,
                    'is_active': is_active,
                    'description': description or 'No description provided',
                    'has_value': bool(encrypted_value),
                    'created_at': str(created_at) if created_at else None,
                    'updated_at': str(updated_at) if updated_at else None
                }
                sections[category]['secrets'].append(secret_info)
        
        return jsonify({
            'success': True,
            'sections': sections,
            'total_secrets': len(all_secrets),
            'section_counts': {section: len(data['secrets']) for section, data in sections.items()}
        })
        
    except Exception as e:
        logger.error(f"Error getting unified secrets: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_secrets_bp.route('/edit/<key_name>')
@login_required
@superadmin_required
def edit_secret_form(key_name):
    """Form to edit an individual secret"""
    try:
        current_secrets_manager = get_secrets_manager()
        if not current_secrets_manager:
            flash('Secrets manager not available', 'error')
            return redirect(url_for('admin_secrets.secrets_dashboard'))
        
        # Get the secret details
        secret_value = current_secrets_manager.get_secret(key_name)
        if secret_value is None:
            flash(f'Secret {key_name} not found', 'error')
            return redirect(url_for('admin_secrets.secrets_dashboard'))
        
        # Get secret metadata
        secrets_list = current_secrets_manager.list_secrets()
        secret_meta = next((s for s in secrets_list if s['key_name'] == key_name), None)
        
        if not secret_meta:
            flash(f'Secret metadata for {key_name} not found', 'error')
            return redirect(url_for('admin_secrets.secrets_dashboard'))
        
        return render_template('admin/edit_secret.html', 
                             secret=secret_meta,
                             secret_value=secret_value)
        
    except Exception as e:
        logger.error(f"Error loading edit form for {key_name}: {e}")
        flash('Error loading secret edit form', 'error')
        return redirect(url_for('admin_secrets.secrets_dashboard'))

@admin_secrets_bp.route('/add')
@login_required
@superadmin_required  
def add_secret_form():
    """Form to add a new secret"""
    try:
        category = request.args.get('category', 'external_apis')
        secret_type = request.args.get('type', '')
        
        return render_template('admin/add_secret.html',
                             category=category,
                             secret_type=secret_type)
        
    except Exception as e:
        logger.error(f"Error loading add secret form: {e}")
        flash('Error loading add secret form', 'error')
        return redirect(url_for('admin_secrets.secrets_dashboard'))

# New API endpoints for the Secrets Management Dashboard

@admin_secrets_bp.route('/api/smtp', methods=['GET'])
@admin_required
def get_smtp_config():
    """Get SMTP configuration from database using SMTPConfig model"""
    try:
        smtp_use_tls = SMTPConfig.get_config('smtp_use_tls', 'true').lower() == 'true'
        smtp_use_ssl = SMTPConfig.get_config('smtp_use_ssl', 'false').lower() == 'true'
        
        # Determine security setting
        security_type = 'None'
        if smtp_use_ssl:
            security_type = 'SSL'
        elif smtp_use_tls:
            security_type = 'TLS/STARTTLS'
            
        config = {
            'smtp_server': SMTPConfig.get_config('smtp_server', ''),
            'smtp_port': int(SMTPConfig.get_config('smtp_port', 587)),
            'smtp_username': SMTPConfig.get_config('smtp_username', ''),
            'smtp_password': '••••••••••••••••' if SMTPConfig.get_config('smtp_password') else '',
            'smtp_from': SMTPConfig.get_config('mail_default_sender', ''),
            'smtp_use_tls': smtp_use_tls,
            'smtp_use_ssl': smtp_use_ssl,
            'smtp_security': security_type
        }
        
        return jsonify({'success': True, 'config': config})
        
    except Exception as e:
        logger.error(f"Error getting SMTP config: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_secrets_bp.route('/api/smtp', methods=['POST'])
@admin_required
def save_smtp_config():
    """Save SMTP configuration to smtp_config table using SMTPConfig model"""
    try:
        data = request.get_json()
        
        # Save each SMTP setting using SMTPConfig model
        SMTPConfig.set_config('smtp_server', data.get('smtp_server', ''), 'SMTP server hostname', encrypted=False)
        SMTPConfig.set_config('smtp_port', str(data.get('smtp_port', 587)), 'SMTP server port', encrypted=False)
        SMTPConfig.set_config('smtp_username', data.get('smtp_username', ''), 'SMTP authentication username', encrypted=False)
        
        # Only update password if it's not the masked value
        if data.get('smtp_password') and data.get('smtp_password') != '••••••••••••••••':
            SMTPConfig.set_config('smtp_password', data.get('smtp_password', ''), 'SMTP authentication password', encrypted=True)
        
        SMTPConfig.set_config('mail_default_sender', data.get('smtp_from', ''), 'Default sender email address', encrypted=False)
        SMTPConfig.set_config('smtp_use_tls', str(data.get('smtp_use_tls', True)).lower(), 'Enable TLS encryption', encrypted=False)
        SMTPConfig.set_config('smtp_use_ssl', str(data.get('smtp_use_ssl', False)).lower(), 'Enable SSL encryption', encrypted=False)
        
        # Enable SMTP if configuration is provided
        if data.get('smtp_server') and data.get('smtp_username'):
            SMTPConfig.set_config('smtp_enabled', 'true', 'Enable/disable SMTP email functionality', encrypted=False)
        
        logger.info(f"SMTP configuration saved by user: {current_user.email}")
        return jsonify({'success': True, 'message': 'SMTP configuration saved successfully'})
        
    except Exception as e:
        logger.error(f"Error saving SMTP config: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_secrets_bp.route('/api/servicenow', methods=['GET'])
@admin_required
def get_servicenow_config():
    """Get ServiceNow configuration from database using ServiceNowConfig model"""
    try:
        config = {
            'servicenow_instance_url': ServiceNowConfig.get_config('instance_url', ''),
            'servicenow_username': ServiceNowConfig.get_config('username', ''),
            'servicenow_password': '••••••••' if ServiceNowConfig.get_config('password') else '',
            'servicenow_assignment_groups': ServiceNowConfig.get_config('assignment_groups', ''),
            'servicenow_timeout': int(ServiceNowConfig.get_config('timeout', 30)),
            'servicenow_enabled': ServiceNowConfig.get_config('enabled', 'false').lower() == 'true'
        }
        
        return jsonify({'success': True, 'config': config})
        
    except Exception as e:
        logger.error(f"Error getting ServiceNow config: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_secrets_bp.route('/api/servicenow', methods=['POST'])
@admin_required
def save_servicenow_config():
    """Save ServiceNow configuration to servicenow_config table using ServiceNowConfig model"""
    try:
        data = request.get_json()
        
        # Save each ServiceNow setting using ServiceNowConfig model
        ServiceNowConfig.set_config('instance_url', data.get('servicenow_instance_url', ''), 'ServiceNow instance URL', encrypted=False)
        ServiceNowConfig.set_config('username', data.get('servicenow_username', ''), 'ServiceNow API username', encrypted=False)
        
        # Only update password if it's not the masked value
        if data.get('servicenow_password') and data.get('servicenow_password') != '••••••••':
            ServiceNowConfig.set_config('password', data.get('servicenow_password', ''), 'ServiceNow API password', encrypted=True)
        
        ServiceNowConfig.set_config('assignment_groups', data.get('assignment_groups', ''), 'ServiceNow assignment groups to monitor', encrypted=False)
        ServiceNowConfig.set_config('timeout', str(data.get('servicenow_timeout', 30)), 'ServiceNow API timeout in seconds', encrypted=False)
        ServiceNowConfig.set_config('table', data.get('servicenow_table', 'incident'), 'Default ServiceNow table', encrypted=False)
        
        # Enable ServiceNow if configuration is provided
        if data.get('servicenow_instance_url') and data.get('servicenow_username'):
            ServiceNowConfig.set_config('enabled', 'true', 'Enable/disable ServiceNow integration', encrypted=False)
        
        logger.info(f"ServiceNow configuration saved by user: {current_user.email}")
        return jsonify({'success': True, 'message': 'ServiceNow configuration saved successfully'})
        
    except Exception as e:
        logger.error(f"Error saving ServiceNow config: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_secrets_bp.route('/api/application', methods=['GET'])
@admin_required
def get_application_config():
    """Get Application configuration from database"""
    try:
        from models.app_config import AppConfig
        
        config = {
            'database_url': 'mysql+pymysql://user:••••••••@db/shift_handover',  # Masked for security
            'secret_key': '••••••••••••••••••••••••••••••••',  # Masked for security
            'session_timeout': int(AppConfig.get_config('session_timeout', '3600')),
            'max_workers': int(AppConfig.get_config('max_workers', '4')),
            'log_level': AppConfig.get_config('log_level', 'INFO'),
            'app_timezone': AppConfig.get_config('app_timezone', 'Asia/Kolkata'),
            'day_shift_start': AppConfig.get_config('day_shift_start', '06:30'),
            'day_shift_end': AppConfig.get_config('day_shift_end', '15:30'),
            'evening_shift_start': AppConfig.get_config('evening_shift_start', '14:45'),
            'evening_shift_end': AppConfig.get_config('evening_shift_end', '23:45'),
            'night_shift_start': AppConfig.get_config('night_shift_start', '21:45'),
            'night_shift_end': AppConfig.get_config('night_shift_end', '06:45'),
            'onshore_shift_start': AppConfig.get_config('onshore_shift_start', '10:00'),
            'onshore_shift_end': AppConfig.get_config('onshore_shift_end', '22:00'),
            'offshore_shift_start': AppConfig.get_config('offshore_shift_start', '22:00'),
            'offshore_shift_end': AppConfig.get_config('offshore_shift_end', '10:00')
        }
        
        return jsonify({'success': True, 'config': config})
        
    except Exception as e:
        logger.error(f"Error getting Application config: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_secrets_bp.route('/api/application', methods=['POST'])
@admin_required
def save_application_config():
    """Save Application configuration to database"""
    try:
        data = request.get_json()
        from models.app_config import AppConfig
        
        # Save application settings (excluding critical secrets like database_url and secret_key)
        AppConfig.set_config('session_timeout', str(data.get('session_timeout', 3600)), 'User session timeout', 'application')
        AppConfig.set_config('max_workers', str(data.get('max_workers', 4)), 'Maximum worker processes', 'application')
        AppConfig.set_config('log_level', data.get('log_level', 'INFO'), 'Application log level', 'application')
        
        # Save timezone configuration
        AppConfig.set_config('app_timezone', data.get('app_timezone', 'Asia/Kolkata'), 'Application timezone', 'application')
        
        # Save shift timing configuration
        AppConfig.set_config('day_shift_start', data.get('day_shift_start', '06:30'), 'Day shift start time', 'application')
        AppConfig.set_config('day_shift_end', data.get('day_shift_end', '15:30'), 'Day shift end time', 'application')
        AppConfig.set_config('evening_shift_start', data.get('evening_shift_start', '14:45'), 'Evening shift start time', 'application')
        AppConfig.set_config('evening_shift_end', data.get('evening_shift_end', '23:45'), 'Evening shift end time', 'application')
        AppConfig.set_config('night_shift_start', data.get('night_shift_start', '21:45'), 'Night shift start time', 'application')
        AppConfig.set_config('night_shift_end', data.get('night_shift_end', '06:45'), 'Night shift end time', 'application')
        AppConfig.set_config('onshore_shift_start', data.get('onshore_shift_start', '10:00'), 'OnShore shift start time', 'application')
        AppConfig.set_config('onshore_shift_end', data.get('onshore_shift_end', '22:00'), 'OnShore shift end time', 'application')
        AppConfig.set_config('offshore_shift_start', data.get('offshore_shift_start', '22:00'), 'OffShore shift start time', 'application')
        AppConfig.set_config('offshore_shift_end', data.get('offshore_shift_end', '10:00'), 'OffShore shift end time', 'application')
        
        # Reload configuration in the app
        from config import Config
        from models.secrets_manager import HybridSecretsManager
        secrets_mgr = HybridSecretsManager()
        Config.init_from_database(secrets_mgr)
        
        return jsonify({'success': True, 'message': 'Application settings saved successfully'})
        
    except Exception as e:
        logger.error(f"Error saving Application config: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Alias endpoint for backward compatibility
@admin_secrets_bp.route('/application-config', methods=['POST'])
@admin_required
def save_application_config_alias():
    """Alias for application configuration - backward compatibility"""
    return save_application_config()


# ===========================
# Email Recipients Configuration Routes
# ===========================

@admin_secrets_bp.route('/api/email-recipients', methods=['GET'])
@login_required
@superadmin_required
def get_email_recipients():
    """Get email recipients configuration"""
    try:
        from models.app_config import AppConfig
        
        config = {
            'handover_recipients': AppConfig.get_config('handover_email_recipients', ''),
            'priority_recipients': AppConfig.get_config('priority_alert_recipients', ''),
            'notifications_enabled': AppConfig.get_config('email_notifications_enabled', 'true').lower() == 'true'
        }
        
        return jsonify({'success': True, **config})
        
    except Exception as e:
        logger.error(f"Error getting email recipients config: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_secrets_bp.route('/api/email-recipients', methods=['POST'])
@login_required
@superadmin_required
def save_email_recipients():
    """Save email recipients configuration"""
    try:
        data = request.get_json()
        
        # Debug logging
        logger.info(f"Received email recipients save request - data: {data}")
        print(f"[DEBUG] Email recipients save - data: {data}")
        
        from models.app_config import AppConfig
        
        # Check if this is a single field save (new format) or bulk save (old format)
        if 'field' in data and 'emails' in data:
            # Single field save format
            field = data.get('field')
            emails = data.get('emails', '').strip()
            
            # Validate email format
            if emails and not validate_email_list(emails):
                return jsonify({'success': False, 'error': 'Invalid email format. Please use comma-separated valid email addresses.'}), 400
            
            # Map field names to config keys
            field_mapping = {
                'handover_email_recipients': 'handover_email_recipients',
                'priority_alert_recipients': 'priority_alert_recipients',
                'handover_recipients': 'handover_email_recipients',
                'priority_recipients': 'priority_alert_recipients'
            }
            
            if field not in field_mapping:
                available_fields = ', '.join(field_mapping.keys())
                error_msg = f"Invalid field name: '{field}'. Available fields: {available_fields}"
                logger.error(error_msg)
                return jsonify({'success': False, 'error': error_msg}), 400
            
            config_key = field_mapping[field]
            description = f"Email recipients for {field.replace('_', ' ').title()}"
            
            # Save to database
            AppConfig.set_config(config_key, emails, description, 'email')
            
            # Log the action
            from services.audit_service import log_action
            log_action('Update Email Recipients', f'Updated {config_key}: {len(emails.split(",") if emails else [])} recipients')
            
            logger.info(f"Successfully saved email recipients for {config_key}")
            return jsonify({'success': True, 'message': f'{description} saved successfully'})
            
        elif 'handover_recipients' in data or 'priority_recipients' in data:
            # Bulk save format (from main template)
            handover_emails = data.get('handover_recipients', '').strip()
            priority_emails = data.get('priority_recipients', '').strip()
            
            # Validate email formats
            if handover_emails and not validate_email_list(handover_emails):
                return jsonify({'success': False, 'error': 'Invalid handover email format. Please use comma-separated valid email addresses.'}), 400
            
            if priority_emails and not validate_email_list(priority_emails):
                return jsonify({'success': False, 'error': 'Invalid priority email format. Please use comma-separated valid email addresses.'}), 400
            
            # Save both configurations
            AppConfig.set_config('handover_email_recipients', handover_emails, 'Handover Email Recipients', 'email')
            AppConfig.set_config('priority_alert_recipients', priority_emails, 'Priority Alert Recipients', 'email')
            
            # Log the action
            from services.audit_service import log_action
            handover_count = len(handover_emails.split(",")) if handover_emails else 0
            priority_count = len(priority_emails.split(",")) if priority_emails else 0
            log_action('Update Email Recipients', f'Updated handover: {handover_count} recipients, priority: {priority_count} recipients')
            
            logger.info(f"Successfully saved bulk email recipients - handover: {handover_count}, priority: {priority_count}")
            return jsonify({'success': True, 'message': 'Email recipients saved successfully'})
        
        else:
            return jsonify({'success': False, 'error': 'Invalid request format. Expected either field/emails or handover_recipients/priority_recipients.'}), 400
        
    except Exception as e:
        logger.error(f"Error saving email recipients: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_secrets_bp.route('/api/email-notifications', methods=['POST'])
@login_required
@superadmin_required
def toggle_email_notifications():
    """Enable/disable email notifications"""
    try:
        data = request.get_json()
        enabled = data.get('enabled', True)
        
        from models.app_config import AppConfig
        
        AppConfig.set_config('email_notifications_enabled', str(enabled).lower(), 
                           'Enable/disable email notifications for handovers', 'email')
        
        # Log the action
        from services.audit_service import log_action
        log_action('Toggle Email Notifications', f'Email notifications {"enabled" if enabled else "disabled"}')
        
        return jsonify({'success': True, 'enabled': enabled})
        
    except Exception as e:
        logger.error(f"Error toggling email notifications: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_secrets_bp.route('/api/smtp-status', methods=['GET'])
@login_required
@superadmin_required
def get_smtp_status():
    """Get SMTP configuration status and details"""
    try:
        from models.smtp_config import SMTPConfig
        
        # Get configuration values
        smtp_server = SMTPConfig.get_config('smtp_server', '')
        smtp_port = SMTPConfig.get_config('smtp_port', '')
        smtp_username = SMTPConfig.get_config('smtp_username', '')
        smtp_password = SMTPConfig.get_config('smtp_password', '')
        smtp_enabled = SMTPConfig.get_config('smtp_enabled', 'false')
        smtp_use_tls = SMTPConfig.get_config('smtp_use_tls', 'true')
        smtp_use_ssl = SMTPConfig.get_config('smtp_use_ssl', 'false')
        mail_default_sender = SMTPConfig.get_config('mail_default_sender', '')
        
        # Check configuration status
        is_configured = SMTPConfig.is_configured()
        
        # Determine what's missing
        missing_fields = []
        if not smtp_server or smtp_server == '[TO_BE_CONFIGURED]':
            missing_fields.append('SMTP Server')
        if not smtp_port or smtp_port == '[TO_BE_CONFIGURED]':
            missing_fields.append('SMTP Port')
        if not smtp_username or smtp_username == '[TO_BE_CONFIGURED]':
            missing_fields.append('SMTP Username')
        if not smtp_password or smtp_password == '[TO_BE_CONFIGURED]':
            missing_fields.append('SMTP Password')
        if smtp_enabled.lower() != 'true':
            missing_fields.append('SMTP Enabled (must be set to true)')
        
        status_info = {
            'is_configured': is_configured,
            'smtp_enabled': smtp_enabled.lower() == 'true',
            'fields_configured': {
                'smtp_server': bool(smtp_server and smtp_server != '[TO_BE_CONFIGURED]'),
                'smtp_port': bool(smtp_port and smtp_port != '[TO_BE_CONFIGURED]'),
                'smtp_username': bool(smtp_username and smtp_username != '[TO_BE_CONFIGURED]'),
                'smtp_password': bool(smtp_password and smtp_password != '[TO_BE_CONFIGURED]'),
                'mail_default_sender': bool(mail_default_sender and mail_default_sender != '[TO_BE_CONFIGURED]')
            },
            'missing_fields': missing_fields,
            'configuration_summary': {
                'smtp_server': smtp_server if smtp_server != '[TO_BE_CONFIGURED]' else 'Not configured',
                'smtp_port': smtp_port if smtp_port != '[TO_BE_CONFIGURED]' else 'Not configured',
                'smtp_username': smtp_username if smtp_username != '[TO_BE_CONFIGURED]' else 'Not configured',
                'smtp_use_tls': smtp_use_tls == 'true',
                'smtp_use_ssl': smtp_use_ssl == 'true',
                'mail_default_sender': mail_default_sender if mail_default_sender != '[TO_BE_CONFIGURED]' else 'Not configured'
            }
        }
        
        return jsonify({'success': True, 'status': status_info})
        
    except Exception as e:
        logger.error(f"Error getting SMTP status: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_secrets_bp.route('/api/test-email-recipients', methods=['POST'])
@login_required
@superadmin_required
def test_email_recipients():
    """Send test emails to configured recipients"""
    try:
        logger.info("Starting test email recipients process")
        
        data = request.get_json()
        handover_recipients = data.get('handover_recipients', '').strip()
        priority_recipients = data.get('priority_recipients', '').strip()
        
        logger.info(f"Test email request - handover: {handover_recipients}, priority: {priority_recipients}")
        
        # Check if SMTP is configured first
        from models.smtp_config import SMTPConfig
        if not SMTPConfig.is_configured():
            logger.error("SMTP not configured")
            return jsonify({'success': False, 'error': 'SMTP configuration is incomplete. Please configure SMTP settings first in the SMTP Email tab.'}), 400
        
        # Try to get Flask-Mail instance
        from flask import current_app
        mail = current_app.extensions.get('mail')
        
        if not mail:
            logger.error("Flask-Mail not initialized")
            return jsonify({'success': False, 'error': 'Email service is not initialized. Please check your SMTP configuration and restart the application.'}), 500
        
        # Prepare recipient lists
        recipients_to_test = []
        if handover_recipients:
            recipients_to_test.extend([email.strip() for email in handover_recipients.split(',') if email.strip()])
        if priority_recipients:
            recipients_to_test.extend([email.strip() for email in priority_recipients.split(',') if email.strip()])
        
        # Remove duplicates
        recipients_to_test = list(set(recipients_to_test))
        
        if not recipients_to_test:
            logger.warning("No recipients to test")
            return jsonify({'success': False, 'error': 'No recipients configured to test. Please add email recipients first.'}), 400
        
        logger.info(f"Sending test email to {len(recipients_to_test)} recipients: {recipients_to_test}")
        
        # Send test email
        from flask_mail import Message
        from datetime import datetime
        
        subject = "🧪 Shift Handover Email Test - Configuration Verification"
        
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
                <h2 style="margin: 0;">🧪 Email Configuration Test</h2>
                <p style="margin: 10px 0 0 0;">This is a test email to verify your shift handover email configuration.</p>
            </div>
            
            <div style="padding: 20px; background-color: #f8f9fa; border-radius: 8px; margin-bottom: 20px;">
                <h3 style="color: #495057;">✅ Configuration Status</h3>
                <p><strong>Test Recipients:</strong> {len(recipients_to_test)} email addresses</p>
                <p><strong>Handover Recipients:</strong> {"Configured" if handover_recipients else "Not configured"}</p>
                <p><strong>Priority Alert Recipients:</strong> {"Configured" if priority_recipients else "Not configured"}</p>
                <p><strong>Test Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            
            <div style="padding: 15px; background-color: #d1ecf1; border-radius: 5px; border-left: 4px solid #bee5eb;">
                <p style="margin: 0;"><strong>✉️ If you received this email:</strong></p>
                <p style="margin: 5px 0 0 0;">Your email configuration is working correctly! You will receive shift handover notifications at this address.</p>
            </div>
            
            <div style="margin-top: 30px; padding: 15px; background-color: #f8f9fa; border-radius: 5px; font-size: 0.9em; color: #6c757d;">
                <p style="margin: 0;"><strong>🔧 Generated by:</strong> Shift Handover Management System</p>
                <p style="margin: 5px 0 0 0;"><strong>🏢 Administrator:</strong> {current_user.username}</p>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        EMAIL CONFIGURATION TEST
        ========================
        
        This is a test email to verify your shift handover email configuration.
        
        Configuration Status:
        - Test Recipients: {len(recipients_to_test)} email addresses
        - Handover Recipients: {"Configured" if handover_recipients else "Not configured"}
        - Priority Alert Recipients: {"Configured" if priority_recipients else "Not configured"}
        - Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        
        If you received this email, your email configuration is working correctly!
        
        Generated by: Shift Handover Management System
        Administrator: {current_user.username}
        """
        
        # Get the configured default sender
        sender = current_app.config.get('MAIL_DEFAULT_SENDER')
        if not sender:
            sender = current_app.config.get('MAIL_USERNAME')
        
        # If Flask config doesn't have sender, try to load from SMTPConfig directly
        if not sender:
            try:
                from models.smtp_config import SMTPConfig
                sender = SMTPConfig.get_config('mail_default_sender')
                print(f"[ADMIN] ✅ Loaded sender from SMTPConfig: {sender}")
            except Exception as e:
                print(f"[ADMIN] ❌ Failed to load sender from SMTPConfig: {e}")
                sender = 'noreply@shift-handover.local'  # Final fallback
                print(f"[ADMIN] ⚠️ Using fallback sender: {sender}")
        
        print(f"[ADMIN] 📧 Using sender for test email: {sender}")
        
        msg = Message(subject=subject, recipients=recipients_to_test, sender=sender)
        msg.body = text_content
        msg.html = html_content
        
        # Try to send the email
        logger.info("Attempting to send test email...")
        mail.send(msg)
        logger.info("Test email sent successfully")
        
        # Log the action
        from services.audit_service import log_action
        log_action('Test Email Recipients', f'Test email sent to {len(recipients_to_test)} recipients: {", ".join(recipients_to_test)}')
        
        return jsonify({
            'success': True, 
            'message': f'✅ Test emails sent successfully to {len(recipients_to_test)} recipients! Please check the recipient inboxes (including spam/junk folders).',
            'recipients_count': len(recipients_to_test),
            'recipients': recipients_to_test
        })
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error sending test emails: {error_msg}")
        
        # Provide more specific error messages for common issues
        if 'SMTPAuthenticationError' in error_msg:
            error_msg = "SMTP Authentication failed. Please check your username and password in SMTP configuration."
        elif 'SMTPConnectError' in error_msg:
            error_msg = "Cannot connect to SMTP server. Please check your SMTP server and port settings."
        elif 'SMTPServerDisconnected' in error_msg:
            error_msg = "SMTP server disconnected. Please check your SMTP configuration and try again."
        elif 'gaierror' in error_msg or 'Name or service not known' in error_msg:
            error_msg = "Cannot resolve SMTP server hostname. Please check your SMTP server address."
        
        return jsonify({'success': False, 'error': f'❌ Failed to send test emails: {error_msg}'}), 500


def validate_email_list(email_string):
    """Validate a comma-separated list of email addresses"""
    if not email_string:
        return True  # Empty is valid
    
    import re
    emails = [email.strip() for email in email_string.split(',') if email.strip()]
    email_regex = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
    
    return all(email_regex.match(email) for email in emails)
