import os
import logging
from cryptography.fernet import Fernet

# Remove .env loading - we'll use Docker secrets + database
# load_dotenv()  # Disabled

class SecureConfigManager:
    """Secure configuration manager for Docker secrets + database storage"""
    
    @staticmethod
    def get_docker_secret(secret_name, default=None, required=False):
        """
        Get secret from Docker secrets (highest priority for critical credentials)
        Falls back to environment variables and then defaults for development
        """
        # Try Docker Secrets first (production)
        secret_file = f"/run/secrets/{secret_name.lower()}"
        if os.path.exists(secret_file):
            try:
                with open(secret_file, 'r') as f:
                    value = f.read().strip()
                    logging.info(f"✅ Loaded {secret_name} from Docker secret")
                    return value
            except Exception as e:
                logging.error(f"Error reading Docker secret {secret_name}: {e}")
        
        # Try local secrets directory (development/testing)
        local_secret_file = f"./secrets/{secret_name.lower()}"
        if os.path.exists(local_secret_file):
            try:
                with open(local_secret_file, 'r') as f:
                    value = f.read().strip()
                    logging.info(f"✅ Loaded {secret_name} from local secrets file")
                    return value
            except Exception as e:
                logging.error(f"Error reading local secret {secret_name}: {e}")
        
        # Fallback to environment variables for development
        env_value = os.environ.get(secret_name.upper())
        if env_value:
            logging.info(f"✅ Loaded {secret_name} from environment variable")
            return env_value
        
        # Check if running in development mode
        is_development = os.environ.get('FLASK_ENV', 'development') == 'development'
        
        # For development, provide secure defaults instead of failing
        if is_development and secret_name in ['flask_secret_key', 'secrets_master_key']:
            if secret_name == 'flask_secret_key':
                # Read from secrets file if it exists, otherwise generate
                secret_file_path = './secrets/flask_secret_key'
                if os.path.exists(secret_file_path):
                    try:
                        with open(secret_file_path, 'r') as f:
                            value = f.read().strip()
                            logging.info(f"✅ Loaded {secret_name} from local secrets file")
                            return value
                    except Exception as e:
                        logging.warning(f"Could not read local secret file: {e}")
                
                # Generate secure key for development
                from cryptography.fernet import Fernet
                dev_key = Fernet.generate_key().decode()
                logging.warning(f"⚠️ Generated temporary {secret_name} for development: {dev_key}")
                return dev_key
                
            elif secret_name == 'secrets_master_key':
                # Read from secrets file if it exists, otherwise generate
                secret_file_path = './secrets/secrets_master_key.txt'
                if os.path.exists(secret_file_path):
                    try:
                        with open(secret_file_path, 'r') as f:
                            value = f.read().strip()
                            logging.info(f"✅ Loaded {secret_name} from local secrets file")
                            return value
                    except Exception as e:
                        logging.warning(f"Could not read local secret file: {e}")
                
                # Generate secure master key for development
                from cryptography.fernet import Fernet
                dev_key = Fernet.generate_key().decode()
                logging.warning(f"⚠️ Generated temporary {secret_name} for development: {dev_key}")
                return dev_key
        
        # Return default or raise error
        if required and default is None and not is_development:
            raise ValueError(f"❌ Required secret '{secret_name}' not found in Docker secrets or environment")
        
        if default is not None:
            logging.info(f"✅ Using default value for {secret_name}")
            return default
        
        logging.warning(f"⚠️ Secret {secret_name} not found, returning None")
        return None
    
    @staticmethod
    def build_database_url():
        """Build database URL from Docker secrets or environment variables"""
        
        # Check if we're in local development mode first
        is_local_dev = os.environ.get('LOCAL_DEVELOPMENT', 'false').lower() == 'true'
        
        # For local development, prioritize SQLite
        if is_local_dev:
            database_url = os.environ.get('DATABASE_URL')
            if database_url and 'sqlite' in database_url:
                logging.info("✅ Using SQLite database for local development")
                return database_url
            # Force SQLite for local development if no proper URL is set
            sqlite_url = 'sqlite:///local_shifthandover.db'
            logging.info("✅ Forcing SQLite database for local development")
            return sqlite_url
        
        # First try to read full DATABASE_URL from Docker secret file
        database_url_file = os.environ.get('DATABASE_URL_FILE')
        if database_url_file and os.path.exists(database_url_file):
            try:
                with open(database_url_file, 'r') as f:
                    database_url = f.read().strip()
                    logging.info("✅ Using DATABASE_URL from Docker secret file")
                    return database_url
            except Exception as e:
                logging.warning(f"⚠️ Could not read DATABASE_URL_FILE: {e}")
        
        # Try to get full DATABASE_URL from Docker secret
        database_url = SecureConfigManager.get_docker_secret('database_url')
        if database_url:
            logging.info("✅ Using DATABASE_URL from Docker secret")
            return database_url
        
        # Fallback to full DATABASE_URL from environment
        database_url = os.environ.get('DATABASE_URL')
        if database_url:
            logging.info("✅ Using DATABASE_URL from environment")
            return database_url
        
        # Try to get individual components for Docker secrets
        host = os.environ.get('DATABASE_HOST', 'db')
        port = os.environ.get('DATABASE_PORT', '3306')
        name = os.environ.get('DATABASE_NAME', 'shifthandover')
        user = os.environ.get('DATABASE_USER', 'user')
        
        # Get password from Docker secret (try multiple possible names)
        password = (SecureConfigManager.get_docker_secret('mysql_user_password') or 
                   SecureConfigManager.get_docker_secret('mysql_password') or
                   os.environ.get('DATABASE_PASSWORD'))
        
        if password:
            database_url = f"mysql+pymysql://{user}:{password}@{host}:{port}/{name}"
            logging.info("✅ Built database URL from Docker secrets/environment")
            return database_url
        
        # Development fallback - always use SQLite for development when no database configured
        logging.warning("⚠️ No database credentials found, using SQLite for development")
        return 'sqlite:///shifthandover.db'
        
        # Return default or raise error
        if required and default is None:
            raise ValueError(f"❌ Required secret '{secret_name}' not found in any source")
        
        if default is not None:
            if secret_name.lower() in ['password', 'key', 'secret']:
                logging.warning(f"⚠️ Using default value for sensitive config: {secret_name}")
            else:
                logging.info(f"✅ Using default value for {secret_name}")
            return default
        
        logging.warning(f"⚠️ Secret {secret_name} not found, returning None")
        return None

# Initialize secure config manager
secure_config = SecureConfigManager()

class Config:
    """Base configuration class with Docker secrets + database storage"""
    
    # Core Flask settings - FROM DOCKER SECRETS OR DEVELOPMENT FALLBACKS
    SECRET_KEY = secure_config.get_docker_secret('flask_secret_key', required=False)
    
    # Database configuration - FROM DOCKER SECRETS OR DEVELOPMENT FALLBACKS  
    SQLALCHEMY_DATABASE_URI = secure_config.build_database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }
    
    # Master key for encrypting secrets in database - FROM DOCKER SECRETS OR DEVELOPMENT FALLBACKS
    SECRETS_MASTER_KEY = secure_config.get_docker_secret('secrets_master_key', required=False)
    
    # SSO encryption key for SSO configuration secrets - FROM DOCKER SECRETS OR DEVELOPMENT FALLBACKS
    SSO_ENCRYPTION_KEY = secure_config.get_docker_secret('sso_encryption_key', required=False)
    
    # All other configuration will be loaded from database via SecretsManager
    # This includes:
    # - SMTP settings (server, port, username, password)
    # - ServiceNow configuration
    # - OAuth settings
    # - Application-specific settings
    
    # SMTP Configuration - Load from database only (no hardcoded defaults)
    MAIL_SERVER = None  # Will be loaded from SMTPConfig database table
    MAIL_PORT = None    # Will be loaded from SMTPConfig database table
    MAIL_USE_TLS = None # Will be loaded from SMTPConfig database table
    MAIL_USE_SSL = None # Will be loaded from SMTPConfig database table
    MAIL_USERNAME = None # Will be loaded from SMTPConfig database table
    MAIL_PASSWORD = None # Will be loaded from SMTPConfig database table
    MAIL_DEFAULT_SENDER = None # Will be loaded from SMTPConfig database table
    TEAM_EMAIL = None
    
    SERVICENOW_INSTANCE = None
    SERVICENOW_USERNAME = None
    SERVICENOW_PASSWORD = None
    SERVICENOW_TIMEOUT = 30
    SERVICENOW_ASSIGNMENT_GROUPS = ''
    SERVICENOW_ENABLED = False
    
    GOOGLE_OAUTH_CLIENT_ID = None
    GOOGLE_OAUTH_CLIENT_SECRET = None
    
    # UNS Email Service Configuration (will be overridden by database)
    UNS_EMAIL_HOST = None
    UNS_EMAIL_PORT = 587
    UNS_EMAIL_USERNAME = None
    UNS_EMAIL_PASSWORD = None
    UNS_EMAIL_SENDER_ADDRESS = 'shift-handover@epam.com'
    UNS_EMAIL_SENDER_NAME = 'Shift Handover System'
    UNS_EMAIL_ENABLED = True
    
    SESSION_TIMEOUT = 3600
    MAX_WORKERS = 4
    LOG_LEVEL = 'INFO'
    
    # Timezone configuration
    APP_TIMEZONE = 'Asia/Kolkata'
    
    # Shift timing configuration 
    DAY_SHIFT_START = '06:30'
    DAY_SHIFT_END = '15:30'
    EVENING_SHIFT_START = '14:45'
    EVENING_SHIFT_END = '23:45'
    NIGHT_SHIFT_START = '21:45'
    NIGHT_SHIFT_END = '06:45'
    
    @classmethod
    def init_from_database(cls, secrets_manager):
        """Initialize configuration from database-stored secrets"""
        try:
            # Load SMTP configuration exclusively from database (SMTPConfig table)
            print(f"[CONFIG] 📧 Loading SMTP configuration from database SMTPConfig table...")
            try:
                from models.smtp_config import SMTPConfig
                
                # Load all SMTP settings from database table only
                cls.MAIL_SERVER = SMTPConfig.get_config('smtp_server')
                cls.MAIL_PORT = int(SMTPConfig.get_config('smtp_port', 587))  # Only port has a sensible default
                cls.MAIL_USERNAME = SMTPConfig.get_config('smtp_username')
                cls.MAIL_PASSWORD = SMTPConfig.get_config('smtp_password')
                cls.MAIL_USE_TLS = SMTPConfig.get_config('smtp_use_tls', 'true').lower() == 'true'
                cls.MAIL_USE_SSL = SMTPConfig.get_config('smtp_use_ssl', 'false').lower() == 'true'
                cls.MAIL_DEFAULT_SENDER = SMTPConfig.get_config('mail_default_sender')
                
                # Validate that essential SMTP settings are configured
                if not cls.MAIL_SERVER:
                    print(f"[CONFIG] ❌ MAIL_SERVER not configured in database - email will not work")
                if not cls.MAIL_USERNAME:
                    print(f"[CONFIG] ❌ MAIL_USERNAME not configured in database - email will not work") 
                if not cls.MAIL_PASSWORD:
                    print(f"[CONFIG] ❌ MAIL_PASSWORD not configured in database - email will not work")
                if not cls.MAIL_DEFAULT_SENDER:
                    print(f"[CONFIG] ❌ MAIL_DEFAULT_SENDER not configured in database - email will not work")
                
                print(f"[CONFIG] ✅ SMTP config loaded from database: {cls.MAIL_SERVER}:{cls.MAIL_PORT}")
                print(f"[CONFIG] ✅ SMTP auth configured: {bool(cls.MAIL_USERNAME and cls.MAIL_PASSWORD)}")
                print(f"[CONFIG] ✅ SMTP sender configured: {bool(cls.MAIL_DEFAULT_SENDER)}")
                
            except Exception as e:
                print(f"[CONFIG] ❌ Failed to load SMTP config from database: {e}")
                print(f"[CONFIG] ⚠️ SMTP configuration not available - emails will not work")
                # Set None values - no hardcoded fallbacks
                cls.MAIL_SERVER = None
                cls.MAIL_PORT = 587
                cls.MAIL_USERNAME = None
                cls.MAIL_PASSWORD = None
                cls.MAIL_USE_TLS = True
                cls.MAIL_USE_SSL = False
                cls.MAIL_DEFAULT_SENDER = None
            
            # Get mail default sender from SMTP config or fallback to username
            try:
                from models.smtp_config import SMTPConfig
                cls.MAIL_DEFAULT_SENDER = SMTPConfig.get_config('mail_default_sender', cls.MAIL_USERNAME)
                print(f"[CONFIG] ✅ Loaded MAIL_DEFAULT_SENDER from SMTPConfig: {cls.MAIL_DEFAULT_SENDER}")
            except Exception as e:
                print(f"[CONFIG] SMTPConfig failed for default sender: {e}")
                # Fallback if SMTPConfig is not available
                cls.MAIL_DEFAULT_SENDER = secrets_manager.get_secret('smtp_from', cls.MAIL_USERNAME)
                print(f"[CONFIG] ⚠️ Using secrets manager fallback for MAIL_DEFAULT_SENDER: {cls.MAIL_DEFAULT_SENDER}")
            
            cls.TEAM_EMAIL = cls.MAIL_DEFAULT_SENDER
            
            # Load ServiceNow configuration from database
            cls.SERVICENOW_INSTANCE = secrets_manager.get_secret('servicenow_instance')
            cls.SERVICENOW_USERNAME = secrets_manager.get_secret('servicenow_username')
            cls.SERVICENOW_PASSWORD = secrets_manager.get_secret('servicenow_password')
            cls.SERVICENOW_TIMEOUT = int(secrets_manager.get_secret('servicenow_timeout', 30))
            cls.SERVICENOW_ASSIGNMENT_GROUPS = secrets_manager.get_secret('servicenow_assignment_groups', '')
            cls.SERVICENOW_ENABLED = secrets_manager.get_secret('servicenow_enabled', 'false').lower() == 'true'
            
            # Load OAuth configuration from database
            cls.GOOGLE_OAUTH_CLIENT_ID = secrets_manager.get_secret('google_oauth_client_id')
            cls.GOOGLE_OAUTH_CLIENT_SECRET = secrets_manager.get_secret('google_oauth_client_secret')
            
            # Load application settings from database
            cls.SESSION_TIMEOUT = int(secrets_manager.get_secret('session_timeout', 3600))
            cls.MAX_WORKERS = int(secrets_manager.get_secret('max_workers', 4))
            cls.LOG_LEVEL = secrets_manager.get_secret('log_level', 'INFO')
            
            # Load timezone configuration
            cls.APP_TIMEZONE = secrets_manager.get_secret('app_timezone', 'Asia/Kolkata')
            
            # Load shift timing configuration
            cls.DAY_SHIFT_START = secrets_manager.get_secret('day_shift_start', '06:30')
            cls.DAY_SHIFT_END = secrets_manager.get_secret('day_shift_end', '15:30')
            cls.EVENING_SHIFT_START = secrets_manager.get_secret('evening_shift_start', '14:45')
            cls.EVENING_SHIFT_END = secrets_manager.get_secret('evening_shift_end', '23:45')
            cls.NIGHT_SHIFT_START = secrets_manager.get_secret('night_shift_start', '21:45')
            cls.NIGHT_SHIFT_END = secrets_manager.get_secret('night_shift_end', '06:45')
            cls.ONSHORE_SHIFT_START = secrets_manager.get_secret('onshore_shift_start', '10:00')
            cls.ONSHORE_SHIFT_END = secrets_manager.get_secret('onshore_shift_end', '22:00')
            cls.OFFSHORE_SHIFT_START = secrets_manager.get_secret('offshore_shift_start', '22:00')
            cls.OFFSHORE_SHIFT_END = secrets_manager.get_secret('offshore_shift_end', '10:00')
            
            # Load UNS Email configuration from database
            cls.UNS_EMAIL_HOST = secrets_manager.get_secret('email_notification_host', 'localhost')
            cls.UNS_EMAIL_PORT = int(secrets_manager.get_secret('email_notification_port', 587))
            cls.UNS_EMAIL_USERNAME = secrets_manager.get_secret('email_notification_username')
            cls.UNS_EMAIL_PASSWORD = secrets_manager.get_secret('email_notification_password')
            cls.UNS_EMAIL_SENDER_ADDRESS = secrets_manager.get_secret('email_notification_sender_address', 'shift-handover@epam.com')
            cls.UNS_EMAIL_SENDER_NAME = secrets_manager.get_secret('email_notification_sender_name', 'Shift Handover System')
            cls.UNS_EMAIL_ENABLED = secrets_manager.get_secret('email_notification_enabled', 'true').lower() == 'true'
            
            logging.info("✅ Configuration loaded from database successfully")
            return True
            
        except Exception as e:
            logging.error(f"❌ Error loading configuration from database: {e}")
            return False
    
    # Security settings
    SESSION_COOKIE_SECURE = os.environ.get('FORCE_HTTPS', 'false').lower() == 'true'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 86400  # 24 hours
    
    # HTTPS and Domain Configuration
    APP_DOMAIN = os.environ.get('APP_DOMAIN', 'localhost')
    APP_BASE_URL = os.environ.get('APP_BASE_URL', 'http://localhost:5000')
    FORCE_HTTPS = os.environ.get('FORCE_HTTPS', 'false').lower() == 'true'
    SECURE_HEADERS = os.environ.get('SECURE_HEADERS', 'false').lower() == 'true'
    
    # Trust proxy headers for HTTPS detection
    PREFERRED_URL_SCHEME = 'https' if FORCE_HTTPS else 'http'
    
    @classmethod
    def configure_https_headers(cls, app):
        """Configure HTTPS security headers and settings"""
        if cls.FORCE_HTTPS:
            from flask_talisman import Talisman
            
            # Configure Content Security Policy
            csp = {
                'default-src': ["'self'"],
                'script-src': ["'self'", "'unsafe-inline'", 'cdnjs.cloudflare.com', 'cdn.jsdelivr.net'],
                'style-src': ["'self'", "'unsafe-inline'", 'cdnjs.cloudflare.com', 'fonts.googleapis.com'],
                'font-src': ["'self'", 'fonts.gstatic.com', 'cdnjs.cloudflare.com'],
                'img-src': ["'self'", 'data:', 'https:'],
                'connect-src': ["'self'"],
                'form-action': ["'self'"],
                'frame-ancestors': ["'none'"],
                'object-src': ["'none'"],
                'base-uri': ["'self'"]
            }
            
            # Apply Talisman for security headers
            Talisman(app, 
                force_https=True,
                strict_transport_security=True,
                strict_transport_security_max_age=31536000,
                content_security_policy=csp,
                content_security_policy_nonce_in=['script-src', 'style-src'],
                force_file_save=False
            )
        
        # Configure Flask session security
        app.config['SESSION_COOKIE_SECURE'] = cls.FORCE_HTTPS
        app.config['SESSION_COOKIE_HTTPONLY'] = True
        app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
        
        # Add security headers middleware
        @app.after_request
        def add_security_headers(response):
            if cls.SECURE_HEADERS:
                response.headers['X-Content-Type-Options'] = 'nosniff'
                response.headers['X-Frame-Options'] = 'SAMEORIGIN'
                response.headers['X-XSS-Protection'] = '1; mode=block'
                response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
                
                if cls.FORCE_HTTPS:
                    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
            
            return response
    
    @classmethod
    def validate_security(cls):
        """Validate security configuration and warn about issues"""
        issues = []
        warnings = []
        
        # Check for weak or default values
        if not cls.SECRET_KEY or len(cls.SECRET_KEY) < 32:
            issues.append("SECRET_KEY is too weak or missing")
        
        if cls.DATABASE_URL and 'sqlite' in cls.DATABASE_URL.lower():
            warnings.append("Using SQLite database (not recommended for production)")
        
        if cls.MAIL_PASSWORD == '*** MIGRATED TO DATABASE - ROTATE IMMEDIATELY ***':
            issues.append("🚨 CRITICAL: Default Gmail password is exposed!")
        
        if not cls.SSO_ENCRYPTION_KEY:
            issues.append("SSO_ENCRYPTION_KEY is missing")
        
        # Print results
        if issues:
            print("🚨 SECURITY ISSUES:")
            for issue in issues:
                print(f"  ❌ {issue}")
        
        if warnings:
            print("⚠️ SECURITY WARNINGS:")
            for warning in warnings:
                print(f"  ⚠️ {warning}")
        
        if not issues and not warnings:
            print("✅ Security configuration looks good!")
        
        return len(issues) == 0

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False
    FLASK_ENV = 'development'

class ProductionConfig(Config):
    """Production configuration with enhanced security"""
    DEBUG = False
    TESTING = False
    FLASK_ENV = 'production'
    
    # Enforce HTTPS in production
    PREFERRED_URL_SCHEME = 'https'
    SESSION_COOKIE_SECURE = True
    
    # Additional security headers
    SEND_FILE_MAX_AGE_DEFAULT = 31536000  # 1 year cache
    
    @classmethod
    def validate_production_security(cls):
        """Additional production security validation"""
        issues = []
        
        # Production-specific checks
        if 'sqlite' in cls.SQLALCHEMY_DATABASE_URI.lower():
            issues.append("SQLite not suitable for production")
        
        if not cls.MAIL_USERNAME or not cls.MAIL_PASSWORD:
            issues.append("Email configuration required for production")
        
        if not cls.SSO_ENCRYPTION_KEY:
            issues.append("SSO encryption key required for production")
        
        if issues:
            print("🚨 PRODUCTION SECURITY ISSUES:")
            for issue in issues:
                print(f"  ❌ {issue}")
            return False
        
        print("✅ Production security validation passed!")
        return True

# Auto-detect configuration based on environment
if os.environ.get('FLASK_ENV') == 'production':
    AppConfig = ProductionConfig
else:
    AppConfig = DevelopmentConfig
