"""
Collaborative Handover Models
=============================
Database models for real-time collaborative editing of handover forms.
Supports multiple users editing the same draft simultaneously without Redis.
"""

from datetime import datetime, timedelta
from models.models import db
from sqlalchemy import event
import json


class HandoverSession(db.Model):
    """
    Tracks active editing sessions for handover drafts.
    Each user working on a draft has an active session.
    """
    __tablename__ = 'handover_session'
    
    id = db.Column(db.Integer, primary_key=True)
    shift_id = db.Column(db.Integer, db.ForeignKey('shift.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Session tracking
    session_token = db.Column(db.String(64), unique=True, nullable=False, index=True)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_heartbeat = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    is_active = db.Column(db.Boolean, default=True, index=True)
    
    # Current editing context
    current_section = db.Column(db.String(64), nullable=True)  # e.g., 'incidents', 'keypoints', 'changes'
    current_item_id = db.Column(db.String(64), nullable=True)  # e.g., 'incident_3', 'keypoint_new_1'
    
    # Relationships
    user = db.relationship('User', backref=db.backref('handover_sessions', lazy='dynamic'))
    shift = db.relationship('Shift', backref=db.backref('editing_sessions', lazy='dynamic'))
    
    # Indexes for efficient queries
    __table_args__ = (
        db.Index('idx_active_sessions', 'shift_id', 'is_active'),
        db.Index('idx_session_heartbeat', 'is_active', 'last_heartbeat'),
    )
    
    def __repr__(self):
        return f'<HandoverSession {self.id}: User {self.user_id} on Shift {self.shift_id}>'
    
    def to_dict(self):
        user_display_name = 'Unknown'
        user_initials = '?'
        if self.user:
            user_display_name = self.user.display_name or self.user.username
            # Get proper initials from display name
            name_parts = user_display_name.split()
            if len(name_parts) >= 2:
                user_initials = (name_parts[0][0] + name_parts[1][0]).upper()
            else:
                user_initials = user_display_name[:2].upper() if user_display_name else '?'
        
        return {
            'id': self.id,
            'shift_id': self.shift_id,
            'user_id': self.user_id,
            'user_name': user_display_name,
            'username': user_display_name,  # Alias for compatibility
            'user_avatar': user_initials,
            'session_token': self.session_token,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'last_heartbeat': self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            'is_active': self.is_active,
            'current_section': self.current_section,
            'current_item_id': self.current_item_id
        }
    
    @classmethod
    def cleanup_stale_sessions(cls, timeout_minutes=2):
        """Remove sessions that haven't sent a heartbeat recently"""
        cutoff = datetime.utcnow() - timedelta(minutes=timeout_minutes)
        stale_sessions = cls.query.filter(
            cls.is_active == True,
            cls.last_heartbeat < cutoff
        ).all()
        
        for session in stale_sessions:
            session.is_active = False
        
        db.session.commit()
        return len(stale_sessions)
    
    @classmethod
    def get_active_users(cls, shift_id):
        """Get all active users editing a specific shift"""
        cls.cleanup_stale_sessions()
        return cls.query.filter_by(shift_id=shift_id, is_active=True).all()


class SectionLock(db.Model):
    """
    Soft locks for sections being actively edited.
    Prevents conflicts by indicating who is editing what.
    """
    __tablename__ = 'section_lock'
    
    id = db.Column(db.Integer, primary_key=True)
    shift_id = db.Column(db.Integer, db.ForeignKey('shift.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Lock details
    section_type = db.Column(db.String(32), nullable=False)  # 'incident', 'keypoint', 'change', 'kb'
    item_id = db.Column(db.String(64), nullable=False)  # 'open_1', 'new_incident_abc123', etc.
    
    # Timing
    locked_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('section_locks', lazy='dynamic'))
    
    __table_args__ = (
        db.UniqueConstraint('shift_id', 'section_type', 'item_id', name='uq_section_lock'),
        db.Index('idx_lock_expiry', 'expires_at'),
    )
    
    def __repr__(self):
        return f'<SectionLock {self.section_type}:{self.item_id} by User {self.user_id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'shift_id': self.shift_id,
            'user_id': self.user_id,
            'user_name': self.user.display_name or self.user.username if self.user else 'Unknown',
            'section_type': self.section_type,
            'item_id': self.item_id,
            'locked_at': self.locked_at.isoformat() if self.locked_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'is_expired': datetime.utcnow() > self.expires_at if self.expires_at else True
        }
    
    @classmethod
    def acquire_lock(cls, shift_id, user_id, section_type, item_id, duration_seconds=60):
        """Try to acquire a lock on a section. Returns the lock if successful, None if already locked."""
        # Clean up expired locks first
        cls.cleanup_expired()
        
        # Check for existing lock
        existing = cls.query.filter_by(
            shift_id=shift_id,
            section_type=section_type,
            item_id=item_id
        ).first()
        
        if existing:
            if existing.user_id == user_id:
                # Extend own lock
                existing.expires_at = datetime.utcnow() + timedelta(seconds=duration_seconds)
                db.session.commit()
                return existing
            elif datetime.utcnow() > existing.expires_at:
                # Take over expired lock
                existing.user_id = user_id
                existing.locked_at = datetime.utcnow()
                existing.expires_at = datetime.utcnow() + timedelta(seconds=duration_seconds)
                db.session.commit()
                return existing
            else:
                # Lock held by another user
                return None
        
        # Create new lock
        lock = cls(
            shift_id=shift_id,
            user_id=user_id,
            section_type=section_type,
            item_id=item_id,
            expires_at=datetime.utcnow() + timedelta(seconds=duration_seconds)
        )
        db.session.add(lock)
        db.session.commit()
        return lock
    
    @classmethod
    def release_lock(cls, shift_id, user_id, section_type, item_id):
        """Release a lock if owned by the user"""
        lock = cls.query.filter_by(
            shift_id=shift_id,
            user_id=user_id,
            section_type=section_type,
            item_id=item_id
        ).first()
        
        if lock:
            db.session.delete(lock)
            db.session.commit()
            return True
        return False
    
    @classmethod
    def cleanup_expired(cls):
        """Remove all expired locks"""
        cls.query.filter(cls.expires_at < datetime.utcnow()).delete()
        db.session.commit()
    
    @classmethod
    def get_locks_for_shift(cls, shift_id):
        """Get all active locks for a shift"""
        cls.cleanup_expired()
        return cls.query.filter_by(shift_id=shift_id).filter(cls.expires_at > datetime.utcnow()).all()


class HandoverChange(db.Model):
    """
    Tracks individual changes made to a handover draft.
    Provides audit trail and enables conflict detection/resolution.
    """
    __tablename__ = 'handover_change'
    
    id = db.Column(db.Integer, primary_key=True)
    shift_id = db.Column(db.Integer, db.ForeignKey('shift.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Change details
    change_type = db.Column(db.String(32), nullable=False)  # 'add', 'update', 'delete'
    section_type = db.Column(db.String(32), nullable=False)  # 'incident', 'keypoint', 'change', 'kb'
    item_id = db.Column(db.String(64), nullable=True)  # ID of the item changed
    
    # Change data (JSON)
    field_name = db.Column(db.String(64), nullable=True)  # Specific field changed
    old_value = db.Column(db.Text, nullable=True)  # Previous value (JSON)
    new_value = db.Column(db.Text, nullable=True)  # New value (JSON)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    version = db.Column(db.Integer, default=1)  # For optimistic locking
    
    # Sync status
    synced = db.Column(db.Boolean, default=False, index=True)  # Has been broadcast to other clients
    
    # Relationships
    user = db.relationship('User', backref=db.backref('handover_changes', lazy='dynamic'))
    
    __table_args__ = (
        db.Index('idx_change_sync', 'shift_id', 'synced', 'created_at'),
    )
    
    def __repr__(self):
        return f'<HandoverChange {self.change_type} {self.section_type}:{self.item_id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'shift_id': self.shift_id,
            'user_id': self.user_id,
            'user_name': self.user.display_name or self.user.username if self.user else 'Unknown',
            'change_type': self.change_type,
            'section_type': self.section_type,
            'item_id': self.item_id,
            'field_name': self.field_name,
            'old_value': json.loads(self.old_value) if self.old_value else None,
            'new_value': json.loads(self.new_value) if self.new_value else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'version': self.version
        }
    
    @classmethod
    def get_unsynced_changes(cls, shift_id, since_id=0):
        """Get changes that haven't been synced to a client"""
        return cls.query.filter(
            cls.shift_id == shift_id,
            cls.id > since_id
        ).order_by(cls.id.asc()).all()
    
    @classmethod
    def record_change(cls, shift_id, user_id, change_type, section_type, item_id=None, 
                      field_name=None, old_value=None, new_value=None):
        """Record a change to the handover"""
        change = cls(
            shift_id=shift_id,
            user_id=user_id,
            change_type=change_type,
            section_type=section_type,
            item_id=item_id,
            field_name=field_name,
            old_value=json.dumps(old_value) if old_value is not None else None,
            new_value=json.dumps(new_value) if new_value is not None else None
        )
        db.session.add(change)
        db.session.commit()
        return change


class DraftIncident(db.Model):
    """
    Temporary storage for incidents in a collaborative draft.
    Allows multiple users to add incidents simultaneously before final submission.
    """
    __tablename__ = 'draft_incident'
    
    id = db.Column(db.Integer, primary_key=True)
    shift_id = db.Column(db.Integer, db.ForeignKey('shift.id'), nullable=False, index=True)
    temp_id = db.Column(db.String(64), nullable=False)  # Client-generated temporary ID
    
    # Incident data
    incident_type = db.Column(db.String(32), nullable=False)  # 'Open', 'Closed', 'Priority', 'Handover', 'Escalated'
    app_name = db.Column(db.String(128))
    incident_id = db.Column(db.String(64))
    title = db.Column(db.String(256))
    description = db.Column(db.Text)
    priority = db.Column(db.String(32))
    status = db.Column(db.String(32))
    assigned_to = db.Column(db.String(128))
    escalated_to = db.Column(db.String(128))
    resolution = db.Column(db.Text)
    
    # Attribution
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    
    # Version for conflict detection
    version = db.Column(db.Integer, default=1)
    
    # Relationships
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    updated_by = db.relationship('User', foreign_keys=[updated_by_id])
    
    __table_args__ = (
        db.UniqueConstraint('shift_id', 'temp_id', name='uq_draft_incident'),
        db.Index('idx_draft_incident_shift', 'shift_id'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'shift_id': self.shift_id,
            'temp_id': self.temp_id,
            'incident_type': self.incident_type,
            'app_name': self.app_name,
            'incident_id': self.incident_id,
            'title': self.title,
            'description': self.description,
            'priority': self.priority,
            'status': self.status,
            'assigned_to': self.assigned_to,
            'escalated_to': self.escalated_to,
            'resolution': self.resolution,
            'created_by_id': self.created_by_id,
            'created_by_name': self.created_by.display_name or self.created_by.username if self.created_by else 'Unknown',
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_by_id': self.updated_by_id,
            'updated_by_name': self.updated_by.display_name or self.updated_by.username if self.updated_by else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'version': self.version
        }


class DraftKeyPoint(db.Model):
    """
    Temporary storage for key points in a collaborative draft.
    """
    __tablename__ = 'draft_key_point'
    
    id = db.Column(db.Integer, primary_key=True)
    shift_id = db.Column(db.Integer, db.ForeignKey('shift.id'), nullable=False, index=True)
    temp_id = db.Column(db.String(64), nullable=False)
    
    # Key point data
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(32), default='Open')
    responsible_engineer_id = db.Column(db.Integer, db.ForeignKey('team_member.id'))
    jira_id = db.Column(db.String(64))
    
    # Attribution
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    
    version = db.Column(db.Integer, default=1)
    
    # Relationships
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    updated_by = db.relationship('User', foreign_keys=[updated_by_id])
    responsible_engineer = db.relationship('TeamMember')
    
    __table_args__ = (
        db.UniqueConstraint('shift_id', 'temp_id', name='uq_draft_keypoint'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'shift_id': self.shift_id,
            'temp_id': self.temp_id,
            'description': self.description,
            'status': self.status,
            'responsible_engineer_id': self.responsible_engineer_id,
            'responsible_engineer_name': self.responsible_engineer.name if self.responsible_engineer else None,
            'jira_id': self.jira_id,
            'created_by_id': self.created_by_id,
            'created_by_name': self.created_by.display_name or self.created_by.username if self.created_by else 'Unknown',
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_by_id': self.updated_by_id,
            'updated_by_name': self.updated_by.display_name or self.updated_by.username if self.updated_by else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'version': self.version
        }


class DraftChangeInfo(db.Model):
    """
    Temporary storage for change info in a collaborative draft.
    """
    __tablename__ = 'draft_change_info'
    
    id = db.Column(db.Integer, primary_key=True)
    shift_id = db.Column(db.Integer, db.ForeignKey('shift.id'), nullable=False, index=True)
    temp_id = db.Column(db.String(64), nullable=False)
    
    # Change Info data
    application_name = db.Column(db.String(128))
    change_number = db.Column(db.String(64))
    description = db.Column(db.Text)
    change_datetime = db.Column(db.String(64))  # Store as string for flexibility
    responsible_engineer_id = db.Column(db.Integer, db.ForeignKey('team_member.id'))
    status = db.Column(db.String(32), default='Pending')
    
    # Attribution
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    
    version = db.Column(db.Integer, default=1)
    
    # Relationships
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    updated_by = db.relationship('User', foreign_keys=[updated_by_id])
    responsible_engineer = db.relationship('TeamMember')
    
    __table_args__ = (
        db.UniqueConstraint('shift_id', 'temp_id', name='uq_draft_changeinfo'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'shift_id': self.shift_id,
            'temp_id': self.temp_id,
            'application_name': self.application_name,
            'change_number': self.change_number,
            'description': self.description,
            'change_datetime': self.change_datetime,
            'responsible_engineer_id': self.responsible_engineer_id,
            'responsible_engineer_name': self.responsible_engineer.name if self.responsible_engineer else None,
            'status': self.status,
            'created_by_id': self.created_by_id,
            'created_by_name': self.created_by.display_name or self.created_by.username if self.created_by else 'Unknown',
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_by_id': self.updated_by_id,
            'updated_by_name': self.updated_by.display_name or self.updated_by.username if self.updated_by else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'version': self.version
        }


class DraftKBUpdate(db.Model):
    """
    Temporary storage for KB updates in a collaborative draft.
    """
    __tablename__ = 'draft_kb_update'
    
    id = db.Column(db.Integer, primary_key=True)
    shift_id = db.Column(db.Integer, db.ForeignKey('shift.id'), nullable=False, index=True)
    temp_id = db.Column(db.String(64), nullable=False)
    
    # KB Update data
    application_name = db.Column(db.String(128))
    kb_number = db.Column(db.String(64))
    description = db.Column(db.Text)
    responsible_person_id = db.Column(db.Integer, db.ForeignKey('team_member.id'))
    status = db.Column(db.String(32), default='Pending')
    
    # Attribution
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    
    version = db.Column(db.Integer, default=1)
    
    # Relationships
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    updated_by = db.relationship('User', foreign_keys=[updated_by_id])
    responsible_person = db.relationship('TeamMember')
    
    __table_args__ = (
        db.UniqueConstraint('shift_id', 'temp_id', name='uq_draft_kbupdate'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'shift_id': self.shift_id,
            'temp_id': self.temp_id,
            'application_name': self.application_name,
            'kb_number': self.kb_number,
            'description': self.description,
            'responsible_person_id': self.responsible_person_id,
            'responsible_person_name': self.responsible_person.name if self.responsible_person else None,
            'status': self.status,
            'created_by_id': self.created_by_id,
            'created_by_name': self.created_by.display_name or self.created_by.username if self.created_by else 'Unknown',
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_by_id': self.updated_by_id,
            'updated_by_name': self.updated_by.display_name or self.updated_by.username if self.updated_by else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'version': self.version
        }
