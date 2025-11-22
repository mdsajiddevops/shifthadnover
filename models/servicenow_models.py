"""
ServiceNow Incident Model

This model stores ServiceNow incidents locally for:
- Caching frequently accessed incidents
- Maintaining incident history
- Offline access capabilities
- Performance optimization
"""

from datetime import datetime
from models.models import db


class ServiceNowIncident(db.Model):
    """Model to store ServiceNow incidents locally"""
    
    __tablename__ = 'servicenow_incidents'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # ServiceNow fields
    sys_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    title = db.Column(db.String(500), nullable=False)
    description = db.Column(db.Text)
    
    # Status and classification
    state = db.Column(db.String(50), nullable=False, index=True)
    priority = db.Column(db.String(20), index=True)
    urgency = db.Column(db.String(20))
    impact = db.Column(db.String(20))
    category = db.Column(db.String(100))
    subcategory = db.Column(db.String(100))
    
    # Assignment information
    assignment_group = db.Column(db.String(100), index=True)
    assigned_to = db.Column(db.String(100))
    caller = db.Column(db.String(100))
    opened_by = db.Column(db.String(100))
    
    # Timestamps
    created_on = db.Column(db.DateTime, nullable=False, index=True)
    updated_on = db.Column(db.DateTime, nullable=False)
    resolved_at = db.Column(db.DateTime)
    closed_at = db.Column(db.DateTime)
    
    # Additional information
    close_notes = db.Column(db.Text)
    work_notes = db.Column(db.Text)
    comments = db.Column(db.Text)
    
    # Local tracking
    last_synced = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    sync_status = db.Column(db.String(20), default='synced', nullable=False)  # synced, error, pending
    
    # Relationship to local shift data
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'))
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'))
    
    def __repr__(self):
        return f'<ServiceNowIncident {self.number}: {self.title[:50]}>'
    
    def to_dict(self):
        """Convert incident to dictionary"""
        return {
            'id': self.id,
            'sys_id': self.sys_id,
            'number': self.number,
            'title': self.title,
            'description': self.description,
            'state': self.state,
            'priority': self.priority,
            'urgency': self.urgency,
            'impact': self.impact,
            'category': self.category,
            'subcategory': self.subcategory,
            'assignment_group': self.assignment_group,
            'assigned_to': self.assigned_to,
            'caller': self.caller,
            'opened_by': self.opened_by,
            'created_on': self.created_on.isoformat() if self.created_on else None,
            'updated_on': self.updated_on.isoformat() if self.updated_on else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'closed_at': self.closed_at.isoformat() if self.closed_at else None,
            'close_notes': self.close_notes,
            'work_notes': self.work_notes,
            'comments': self.comments,
            'last_synced': self.last_synced.isoformat() if self.last_synced else None,
            'sync_status': self.sync_status,
            'source': 'ServiceNow'
        }
    
    @classmethod
    def from_servicenow_data(cls, data, account_id=None, team_id=None):
        """Create incident from ServiceNow API data"""
        incident = cls(
            sys_id=data.get('sys_id'),
            number=data.get('number'),
            title=data.get('title', ''),
            description=data.get('description', ''),
            state=data.get('state', ''),
            priority=data.get('priority', ''),
            urgency=data.get('urgency', ''),
            impact=data.get('impact', ''),
            category=data.get('category', ''),
            subcategory=data.get('subcategory', ''),
            assignment_group=data.get('assignment_group', ''),
            assigned_to=data.get('assigned_to', ''),
            caller=data.get('caller', ''),
            opened_by=data.get('opened_by', ''),
            created_on=data.get('created_on'),
            updated_on=data.get('updated_on'),
            resolved_at=data.get('resolved_at'),
            closed_at=data.get('closed_at'),
            close_notes=data.get('close_notes', ''),
            work_notes=data.get('work_notes', ''),
            comments=data.get('comments', ''),
            account_id=account_id,
            team_id=team_id,
            last_synced=datetime.utcnow(),
            sync_status='synced'
        )
        return incident
    
    def update_from_servicenow_data(self, data):
        """Update existing incident with new ServiceNow data"""
        self.title = data.get('title', self.title)
        self.description = data.get('description', self.description)
        self.state = data.get('state', self.state)
        self.priority = data.get('priority', self.priority)
        self.urgency = data.get('urgency', self.urgency)
        self.impact = data.get('impact', self.impact)
        self.category = data.get('category', self.category)
        self.subcategory = data.get('subcategory', self.subcategory)
        self.assignment_group = data.get('assignment_group', self.assignment_group)
        self.assigned_to = data.get('assigned_to', self.assigned_to)
        self.caller = data.get('caller', self.caller)
        self.opened_by = data.get('opened_by', self.opened_by)
        self.updated_on = data.get('updated_on', self.updated_on)
        self.resolved_at = data.get('resolved_at', self.resolved_at)
        self.closed_at = data.get('closed_at', self.closed_at)
        self.close_notes = data.get('close_notes', self.close_notes)
        self.work_notes = data.get('work_notes', self.work_notes)
        self.comments = data.get('comments', self.comments)
        self.last_synced = datetime.utcnow()
        self.sync_status = 'synced'
    
    @classmethod
    def sync_incidents(cls, incidents_data, account_id=None, team_id=None):
        """Sync multiple incidents from ServiceNow"""
        synced_count = 0
        updated_count = 0
        
        for incident_data in incidents_data:
            existing = cls.query.filter_by(sys_id=incident_data.get('sys_id')).first()
            
            if existing:
                existing.update_from_servicenow_data(incident_data)
                updated_count += 1
            else:
                new_incident = cls.from_servicenow_data(incident_data, account_id, team_id)
                db.session.add(new_incident)
                synced_count += 1
        
        try:
            db.session.commit()
            return synced_count, updated_count
        except Exception as e:
            db.session.rollback()
            raise e
    
    @classmethod
    def get_incidents_for_shift(cls, shift_start, shift_end, account_id=None, team_id=None, include_closed=True):
        """Get incidents for a specific shift time"""
        query = cls.query.filter(
            db.or_(
                db.and_(cls.created_on >= shift_start, cls.created_on <= shift_end),
                db.and_(cls.updated_on >= shift_start, cls.updated_on <= shift_end)
            )
        )
        
        if account_id:
            query = query.filter(cls.account_id == account_id)
            
        if team_id:
            query = query.filter(cls.team_id == team_id)
            
        if not include_closed:
            query = query.filter(~cls.state.in_(['Closed', 'Resolved', 'Cancelled']))
            
        return query.order_by(cls.created_on.desc()).all()


class ServiceNowSyncLog(db.Model):
    """Track ServiceNow synchronization activities"""
    
    __tablename__ = 'servicenow_sync_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    sync_started = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    sync_completed = db.Column(db.DateTime)
    status = db.Column(db.String(20), nullable=False)  # success, error, in_progress
    incidents_synced = db.Column(db.Integer, default=0)
    incidents_updated = db.Column(db.Integer, default=0)
    error_message = db.Column(db.Text)
    sync_type = db.Column(db.String(50), default='manual')  # manual, scheduled, shift_handover
    triggered_by = db.Column(db.String(100))  # username who triggered the sync
    
    # Filter criteria used for sync
    service_groups = db.Column(db.JSON)
    shift_start = db.Column(db.DateTime)
    shift_end = db.Column(db.DateTime)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'))
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'))
    
    def __repr__(self):
        return f'<ServiceNowSyncLog {self.id}: {self.status} at {self.sync_started}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'sync_started': self.sync_started.isoformat() if self.sync_started else None,
            'sync_completed': self.sync_completed.isoformat() if self.sync_completed else None,
            'status': self.status,
            'incidents_synced': self.incidents_synced,
            'incidents_updated': self.incidents_updated,
            'error_message': self.error_message,
            'sync_type': self.sync_type,
            'triggered_by': self.triggered_by,
            'service_groups': self.service_groups,
            'shift_start': self.shift_start.isoformat() if self.shift_start else None,
            'shift_end': self.shift_end.isoformat() if self.shift_end else None
        }


class ServiceNowAssignmentGroup(db.Model):
    """Model to store ServiceNow assignment groups locally"""
    
    __tablename__ = 'servicenow_assignment_groups'
    
    id = db.Column(db.Integer, primary_key=True)
    sys_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False, index=True)
    description = db.Column(db.Text)
    active = db.Column(db.Boolean, default=True, nullable=False)
    
    # Local mapping
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'))
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'))
    
    # Tracking
    created_on = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_on = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_synced = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f'<ServiceNowAssignmentGroup {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'sys_id': self.sys_id,
            'name': self.name,
            'description': self.description,
            'active': self.active,
            'account_id': self.account_id,
            'team_id': self.team_id,
            'created_on': self.created_on.isoformat() if self.created_on else None,
            'updated_on': self.updated_on.isoformat() if self.updated_on else None,
            'last_synced': self.last_synced.isoformat() if self.last_synced else None
        }