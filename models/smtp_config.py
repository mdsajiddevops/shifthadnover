"""
SMTP/Email Configuration Model

This model handles SMTP email integration configuration stored in database,
allowing for runtime configuration changes through the admin interface.
"""

from flask_sqlalchemy import SQLAlchemy
from models.models import db
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class SMTPConfig(db.Model):
    __tablename__ = 'smtp_config'
    
    id = db.Column(db.Integer, primary_key=True)
    config_key = db.Column(db.String(128), unique=True, nullable=False)
    config_value = db.Column(db.Text, nullable=True)  # Use Text for potentially long values
    encrypted = db.Column(db.Boolean, default=False, nullable=False)  # For password encryption
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())
    
    @staticmethod
    def get_config(key, default=None):
        """Get SMTP configuration value by key"""
        try:
            config = SMTPConfig.query.filter_by(config_key=key).first()
            return config.config_value if config else default
        except Exception as e:
            logger.error(f"Error getting SMTP config {key}: {str(e)}")
            return default
    
    @staticmethod
    def set_config(key, value, description=None, encrypted=False):
        """Set SMTP configuration value"""
        try:
            config = SMTPConfig.query.filter_by(config_key=key).first()
            if config:
                config.config_value = value
                config.encrypted = encrypted
                if description:
                    config.description = description
                config.updated_at = datetime.utcnow()
            else:
                config = SMTPConfig(
                    config_key=key,
                    config_value=value,
                    encrypted=encrypted,
                    description=description or f"SMTP configuration for {key}"
                )
                db.session.add(config)
            
            db.session.commit()
            logger.info(f"SMTP config {key} updated successfully")
            return True
        except Exception as e:
            logger.error(f"Error setting SMTP config {key}: {str(e)}")
            db.session.rollback()
            return False
    
    @staticmethod
    def get_all_configs():
        """Get all SMTP configurations"""
        try:
            configs = SMTPConfig.query.all()
            return {config.config_key: config.config_value for config in configs}
        except Exception as e:
            logger.error(f"Error getting all SMTP configs: {str(e)}")
            return {}
    
    @staticmethod
    def delete_config(key):
        """Delete SMTP configuration"""
        try:
            config = SMTPConfig.query.filter_by(config_key=key).first()
            if config:
                db.session.delete(config)
                db.session.commit()
                logger.info(f"SMTP config {key} deleted successfully")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting SMTP config {key}: {str(e)}")
            db.session.rollback()
            return False
    
    @staticmethod
    def initialize_default_configs():
        """Initialize default SMTP configurations"""
        default_configs = {
            'smtp_server': {
                'value': 'smtp.gmail.com',
                'description': 'SMTP server hostname',
                'encrypted': False
            },
            'smtp_port': {
                'value': '587',
                'description': 'SMTP server port',
                'encrypted': False
            },
            'smtp_use_tls': {
                'value': 'true',
                'description': 'Enable TLS encryption',
                'encrypted': False
            },
            'smtp_use_ssl': {
                'value': 'false',
                'description': 'Enable SSL encryption',
                'encrypted': False
            },
            'smtp_username': {
                'value': '[TO_BE_CONFIGURED]',
                'description': 'SMTP authentication username',
                'encrypted': False
            },
            'smtp_password': {
                'value': '[TO_BE_CONFIGURED]',
                'description': 'SMTP authentication password',
                'encrypted': True
            },
            'mail_default_sender': {
                'value': '[TO_BE_CONFIGURED]',
                'description': 'Default sender email address',
                'encrypted': False
            },
            'mail_reply_to': {
                'value': '[TO_BE_CONFIGURED]',
                'description': 'Reply-to email address',
                'encrypted': False
            },
            'team_email': {
                'value': '[TO_BE_CONFIGURED]',
                'description': 'Team email address for notifications',
                'encrypted': False
            },
            'smtp_enabled': {
                'value': 'false',
                'description': 'Enable/disable SMTP email functionality',
                'encrypted': False
            }
        }
        
        try:
            for key, config_data in default_configs.items():
                existing = SMTPConfig.query.filter_by(config_key=key).first()
                if not existing:
                    SMTPConfig.set_config(
                        key=key,
                        value=config_data['value'],
                        description=config_data['description'],
                        encrypted=config_data['encrypted']
                    )
            
            logger.info("✅ SMTP default configurations initialized")
            return True
        except Exception as e:
            logger.error(f"Error initializing SMTP default configs: {str(e)}")
            return False
    
    @staticmethod
    def is_configured():
        """Check if SMTP is properly configured"""
        required_configs = ['smtp_server', 'smtp_port', 'smtp_username', 'smtp_password']
        
        try:
            for key in required_configs:
                value = SMTPConfig.get_config(key)
                if not value or value == '[TO_BE_CONFIGURED]':
                    return False
            
            # Check if SMTP is enabled
            enabled = SMTPConfig.get_config('smtp_enabled', 'false')
            return enabled.lower() == 'true'
        except Exception as e:
            logger.error(f"Error checking SMTP configuration: {str(e)}")
            return False
    
    @staticmethod
    def get_flask_mail_config():
        """Get configuration in Flask-Mail format"""
        try:
            if not SMTPConfig.is_configured():
                return {}
            
            config = {
                'MAIL_SERVER': SMTPConfig.get_config('smtp_server'),
                'MAIL_PORT': int(SMTPConfig.get_config('smtp_port', 587)),
                'MAIL_USE_TLS': SMTPConfig.get_config('smtp_use_tls', 'true').lower() == 'true',
                'MAIL_USE_SSL': SMTPConfig.get_config('smtp_use_ssl', 'false').lower() == 'true',
                'MAIL_USERNAME': SMTPConfig.get_config('smtp_username'),
                'MAIL_PASSWORD': SMTPConfig.get_config('smtp_password'),
                'MAIL_DEFAULT_SENDER': SMTPConfig.get_config('mail_default_sender'),
                'TEAM_EMAIL': SMTPConfig.get_config('team_email')
            }
            
            return config
        except Exception as e:
            logger.error(f"Error getting Flask-Mail config: {str(e)}")
            return {}
    
    @staticmethod
    def test_connection():
        """Test SMTP connection"""
        try:
            from flask_mail import Mail, Message
            from flask import current_app
            
            # Get configuration
            config = SMTPConfig.get_flask_mail_config()
            if not config:
                return False, "SMTP not configured"
            
            # Temporarily update app config
            original_config = {}
            for key, value in config.items():
                original_config[key] = current_app.config.get(key)
                current_app.config[key] = value
            
            # Test connection
            mail = Mail(current_app)
            
            # Try to connect
            with mail.connect() as conn:
                logger.info("✅ SMTP connection test successful")
                
            # Restore original config
            for key, value in original_config.items():
                if value is not None:
                    current_app.config[key] = value
                else:
                    current_app.config.pop(key, None)
            
            return True, "Connection successful"
            
        except Exception as e:
            logger.error(f"SMTP connection test failed: {str(e)}")
            return False, str(e)

    def __repr__(self):
        return f'<SMTPConfig {self.config_key}: {self.config_value[:20]}{"..." if len(str(self.config_value)) > 20 else ""}>'