from flask import Flask, render_template, request, jsonify, redirect
from werkzeug.middleware.proxy_fix import ProxyFix

# from services.audit_service import log_action

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from flask_migrate import Migrate
from config import Config
import os
import time
import logging
from logging.handlers import RotatingFileHandler

# Import secrets management system
from models.secrets_manager import init_secrets_manager, secrets_manager

# =============================================================
# Configure Logging - Phase 1 Performance Improvement
# =============================================================
def setup_logging(app):
    """Configure application logging with proper levels and handlers"""
    
    # Create logs directory if it doesn't exist
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # Set log level based on environment
    log_level = logging.DEBUG if app.debug else logging.INFO
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # File handler for all logs (rotating, max 10MB, keep 5 backups)
    file_handler = RotatingFileHandler(
        'logs/app.log', 
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(log_level)
    
    # Error file handler (only errors)
    error_handler = RotatingFileHandler(
        'logs/error.log',
        maxBytes=10*1024*1024,
        backupCount=5
    )
    error_handler.setFormatter(formatter)
    error_handler.setLevel(logging.ERROR)
    
    # Console handler (only in development)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(error_handler)
    
    # Only add console handler in development
    if os.environ.get('LOCAL_DEVELOPMENT', 'false').lower() == 'true':
        root_logger.addHandler(console_handler)
    
    # Configure Flask app logger
    app.logger.setLevel(log_level)
    app.logger.addHandler(file_handler)
    app.logger.addHandler(error_handler)
    
    # Reduce SQLAlchemy logging noise in production
    if not app.debug:
        logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
        logging.getLogger('werkzeug').setLevel(logging.WARNING)
    
    return logging.getLogger(__name__)

# Create logger for this module
logger = logging.getLogger(__name__)

# Audit function using proper logging
def log_action(action, details=None):
    """Log audit actions - uses proper logging instead of print"""
    logger.info(f"AUDIT: {action} - {details}")

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Setup logging FIRST before any other operations
app_logger = setup_logging(app)

# Configure ProxyFix for nginx reverse proxy only in production
# This fixes URL generation behind nginx proxy
if not os.environ.get('LOCAL_DEVELOPMENT', 'false').lower() == 'true':
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
    app_logger.info("ProxyFix middleware configured for nginx reverse proxy")
else:
    app_logger.info("Local development mode - ProxyFix middleware disabled")

# Configure HTTPS and security headers for production
if app.config.get('FORCE_HTTPS'):
    try:
        Config.configure_https_headers(app)
    except ImportError:
        # flask-talisman not installed, apply basic security headers
        @app.after_request
        def add_basic_security_headers(response):
            if app.config.get('SECURE_HEADERS'):
                response.headers['X-Content-Type-Options'] = 'nosniff'
                response.headers['X-Frame-Options'] = 'SAMEORIGIN'
                response.headers['X-XSS-Protection'] = '1; mode=block'
                response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
                response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
            return response

# Smart cache headers - allow caching for static files, disable for dynamic content
@app.after_request
def after_request(response):
    # Check if this is a static file request
    if request.path.startswith('/static/'):
        # Allow caching for static files (1 day for CSS/JS, 1 year for fonts/images)
        if any(request.path.endswith(ext) for ext in ['.woff', '.woff2', '.ttf', '.eot', '.png', '.jpg', '.jpeg', '.gif', '.ico', '.svg']):
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        else:
            # CSS/JS - cache for 1 day, but revalidate
            response.headers["Cache-Control"] = "public, max-age=86400"
    else:
        # Dynamic content - no caching
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

# Log every page/tab visit
@app.before_request
def log_page_visit():
    from flask_login import current_user
    from datetime import datetime
    if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
        log_action('Page Visit', f'Visited {request.path}')
        
        # 🔧 Track user activity for active session monitoring
        # Only update if last activity was more than 1 minute ago (to reduce DB writes)
        if not current_user.last_activity or (datetime.now() - current_user.last_activity).total_seconds() > 60:
            try:
                from models.models import db
                current_user.last_activity = datetime.now()
                db.session.commit()
            except Exception as e:
                app_logger.debug(f"Failed to update last_activity: {e}")


# Initialize extensions
from models.models import db
from models.servicenow_config import ServiceNowConfig  # Import ServiceNow config model
from models.team_shift_timing_config import TeamShiftTimingConfig  # Import team shift timing config model
from models.escalation_matrix import EscalationMatrixEntry  # Import escalation matrix model
db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'auth.login'  # Redirect to login page for unauthenticated users
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'
mail = Mail(app)
migrate = Migrate(app, db)

# Initialize secrets manager and load configuration from database
with app.app_context():
    try:
        # Initialize secrets manager with master key from Docker secrets
        init_secrets_manager(db.session, app.config['SECRETS_MASTER_KEY'])
        
        # Load configuration from database
        from config import Config
        Config.init_from_database(secrets_manager)
        
        # Update app config with database values
        app.config.update({
            'MAIL_SERVER': Config.MAIL_SERVER,
            'MAIL_PORT': Config.MAIL_PORT,
            'MAIL_USE_TLS': Config.MAIL_USE_TLS,
            'MAIL_USERNAME': Config.MAIL_USERNAME,
            'MAIL_PASSWORD': Config.MAIL_PASSWORD,
            'MAIL_DEFAULT_SENDER': Config.MAIL_DEFAULT_SENDER,
            'APP_TIMEZONE': Config.APP_TIMEZONE,
            'DAY_SHIFT_START': Config.DAY_SHIFT_START,
            'DAY_SHIFT_END': Config.DAY_SHIFT_END,
            'EVENING_SHIFT_START': Config.EVENING_SHIFT_START,
            'EVENING_SHIFT_END': Config.EVENING_SHIFT_END,
            'NIGHT_SHIFT_START': Config.NIGHT_SHIFT_START,
            'NIGHT_SHIFT_END': Config.NIGHT_SHIFT_END,
            # UNS Email Configuration
            'UNS_EMAIL_HOST': Config.UNS_EMAIL_HOST,
            'UNS_EMAIL_PORT': Config.UNS_EMAIL_PORT,
            'UNS_EMAIL_USERNAME': Config.UNS_EMAIL_USERNAME,
            'UNS_EMAIL_PASSWORD': Config.UNS_EMAIL_PASSWORD,
            'UNS_EMAIL_SENDER_ADDRESS': Config.UNS_EMAIL_SENDER_ADDRESS,
            'UNS_EMAIL_SENDER_NAME': Config.UNS_EMAIL_SENDER_NAME,
            'UNS_EMAIL_ENABLED': Config.UNS_EMAIL_ENABLED,
        })
        
        # Reinitialize mail with new config
        mail.init_app(app)
        
        # Initialize UNS Email Service
        from services.flask_uns_email import init_uns_email
        init_uns_email(app)
        
        # Create email configuration tables if they don't exist
        try:
            from models.email_config import TeamEmailConfig, EmailConfigAuditLog
            db.create_all()
            app_logger.info("Email configuration tables verified/created")
        except Exception as e:
            app_logger.warning(f"Could not create email configuration tables: {e}")
        
        app_logger.info("Configuration loaded from database successfully")
        app_logger.info("UNS Email Service initialized")
        
    except Exception as e:
        app_logger.warning(f"Could not load configuration from database: {e}")
        app_logger.warning("Using default configuration values")

# Import blueprints

from routes.auth import auth_bp

# Patch login/logout to log actions
from flask import request
from flask_login import login_user, logout_user, current_user, login_required
import routes.auth
orig_login_user = login_user
orig_logout_user = logout_user
def patched_login_user(user, *args, **kwargs):
    log_action('Login', f'User {getattr(user, "username", user)} logged in')
    return orig_login_user(user, *args, **kwargs)
def patched_logout_user(*args, **kwargs):
    log_action('Logout', f'User {getattr(current_user, "username", current_user)} logged out')
    return orig_logout_user(*args, **kwargs)
routes.auth.login_user = patched_login_user
routes.auth.logout_user = patched_logout_user
from routes.handover import handover_bp
from routes.dashboard import dashboard_bp
from routes.roster import roster_bp
from routes.team_simple import team_bp
from routes.roster_upload import roster_upload_bp
from routes.shift_allowance import shift_allowance_bp
from routes.reports import reports_bp
from routes.team_roster import team_roster_bp
from routes.team_utils import team_utils_bp




# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(handover_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(roster_bp)
app.register_blueprint(team_bp)
app.register_blueprint(roster_upload_bp)
app.register_blueprint(shift_allowance_bp)
app.register_blueprint(reports_bp)
app.register_blueprint(team_roster_bp)
app.register_blueprint(team_utils_bp)
# Register admin blueprints
from routes.admin import admin_bp
app.register_blueprint(admin_bp, url_prefix='/admin')

from routes.admin_uns_email import admin_uns_email_bp
app.register_blueprint(admin_uns_email_bp)

from routes.escalation_matrix import escalation_bp
app.register_blueprint(escalation_bp)

# Register user management blueprint
from routes.user_management import user_mgmt_bp
app.register_blueprint(user_mgmt_bp)

# Register keypoints updates blueprint
from routes.keypoints import keypoints_bp
app.register_blueprint(keypoints_bp)

# Register ctask assignment blueprint
from routes.ctask_assignment import ctask_assignment_bp
app.register_blueprint(ctask_assignment_bp)

# Register config blueprint for admin configuration
from routes.config import config_bp
app.register_blueprint(config_bp)

# Register enhanced handover blueprint
from routes.handover_enhanced_routes import handover_enhanced_bp
app.register_blueprint(handover_enhanced_bp)

# Register debug blueprint for form troubleshooting
from routes.debug_form import debug_bp
app.register_blueprint(debug_bp)

# Register email configuration blueprint
from routes.email_config_routes import email_config_bp
app.register_blueprint(email_config_bp)

# Register shift configuration blueprint
from routes.shift_config import shift_config_bp
app.register_blueprint(shift_config_bp)

# Register incident assignment blueprint
from routes.incident_assignment import incident_assignment_bp
app.register_blueprint(incident_assignment_bp)

# Register misc blueprint for 'coming soon' tabs
from routes.misc import misc_bp
app.register_blueprint(misc_bp)

# Register shift swap and leave management blueprint
from routes.shift_swap_leave import shift_swap_leave_bp
app.register_blueprint(shift_swap_leave_bp)

# Register audit logs blueprint
from routes.logs import logs_bp
app.register_blueprint(logs_bp)

# Register check-in blueprint for team member status tracking
from routes.checkin import checkin_bp
app.register_blueprint(checkin_bp)

# Register test blueprint
from routes.test_routes import test_bp
app.register_blueprint(test_bp)

# Register SSO authentication blueprints
from routes.sso_auth import sso_auth
from routes.sso_config import sso_config_bp
app.register_blueprint(sso_auth)
app.register_blueprint(sso_config_bp)

# Register user profile blueprint
from routes.user_profile import user_profile_bp
app.register_blueprint(user_profile_bp)

# Register admin linking blueprint
from routes.admin_linking import admin_linking
app.register_blueprint(admin_linking)

# Register assignment response blueprint
from routes.assignment_response import assignment_response_bp, notification_dashboard_bp
app.register_blueprint(assignment_response_bp)
app.register_blueprint(notification_dashboard_bp)

# Register onboarding blueprint
from routes.onboarding import onboarding_bp
app.register_blueprint(onboarding_bp)

# Register secrets management admin blueprint
from routes.admin_secrets import admin_secrets_bp
app.register_blueprint(admin_secrets_bp)

# Register vendor details blueprint
from routes.vendor_details import bp as vendor_details_bp
app.register_blueprint(vendor_details_bp)

# Add template global functions
@app.template_global()
def is_tab_enabled(tab_name):
    """Check if a specific tab is enabled based on database configuration."""
    try:
        from models.app_config import AppConfig
        # Get the configuration value from database
        config_value = AppConfig.get_config(tab_name, default='true')
        return config_value.lower() == 'true'
    except Exception as e:
        # Fallback to default values if database not available
        enabled_tabs = {
            'tab_kb_articles': True,
            'tab_vendor_details': True,
            'tab_applications': True,
            'tab_change_management': True,
            'tab_problem_tickets': True,
            'tab_post_mortems': True
        }
        return enabled_tabs.get(tab_name, True)

@app.template_filter('safe_engineer_name')
def safe_engineer_name(engineer):
    """Safely get engineer name from object or dict"""
    try:
        if hasattr(engineer, 'name'):
            return engineer.name
        elif isinstance(engineer, dict) and 'name' in engineer:
            return engineer['name']
        else:
            return str(engineer)
    except:
        return 'Unknown Engineer'

@app.template_global()
def is_feature_enabled(feature_name):
    """Check if a specific feature is enabled based on database configuration."""
    try:
        from models.app_config import AppConfig
        # Get the configuration value from database
        config_value = AppConfig.get_config(feature_name, default='true')
        return config_value.lower() == 'true'
    except Exception as e:
        # Fallback to default values if database not available
        enabled_features = {
            'feature_servicenow_integration': True,
            'feature_ctask_assignment': True
        }
        return enabled_features.get(feature_name, True)

@app.template_global()
def is_servicenow_enabled_and_configured():
    """Check if ServiceNow is both enabled and properly configured"""
    try:
        from models.app_config import AppConfig
        from models.servicenow_config import ServiceNowConfig
        
        # Check feature toggle
        feature_enabled = AppConfig.is_enabled('feature_servicenow_integration')
        
        # Check configuration completeness
        config_complete = ServiceNowConfig.is_configured()
        
        return feature_enabled and config_complete
    except Exception as e:
        return False

@app.template_global()
def is_nav_active(path):
    """Check if the current request path matches the navigation link"""
    from flask import request
    current_path = request.path
    
    # Exact match for root paths
    if path == '/' and current_path == '/':
        return True
    
    # Special case: /reports should be active for /handover-reports since /reports redirects there
    if path == '/reports' and current_path.startswith('/handover-reports'):
        return True
    
    # Special case: /handover should NOT match /handover-reports (to avoid conflict with reports)
    if path == '/handover' and current_path.startswith('/handover-reports'):
        return False
    
    # Special case: /roster should NOT match /roster-upload (to avoid both being highlighted)
    if path == '/roster' and current_path.startswith('/roster-upload'):
        return False
    
    # For other paths, check if current path starts with the nav path
    # Add trailing slash check to ensure exact path matching
    if path != '/':
        # Exact match first
        if current_path == path:
            return True
        # Then check if current path starts with nav path followed by '/' or query params
        if current_path.startswith(path + '/') or current_path.startswith(path + '?'):
            return True
        
    return False

# Add template filters
@app.template_filter('date_day_name')
def date_day_name_filter(date):
    """Convert date to day name (e.g., Monday, Tuesday)"""
    from datetime import datetime
    if isinstance(date, str):
        try:
            date = datetime.strptime(date, '%Y-%m-%d').date()
        except ValueError:
            return "Unknown"
    elif isinstance(date, datetime):
        date = date.date()
    
    if date:
        return date.strftime('%A')
    return "Unknown"

@app.template_filter('strptime')
def strptime_filter(date_string, format='%Y-%m-%d'):
    """Parse date string to datetime object"""
    from datetime import datetime
    try:
        return datetime.strptime(date_string, format)
    except (ValueError, TypeError):
        return None

@login_manager.user_loader
def load_user(user_id):
    from models.models import User
    return User.query.get(int(user_id))

# Auto-start CTask assignment service when Flask app starts
_services_initialized = False  # Flag to prevent duplicate initialization

def initialize_services():
    """Initialize background services when the Flask app starts"""
    global _services_initialized
    
    # Prevent duplicate initialization
    if _services_initialized:
        return
        
    try:
        # Initialize database configurations
        with app.app_context():
            try:
                # Initialize secrets management system
                from models.models import db
                master_key = os.environ.get('SECRETS_MASTER_KEY')
                if master_key:
                    init_secrets_manager(db.session, master_key)
                    app_logger.info("Secrets management system initialized successfully")
                    
                    # Store in app context for admin routes access
                    app.secrets_manager = secrets_manager
                    
                    # Update app config with secrets from database
                    if secrets_manager:
                        # Update mail configuration from secrets
                        smtp_username = secrets_manager.get_secret('SMTP_USERNAME')
                        if smtp_username and smtp_username != '[TO_BE_SET_VIA_UI]':
                            app.config['MAIL_USERNAME'] = smtp_username
                            app_logger.info("Updated MAIL_USERNAME from secrets")
                        
                        smtp_password = secrets_manager.get_secret('SMTP_PASSWORD')
                        if smtp_password and smtp_password != '[TO_BE_SET_VIA_UI]':
                            app.config['MAIL_PASSWORD'] = smtp_password
                            app_logger.info("Updated MAIL_PASSWORD from secrets")
                        
                        # ServiceNow configuration from secrets
                        servicenow_instance = secrets_manager.get_secret('SERVICENOW_INSTANCE')
                        if servicenow_instance and servicenow_instance != '[TO_BE_SET_VIA_UI]':
                            app.config['SERVICENOW_INSTANCE'] = servicenow_instance
                            app_logger.info("Updated SERVICENOW_INSTANCE from secrets")
                        
                        servicenow_username = secrets_manager.get_secret('SERVICENOW_USERNAME')
                        if servicenow_username and servicenow_username != '[TO_BE_SET_VIA_UI]':
                            app.config['SERVICENOW_USERNAME'] = servicenow_username
                            app_logger.info("Updated SERVICENOW_USERNAME from secrets")
                        
                        servicenow_password = secrets_manager.get_secret('SERVICENOW_PASSWORD')
                        if servicenow_password and servicenow_password != '[TO_BE_SET_VIA_UI]':
                            app.config['SERVICENOW_PASSWORD'] = servicenow_password
                            app_logger.info("Updated SERVICENOW_PASSWORD from secrets")
                else:
                    app_logger.warning("SECRETS_MASTER_KEY not set - secrets management not initialized")
                
                from models.app_config import AppConfig
                from models.servicenow_config import ServiceNowConfig
                
                # Initialize default configurations
                AppConfig.initialize_defaults()
                ServiceNowConfig.initialize_defaults()
                
                app_logger.info("Configuration defaults initialized")
            except Exception as e:
                app_logger.warning(f"Could not initialize configurations: {e}")
        
        # Check if CTask assignment feature is enabled
        # Only initialize CTask scheduler in production and not during worker preload
        # Note: os is already imported at module level
        if os.environ.get('FLASK_ENV') == 'production' and not os.environ.get('GUNICORN_PRELOAD'):
            try:
                from models.app_config import AppConfig
                if AppConfig.is_enabled('feature_ctask_assignment'):
                    # Start the CTask assignment scheduler automatically (non-blocking)
                    from services.ctask_scheduler import start_ctask_scheduler, get_scheduler_status
                    
                    # Quick check if scheduler is already running
                    status = get_scheduler_status()
                    if not status['running']:
                        app_logger.info("Auto-starting CTask assignment scheduler...")
                        start_ctask_scheduler()
                        app_logger.warning("CTask assignment service started but ServiceNow not configured")
                    else:
                        app_logger.info("CTask assignment scheduler already running")
            except Exception as e:
                app_logger.warning(f"CTask scheduler initialization skipped: {e}")
                
        _services_initialized = True  # Mark as initialized
                
    except Exception as e:
        app_logger.error(f"Failed to auto-start CTask assignment service: {e}")
        _services_initialized = True  # Mark as attempted even if failed

# Support for both old and new Flask versions
try:
    # For older Flask versions
    @app.before_first_request
    def init_services_old():
        initialize_services()
except AttributeError:
    # For newer Flask versions, we'll call it during app startup
    with app.app_context():
        initialize_services()

# Test route for SMTP configuration
@app.route('/smtp-test')
def smtp_test():
    """Test page for SMTP configuration"""
    return render_template('smtp_test.html')

# Health check endpoint for load balancer
@app.route('/health')
def health_check():
    """Health check endpoint for monitoring and load balancers"""
    try:
        # Check database connection
        from models.models import db
        from sqlalchemy import text
        db.session.execute(text('SELECT 1'))
        db.session.commit()
        
        return jsonify({
            'status': 'healthy',
            'timestamp': time.time(),
            'services': {
                'database': 'up',
                'application': 'up'
            }
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'timestamp': time.time(),
            'error': str(e),
            'services': {
                'database': 'down',
                'application': 'up'
            }
        }), 503

# Force HTTPS redirect for production
@app.before_request
def force_https():
    """Force HTTPS in production"""
    if app.config.get('FORCE_HTTPS') and not request.is_secure:
        if request.headers.get('X-Forwarded-Proto') != 'https':
            return redirect(request.url.replace('http://', 'https://'), code=301)

# Direct notifications route (registered last to take precedence)
@app.route('/notifications')
@login_required
def notifications_direct():
    """Direct route for notifications using enhanced template"""
    from models import HandoverNotification
    from flask_login import current_user
    from flask import render_template
    
    app_logger.debug(f"Direct /notifications route called for user {current_user.username}")
    
    # Get all notifications for current user
    all_notifications = HandoverNotification.query.filter_by(
        recipient_id=current_user.id
    ).order_by(HandoverNotification.created_at.desc()).all()
    
    # Separate pending assignments (unread) from other notifications
    pending_assignments = []
    notifications = []
    
    for notification in all_notifications:
        if not notification.is_read and notification.notification_type == 'incident_assignment':
            pending_assignments.append({
                'notification_id': notification.id,
                'id': notification.id,
                'incident_title': notification.incident_title,
                'incident_description': notification.description,
                'incident_priority': notification.priority or 'medium',
                'assigned_at': notification.created_at.isoformat()
            })
        else:
            notifications.append({
                'id': notification.id,
                'title': notification.incident_title,
                'message': notification.description,
                'type': notification.notification_type,
                'is_read': notification.is_read,
                'created_at': notification.created_at.isoformat()
            })
    
    return render_template('notifications_enhanced.html', 
                         incident_notifications=pending_assignments, handover_notifications=notifications,
                         notifications=notifications)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
