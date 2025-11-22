"""
SSO Configuration Model
Stores SSO provider settings in database for flexible configuration
"""

from models.models import db
from datetime import datetime
from cryptography.fernet import Fernet
import os
import base64

class SSOConfig(db.Model):
    __tablename__ = 'sso_config'
    
    id = db.Column(db.Integer, primary_key=True)
    provider_type = db.Column(db.String(50), nullable=False)  # 'saml', 'oauth', 'azure_ad', 'ldap'
    provider_name = db.Column(db.String(100), nullable=False)  # Display name
    enabled = db.Column(db.Boolean, default=False)
    
    # Configuration as JSON-like key-value pairs
    config_key = db.Column(db.String(100), nullable=False)
    config_value = db.Column(db.Text, nullable=True)
    encrypted = db.Column(db.Boolean, default=False)
    
    # Metadata
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=True)  # Account-specific SSO
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<SSOConfig {self.provider_name}: {self.config_key}>'
    
    @staticmethod
    def get_provider_config(provider_type, account_id=None):
        """Get all configuration for a specific SSO provider"""
        query = SSOConfig.query.filter_by(provider_type=provider_type, enabled=True)
        if account_id:
            query = query.filter_by(account_id=account_id)
        
        configs = query.all()
        result = {}
        for config in configs:
            if config.encrypted:
                result[config.config_key] = SSOConfig._decrypt_value(config.config_value)
            else:
                result[config.config_key] = config.config_value
        return result
    
    @staticmethod
    def set_provider_config(provider_type, provider_name, config_dict, account_id=None, encrypt_keys=None):
        """Set configuration for an SSO provider"""
        encrypt_keys = encrypt_keys or ['client_secret', 'private_key', 'password']
        
        # Remove existing config for this provider
        SSOConfig.query.filter_by(provider_type=provider_type, account_id=account_id).delete()
        
        # Add new configuration
        for key, value in config_dict.items():
            should_encrypt = key.lower() in [k.lower() for k in encrypt_keys]
            encrypted_value = SSOConfig._encrypt_value(value) if should_encrypt else value
            
            config = SSOConfig(
                provider_type=provider_type,
                provider_name=provider_name,
                enabled=True,
                config_key=key,
                config_value=encrypted_value,
                encrypted=should_encrypt,
                account_id=account_id
            )
            db.session.add(config)
        
        db.session.commit()
    
    @staticmethod
    def is_provider_enabled(provider_type, account_id=None):
        """Check if an SSO provider is enabled"""
        query = SSOConfig.query.filter_by(provider_type=provider_type, enabled=True)
        if account_id:
            query = query.filter_by(account_id=account_id)
        return query.first() is not None
    
    @staticmethod
    def _get_encryption_key():
        """Get encryption key for sensitive data from Docker secrets"""
        # First try environment variable (fastest)
        key = os.environ.get('SSO_ENCRYPTION_KEY')
        if key:
            return key.encode()
        
        # Try Docker secrets directly (avoid circular import)
        docker_secret_paths = [
            '/run/secrets/sso_encryption_key',  # Production Docker
            './secrets/sso_encryption_key'      # Development
        ]
        
        for secret_path in docker_secret_paths:
            if os.path.exists(secret_path):
                try:
                    with open(secret_path, 'r') as f:
                        key = f.read().strip()
                        if key:
                            return key.encode()
                except Exception as e:
                    print(f"Error reading SSO encryption key from {secret_path}: {e}")
        
        # Generate a new key as last resort
        key = Fernet.generate_key()
        print(f"⚠️  Generated new SSO encryption key: {key.decode()}")
        print("⚠️  Please store this key securely in Docker secrets as 'sso_encryption_key'")
        return key
    
    @staticmethod
    def _encrypt_value(value):
        """Encrypt sensitive configuration values"""
        if not value:
            return value
        
        try:
            key = SSOConfig._get_encryption_key()
            f = Fernet(key)
            return f.encrypt(value.encode()).decode()
        except Exception as e:
            print(f"Encryption error: {e}")
            return value
    
    @staticmethod
    def _decrypt_value(encrypted_value):
        """Decrypt sensitive configuration values"""
        if not encrypted_value:
            return encrypted_value
        
        try:
            key = SSOConfig._get_encryption_key()
            f = Fernet(key)
            return f.decrypt(encrypted_value.encode()).decode()
        except Exception as e:
            print(f"Decryption error: {e}")
            return encrypted_value
