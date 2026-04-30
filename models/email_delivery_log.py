"""
Email Delivery Log Model
Tracks all email delivery attempts for monitoring and debugging purposes
"""
from models.models import db
from datetime import datetime


class EmailDeliveryLog(db.Model):
    """Model to track email delivery attempts and their status"""
    __tablename__ = 'email_delivery_log'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Email details
    subject = db.Column(db.String(500), nullable=False)
    recipients = db.Column(db.Text, nullable=False)  # JSON list of recipients
    cc_recipients = db.Column(db.Text, nullable=True)  # JSON list of CC recipients
    sender = db.Column(db.String(255), nullable=True)
    
    # Source information
    source_type = db.Column(db.String(50), nullable=False)  # 'handover', 'incident_assignment', 'notification', etc.
    source_id = db.Column(db.Integer, nullable=True)  # shift_id, incident_id, etc.
    
    # Delivery status
    status = db.Column(db.String(50), nullable=False, default='pending')  # pending, sent, failed, skipped
    error_message = db.Column(db.Text, nullable=True)
    
    # SMTP details
    smtp_server = db.Column(db.String(255), nullable=True)
    smtp_port = db.Column(db.Integer, nullable=True)
    
    # Timing
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)
    sent_at = db.Column(db.DateTime, nullable=True)
    duration_seconds = db.Column(db.Float, nullable=True)  # Time taken to send
    
    # User/Account context
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=True)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=True)
    triggered_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    # Relationships
    account = db.relationship('Account', backref=db.backref('email_logs', lazy='dynamic'))
    team = db.relationship('Team', backref=db.backref('email_logs', lazy='dynamic'))
    triggered_by = db.relationship('User', backref=db.backref('triggered_emails', lazy='dynamic'))
    
    # Additional metadata
    recipient_count = db.Column(db.Integer, default=0)
    retry_count = db.Column(db.Integer, default=0)
    
    # UNS Event ID - unique identifier returned by or generated for UNS email service
    uns_event_id = db.Column(db.String(100), nullable=True, index=True)
    
    def __repr__(self):
        return f'<EmailDeliveryLog {self.id} - {self.status} - {self.subject[:30]}>'
    
    @classmethod
    def log_email_attempt(cls, subject, recipients, source_type, source_id=None, 
                          cc_recipients=None, sender=None, account_id=None, 
                          team_id=None, triggered_by_id=None, smtp_server=None, smtp_port=None,
                          uns_event_id=None):
        """Create a new email delivery log entry"""
        import json
        import uuid
        
        # Convert lists to JSON strings
        recipients_json = json.dumps(recipients) if isinstance(recipients, list) else recipients
        cc_json = json.dumps(cc_recipients) if cc_recipients and isinstance(cc_recipients, list) else cc_recipients
        
        # Generate UNS event ID if not provided
        if not uns_event_id:
            uns_event_id = str(uuid.uuid4())
        
        log = cls(
            subject=subject[:500] if subject else 'No Subject',
            recipients=recipients_json,
            cc_recipients=cc_json,
            sender=sender,
            source_type=source_type,
            source_id=source_id,
            status='pending',
            account_id=account_id,
            team_id=team_id,
            triggered_by_id=triggered_by_id,
            smtp_server=smtp_server,
            smtp_port=smtp_port,
            recipient_count=len(recipients) if isinstance(recipients, list) else 1,
            created_at=datetime.now(),
            uns_event_id=uns_event_id
        )
        db.session.add(log)
        db.session.flush()  # Get the ID without committing
        return log
    
    def mark_sent(self, duration=None, uns_event_id=None):
        """Mark email as successfully sent"""
        self.status = 'sent'
        self.sent_at = datetime.now()
        if duration:
            self.duration_seconds = duration
        if uns_event_id:
            self.uns_event_id = uns_event_id
        db.session.commit()
    
    def mark_failed(self, error_message, duration=None):
        """Mark email as failed with error message"""
        self.status = 'failed'
        self.error_message = str(error_message)[:2000] if error_message else None
        self.sent_at = datetime.now()
        if duration:
            self.duration_seconds = duration
        db.session.commit()
    
    def mark_skipped(self, reason):
        """Mark email as skipped (e.g., notifications disabled)"""
        self.status = 'skipped'
        self.error_message = reason
        db.session.commit()
    
    def get_recipients_list(self):
        """Get recipients as a list"""
        import json
        try:
            return json.loads(self.recipients) if self.recipients else []
        except:
            return [self.recipients] if self.recipients else []
    
    def get_cc_list(self):
        """Get CC recipients as a list"""
        import json
        try:
            return json.loads(self.cc_recipients) if self.cc_recipients else []
        except:
            return [self.cc_recipients] if self.cc_recipients else []

