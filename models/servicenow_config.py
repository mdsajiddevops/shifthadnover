"""
ServiceNow Configuration Model

This model handles ServiceNow integration configuration stored in database,
allowing for runtime configuration changes through the admin interface.
"""

from flask_sqlalchemy import SQLAlchemy
from models.models import db
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class ServiceNowConfig(db.Model):
    __tablename__ = 'servicenow_config'
    
    id = db.Column(db.Integer, primary_key=True)
    config_key = db.Column(db.String(128), unique=True, nullable=False)
    config_value = db.Column(db.Text, nullable=True)  # Use Text for potentially long values
    encrypted = db.Column(db.Boolean, default=False, nullable=False)  # For future password encryption
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())
    
    @staticmethod
    def get_config(key, default=None):
        """Get ServiceNow configuration value by key"""
        try:
            config = ServiceNowConfig.query.filter_by(config_key=key).first()
            return config.config_value if config else default
        except Exception as e:
            logger.error(f"Error getting ServiceNow config {key}: {str(e)}")
            return default
    
    @staticmethod
    def set_config(key, value, description=None, encrypted=False):
        """Set ServiceNow configuration value"""
        try:
            config = ServiceNowConfig.query.filter_by(config_key=key).first()
            if config:
                config.config_value = value
                config.encrypted = encrypted
                if description:
                    config.description = description
                config.updated_at = datetime.utcnow()
            else:
                config = ServiceNowConfig(
                    config_key=key,
                    config_value=value,
                    description=description,
                    encrypted=encrypted
                )
                db.session.add(config)
            db.session.commit()
            logger.info(f"ServiceNow config {key} updated successfully")
            return config
        except Exception as e:
            logger.error(f"Error setting ServiceNow config {key}: {str(e)}")
            db.session.rollback()
            return None
    
    @staticmethod
    def is_enabled():
        """Check if ServiceNow integration is enabled"""
        try:
            from models.app_config import AppConfig
            # Check both feature toggle AND configuration completeness
            feature_enabled = AppConfig.is_enabled('feature_servicenow_integration')
            config_complete = ServiceNowConfig.is_configured()
            return feature_enabled and config_complete
        except Exception as e:
            logger.error(f"Error checking ServiceNow enabled status: {str(e)}")
            return False
    
    @staticmethod
    def is_configured():
        """Check if ServiceNow is properly configured with required settings"""
        try:
            required_configs = ['instance_url', 'username', 'password']
            
            for key in required_configs:
                value = ServiceNowConfig.get_config(key)
                if not value or value.strip() == '':
                    return False
            return True
        except Exception as e:
            logger.error(f"Error checking ServiceNow configuration: {str(e)}")
            return False
    
    @staticmethod
    def get_connection_config():
        """Get all connection configuration as a dictionary"""
        try:
            config_keys = [
                'instance_url', 'username', 'password', 'timeout', 
                'assignment_groups', 'enabled'
            ]
            
            config = {}
            for key in config_keys:
                value = ServiceNowConfig.get_config(key)
                if value:
                    # Convert specific values to appropriate types
                    if key == 'timeout':
                        config[key] = int(value) if value.isdigit() else 30
                    elif key == 'enabled':
                        config[key] = value.lower() in ['true', '1', 'yes', 'enabled']
                    elif key == 'assignment_groups':
                        # Convert comma-separated string to list
                        config[key] = [group.strip() for group in value.split(',') if group.strip()]
                    else:
                        config[key] = value
                
            return config
        except Exception as e:
            logger.error(f"Error getting ServiceNow connection config: {str(e)}")
            return {}
    
    @staticmethod
    def initialize_defaults():
        """Initialize default ServiceNow configuration values"""
        default_configs = [
            ('enabled', 'true', 'Enable/Disable ServiceNow integration at connection level'),
            ('instance_url', '', 'ServiceNow instance URL (e.g., yourcompany.service-now.com)'),
            ('username', '', 'ServiceNow API username'),
            ('password', '', 'ServiceNow API password', True),  # Encrypted
            ('timeout', '30', 'API request timeout in seconds'),
            ('assignment_groups', '', 'Comma-separated list of assignment groups to monitor'),
            ('api_version', 'v1', 'ServiceNow API version'),
            ('auto_fetch_incidents', 'true', 'Automatically fetch incidents for handover forms'),
            ('auto_assign_ctasks', 'true', 'Automatically assign CTasks to on-shift engineers'),
        ]
        
        try:
            for item in default_configs:
                if len(item) == 4:
                    key, value, description, encrypted = item
                else:
                    key, value, description = item
                    encrypted = False
                    
                existing = ServiceNowConfig.query.filter_by(config_key=key).first()
                if not existing:
                    ServiceNowConfig.set_config(key, value, description, encrypted)
                    
            logger.info("ServiceNow default configurations initialized")
        except Exception as e:
            logger.error(f"Error initializing ServiceNow defaults: {str(e)}")
    
    @staticmethod
    def test_connection_config():
        """Test if current configuration can establish a connection"""
        try:
            config = ServiceNowConfig.get_connection_config()
            
            # Check required fields
            required_fields = ['instance_url', 'username', 'password']
            missing_fields = [field for field in required_fields if not config.get(field)]
            
            if missing_fields:
                return {
                    'success': False,
                    'error': f'Missing required configuration: {", ".join(missing_fields)}',
                    'config_complete': False
                }
            
            # Basic validation
            instance_url = config['instance_url']
            if not instance_url.startswith('https://') and not instance_url.startswith('http://'):
                # Auto-correct common mistake
                instance_url = f"https://{instance_url}"
                ServiceNowConfig.set_config('instance_url', instance_url)
            
            return {
                'success': True,
                'message': 'Configuration appears valid',
                'config_complete': True,
                'instance_url': instance_url
            }
            
        except Exception as e:
            logger.error(f"Error testing ServiceNow configuration: {str(e)}")
            return {
                'success': False,
                'error': f'Configuration test failed: {str(e)}',
                'config_complete': False
            }
    
    def __repr__(self):
        return f'<ServiceNowConfig {self.config_key}: {self.config_value[:20]}...>'