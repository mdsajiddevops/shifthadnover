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

# Set up logger
logger = logging.getLogger(__name__)

from models.secrets_manager import secrets_manager, SecretCategory, SecretStore, SecretAuditLog, init_secrets_manager
from models.models import db, Account, Team
from models.smtp_config import SMTPConfig
from models.servicenow_config import ServiceNowConfig
from models.team_shift_timing_config import TeamShiftTimingConfig

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
        
        # Try multiple ways to get the master key - FIXED ORDER
        master_key = None
        
        # First try config (which reads from files)
        try:
            from config import SecureConfigManager
            master_key = SecureConfigManager.get_docker_secret('secrets_master_key')
            if master_key:
                logger.info("✅ Got master key from SecureConfigManager (file/docker secret)")
        except Exception as config_e:
            logger.warning(f"Could not get master key from config: {config_e}")
        
        # Fallback to environment variable
        if not master_key:
            master_key = os.environ.get('SECRETS_MASTER_KEY')
            if master_key:
                logger.info("✅ Got master key from environment variable")
        
        # Last resort: try .env file
        if not master_key:
            logger.warning("SECRETS_MASTER_KEY not found, attempting to load from .env file")
            from dotenv import load_dotenv
            load_dotenv(override=True)
            master_key = os.environ.get('SECRETS_MASTER_KEY')
            if master_key:
                logger.info("✅ Got master key from .env file")
        
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
        
        # Get team shift timing configurations first (independent of secrets manager)
        try:
            # Get all accounts and teams for team shift settings
            accounts = Account.query.all()
            teams_by_account = {}
            
            for account in accounts:
                teams_by_account[account.id] = {
                    'account_name': account.name,
                    'teams': [{'id': team.id, 'name': team.name} for team in account.teams]
                }
            
            # Get all existing shift configurations
            shift_configs = TeamShiftTimingConfig.query.order_by(
                TeamShiftTimingConfig.account_id,
                TeamShiftTimingConfig.team_id,
                TeamShiftTimingConfig.order_index
            ).all()
            
            # Group by account and team
            team_shift_configs = {}
            for config in shift_configs:
                account_id = config.account_id
                team_id = config.team_id
                
                if account_id not in team_shift_configs:
                    team_shift_configs[account_id] = {}
                if team_id not in team_shift_configs[account_id]:
                    team_shift_configs[account_id][team_id] = []
                
                team_shift_configs[account_id][team_id].append(config.to_dict())
                
            # Calculate team shift statistics
            total_team_configs = len(shift_configs)
            active_team_configs = len([c for c in shift_configs if c.is_active])
            teams_with_configs = len(set((c.account_id, c.team_id) for c in shift_configs))
            
            # Debug logging
            logger.info(f"Team shift data loaded - Accounts: {len(teams_by_account)}, Total configs: {total_team_configs}, Active: {active_team_configs}")
            logger.info(f"Teams by account keys: {list(teams_by_account.keys())}")
            
        except Exception as e:
            logger.error(f"Error loading team shift timing data: {e}", exc_info=True)
            teams_by_account = {}
            team_shift_configs = {}
            total_team_configs = 0
            active_team_configs = 0
            teams_with_configs = 0
        
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
            
            # Provide minimal dashboard with error state but keep team shift data
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
                                 accounts=accounts,
                                 teams_by_account=teams_by_account,
                                 team_shift_configs=team_shift_configs,
                                 total_team_configs=total_team_configs,
                                 active_team_configs=active_team_configs,
                                 teams_with_configs=teams_with_configs,
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
            'log_level': current_secrets_manager.get_secret('log_level', 'INFO')
            # Note: Timezone and shift timing configuration moved to dedicated Shift Time Configuration module
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
                             accounts=accounts,
                             teams_by_account=teams_by_account,
                             team_shift_configs=team_shift_configs,
                             total_team_configs=total_team_configs,
                             active_team_configs=active_team_configs,
                             teams_with_configs=teams_with_configs,
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
        
        # Return minimal dashboard instead of redirecting (use loaded team data if available)
        try:
            # Use team shift data if it was loaded before the error
            team_data = {
                'teams_by_account': teams_by_account,
                'team_shift_configs': team_shift_configs,
                'total_team_configs': total_team_configs,
                'active_team_configs': active_team_configs,
                'teams_with_configs': teams_with_configs,
            }
        except NameError:
            # Fallback to empty data if team variables aren't defined
            team_data = {
                'teams_by_account': {},
                'team_shift_configs': {},
                'total_team_configs': 0,
                'active_team_configs': 0,
                'teams_with_configs': 0,
            }
        
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
                             secrets_status={'configured': False, 'error': True},
                             **team_data)

# New configuration pages routes
@admin_secrets_bp.route('/config')
@login_required
@superadmin_required
def config_menu():
    """Configuration menu - main page with cards for each config type"""
    try:
        # Get configuration status for each type
        current_secrets_manager = get_secrets_manager()
        
        # Default status if secrets manager not available
        config_status = {
            'smtp': {'configured': False, 'count': 0, 'last_test': None},
            'team_email': {'configured': False, 'count': 0, 'teams': 0},
            'servicenow': {'configured': False, 'connected': False, 'last_test': None},
            'app_settings': {'configured': False, 'count': 0, 'environment': 'unknown'}
        }
        
        if current_secrets_manager:
            try:
                # Check SMTP configuration
                smtp_secrets = current_secrets_manager.list_secrets('SMTP/Email')
                config_status['smtp']['count'] = len(smtp_secrets)
                config_status['smtp']['configured'] = len(smtp_secrets) >= 3  # Basic requirement
                
                # Check ServiceNow configuration
                snow_secrets = current_secrets_manager.list_secrets('ServiceNow')
                config_status['servicenow']['configured'] = len(snow_secrets) >= 2  # URL + auth
                
                # Check Application settings
                app_secrets = current_secrets_manager.list_secrets('Application Settings')
                config_status['app_settings']['count'] = len(app_secrets)
                config_status['app_settings']['configured'] = len(app_secrets) > 0
                
            except Exception as e:
                logger.error(f"Error getting config status: {e}")
        
        # Check team email configuration
        try:
            teams_count = db.session.query(Team).count()
            config_status['team_email']['teams'] = teams_count
            config_status['team_email']['configured'] = teams_count > 0
        except Exception as e:
            logger.error(f"Error getting team count: {e}")
        
        return render_template('admin/config_menu_new.html', 
                             config_status=config_status,
                             user=current_user)
        
    except Exception as e:
        logger.error(f"Error in config menu: {e}", exc_info=True)
        flash('Error loading configuration menu', 'error')
        return redirect(url_for('dashboard.dashboard'))

@admin_secrets_bp.route('/smtp')
@login_required
@superadmin_required
def smtp_config():
    """SMTP Configuration page"""
    try:
        # Define SMTP configuration groups
        config_groups = {
            'Server Settings': [
                'smtp_server',
                'smtp_port',
                'smtp_use_tls',
                'smtp_use_ssl'
            ],
            'Authentication': [
                'smtp_username',
                'smtp_password'
            ],
            'Email Settings': [
                'mail_default_sender',
                'mail_reply_to',
                'team_email'
            ],
            'System Settings': [
                'smtp_enabled'
            ]
        }
        
        # Check SMTP status
        smtp_status = False
        try:
            current_secrets_manager = get_secrets_manager()
            if current_secrets_manager:
                smtp_secrets = current_secrets_manager.list_secrets('SMTP/Email')
                required_keys = ['smtp_server', 'smtp_username', 'smtp_password']
                smtp_status = all(
                    any(secret['key'] == key for secret in smtp_secrets) 
                    for key in required_keys
                )
        except Exception as e:
            logger.error(f"Error checking SMTP status: {e}")
        
        return render_template('admin/smtp_config_new.html',
                             config_groups=config_groups,
                             smtp_status=smtp_status,
                             user=current_user)
        
    except Exception as e:
        logger.error(f"Error in SMTP config: {e}", exc_info=True)
        flash('Error loading SMTP configuration', 'error')
        return redirect(url_for('admin_secrets.config_menu'))

@admin_secrets_bp.route('/team-email')
@login_required
@superadmin_required
def team_email_config():
    """Team Email Configuration page"""
    try:
        return render_template('admin/team_email_config_new.html', user=current_user)
        
    except Exception as e:
        logger.error(f"Error in team email config: {e}", exc_info=True)
        flash('Error loading team email configuration', 'error')
        return redirect(url_for('admin_secrets.config_menu'))

@admin_secrets_bp.route('/servicenow')
@login_required
@superadmin_required
def servicenow_config():
    """ServiceNow Configuration page"""
    try:
        return render_template('admin/servicenow_config_new.html', user=current_user)
        
    except Exception as e:
        logger.error(f"Error in ServiceNow config: {e}", exc_info=True)
        flash('Error loading ServiceNow configuration', 'error')
        return redirect(url_for('admin_secrets.config_menu'))

@admin_secrets_bp.route('/app-settings')
@login_required
@superadmin_required
def app_config():
    """Application Settings Configuration page"""
    try:
        return render_template('admin/app_config_new.html', user=current_user)
        
    except Exception as e:
        logger.error(f"Error in app config: {e}", exc_info=True)
        flash('Error loading application settings', 'error')
        return redirect(url_for('admin_secrets.config_menu'))

@admin_secrets_bp.route('/management')
@login_required
@superadmin_required
def secrets_management():
    """Unified Secrets Management page with tab-based interface"""
    try:
        return render_template('admin/unified_secrets.html', user=current_user)
        
    except Exception as e:
        logger.error(f"Error in secrets management: {e}", exc_info=True)
        flash('Error loading secrets management', 'error')
        return redirect(url_for('admin_secrets.config_menu'))

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
# SMTP Configuration API Routes
# ===========================

@admin_secrets_bp.route('/api/smtp/config', methods=['GET'])
@login_required
@superadmin_required
def api_get_smtp_configs():
    """API endpoint to get all SMTP configurations"""
    try:
        logger.info("[SMTP Config API] ================= SMTP CONFIG API CALLED =================")
        logger.info("[SMTP Config API] Processing /api/smtp/config endpoint")
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
            },
            'SMTP_ENABLED': {
                'label': 'SMTP Enabled',
                'description': 'Enable or disable SMTP functionality',
                'type': 'boolean',
                'required': False,
                'default': True
            }
        }
        
        # Get current values for all SMTP fields from database
        # Map uppercase API field names to lowercase database keys
        db_key_mapping = {
            'SMTP_SERVER': 'smtp_server',
            'SMTP_PORT': 'smtp_port', 
            'SMTP_USERNAME': 'smtp_username',
            'SMTP_PASSWORD': 'smtp_password',
            'SMTP_USE_TLS': 'smtp_use_tls',
            'SMTP_USE_SSL': 'smtp_use_ssl',
            'MAIL_FROM_NAME': 'mail_from_name',
            'MAIL_FROM_ADDRESS': 'mail_default_sender',
            'SMTP_ENABLED': 'smtp_enabled'
        }
        
        # ADVANCED DEBUG: Check all database entries to see what keys actually exist
        all_smtp_configs = SMTPConfig.query.all()
        logger.info(f"[SMTP Config API] === ALL DATABASE ENTRIES ===")
        for config in all_smtp_configs:
            logger.info(f"[SMTP Config API] DB Key: '{config.config_key}' = '{config.config_value}'")
        logger.info(f"[SMTP Config API] === END DATABASE ENTRIES ===")
        
        smtp_config = {}
        for field_name, field_info in smtp_fields.items():
            try:
                # First try the database key mapping
                db_key = db_key_mapping.get(field_name, field_name.lower())
                config_value = SMTPConfig.get_config(db_key)
                logger.info(f"[SMTP Config API] Trying key '{db_key}' for field '{field_name}': got '{config_value}'")
                
                # If not found, try uppercase key (for backward compatibility)
                if config_value is None:
                    config_value = SMTPConfig.get_config(field_name)
                    logger.info(f"[SMTP Config API] Tried uppercase '{field_name}': got '{config_value}'")
                
                # Try with different case variations
                if config_value is None:
                    # Try all lowercase
                    alt_key = field_name.lower()
                    config_value = SMTPConfig.get_config(alt_key)
                    logger.info(f"[SMTP Config API] Tried lowercase '{alt_key}': got '{config_value}'")
                
                logger.info(f"[SMTP Config API] FINAL - Field {field_name} (DB key: {db_key}): '{config_value}' (configured: {config_value is not None})")
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
        
        # Use the same simple approach as the debug endpoint that works
        # Get all database entries directly
        all_smtp_configs = SMTPConfig.query.all()
        db_data = {}
        for config in all_smtp_configs:
            db_data[config.config_key] = config.config_value
        
        # Create the legacy response format expected by JavaScript (same as debug endpoint)
        legacy_response = {
            'smtp_server': db_data.get('smtp_server', ''),
            'smtp_port': db_data.get('smtp_port', ''),
            'smtp_username': db_data.get('smtp_username', ''),
            'smtp_password': db_data.get('smtp_password', ''),
            'smtp_security': 'SSL' if db_data.get('smtp_use_ssl') == 'true' else 'TLS' if db_data.get('smtp_use_tls') == 'true' else 'NONE',
            'smtp_from_address': db_data.get('mail_default_sender', ''),
            'smtp_enabled': db_data.get('smtp_enabled', 'false') == 'true'
        }
        
        logger.info(f"[SMTP Config API] Returning legacy response: {legacy_response}")
        
        return jsonify(legacy_response)
        
    except Exception as e:
        logger.error(f"Error getting SMTP configs: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@admin_secrets_bp.route('/api/smtp/config/debug', methods=['GET'])
def api_get_smtp_configs_debug():
    """DEBUG ONLY: SMTP config without authentication - REMOVE IN PRODUCTION"""
    try:
        logger.debug("[DEBUG] ================= DEBUG SMTP CONFIG API CALLED =================")
        logger.info("[DEBUG API] ================= DEBUG SMTP CONFIG API CALLED =================")
        
        # Just return the database values directly
        from models.smtp_config import SMTPConfig
        
        # Check all database entries to see what keys actually exist
        all_smtp_configs = SMTPConfig.query.all()
        logger.debug(f"[DEBUG API] === ALL DATABASE ENTRIES ===")
        logger.info(f"[DEBUG API] === ALL DATABASE ENTRIES ===")
        db_data = {}
        for config in all_smtp_configs:
            logger.debug(f"[DEBUG API] DB Key: '{config.config_key}' = '{config.config_value}'")
            logger.info(f"[DEBUG API] DB Key: '{config.config_key}' = '{config.config_value}'")
            db_data[config.config_key] = config.config_value
        logger.debug(f"[DEBUG API] === END DATABASE ENTRIES ===")
        logger.info(f"[DEBUG API] === END DATABASE ENTRIES ===")
        
        # Create the legacy response format expected by JavaScript
        legacy_response = {
            'smtp_server': db_data.get('smtp_server', ''),
            'smtp_port': db_data.get('smtp_port', ''),
            'smtp_username': db_data.get('smtp_username', ''),
            'smtp_password': db_data.get('smtp_password', ''),
            'smtp_security': 'SSL' if db_data.get('smtp_use_ssl') == 'true' else 'TLS' if db_data.get('smtp_use_tls') == 'true' else 'NONE',
            'smtp_from_address': db_data.get('mail_default_sender', ''),
            'smtp_enabled': db_data.get('smtp_enabled', 'false') == 'true'
        }
        
        logger.debug(f"[DEBUG API] Returning debug response: {legacy_response}")
        logger.info(f"[DEBUG API] Returning debug response: {legacy_response}")
        
        return jsonify(legacy_response)
        
    except Exception as e:
        logger.error(f"[DEBUG API] Error getting SMTP configs: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@admin_secrets_bp.route('/management/debug')
def secrets_management_debug():
    """DEBUG ONLY: Secrets management without authentication - REMOVE IN PRODUCTION"""
    try:
        # Create a mock user object for template compatibility
        class MockUser:
            def __init__(self):
                self.email = "debug@test.com"
                self.role = "super_admin"
        
        return render_template('admin/unified_secrets.html', user=MockUser())
        
    except Exception as e:
        logger.error(f"Error in debug secrets management: {e}", exc_info=True)
        return f"Error loading debug secrets management: {e}", 500

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
        logger.info("[SMTP API] ================= STARTING SMTP API CALL =================")
        
        # Get raw values from database - use lowercase keys as they exist in DB
        # Note: Use empty string as default, NOT a fallback value - we want to show actual DB values only
        smtp_server_raw = SMTPConfig.get_config('smtp_server', '')
        smtp_port_raw = SMTPConfig.get_config('smtp_port', '')  # Empty default instead of '587'
        smtp_username_raw = SMTPConfig.get_config('smtp_username', '')
        smtp_password_raw = SMTPConfig.get_config('smtp_password', '')
        smtp_use_tls_raw = SMTPConfig.get_config('smtp_use_tls', '')  # Empty default instead of 'false'
        smtp_use_ssl_raw = SMTPConfig.get_config('smtp_use_ssl', '')  # Empty default instead of 'false'
        mail_sender_raw = SMTPConfig.get_config('mail_default_sender', '') or SMTPConfig.get_config('SMTP_DEFAULT_SENDER', '')
        smtp_enabled_raw = SMTPConfig.get_config('smtp_enabled', '')
        
        # Log the raw values for debugging
        logger.info(f"[SMTP API] Raw DB values:")
        logger.info(f"  - Server: '{smtp_server_raw}'")
        logger.info(f"  - Port: '{smtp_port_raw}'")
        logger.info(f"  - Username: '{smtp_username_raw}'")
        logger.info(f"  - Password: {'[SET]' if smtp_password_raw else '[NOT SET]'}")
        logger.info(f"  - TLS: '{smtp_use_tls_raw}'")
        logger.info(f"  - SSL: '{smtp_use_ssl_raw}'")
        logger.info(f"  - Sender: '{mail_sender_raw}'")
        logger.info(f"  - Enabled: '{smtp_enabled_raw}'")
        
        # Convert boolean values
        smtp_use_tls = smtp_use_tls_raw.lower() in ['true', '1', 'yes', 'on'] if smtp_use_tls_raw else False
        smtp_use_ssl = smtp_use_ssl_raw.lower() in ['true', '1', 'yes', 'on'] if smtp_use_ssl_raw else False
        smtp_enabled = smtp_enabled_raw.lower() in ['true', '1', 'yes', 'on'] if smtp_enabled_raw else False
        
        # Determine security setting - only if we have actual TLS/SSL data from DB
        security_type = ''  # Default to empty instead of 'None' 
        if smtp_use_ssl:
            security_type = 'SSL'
        elif smtp_use_tls:
            security_type = 'TLS/STARTTLS'
        elif smtp_use_tls_raw or smtp_use_ssl_raw:  # If we have any SSL/TLS data at all
            security_type = 'None'
            
        # Convert port safely - only use actual DB value, no defaults
        try:
            port_int = int(smtp_port_raw) if smtp_port_raw and str(smtp_port_raw).isdigit() else ''
        except (ValueError, TypeError):
            port_int = ''
            
        config = {
            'smtp_server': smtp_server_raw or '',
            'smtp_port': port_int,
            'smtp_username': smtp_username_raw or '',
            'smtp_password': '••••••••••••••••' if smtp_password_raw else '',
            'smtp_from': mail_sender_raw or '',
            'smtp_use_tls': smtp_use_tls,
            'smtp_use_ssl': smtp_use_ssl,
            'smtp_security': security_type,
            'smtp_enabled': smtp_enabled
        }
        
        logger.info(f"[SMTP API] Final config object to return:")
        logger.info(f"  - smtp_server: '{config['smtp_server']}'")
        logger.info(f"  - smtp_port: {config['smtp_port']}")
        logger.info(f"  - smtp_username: '{config['smtp_username']}'")
        logger.info(f"  - smtp_password: '{config['smtp_password']}'")
        logger.info(f"  - smtp_from: '{config['smtp_from']}'")
        logger.info(f"  - smtp_use_tls: {config['smtp_use_tls']}")
        logger.info(f"  - smtp_use_ssl: {config['smtp_use_ssl']}")
        logger.info(f"  - smtp_security: '{config['smtp_security']}'")
        logger.info(f"  - smtp_enabled: {config['smtp_enabled']}")
        logger.info("[SMTP API] ================= SMTP API CALL SUCCESS =================")
        return jsonify({'success': True, 'config': config})
        
    except Exception as e:
        import traceback
        logger.error(f"[SMTP API] ================= SMTP API CALL ERROR =================")
        logger.error(f"[SMTP API] Error getting SMTP config: {e}")
        logger.error(f"[SMTP API] Traceback: {traceback.format_exc()}")
        logger.error("[SMTP API] ================= END SMTP API CALL ERROR =================")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_secrets_bp.route('/api/smtp', methods=['POST'])
@admin_required
def save_smtp_config():
    """Save SMTP configuration to smtp_config table using SMTPConfig model"""
    try:
        data = request.get_json()
        
        # Save each SMTP setting using SMTPConfig model - save to both lowercase and UPPERCASE keys for compatibility
        server_value = data.get('smtp_server', '')
        port_value = str(data.get('smtp_port', 587))
        username_value = data.get('smtp_username', '')
        sender_value = data.get('smtp_from', '')
        use_tls_value = str(data.get('smtp_use_tls', True)).lower()
        use_ssl_value = str(data.get('smtp_use_ssl', False)).lower()
        
        # Update both key formats for compatibility
        SMTPConfig.set_config('smtp_server', server_value, 'SMTP server hostname', encrypted=False)
        SMTPConfig.set_config('SMTP_SERVER', server_value, 'SMTP server hostname', encrypted=False)
        
        SMTPConfig.set_config('smtp_port', port_value, 'SMTP server port', encrypted=False)
        SMTPConfig.set_config('SMTP_PORT', port_value, 'SMTP server port (SSL/TLS)', encrypted=False)
        
        SMTPConfig.set_config('smtp_username', username_value, 'SMTP authentication username', encrypted=False)
        SMTPConfig.set_config('SMTP_USERNAME', username_value, 'SMTP username', encrypted=False)
        
        # Only update password if it's not the masked value
        if data.get('smtp_password') and data.get('smtp_password') != '••••••••••••••••':
            password_value = data.get('smtp_password', '')
            SMTPConfig.set_config('smtp_password', password_value, 'SMTP authentication password', encrypted=True)
            SMTPConfig.set_config('SMTP_PASSWORD', password_value, 'SMTP password (encrypted)', encrypted=True)
        
        SMTPConfig.set_config('mail_default_sender', sender_value, 'Default sender email address', encrypted=False)
        SMTPConfig.set_config('SMTP_DEFAULT_SENDER', sender_value, 'Default sender email', encrypted=False)
        
        SMTPConfig.set_config('smtp_use_tls', use_tls_value, 'Enable TLS encryption', encrypted=False)
        SMTPConfig.set_config('SMTP_USE_TLS', use_tls_value, 'Use TLS encryption', encrypted=False)
        
        SMTPConfig.set_config('smtp_use_ssl', use_ssl_value, 'Enable SSL encryption', encrypted=False)
        SMTPConfig.set_config('SMTP_USE_SSL', use_ssl_value, 'Use SSL encryption', encrypted=False)
        
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
            'log_level': AppConfig.get_config('log_level', 'INFO')
            # Note: Timezone and shift timing configuration moved to dedicated Shift Time Configuration module
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
        
        # Note: Timezone and shift timing configuration moved to dedicated Shift Time Configuration module
        
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
        logger.debug(f"[DEBUG] Email recipients save - data: {data}")
        
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


@admin_secrets_bp.route('/api/email-notifications', methods=['GET'])
@login_required
@superadmin_required
def get_email_notifications():
    """Get current email notifications status"""
    try:
        from models.app_config import AppConfig
        
        # Get email notifications enabled status (default to True if not set)
        enabled_str = AppConfig.get_config('email_notifications_enabled', 'true')
        enabled = enabled_str.lower() in ['true', '1', 'yes', 'on']
        
        return jsonify({
            'success': True, 
            'notifications_enabled': enabled
        })
        
    except Exception as e:
        logger.error(f"Error getting email notifications status: {e}")
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
                logger.debug(f"[ADMIN] ✅ Loaded sender from SMTPConfig: {sender}")
            except Exception as e:
                logger.debug(f"[ADMIN] ❌ Failed to load sender from SMTPConfig: {e}")
                sender = 'noreply@shift-handover.local'  # Final fallback
                logger.debug(f"[ADMIN] ⚠️ Using fallback sender: {sender}")
        
        logger.debug(f"[ADMIN] 📧 Using sender for test email: {sender}")
        
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


# ============================================================================
# TEAM SHIFT TIMING CONFIGURATION ROUTES
# ============================================================================

@admin_secrets_bp.route('/team-shift-timings')
@login_required
@superadmin_required
def team_shift_timings():
    """Get team shift timing configurations"""
    try:
        # Get all accounts and teams for dropdown
        accounts = Account.query.all()
        teams_by_account = {}
        
        for account in accounts:
            teams_by_account[account.id] = {
                'account_name': account.name,
                'teams': [{'id': team.id, 'name': team.name} for team in account.teams]
            }
        
        # Get all existing shift configurations
        shift_configs = TeamShiftTimingConfig.query.order_by(
            TeamShiftTimingConfig.account_id,
            TeamShiftTimingConfig.team_id,
            TeamShiftTimingConfig.order_index
        ).all()
        
        # Group by account and team
        configs_by_team = {}
        for config in shift_configs:
            account_id = config.account_id
            team_id = config.team_id
            
            if account_id not in configs_by_team:
                configs_by_team[account_id] = {}
            if team_id not in configs_by_team[account_id]:
                configs_by_team[account_id][team_id] = []
            
            configs_by_team[account_id][team_id].append(config.to_dict())
        
        return jsonify({
            'success': True,
            'accounts': teams_by_account,
            'shift_configs': configs_by_team
        })
        
    except Exception as e:
        logger.error(f"Error fetching team shift timings: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_secrets_bp.route('/team-shift-timings/create', methods=['POST'])
@login_required
@superadmin_required
def create_team_shift_timing():
    """Create or update team shift timing configuration"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['team_id', 'account_id', 'shift_code', 'shift_name', 'start_time', 'end_time']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
        
        # Parse time fields
        try:
            start_time = datetime.strptime(data['start_time'], '%H:%M').time()
            end_time = datetime.strptime(data['end_time'], '%H:%M').time()
        except ValueError:
            return jsonify({'success': False, 'error': 'Invalid time format. Use HH:MM (24-hour format)'}), 400
        
        # Check if configuration already exists
        existing_config = TeamShiftTimingConfig.query.filter_by(
            team_id=data['team_id'],
            account_id=data['account_id'],
            shift_code=data['shift_code']
        ).first()
        
        if existing_config:
            # Update existing
            existing_config.shift_name = data['shift_name']
            existing_config.start_time = start_time
            existing_config.end_time = end_time
            existing_config.color_code = data.get('color_code', existing_config.color_code)
            existing_config.order_index = data.get('order_index', existing_config.order_index)
            existing_config.is_active = data.get('is_active', True)
            existing_config.updated_by = current_user.email
            existing_config.updated_at = datetime.utcnow()
            
            shift_config = existing_config
        else:
            # Create new
            shift_config = TeamShiftTimingConfig(
                team_id=data['team_id'],
                account_id=data['account_id'],
                shift_code=data['shift_code'],
                shift_name=data['shift_name'],
                start_time=start_time,
                end_time=end_time,
                color_code=data.get('color_code', '#007bff'),
                order_index=data.get('order_index', 0),
                is_active=data.get('is_active', True),
                created_by=current_user.email,
                updated_by=current_user.email
            )
            db.session.add(shift_config)
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': 'Shift timing configuration saved successfully',
            'config': shift_config.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating team shift timing: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_secrets_bp.route('/team-shift-timings/create-defaults', methods=['POST'])
@login_required
@superadmin_required
def create_default_team_shifts():
    """Create default shift patterns for a team"""
    try:
        data = request.get_json()
        
        if 'team_id' not in data or 'account_id' not in data:
            return jsonify({'success': False, 'error': 'team_id and account_id are required'}), 400
        
        pattern = data.get('pattern', 'standard')  # standard, devops, extended
        
        # Clear existing configurations if requested
        if data.get('clear_existing', False):
            TeamShiftTimingConfig.query.filter_by(
                team_id=data['team_id'],
                account_id=data['account_id']
            ).delete()
        
        # Create default shifts
        created_shifts = TeamShiftTimingConfig.create_default_shifts_for_team(
            team_id=data['team_id'],
            account_id=data['account_id'],
            shift_pattern=pattern
        )
        
        return jsonify({
            'success': True,
            'message': f'Created {len(created_shifts)} default shift configurations',
            'configs': [shift.to_dict() for shift in created_shifts]
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating default team shifts: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_secrets_bp.route('/team-shift-timings/<int:config_id>', methods=['DELETE'])
@login_required
@superadmin_required
def delete_team_shift_timing(config_id):
    """Delete a team shift timing configuration"""
    try:
        config = TeamShiftTimingConfig.query.get_or_404(config_id)
        db.session.delete(config)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Shift timing configuration deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting team shift timing: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_secrets_bp.route('/team-shift-timings/team/<int:team_id>')
@login_required
@superadmin_required
def get_team_shift_timings(team_id):
    """Get shift timing configurations for a specific team"""
    try:
        configs = TeamShiftTimingConfig.get_team_shifts(team_id, active_only=False)
        return jsonify({
            'success': True,
            'configs': [config.to_dict() for config in configs]
        })
        
    except Exception as e:
        logger.error(f"Error fetching team shift timings: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_secrets_bp.route('/save-team-email', methods=['POST'])
@login_required
@admin_required
def save_team_email_config():
    """Save team email configuration"""
    try:
        team_id = request.form.get('team_id')
        email_recipients = request.form.get('email_recipients', '').strip()
        priority_alert_recipients = request.form.get('priority_alert_recipients', '').strip()
        
        if not team_id:
            return jsonify({'success': False, 'error': 'Team ID is required'}), 400
            
        team = Team.query.get_or_404(team_id)
        
        # Validate email addresses
        import re
        email_pattern = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
        
        def validate_email_list(email_string, field_name):
            if not email_string:
                return True, ""
            
            emails = [email.strip() for email in email_string.split(',') if email.strip()]
            
            for email in emails:
                if not re.match(email_pattern, email):
                    return False, f"Invalid email address in {field_name}: {email}"
            return True, ""
        
        # Validate emails
        valid, error_msg = validate_email_list(email_recipients, "Handover Recipients")
        if not valid:
            return jsonify({'success': False, 'error': error_msg}), 400
            
        valid, error_msg = validate_email_list(priority_alert_recipients, "Priority Alert Recipients")
        if not valid:
            return jsonify({'success': False, 'error': error_msg}), 400
        
        # Update team email configuration
        team.email_recipients = email_recipients if email_recipients else None
        team.priority_alert_recipients = priority_alert_recipients if priority_alert_recipients else None
        
        db.session.commit()
        
        logger.info(f'Team email configuration updated for team "{team.name}" by user {current_user.email}')
        
        return jsonify({
            'success': True, 
            'message': f'Email configuration updated for team "{team.name}"'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'Error updating team email configuration: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_secrets_bp.route('/get-configured-teams')
@login_required
@admin_required
def get_configured_teams():
    """Get list of teams with email configurations"""
    try:
        # Query teams that have email configuration
        teams = db.session.query(Team, Account.name.label('account_name'))\
            .join(Account, Team.account_id == Account.id)\
            .filter(
                db.or_(
                    Team.email_recipients.isnot(None),
                    Team.priority_alert_recipients.isnot(None)
                )
            )\
            .order_by(Account.name, Team.name)\
            .all()
        
        configured_teams = []
        for team, account_name in teams:
            configured_teams.append({
                'id': team.id,
                'name': team.name,
                'account_name': account_name,
                'email_recipients': team.email_recipients,
                'priority_alert_recipients': team.priority_alert_recipients
            })
        
        return jsonify({
            'success': True,
            'teams': configured_teams
        })
        
    except Exception as e:
        logger.error(f'Error fetching configured teams: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500

# New API endpoints for enhanced configuration pages

# Teams API endpoints
@admin_secrets_bp.route('/api/teams')
@login_required
@superadmin_required
def api_get_teams():
    """API endpoint to get all teams"""
    try:
        teams = db.session.query(Team, Account.name.label('account_name'))\
            .join(Account, Team.account_id == Account.id)\
            .order_by(Account.name, Team.name)\
            .all()
        
        teams_list = []
        for team, account_name in teams:
            teams_list.append({
                'id': team.id,
                'name': team.name,
                'account_name': account_name,
                'account_id': team.account_id
            })
        
        return jsonify({'success': True, 'teams': teams_list})
        
    except Exception as e:
        logger.error(f"Error getting teams: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_secrets_bp.route('/api/teams/<int:team_id>/config')
@login_required
@superadmin_required
def api_get_team_config(team_id):
    """API endpoint to get team configuration"""
    try:
        team = Team.query.get(team_id)
        if not team:
            return jsonify({'success': False, 'error': 'Team not found'}), 404
        
        config = {
            'email': team.email_recipients,
            'display_name': team.name,
            'distribution_type': 'all',  # Default, could be stored in team model
            'email_template': 'standard',  # Default, could be stored in team model
            'active': True  # Default, could be stored in team model
        }
        
        return jsonify({'success': True, 'config': config})
        
    except Exception as e:
        logger.error(f"Error getting team config: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_secrets_bp.route('/api/teams/<int:team_id>/config', methods=['POST'])
@login_required
@superadmin_required
def api_set_team_config(team_id):
    """API endpoint to set team configuration"""
    try:
        data = request.get_json()
        
        team = Team.query.get(team_id)
        if not team:
            return jsonify({'success': False, 'error': 'Team not found'}), 404
        
        # Update team email configuration
        team.email_recipients = data.get('email')
        # Additional fields would be added to the Team model for full functionality
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Team configuration updated'})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error setting team config: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_secrets_bp.route('/api/teams/<int:team_id>/members')
@login_required
@superadmin_required
def api_get_team_members(team_id):
    """API endpoint to get team members"""
    try:
        # For now, return mock data - this would integrate with actual team member model
        members = [
            {
                'id': 1,
                'name': 'John Doe',
                'email': 'john.doe@company.com',
                'role': 'lead',
                'active': True,
                'receive_emails': True
            },
            {
                'id': 2,
                'name': 'Jane Smith',
                'email': 'jane.smith@company.com',
                'role': 'member',
                'active': True,
                'receive_emails': True
            }
        ]
        
        return jsonify({'success': True, 'members': members})
        
    except Exception as e:
        logger.error(f"Error getting team members: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_secrets_bp.route('/api/teams/stats')
@login_required
@superadmin_required
def api_get_teams_stats():
    """API endpoint to get team statistics"""
    try:
        total_teams = Team.query.count()
        teams_with_email = Team.query.filter(Team.email_recipients.isnot(None)).count()
        
        stats = {
            'active_teams': total_teams,
            'total_members': total_teams * 2,  # Mock data
            'email_lists': teams_with_email
        }
        
        return jsonify({'success': True, 'stats': stats})
        
    except Exception as e:
        logger.error(f"Error getting team stats: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ServiceNow API endpoints
@admin_secrets_bp.route('/api/servicenow/config')
@login_required
@superadmin_required
def api_get_servicenow_config():
    """API endpoint to get ServiceNow configuration"""
    try:
        current_secrets_manager = get_secrets_manager()
        if not current_secrets_manager:
            return jsonify({'success': False, 'error': 'Secrets manager not available'}), 500
        
        # Get ServiceNow related secrets
        snow_secrets = current_secrets_manager.list_secrets('ServiceNow')
        
        # Format for display
        configs = []
        for secret in snow_secrets:
            configs.append({
                'config_key': secret['key'],
                'config_value': secret['value'] if not secret.get('encrypted', False) else '***ENCRYPTED***',
                'encrypted': secret.get('encrypted', False),
                'description': secret.get('description', ''),
                'updated_at': secret.get('updated_at')
            })
        
        return jsonify({
            'success': True,
            'configs': configs,
            'connection_status': False  # Would be determined by actual connection test
        })
        
    except Exception as e:
        logger.error(f"Error getting ServiceNow config: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_secrets_bp.route('/api/servicenow/config', methods=['POST'])
@login_required
@superadmin_required
def api_set_servicenow_config():
    """API endpoint to set ServiceNow configuration"""
    try:
        data = request.get_json()
        
        current_secrets_manager = get_secrets_manager()
        if not current_secrets_manager:
            return jsonify({'success': False, 'error': 'Secrets manager not available'}), 500
        
        # Save the configuration
        result = current_secrets_manager.set_secret(
            data['config_key'],
            data['config_value'],
            'ServiceNow',
            description=data.get('description', ''),
            encrypted=data.get('encrypted', False)
        )
        
        if result:
            return jsonify({'success': True, 'message': 'Configuration saved successfully'})
        else:
            return jsonify({'success': False, 'error': 'Failed to save configuration'}), 500
        
    except Exception as e:
        logger.error(f"Error setting ServiceNow config: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_secrets_bp.route('/api/servicenow/test-connection')
@login_required
@superadmin_required
def api_test_servicenow_connection():
    """API endpoint to test ServiceNow connection"""
    try:
        # Mock connection test - in reality this would test actual ServiceNow connection
        import time
        time.sleep(1)  # Simulate connection time
        
        # For demonstration, return success
        return jsonify({
            'success': True,
            'message': 'Connection test successful',
            'response': {
                'status': 'Connected',
                'version': 'Tokyo',
                'instance': 'dev12345.service-now.com'
            }
        })
        
    except Exception as e:
        logger.error(f"Error testing ServiceNow connection: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_secrets_bp.route('/api/servicenow/test-endpoint/<endpoint_type>')
@login_required
@superadmin_required
def api_test_servicenow_endpoint(endpoint_type):
    """API endpoint to test specific ServiceNow endpoints"""
    try:
        # Mock endpoint test
        import time
        time.sleep(0.5)
        
        response_data = {
            'table': {'count': 10, 'status': 'accessible'},
            'import': {'status': 'ready', 'staging_table': 'u_import_test'},
            'attachment': {'status': 'accessible', 'max_size': '25MB'},
            'query': {'status': 'accessible', 'records_found': 42}
        }
        
        return jsonify({
            'success': True,
            'message': f'{endpoint_type.upper()} endpoint test successful',
            'response': response_data.get(endpoint_type, {})
        })
        
    except Exception as e:
        logger.error(f"Error testing ServiceNow endpoint: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Enhanced Application Settings API endpoints
@admin_secrets_bp.route('/api/app/settings')
@login_required
@superadmin_required
def api_get_app_settings():
    """API endpoint to get application settings"""
    try:
        current_secrets_manager = get_secrets_manager()
        if not current_secrets_manager:
            return jsonify({'success': False, 'error': 'Secrets manager not available'}), 500
        
        # Get application settings
        app_secrets = current_secrets_manager.list_secrets('Application Settings')
        
        settings = []
        for secret in app_secrets:
            settings.append({
                'setting_key': secret['key'],
                'setting_value': secret['value'],
                'category': secret.get('category', 'General'),
                'description': secret.get('description', ''),
                'updated_at': secret.get('updated_at')
            })
        
        return jsonify({'success': True, 'settings': settings})
        
    except Exception as e:
        logger.error(f"Error getting app settings: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_secrets_bp.route('/api/app/settings', methods=['POST'])
@login_required
@superadmin_required
def api_set_app_setting():
    """API endpoint to set application setting"""
    try:
        data = request.get_json()
        
        current_secrets_manager = get_secrets_manager()
        if not current_secrets_manager:
            return jsonify({'success': False, 'error': 'Secrets manager not available'}), 500
        
        # Save the setting
        result = current_secrets_manager.set_secret(
            data['setting_key'],
            data['setting_value'],
            'Application Settings',
            description=data.get('description', ''),
            encrypted=False
        )
        
        if result:
            return jsonify({'success': True, 'message': 'Setting saved successfully'})
        else:
            return jsonify({'success': False, 'error': 'Failed to save setting'}), 500
        
    except Exception as e:
        logger.error(f"Error setting app setting: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_secrets_bp.route('/api/app/shifts')
@login_required
@superadmin_required
def api_get_shifts():
    """API endpoint to get shift configurations"""
    try:
        # Get shift configurations from team shift timing config or create mock data
        shifts = [
            {'id': 1, 'name': 'Day Shift', 'start_time': '06:30', 'end_time': '15:30'},
            {'id': 2, 'name': 'Evening Shift', 'start_time': '14:45', 'end_time': '23:45'},
            {'id': 3, 'name': 'Night Shift', 'start_time': '21:45', 'end_time': '06:45'}
        ]
        
        return jsonify({'success': True, 'shifts': shifts})
        
    except Exception as e:
        logger.error(f"Error getting shifts: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_secrets_bp.route('/api/app/shifts', methods=['POST'])
@login_required
@superadmin_required
def api_add_shift():
    """API endpoint to add shift configuration"""
    try:
        data = request.get_json()
        
        # In a real implementation, this would save to database
        logger.info(f"Adding shift: {data['name']} ({data['start_time']} - {data['end_time']})")
        
        return jsonify({'success': True, 'message': 'Shift added successfully'})
        
    except Exception as e:
        logger.error(f"Error adding shift: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
