"""
Enhanced Models for Shift Handover with Incident Assignment Workflow
"""

from models.models import db
from datetime import datetime
from sqlalchemy.ext.hybrid import hybrid_property

class HandoverRequest(db.Model):
    """
    Represents a handover request with incident assignments
    """
    __tablename__ = 'handover_request'
    __table_args__ = {'extend_existing': True}  # 🔧 FIXED: Allow coexistence with Shift model
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Basic handover information
    shift_date = db.Column(db.Date, nullable=False)
    current_shift_type = db.Column(db.String(16), nullable=False)  # Morning/Evening/Night
    next_shift_type = db.Column(db.String(16), nullable=False)
    
    # Requestor information
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_by = db.relationship('User', foreign_keys=[created_by_id], backref='handover_requests_created')
    
    # Handover status
    status = db.Column(db.String(32), nullable=False, default='pending')  
    # pending, partially_accepted, fully_accepted, rejected, expired
    
    # General handover notes
    general_notes = db.Column(db.Text)
    shift_summary = db.Column(db.Text)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = db.Column(db.DateTime)  # Auto-expire handovers after certain time
    
    # Team/Account context
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    
    # Relationships
    incident_assignments = db.relationship('IncidentAssignment', backref='handover_request', lazy=True, cascade='all, delete-orphan')
    handover_responses = db.relationship('HandoverResponse', backref='handover_request', lazy=True, cascade='all, delete-orphan')
    notifications = db.relationship('HandoverNotification', backref='handover_request', lazy=True, cascade='all, delete-orphan')
    
    @hybrid_property
    def response_summary(self):
        """Get summary of responses"""
        responses = self.handover_responses
        total = len(responses)
        accepted = len([r for r in responses if r.status == 'accepted'])
        rejected = len([r for r in responses if r.status == 'rejected'])
        pending = len([r for r in responses if r.status == 'pending'])
        
        return {
            'total': total,
            'accepted': accepted,
            'rejected': rejected,
            'pending': pending
        }
    
    @hybrid_property
    def all_incidents_assigned(self):
        """Check if all incidents have been assigned"""
        return len(self.incident_assignments) > 0 and all(
            assignment.assigned_to_id is not None 
            for assignment in self.incident_assignments
        )
    
    def __repr__(self):
        return f'<HandoverRequest {self.id}: {self.current_shift_type} -> {self.next_shift_type} on {self.shift_date}>'


class IncidentAssignment(db.Model):
    """
    Represents assignment of a specific incident to a team member during handover
    """
    __tablename__ = 'incident_assignment'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Handover reference
    handover_request_id = db.Column(db.Integer, db.ForeignKey('handover_request.id'), nullable=False)
    
    # Incident information
    incident_id = db.Column(db.String(64), nullable=False)  # ServiceNow incident ID
    incident_title = db.Column(db.String(256), nullable=False)
    incident_description = db.Column(db.Text)
    incident_priority = db.Column(db.String(16), nullable=False)
    incident_status = db.Column(db.String(32), nullable=False)
    incident_url = db.Column(db.String(512))  # Link to ServiceNow incident
    
    # Assignment details
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    assigned_to = db.relationship('User', foreign_keys=[assigned_to_id], backref='incident_assignments')
    assigned_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    assigned_by = db.relationship('User', foreign_keys=[assigned_by_id])
    
    # Assignment notes and context
    assignment_notes = db.Column(db.Text)  # Notes from the assigner
    handover_context = db.Column(db.Text)  # Specific handover instructions
    
    # Status tracking
    assignment_status = db.Column(db.String(32), nullable=False, default='pending')
    # pending, accepted, rejected, reassigned
    
    # Timestamps
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    responded_at = db.Column(db.DateTime)
    
    # Team/Account context
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    
    # Relationships
    responses = db.relationship('IncidentAssignmentResponse', backref='incident_assignment', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<IncidentAssignment {self.incident_id} -> {self.assigned_to.username if self.assigned_to else "Unassigned"}>'


class IncidentAssignmentResponse(db.Model):
    """
    Response from assigned engineer regarding incident assignment
    """
    __tablename__ = 'incident_assignment_response'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Assignment reference
    incident_assignment_id = db.Column(db.Integer, db.ForeignKey('incident_assignment.id'), nullable=False)
    
    # Response details
    responder_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    responder = db.relationship('User', backref='incident_responses')
    
    status = db.Column(db.String(32), nullable=False)  # accepted, rejected, needs_clarification
    comments = db.Column(db.Text)  # Fixed: matches database column name
    estimated_completion_time = db.Column(db.DateTime)  # When they expect to resolve
    
    # Metadata
    responded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Team/Account context (required by database)
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    
    def __repr__(self):
        return f'<IncidentAssignmentResponse {self.status} by {self.responder.username}>'


class HandoverIncidentResponseLog(db.Model):
    """
    Comprehensive handover incident response tracking table
    Records complete details of handover incident assignments and responses
    """
    __tablename__ = 'handover_incident_response_log'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Date and Time Information
    response_date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date)
    response_datetime = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Shift Information
    from_shift_type = db.Column(db.String(32))  # Morning/Evening/Night
    to_shift_type = db.Column(db.String(32))    # Morning/Evening/Night
    from_shift_id = db.Column(db.Integer, db.ForeignKey('shift.id'))
    to_shift_id = db.Column(db.Integer, db.ForeignKey('shift.id'))
    
    # Assignment Details
    assigned_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    assigned_by = db.relationship('User', foreign_keys=[assigned_by_id], backref='handover_assignments_given')
    assigned_by_name = db.Column(db.String(128))  # Cached name for reporting
    
    accepted_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    accepted_by = db.relationship('User', foreign_keys=[accepted_by_id], backref='handover_assignments_received')
    accepted_by_name = db.Column(db.String(128))  # Cached name for reporting
    
    # Incident Information
    incident_number = db.Column(db.String(64), nullable=False)  # ServiceNow/ticket number
    incident_title = db.Column(db.String(256), nullable=False)
    incident_description = db.Column(db.Text)
    incident_priority = db.Column(db.String(16), nullable=False)  # High/Medium/Low/Critical
    incident_type = db.Column(db.String(32), nullable=False)  # open/active/handover/closed
    incident_category = db.Column(db.String(64))  # Application/Network/Infrastructure etc.
    
    # Status and Response
    assignment_status = db.Column(db.String(32), nullable=False)  # pending/accepted/rejected/reassigned
    response_status = db.Column(db.String(32), nullable=False)    # accepted/rejected/needs_clarification
    response_comments = db.Column(db.Text)  # Detailed comments from responder
    assignment_notes = db.Column(db.Text)   # Original assignment notes
    
    # Timing Information
    assigned_at = db.Column(db.DateTime, nullable=False)  # When assignment was created
    responded_at = db.Column(db.DateTime, nullable=False)  # When response was given
    estimated_completion = db.Column(db.DateTime)         # Expected resolution time
    actual_completion = db.Column(db.DateTime)            # Actual resolution time
    
    # Context and References
    handover_request_id = db.Column(db.Integer, db.ForeignKey('handover_request.id'))
    incident_assignment_id = db.Column(db.Integer, db.ForeignKey('incident_assignment.id'))
    incident_assignment_response_id = db.Column(db.Integer, db.ForeignKey('incident_assignment_response.id'))
    
    # Team and Account Context
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    
    # Additional Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    handover_request = db.relationship('HandoverRequest', backref='response_logs')
    incident_assignment = db.relationship('IncidentAssignment', backref='response_logs')
    incident_assignment_response = db.relationship('IncidentAssignmentResponse', backref='response_logs')
    
    def __repr__(self):
        return f'<HandoverIncidentResponseLog {self.incident_number} {self.response_status} by {self.accepted_by_name}>'
    
    @property
    def response_time_minutes(self):
        """Calculate response time in minutes"""
        if self.assigned_at and self.responded_at:
            delta = self.responded_at - self.assigned_at
            return int(delta.total_seconds() / 60)
        return None
    
    @property
    def is_escalated(self):
        """Check if incident was escalated based on response time"""
        response_time = self.response_time_minutes
        if response_time:
            # Critical: 15 min, High: 30 min, Medium: 60 min, Low: 120 min
            thresholds = {'critical': 15, 'high': 30, 'medium': 60, 'low': 120}
            threshold = thresholds.get(self.incident_priority.lower(), 60)
            return response_time > threshold
        return False
    
    def to_dict(self):
        """Convert to dictionary for reporting"""
        return {
            'id': self.id,
            'response_date': self.response_date.isoformat() if self.response_date else None,
            'response_datetime': self.response_datetime.isoformat() if self.response_datetime else None,
            'from_shift_type': self.from_shift_type,
            'to_shift_type': self.to_shift_type,
            'assigned_by_name': self.assigned_by_name,
            'accepted_by_name': self.accepted_by_name,
            'incident_number': self.incident_number,
            'incident_title': self.incident_title,
            'incident_priority': self.incident_priority,
            'incident_type': self.incident_type,
            'incident_category': self.incident_category,
            'assignment_status': self.assignment_status,
            'response_status': self.response_status,
            'response_comments': self.response_comments,
            'assigned_at': self.assigned_at.isoformat() if self.assigned_at else None,
            'responded_at': self.responded_at.isoformat() if self.responded_at else None,
            'response_time_minutes': self.response_time_minutes,
            'is_escalated': self.is_escalated,
            'estimated_completion': self.estimated_completion.isoformat() if self.estimated_completion else None,
            'actual_completion': self.actual_completion.isoformat() if self.actual_completion else None
        }


class HandoverResponse(db.Model):
    """
    Overall response to handover request by team members
    """
    __tablename__ = 'handover_response'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Handover reference
    handover_request_id = db.Column(db.Integer, db.ForeignKey('handover_request.id'), nullable=False)
    
    # Response details
    responder_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    responder = db.relationship('User', backref='handover_responses')
    
    status = db.Column(db.String(32), nullable=False)  # accepted, rejected, partial
    response_comments = db.Column(db.Text)
    
    # Availability information
    available_from = db.Column(db.DateTime)
    available_until = db.Column(db.DateTime)
    
    # Metadata
    responded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Team/Account context
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    
    def __repr__(self):
        return f'<HandoverResponse {self.status} by {self.responder.username}>'


class HandoverNotification(db.Model):
    """
    Notifications related to handover requests and responses
    """
    __tablename__ = 'handover_notification'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Notification details
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipient = db.relationship('User', backref='handover_notifications')
    
    # Handover reference (optional - some notifications might be general)
    handover_request_id = db.Column(db.Integer, db.ForeignKey('handover_request.id'), nullable=True)
    
    # Notification content
    notification_type = db.Column(db.String(64), nullable=False)
    # handover_assigned, handover_accepted, handover_rejected, incident_assigned, incident_accepted, incident_rejected, handover_completed
    
    title = db.Column(db.String(256), nullable=False)
    message = db.Column(db.Text, nullable=False)
    action_url = db.Column(db.String(512))  # URL for action button
    action_text = db.Column(db.String(64))  # Text for action button
    
    # Status
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    is_dismissed = db.Column(db.Boolean, default=False, nullable=False)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    read_at = db.Column(db.DateTime)
    expires_at = db.Column(db.DateTime)  # Auto-expire notifications
    
    # Team/Account context
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    
    def mark_as_read(self):
        """Mark notification as read"""
        self.is_read = True
        self.read_at = datetime.utcnow()
        db.session.commit()
    
    def __repr__(self):
        return f'<HandoverNotification {self.notification_type} for {self.recipient.username}>'


class HandoverAuditLog(db.Model):
    """
    Audit log for all handover-related actions
    """
    __tablename__ = 'handover_audit_log'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # References
    handover_request_id = db.Column(db.Integer, db.ForeignKey('handover_request.id'), nullable=True)
    incident_assignment_id = db.Column(db.Integer, db.ForeignKey('incident_assignment.id'), nullable=True)
    
    # Action details
    action_type = db.Column(db.String(64), nullable=False)
    # handover_created, handover_submitted, incident_assigned, incident_reassigned, 
    # response_submitted, handover_accepted, handover_rejected, handover_completed, email_sent
    
    performed_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    performed_by = db.relationship('User', backref='handover_audit_logs')
    
    description = db.Column(db.Text, nullable=False)
    details = db.Column(db.JSON)  # Additional structured data
    
    # Metadata
    performed_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    
    # Team/Account context
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    
    def __repr__(self):
        return f'<HandoverAuditLog {self.action_type} by {self.performed_by.username}>'