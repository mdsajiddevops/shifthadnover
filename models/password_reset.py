"""
Password Reset Token Model

This model handles password reset tokens for secure password recovery functionality.
"""

from flask_sqlalchemy import SQLAlchemy
from models.models import db
from datetime import datetime, timedelta
import secrets
import string
import logging

logger = logging.getLogger(__name__)

class PasswordResetToken(db.Model):
    """Password reset tokens for secure password recovery"""
    __tablename__ = 'password_reset_tokens'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    token = db.Column(db.String(255), unique=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    used_at = db.Column(db.DateTime, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # Relationship to user
    user = db.relationship('User', backref='password_reset_tokens')
    
    def __init__(self, user_id, ip_address=None, user_agent=None, expires_in_hours=1):
        """Initialize password reset token"""
        self.user_id = user_id
        self.token = self.generate_secure_token()
        self.created_at = datetime.utcnow()
        self.expires_at = datetime.utcnow() + timedelta(hours=expires_in_hours)
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.is_active = True
    
    @staticmethod
    def generate_secure_token(length=64):
        """Generate a cryptographically secure random token"""
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    def is_valid(self):
        """Check if token is still valid"""
        return (
            self.is_active and 
            self.used_at is None and 
            datetime.utcnow() < self.expires_at
        )
    
    def mark_as_used(self):
        """Mark token as used"""
        self.used_at = datetime.utcnow()
        self.is_active = False
        db.session.commit()
        logger.info(f"Password reset token marked as used for user_id: {self.user_id}")
    
    def deactivate(self):
        """Deactivate token without marking as used"""
        self.is_active = False
        db.session.commit()
        logger.info(f"Password reset token deactivated for user_id: {self.user_id}")
    
    @staticmethod
    def create_token(user_id, ip_address=None, user_agent=None, expires_in_hours=1):
        """Create a new password reset token for a user"""
        try:
            # Deactivate any existing active tokens for this user
            existing_tokens = PasswordResetToken.query.filter_by(
                user_id=user_id, 
                is_active=True
            ).all()
            
            for token in existing_tokens:
                token.deactivate()
            
            # Create new token
            new_token = PasswordResetToken(
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
                expires_in_hours=expires_in_hours
            )
            
            db.session.add(new_token)
            db.session.commit()
            
            logger.info(f"Password reset token created for user_id: {user_id}")
            return new_token
            
        except Exception as e:
            logger.error(f"Error creating password reset token: {str(e)}")
            db.session.rollback()
            return None
    
    @staticmethod
    def find_valid_token(token_string):
        """Find a valid token by token string"""
        try:
            token = PasswordResetToken.query.filter_by(
                token=token_string,
                is_active=True
            ).first()
            
            if token and token.is_valid():
                return token
            elif token and not token.is_valid():
                # Token exists but is expired or used
                token.deactivate()
                
            return None
            
        except Exception as e:
            logger.error(f"Error finding valid token: {str(e)}")
            return None
    
    @staticmethod
    def cleanup_expired_tokens():
        """Clean up expired tokens (should be run periodically)"""
        try:
            expired_tokens = PasswordResetToken.query.filter(
                PasswordResetToken.expires_at < datetime.utcnow(),
                PasswordResetToken.is_active == True
            ).all()
            
            count = 0
            for token in expired_tokens:
                token.deactivate()
                count += 1
            
            logger.info(f"Cleaned up {count} expired password reset tokens")
            return count
            
        except Exception as e:
            logger.error(f"Error cleaning up expired tokens: {str(e)}")
            return 0
    
    def __repr__(self):
        return f'<PasswordResetToken {self.token[:8]}... for user_id {self.user_id}>'