from flask_sqlalchemy import SQLAlchemy
from models.models import db

class AppConfig(db.Model):
    __tablename__ = 'app_config'
    
    id = db.Column(db.Integer, primary_key=True)
    config_key = db.Column(db.String(128), unique=True, nullable=False)
    config_value = db.Column(db.String(256), nullable=False, default='true')
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(64), nullable=False, default='general')
    created_at = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())
    
    @staticmethod
    def get_config(key, default='true'):
        """Get configuration value by key"""
        config = AppConfig.query.filter_by(config_key=key).first()
        return config.config_value if config else default
    
    @staticmethod
    def set_config(key, value, description=None, category='general'):
        """Set configuration value"""
        config = AppConfig.query.filter_by(config_key=key).first()
        if config:
            config.config_value = value
            if description:
                config.description = description
        else:
            config = AppConfig(
                config_key=key,
                config_value=value,
                description=description,
                category=category
            )
            db.session.add(config)
        db.session.commit()
        return config
    
    @staticmethod
    def is_enabled(key):
        """Check if a feature is enabled"""
        return AppConfig.get_config(key, 'false').lower() in ['true', '1', 'yes', 'enabled']
    
    @staticmethod
    def initialize_defaults():
        """Initialize default configuration values"""
        default_configs = [
            ('tab_kb_articles', 'false', 'Enable/Disable KB Articles tab', 'tabs'),
            ('tab_vendor_details', 'false', 'Enable/Disable Vendor Details tab', 'tabs'),
            ('tab_applications', 'false', 'Enable/Disable Applications tab', 'tabs'),
            ('tab_change_management', 'false', 'Enable/Disable Change Management tab', 'tabs'),
            ('tab_problem_tickets', 'false', 'Enable/Disable Problem Tickets tab', 'tabs'),
            ('tab_post_mortems', 'false', 'Enable/Disable Post-mortems tab', 'tabs'),
            # System Features
            ('feature_servicenow_integration', 'true', 'Enable/Disable ServiceNow Integration page and features', 'features'),
            ('feature_ctask_assignment', 'true', 'Enable/Disable CTask Assignment dashboard page', 'features'),
        ]
        
        for key, value, description, category in default_configs:
            existing = AppConfig.query.filter_by(config_key=key).first()
            if not existing:
                AppConfig.set_config(key, value, description, category)