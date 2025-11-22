"""
Shift Swap & Leave Management Models
Database models for handling shift swap requests and leave applications with approval workflow
"""

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from models.models import db

class ShiftSwapRequest(db.Model):
    """Model for shift swap requests between team members"""
    __tablename__ = 'shift_swap_request'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Request details
    requester_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    swap_with_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    reason = db.Column(db.Text, nullable=False)
    
    # Shift details
    original_date = db.Column(db.Date, nullable=False)
    original_shift_code = db.Column(db.String(8), nullable=False)  # D, E, N, OS, OF
    swap_date = db.Column(db.Date, nullable=False)
    swap_shift_code = db.Column(db.String(8), nullable=False)
    
    # Request metadata
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    
    # Status and approval
    status = db.Column(db.String(20), default='pending', nullable=False)  # pending, approved, rejected, cancelled
    approved_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    approval_comments = db.Column(db.Text)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    approved_at = db.Column(db.DateTime)
    
    # Relationships
    requester = db.relationship('User', foreign_keys=[requester_id], backref='requested_swaps')
    swap_with = db.relationship('User', foreign_keys=[swap_with_id], backref='received_swap_requests')
    approved_by = db.relationship('User', foreign_keys=[approved_by_id], backref='approved_swaps')
    account = db.relationship('Account', backref='shift_swap_requests')
    team = db.relationship('Team', backref='shift_swap_requests')
    
    def __repr__(self):
        return f'<ShiftSwapRequest {self.id}: {self.requester.username} <-> {self.swap_with.username}>'

class LeaveRequest(db.Model):
    """Model for leave requests"""
    __tablename__ = 'leave_request'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Request details
    requester_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    leave_type = db.Column(db.String(20), nullable=False)  # sick, emergency, planned, other
    leave_date = db.Column(db.Date, nullable=False)
    shift_code = db.Column(db.String(8), nullable=False)  # D, E, N, OS, OF
    reason = db.Column(db.Text)
    
    # Request metadata
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    
    # Status and approval
    status = db.Column(db.String(20), default='pending', nullable=False)  # pending, approved, rejected, cancelled
    approved_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    approval_comments = db.Column(db.Text)
    
    # Coverage assignment (optional)
    covered_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    coverage_notes = db.Column(db.Text)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    approved_at = db.Column(db.DateTime)
    
    # Relationships
    requester = db.relationship('User', foreign_keys=[requester_id], backref='leave_requests')
    approved_by = db.relationship('User', foreign_keys=[approved_by_id], backref='approved_leaves')
    covered_by = db.relationship('User', foreign_keys=[covered_by_id], backref='coverage_assignments')
    account = db.relationship('Account', backref='leave_requests')  
    team = db.relationship('Team', backref='leave_requests')
    
    def __repr__(self):
        return f'<LeaveRequest {self.id}: {self.requester.username} - {self.leave_type} on {self.leave_date}>'

class SwapLeaveNotification(db.Model):
    """Notifications for shift swap and leave requests"""
    __tablename__ = 'swap_leave_notification'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Notification details
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    notification_type = db.Column(db.String(30), nullable=False)  # swap_request, leave_request, swap_approved, etc.
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    
    # Reference to request
    swap_request_id = db.Column(db.Integer, db.ForeignKey('shift_swap_request.id'), nullable=True)
    leave_request_id = db.Column(db.Integer, db.ForeignKey('leave_request.id'), nullable=True)
    
    # Status
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    email_sent = db.Column(db.Boolean, default=False, nullable=False)
    
    # Metadata
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    read_at = db.Column(db.DateTime)
    
    # Relationships
    recipient = db.relationship('User', backref='swap_leave_notifications')
    swap_request = db.relationship('ShiftSwapRequest', backref='notifications')
    leave_request = db.relationship('LeaveRequest', backref='notifications')
    account = db.relationship('Account', backref='swap_leave_notifications')
    team = db.relationship('Team', backref='swap_leave_notifications')
    
    def __repr__(self):
        return f'<SwapLeaveNotification {self.id}: {self.notification_type} for {self.recipient.username}>'

class SwapLeaveAuditLog(db.Model):
    """Audit log for shift swap and leave management actions"""
    __tablename__ = 'swap_leave_audit_log'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Action details
    action = db.Column(db.String(50), nullable=False)  # request_created, approved, rejected, roster_updated, etc.
    performed_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    target_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    # Request references
    swap_request_id = db.Column(db.Integer, db.ForeignKey('shift_swap_request.id'), nullable=True)
    leave_request_id = db.Column(db.Integer, db.ForeignKey('leave_request.id'), nullable=True)
    
    # Action details
    details = db.Column(db.Text)  # JSON or text description of changes made
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    
    # Metadata
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    
    # Timestamp
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    performed_by = db.relationship('User', foreign_keys=[performed_by_id], backref='swap_leave_actions')
    target_user = db.relationship('User', foreign_keys=[target_user_id], backref='swap_leave_target_actions')
    swap_request = db.relationship('ShiftSwapRequest', backref='audit_logs')
    leave_request = db.relationship('LeaveRequest', backref='audit_logs')
    account = db.relationship('Account', backref='swap_leave_audit_logs')
    team = db.relationship('Team', backref='swap_leave_audit_logs')
    
    def __repr__(self):
        return f'<SwapLeaveAuditLog {self.id}: {self.action} by {self.performed_by.username}>'