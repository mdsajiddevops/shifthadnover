"""
Secure Secrets Management System
Hybrid approach: Critical credentials in environment, others in encrypted DB
"""

import os
import json
import logging
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from sqlalchemy import Column, String, DateTime, Text, Boolean, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from flask_sqlalchemy import SQLAlchemy
from flask_login import current_user
from typing import Dict, Any, Optional, List

Base = declarative_base()
logger = logging.getLogger(__name__)

class SecretCategory:
    """Categories for different types of secrets"""
    CRITICAL = "critical"      # Never stored in DB (DB creds, master keys)
    EXTERNAL = "external"      # Third-party APIs (ServiceNow, SMTP)
    APPLICATION = "application" # App-specific configs
    FEATURE = "feature"        # Feature flags and toggles

class SecretStore(Base):
    """Encrypted secret storage in database"""
    __tablename__ = 'secret_store'
    
    id = Column(Integer, primary_key=True)
    key_name = Column(String(255), unique=True, nullable=False, index=True)
    encrypted_value = Column(Text, nullable=False)
    category = Column(String(50), nullable=False, default=SecretCategory.APPLICATION)
    description = Column(Text)
    is_active = Column(Boolean, default=True, nullable=False)
    requires_restart = Column(Boolean, default=False, nullable=False)
    
    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(255))
    updated_by = Column(String(255))
    
    # Security fields
    last_accessed = Column(DateTime)
    access_count = Column(Integer, default=0)
    expires_at = Column(DateTime)  # For temporary secrets
    
    def __repr__(self):
        return f'<SecretStore {self.key_name}:{self.category}>'

class SecretAuditLog(Base):
    """Audit log for secret access and modifications"""
    __tablename__ = 'secret_audit_log'
    
    id = Column(Integer, primary_key=True)
    secret_key = Column(String(255), nullable=False, index=True)
    action = Column(String(50), nullable=False)  # CREATE, READ, UPDATE, DELETE
    user_id = Column(String(255))
    user_email = Column(String(255))
    ip_address = Column(String(45))
    user_agent = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    old_value_hash = Column(String(64))  # Hash of old value for comparison
    new_value_hash = Column(String(64))  # Hash of new value
    success = Column(Boolean, default=True)
    error_message = Column(Text)
    
    def __repr__(self):
        return f'<SecretAudit {self.secret_key}:{self.action} by {self.user_email}>'

class HybridSecretsManager:
    """
    Hybrid secrets manager that combines environment variables with encrypted database storage
    
    Security Layers:
    1. Critical secrets (DB connection, master keys) ONLY from environment/Docker secrets
    2. External API credentials in encrypted database with UI management
    3. Application configs in database with superadmin control
    4. Comprehensive audit logging for all access
    """
    
    def __init__(self, db_session, master_key: str = None):
        self.db_session = db_session
        
        # Master encryption key - NEVER store in database
        if master_key:
            # master_key is already a base64-encoded string, use it directly
            self.fernet = Fernet(master_key)
        else:
            # Get master key from environment (critical security requirement)
            master_key = os.environ.get('SECRETS_MASTER_KEY')
            if not master_key:
                # Generate new master key - MUST be saved securely
                master_key = Fernet.generate_key().decode()
                logger.critical(f"🚨 Generated new SECRETS_MASTER_KEY: {master_key}")
                logger.critical("🚨 SAVE THIS KEY SECURELY - Store in environment variables!")
            
            # master_key from environment is already a base64-encoded string
            self.fernet = Fernet(master_key)
        
        # Define which secrets NEVER go in database
        self.critical_secrets = {
            'DATABASE_URL',
            'DATABASE_PASSWORD', 
            'MYSQL_PASSWORD',
            'MYSQL_ROOT_PASSWORD',
            'SECRET_KEY',
            'SECRETS_MASTER_KEY',
            'SSO_ENCRYPTION_KEY'
        }
    
    def get_secret(self, key_name: str, default: Any = None, category: str = None) -> Any:
        """
        Get secret with security layer priority:
        1. Critical secrets: Environment/Docker secrets only
        2. Others: Database first, then environment fallback
        """
        try:
            # Layer 1: Critical secrets ONLY from environment
            if key_name.upper() in self.critical_secrets:
                value = self._get_environment_secret(key_name)
                if value:
                    self._log_secret_access(key_name, "READ_ENV", success=True)
                    return value
                else:
                    self._log_secret_access(key_name, "READ_ENV", success=False, 
                                          error="Critical secret not found in environment")
                    if default is not None:
                        return default
                    raise ValueError(f"Critical secret '{key_name}' not found in environment")
            
            # Layer 2: Non-critical secrets from database first
            db_value = self._get_database_secret(key_name)
            if db_value is not None:
                self._log_secret_access(key_name, "READ_DB", success=True)
                return db_value
            
            # Layer 3: Fallback to environment
            env_value = self._get_environment_secret(key_name)
            if env_value:
                self._log_secret_access(key_name, "READ_ENV_FALLBACK", success=True)
                return env_value
            
            # Layer 4: Default value
            if default is not None:
                self._log_secret_access(key_name, "READ_DEFAULT", success=True)
                return default
            
            self._log_secret_access(key_name, "READ_FAILED", success=False, 
                                  error="Secret not found in any source")
            return None
            
        except Exception as e:
            self._log_secret_access(key_name, "READ_ERROR", success=False, error=str(e))
            logger.error(f"Error getting secret {key_name}: {e}")
            return default
    
    def set_secret(self, key_name: str, value: str, category: str = SecretCategory.APPLICATION,
                   description: str = None, requires_restart: bool = False, 
                   expires_in_days: int = None) -> bool:
        """
        Set secret with security validation
        Critical secrets cannot be set via this method
        """
        try:
            # Security check: Critical secrets cannot be stored in database
            if key_name.upper() in self.critical_secrets:
                error_msg = f"Critical secret '{key_name}' cannot be stored in database"
                self._log_secret_access(key_name, "SET_REJECTED", success=False, error=error_msg)
                raise ValueError(error_msg)
            
            # Get current user for audit
            user_id = getattr(current_user, 'id', 'system') if current_user else 'system'
            user_email = getattr(current_user, 'email', 'system') if current_user else 'system'
            
            # Check if secret exists
            existing_secret = self.db_session.query(SecretStore).filter_by(key_name=key_name).first()
            
            # Encrypt the value
            encrypted_value = self.fernet.encrypt(value.encode()).decode()
            
            # Calculate expiration
            expires_at = None
            if expires_in_days:
                expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
            
            if existing_secret:
                # Update existing
                old_hash = self._hash_value(self.fernet.decrypt(existing_secret.encrypted_value.encode()).decode())
                
                existing_secret.encrypted_value = encrypted_value
                existing_secret.category = category
                existing_secret.description = description
                existing_secret.requires_restart = requires_restart
                existing_secret.expires_at = expires_at
                existing_secret.updated_by = user_email
                existing_secret.updated_at = datetime.utcnow()
                
                action = "UPDATE"
            else:
                # Create new
                new_secret = SecretStore(
                    key_name=key_name,
                    encrypted_value=encrypted_value,
                    category=category,
                    description=description,
                    requires_restart=requires_restart,
                    expires_at=expires_at,
                    created_by=user_email
                )
                self.db_session.add(new_secret)
                old_hash = None
                action = "CREATE"
            
            # Commit changes
            self.db_session.commit()
            
            # Log the action
            new_hash = self._hash_value(value)
            self._log_secret_access(key_name, action, success=True, 
                                  old_value_hash=old_hash, new_value_hash=new_hash)
            
            logger.info(f"Secret '{key_name}' {action.lower()}d successfully by {user_email}")
            return True
            
        except Exception as e:
            self.db_session.rollback()
            self._log_secret_access(key_name, "SET_ERROR", success=False, error=str(e))
            logger.error(f"Error setting secret {key_name}: {e}")
            return False
    
    def delete_secret(self, key_name: str) -> bool:
        """Delete secret from database (critical secrets cannot be deleted)"""
        try:
            if key_name.upper() in self.critical_secrets:
                error_msg = f"Critical secret '{key_name}' cannot be deleted"
                self._log_secret_access(key_name, "DELETE_REJECTED", success=False, error=error_msg)
                raise ValueError(error_msg)
            
            secret = self.db_session.query(SecretStore).filter_by(key_name=key_name).first()
            if secret:
                user_email = getattr(current_user, 'email', 'system') if current_user else 'system'
                
                self.db_session.delete(secret)
                self.db_session.commit()
                
                self._log_secret_access(key_name, "DELETE", success=True)
                logger.info(f"Secret '{key_name}' deleted by {user_email}")
                return True
            else:
                self._log_secret_access(key_name, "DELETE_NOT_FOUND", success=False, 
                                      error="Secret not found")
                return False
                
        except Exception as e:
            self.db_session.rollback()
            self._log_secret_access(key_name, "DELETE_ERROR", success=False, error=str(e))
            logger.error(f"Error deleting secret {key_name}: {e}")
            return False
    
    def list_secrets(self, category: str = None, include_values: bool = False) -> List[Dict]:
        """List all secrets with optional filtering"""
        try:
            query = self.db_session.query(SecretStore)
            if category:
                query = query.filter_by(category=category)
            
            secrets = query.all()
            result = []
            
            for secret in secrets:
                secret_info = {
                    'key_name': secret.key_name,
                    'category': secret.category,
                    'description': secret.description,
                    'is_active': secret.is_active,
                    'requires_restart': secret.requires_restart,
                    'created_at': secret.created_at.isoformat(),
                    'updated_at': secret.updated_at.isoformat() if secret.updated_at else None,
                    'created_by': secret.created_by,
                    'updated_by': secret.updated_by,
                    'expires_at': secret.expires_at.isoformat() if secret.expires_at else None,
                    'last_accessed': secret.last_accessed.isoformat() if secret.last_accessed else None,
                    'access_count': secret.access_count
                }
                
                if include_values:
                    try:
                        decrypted_value = self.fernet.decrypt(secret.encrypted_value.encode()).decode()
                        secret_info['value'] = decrypted_value
                    except Exception as e:
                        secret_info['value'] = f"[DECRYPTION_ERROR: {str(e)}]"
                
                result.append(secret_info)
            
            self._log_secret_access("LIST_SECRETS", "LIST", success=True)
            return result
            
        except Exception as e:
            self._log_secret_access("LIST_SECRETS", "LIST_ERROR", success=False, error=str(e))
            logger.error(f"Error listing secrets: {e}")
            return []
    
    def get_audit_log(self, secret_key: str = None, limit: int = 100) -> List[Dict]:
        """Get audit log for secrets access"""
        try:
            query = self.db_session.query(SecretAuditLog)
            if secret_key:
                query = query.filter_by(secret_key=secret_key)
            
            logs = query.order_by(SecretAuditLog.timestamp.desc()).limit(limit).all()
            
            result = []
            for log in logs:
                result.append({
                    'secret_key': log.secret_key,
                    'action': log.action,
                    'user_email': log.user_email,
                    'ip_address': log.ip_address,
                    'timestamp': log.timestamp.isoformat(),
                    'success': log.success,
                    'error_message': log.error_message
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting audit log: {e}")
            return []
    
    def _get_environment_secret(self, key_name: str) -> Optional[str]:
        """Get secret from environment variables or Docker secrets"""
        # Try Docker secrets first
        secret_file = f"/run/secrets/{key_name.lower()}"
        if os.path.exists(secret_file):
            try:
                with open(secret_file, 'r') as f:
                    return f.read().strip()
            except Exception as e:
                logger.error(f"Error reading Docker secret {key_name}: {e}")
        
        # Try environment variables
        return os.environ.get(key_name.upper()) or os.environ.get(key_name)
    
    def _get_database_secret(self, key_name: str) -> Optional[str]:
        """Get and decrypt secret from database - checks both SecretStore and AppConfig"""
        try:
            # First check SecretStore table for encrypted secrets
            secret = self.db_session.query(SecretStore).filter_by(
                key_name=key_name, 
                is_active=True
            ).first()
            
            if secret:
                # Check expiration
                if secret.expires_at and secret.expires_at < datetime.utcnow():
                    logger.warning(f"Secret '{key_name}' has expired")
                    return None
                
                # Update access tracking
                secret.last_accessed = datetime.utcnow()
                secret.access_count = (secret.access_count or 0) + 1
                self.db_session.commit()
                
                # Decrypt and return
                decrypted_value = self.fernet.decrypt(secret.encrypted_value.encode()).decode()
                return decrypted_value
            
            # If not found in SecretStore, check AppConfig for application-level settings
            try:
                from models.app_config import AppConfig
                app_config_value = AppConfig.get_config(key_name)
                if app_config_value is not None:
                    return app_config_value
            except Exception as e:
                logger.debug(f"No AppConfig value found for {key_name}: {e}")
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting database secret {key_name}: {e}")
            return None
    
    def _log_secret_access(self, secret_key: str, action: str, success: bool = True,
                          error: str = None, old_value_hash: str = None, new_value_hash: str = None):
        """Log secret access for audit purposes"""
        try:
            from flask import request
            
            user_id = getattr(current_user, 'id', None) if current_user else None
            user_email = getattr(current_user, 'email', 'system') if current_user else 'system'
            ip_address = request.remote_addr if request else None
            user_agent = request.headers.get('User-Agent') if request else None
            
            audit_log = SecretAuditLog(
                secret_key=secret_key,
                action=action,
                user_id=str(user_id) if user_id else None,
                user_email=user_email,
                ip_address=ip_address,
                user_agent=user_agent,
                success=success,
                error_message=error,
                old_value_hash=old_value_hash,
                new_value_hash=new_value_hash
            )
            
            self.db_session.add(audit_log)
            self.db_session.commit()
            
        except Exception as e:
            logger.error(f"Error logging secret access: {e}")
    
    def _hash_value(self, value: str) -> str:
        """Create hash of value for audit purposes (not storing actual value)"""
        import hashlib
        return hashlib.sha256(value.encode()).hexdigest()[:16]

# Global instance
secrets_manager = None

def init_secrets_manager(db_session, master_key: str = None):
    """Initialize global secrets manager"""
    global secrets_manager
    secrets_manager = HybridSecretsManager(db_session, master_key)
    return secrets_manager

def get_secret(key_name: str, default: Any = None, category: str = None) -> Any:
    """Global function to get secrets"""
    if not secrets_manager:
        raise RuntimeError("Secrets manager not initialized")
    return secrets_manager.get_secret(key_name, default, category)