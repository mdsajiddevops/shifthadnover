"""
Email Configuration Models

Manages email recipient configurations for Account and Team based notifications.
"""

from datetime import datetime
from models.models import db
from sqlalchemy import UniqueConstraint

class TeamEmailConfig(db.Model):
    """
    Email configuration for specific Account + Team combinations.
    Stores email recipients for handover notifications.
    """
    __tablename__ = 'team_email_config'
    
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    
    # Email Recipients Configuration
    to_recipients = db.Column(db.Text, nullable=True)  # Comma-separated email addresses for TO field
    cc_recipients = db.Column(db.Text, nullable=True)  # Comma-separated email addresses for CC field
    priority_recipients = db.Column(db.Text, nullable=True)  # Additional recipients for priority incidents
    
    # Configuration Status
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_default = db.Column(db.Boolean, default=False, nullable=False)  # Fallback configuration for the account
    
    # Metadata
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Foreign Key Relationships
    account = db.relationship('Account', backref='email_configs')
    team = db.relationship('Team', backref='email_configs')
    creator = db.relationship('User', foreign_keys=[created_by], backref='created_email_configs')
    updater = db.relationship('User', foreign_keys=[updated_by], backref='updated_email_configs')
    
    # Ensure only one active configuration per Account + Team
    __table_args__ = (
        UniqueConstraint('account_id', 'team_id', 'is_active', name='uq_account_team_active'),
    )
    
    def __repr__(self):
        return f'<TeamEmailConfig {self.account.name} - {self.team.name}>'
    
    def get_all_recipients(self):
        """Get all email recipients (TO + CC) as a list."""
        recipients = []
        
        if self.to_recipients:
            to_list = [email.strip() for email in self.to_recipients.split(',') if email.strip()]
            recipients.extend(to_list)
            
        if self.cc_recipients:
            cc_list = [email.strip() for email in self.cc_recipients.split(',') if email.strip()]
            recipients.extend(cc_list)
            
        return list(set(recipients))  # Remove duplicates
    
    def get_to_recipients_list(self):
        """Get TO recipients as a list."""
        if not self.to_recipients:
            return []
        return [email.strip() for email in self.to_recipients.split(',') if email.strip()]
    
    def get_cc_recipients_list(self):
        """Get CC recipients as a list."""
        if not self.cc_recipients:
            return []
        return [email.strip() for email in self.cc_recipients.split(',') if email.strip()]
    
    def get_priority_recipients_list(self):
        """Get priority recipients as a list."""
        if not self.priority_recipients:
            return []
        return [email.strip() for email in self.priority_recipients.split(',') if email.strip()]
    
    def validate_recipients(self):
        """Validate all email addresses."""
        import re
        email_pattern = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
        
        all_recipients = []
        if self.to_recipients:
            all_recipients.extend(self.get_to_recipients_list())
        if self.cc_recipients:
            all_recipients.extend(self.get_cc_recipients_list())
        if self.priority_recipients:
            all_recipients.extend(self.get_priority_recipients_list())
        
        invalid_emails = []
        for email in all_recipients:
            if not email_pattern.match(email):
                invalid_emails.append(email)
        
        return invalid_emails
    
    @classmethod
    def get_config_for_team(cls, account_id, team_id):
        """Get active email configuration for specific account and team."""
        return cls.query.filter_by(
            account_id=account_id,
            team_id=team_id,
            is_active=True
        ).first()
    
    @classmethod
    def get_default_config_for_account(cls, account_id):
        """Get default email configuration for account (fallback)."""
        return cls.query.filter_by(
            account_id=account_id,
            is_default=True,
            is_active=True
        ).first()
    
    @classmethod
    def get_configs_for_account(cls, account_id):
        """Get all email configurations for an account."""
        return cls.query.filter_by(account_id=account_id, is_active=True).all()

class EmailConfigAuditLog(db.Model):
    """
    Audit log for email configuration changes.
    Tracks who made what changes when.
    """
    __tablename__ = 'email_config_audit_log'
    
    id = db.Column(db.Integer, primary_key=True)
    config_id = db.Column(db.Integer, db.ForeignKey('team_email_config.id'), nullable=False)
    action = db.Column(db.String(20), nullable=False)  # 'CREATE', 'UPDATE', 'DELETE', 'ACTIVATE', 'DEACTIVATE'
    
    # Change Details
    old_values = db.Column(db.JSON, nullable=True)  # Previous values (for updates)
    new_values = db.Column(db.JSON, nullable=True)  # New values
    change_reason = db.Column(db.Text, nullable=True)  # Optional reason for change
    
    # Metadata
    performed_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    performed_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    ip_address = db.Column(db.String(45), nullable=True)  # Track IP for security
    
    # Relationships
    config = db.relationship('TeamEmailConfig', backref='audit_logs')
    user = db.relationship('User', backref='email_config_audits')
    
    def __repr__(self):
        return f'<EmailConfigAuditLog {self.action} by {self.user.username}>'