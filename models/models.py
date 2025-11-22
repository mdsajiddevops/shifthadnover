
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy()
from flask_login import UserMixin

# Multi-account and multi-team support
class Account(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), unique=True, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    status = db.Column(db.String(16), nullable=False, default='active')  # 'active', 'disabled'
    teams = db.relationship('Team', backref='account', lazy=True)
    users = db.relationship('User', backref='account', lazy=True)

class Team(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    status = db.Column(db.String(16), nullable=False, default='active')  # 'active', 'disabled'
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    members = db.relationship('TeamMember', backref='team', lazy=True)
    users = db.relationship('User', backref='team', lazy=True)

# Escalation Matrix File model for persistent uploads
class EscalationMatrixFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), unique=True, nullable=False)
    upload_time = db.Column(db.DateTime, nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=True)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=True)

class ShiftRoster(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    team_member_id = db.Column(db.Integer, db.ForeignKey('team_member.id'), nullable=False)
    shift_code = db.Column(db.String(8), nullable=True)  # E, D, N, G, LE, VL, HL, CO, or blank
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(32), nullable=False, default='user')  # 'super_admin', 'account_admin', 'team_admin', 'user'
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    status = db.Column(db.String(16), nullable=False, default='active')  # 'active', 'disabled'
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=True)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=True)
    
    # New fields for better user display
    first_name = db.Column(db.String(64), nullable=True)
    last_name = db.Column(db.String(64), nullable=True)
    profile_picture = db.Column(db.String(255), nullable=True)  # URL to profile picture
    
    # Onboarding and login tracking fields
    first_login = db.Column(db.Boolean, default=True, nullable=False)  # True for users who haven't completed onboarding
    last_login = db.Column(db.DateTime, nullable=True)  # Track last login time
    onboarding_completed = db.Column(db.Boolean, default=False, nullable=False)  # Track if onboarding flow is completed
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp(), nullable=False)
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())
    
    @property
    def display_name(self):
        """Return a user-friendly display name"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.last_name:
            return self.last_name
        else:
            # Fallback: convert email to a readable name
            name_part = self.email.split('@')[0].replace('_', ' ').replace('.', ' ')
            return ' '.join(word.capitalize() for word in name_part.split())
    
    @property
    def initials(self):
        """Return user initials for avatar fallback"""
        if self.first_name and self.last_name:
            return f"{self.first_name[0]}{self.last_name[0]}".upper()
        elif self.first_name:
            return self.first_name[0].upper()
        elif self.last_name:
            return self.last_name[0].upper()
        else:
            # Fallback: use first two letters of username
            return self.username[:2].upper() if len(self.username) >= 2 else self.username.upper()
    
    @property
    def is_admin(self):
        """Check if user has admin privileges"""
        return self.role in ['super_admin', 'account_admin', 'team_admin']
    
    @property
    def needs_onboarding(self):
        """Check if user needs onboarding (first-time login without account/team assignment)"""
        # Super admin users never need onboarding
        if self.role == 'super_admin':
            return False
        # Users need onboarding if they haven't completed it and don't have account/team assigned
        return not self.onboarding_completed and (self.account_id is None or self.team_id is None)
    
    def complete_onboarding(self, account_id, team_id):
        """Complete the onboarding process by assigning account and team"""
        self.account_id = account_id
        self.team_id = team_id
        self.onboarding_completed = True
        self.first_login = False
        from datetime import datetime
        self.last_login = datetime.now()
        db.session.commit()

class TeamMember(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    name = db.Column(db.String(64), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    contact_number = db.Column(db.String(32), nullable=False)
    role = db.Column(db.String(64))
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)

class Shift(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    current_shift_type = db.Column(db.String(16), nullable=False) # Morning/Evening/Night
    next_shift_type = db.Column(db.String(16), nullable=False)
    current_engineers = db.relationship('TeamMember', secondary='current_shift_engineers')
    next_engineers = db.relationship('TeamMember', secondary='next_shift_engineers')
    status = db.Column(db.String(16), nullable=False, default='draft')  # draft or sent
    # Submission timestamp for proper chronological ordering
    submitted_at = db.Column(db.DateTime, nullable=True, default=None)  # When handover was submitted
    created_at = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())  # When record was created
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)

class Incident(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(128), nullable=False)
    status = db.Column(db.String(16), nullable=False) # Active/Closed
    priority = db.Column(db.String(16), nullable=False)
    handover = db.Column(db.Text)
    shift_id = db.Column(db.Integer, db.ForeignKey('shift.id'))
    type = db.Column(db.String(32), nullable=False) # Active, Closed, Priority, Handover
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    # Enhanced fields for detailed incident tracking
    description = db.Column(db.Text)  # Detailed description/notes/resolution
    assigned_to = db.Column(db.String(128))  # Person assigned to handle the incident
    escalated_to = db.Column(db.String(128))  # Person/team escalated to


class ShiftKeyPoint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(16), nullable=False) # Open/Closed/In Progress
    responsible_engineer_id = db.Column(db.Integer, db.ForeignKey('team_member.id'))
    shift_id = db.Column(db.Integer, db.ForeignKey('shift.id'))
    jira_id = db.Column(db.String(64), nullable=True)  # New field for JIRA ID
    updates = db.relationship('ShiftKeyPointUpdate', backref='key_point', lazy=True)
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)

# Daily updates for key points
class ShiftKeyPointUpdate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key_point_id = db.Column(db.Integer, db.ForeignKey('shift_key_point.id'), nullable=False)
    update_text = db.Column(db.Text, nullable=False)
    update_date = db.Column(db.Date, nullable=False)
    updated_by = db.Column(db.String(64), nullable=False)

# Association tables
current_shift_engineers = db.Table('current_shift_engineers',
    db.Column('shift_id', db.Integer, db.ForeignKey('shift.id')),
    db.Column('team_member_id', db.Integer, db.ForeignKey('team_member.id'))
)

next_shift_engineers = db.Table('next_shift_engineers',
    db.Column('shift_id', db.Integer, db.ForeignKey('shift.id')),
    db.Column('team_member_id', db.Integer, db.ForeignKey('team_member.id'))
)

# Secrets Management Models
class SecretStore(db.Model):
    """Encrypted secret storage in database"""
    __tablename__ = 'secret_store'
    
    id = db.Column(db.Integer, primary_key=True)
    key_name = db.Column(db.String(255), unique=True, nullable=False, index=True)
    encrypted_value = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False, default='application')
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    requires_restart = db.Column(db.Boolean, default=False, nullable=False)
    
    # Audit fields
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp(), nullable=False)
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())
    created_by = db.Column(db.String(255))
    updated_by = db.Column(db.String(255))
    
    # Security fields
    last_accessed = db.Column(db.DateTime)
    access_count = db.Column(db.Integer, default=0)
    expires_at = db.Column(db.DateTime)  # For temporary secrets
    
    def __repr__(self):
        return f'<SecretStore {self.key_name}:{self.category}>'

class SecretAuditLog(db.Model):
    """Audit log for secret access and modifications"""
    __tablename__ = 'secret_audit_log'
    
    id = db.Column(db.Integer, primary_key=True)
    secret_key = db.Column(db.String(255), nullable=False, index=True)
    action = db.Column(db.String(50), nullable=False)  # CREATE, READ, UPDATE, DELETE
    user_id = db.Column(db.String(255))
    user_email = db.Column(db.String(255))
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp(), nullable=False)
    old_value_hash = db.Column(db.String(64))  # Hash of old value for comparison
    new_value_hash = db.Column(db.String(64))  # Hash of new value
    success = db.Column(db.Boolean, default=True)
    error_message = db.Column(db.Text)
    
    def __repr__(self):
        return f'<SecretAudit {self.secret_key}:{self.action} by {self.user_email}>'

