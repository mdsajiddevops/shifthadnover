
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
    # Team-specific email configuration
    email_recipients = db.Column(db.Text, nullable=True)  # Comma-separated email list for handovers
    priority_alert_recipients = db.Column(db.Text, nullable=True)  # Comma-separated email list for priority alerts
    members = db.relationship('TeamMember', backref='team', lazy=True)
    users = db.relationship('User', backref='team', lazy=True)
    
    def get_users(self, active_only=True):
        """Get all users who are members of this team"""
        query = UserTeamMembership.query.filter_by(team_id=self.id)
        
        if active_only:
            query = query.filter_by(is_active=True)
        
        memberships = query.all()
        user_ids = [m.user_id for m in memberships]
        
        if user_ids:
            user_query = User.query.filter(User.id.in_(user_ids))
            if active_only:
                user_query = user_query.filter_by(is_active=True)
            return user_query.all()
        
        return []
    
    def get_user_count(self, active_only=True):
        """Get count of users in this team"""
        query = UserTeamMembership.query.filter_by(team_id=self.id)
        
        if active_only:
            query = query.filter_by(is_active=True)
        
        return query.count()
    
    def add_user(self, user, is_primary=False, role='member', added_by=None):
        """Add a user to this team"""
        return user.add_team_membership(
            team_id=self.id,
            account_id=self.account_id,
            is_primary=is_primary,
            role=role,
            added_by=added_by
        )
    
    def remove_user(self, user):
        """Remove a user from this team"""
        return user.remove_team_membership(self.id, self.account_id)
    
    def has_user(self, user_id):
        """Check if user is a member of this team"""
        return UserTeamMembership.query.filter_by(
            team_id=self.id,
            user_id=user_id,
            is_active=True
        ).first() is not None

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
    last_activity = db.Column(db.DateTime, nullable=True)  # Track last activity time for active session monitoring
    onboarding_completed = db.Column(db.Boolean, default=False, nullable=False)  # Track if onboarding flow is completed
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp(), nullable=False)
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())
    
    @property
    def is_online(self):
        """Check if user is currently online (active in last 5 minutes)"""
        if not self.last_activity:
            return False
        from datetime import datetime, timedelta
        return datetime.now() - self.last_activity < timedelta(minutes=5)
    
    @property 
    def is_recently_active(self):
        """Check if user was active in last 30 minutes"""
        if not self.last_activity:
            return False
        from datetime import datetime, timedelta
        return datetime.now() - self.last_activity < timedelta(minutes=30)
    
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
        
        # Create primary team membership
        self.add_team_membership(team_id, account_id, is_primary=True)
        db.session.commit()
    
    def add_team_membership(self, team_id, account_id, is_primary=False, role='member', added_by=None):
        """Add user to a team with specified role"""
        # Check if membership already exists
        existing = UserTeamMembership.query.filter_by(
            user_id=self.id,
            team_id=team_id,
            account_id=account_id
        ).first()
        
        if existing:
            if not existing.is_active:
                # Reactivate existing membership
                existing.is_active = True
                existing.is_primary = is_primary
                existing.role = role
                existing.added_by_id = added_by.id if added_by else None
                existing.updated_at = db.func.current_timestamp()
                return existing
            else:
                # Already exists and is active
                return existing
        
        # If setting as primary, remove primary from other teams in same account
        if is_primary:
            UserTeamMembership.query.filter_by(
                user_id=self.id,
                account_id=account_id,
                is_primary=True
            ).update({'is_primary': False})
        
        # Create new membership
        membership = UserTeamMembership(
            user_id=self.id,
            team_id=team_id,
            account_id=account_id,
            is_primary=is_primary,
            role=role,
            added_by_id=added_by.id if added_by else None,
            is_active=True
        )
        
        db.session.add(membership)
        return membership
    
    def remove_team_membership(self, team_id, account_id):
        """Remove user from a team"""
        membership = UserTeamMembership.query.filter_by(
            user_id=self.id,
            team_id=team_id,
            account_id=account_id
        ).first()
        
        if membership:
            if membership.is_primary:
                # If removing primary team, make another team primary if available
                other_membership = UserTeamMembership.query.filter_by(
                    user_id=self.id,
                    account_id=account_id,
                    is_active=True
                ).filter(UserTeamMembership.id != membership.id).first()
                
                if other_membership:
                    other_membership.is_primary = True
                    # Update user's primary team_id
                    self.team_id = other_membership.team_id
            
            membership.is_active = False
            return True
        return False
    
    def get_teams(self, account_id=None, active_only=True):
        """Get all teams user belongs to"""
        query = UserTeamMembership.query.filter_by(user_id=self.id)
        
        if account_id:
            query = query.filter_by(account_id=account_id)
        
        if active_only:
            query = query.filter_by(is_active=True)
        
        return query.all()
    
    def get_primary_team_membership(self, account_id=None):
        """Get user's primary team membership"""
        query = UserTeamMembership.query.filter_by(
            user_id=self.id,
            is_primary=True,
            is_active=True
        )
        
        if account_id:
            query = query.filter_by(account_id=account_id)
        
        return query.first()
    
    def get_primary_team(self, account_id=None):
        # Get user's primary team object
        primary_membership = self.get_primary_team_membership(account_id=account_id)
        if primary_membership:
            return Team.query.get(primary_membership.team_id)
        return None
    
    def is_member_of_team(self, team_id, account_id=None):
        """Check if user is a member of a specific team"""
        query = UserTeamMembership.query.filter_by(
            user_id=self.id,
            team_id=team_id,
            is_active=True
        )
        
        if account_id:
            query = query.filter_by(account_id=account_id)
        
        return query.first() is not None
    
    def is_member_of_team_ids(self, team_ids, account_id=None):
        """Check if user is a member of any of the specified teams"""
        if not team_ids:
            return False
            
        query = UserTeamMembership.query.filter(
            UserTeamMembership.user_id == self.id,
            UserTeamMembership.team_id.in_(team_ids),
            UserTeamMembership.is_active == True
        )
        
        if account_id:
            query = query.filter_by(account_id=account_id)
        
        return query.first() is not None
    
    def get_team_names(self, account_id=None, separator=', '):
        """Get comma-separated list of team names"""
        memberships = self.get_teams(account_id=account_id)
        teams = [Team.query.get(m.team_id) for m in memberships]
        team_names = [t.name for t in teams if t]
        return separator.join(team_names)
    
    @property
    def all_teams_display(self):
        """Display all teams user belongs to with primary indication"""
        # Don't use caching for now to ensure fresh data
        try:
            memberships = self.get_teams()
            teams_info = []
            for membership in memberships:
                team = Team.query.get(membership.team_id)
                if team:
                    name = team.name
                    if membership.is_primary:
                        name += " (Primary)"
                    teams_info.append(name)
            return '; '.join(teams_info) if teams_info else 'No Teams'
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"all_teams_display for user {self.username}: {str(e)}")
            return 'Error loading teams'

class UserTeamMembership(db.Model):
    """Many-to-many relationship table for users and teams with additional metadata"""
    __tablename__ = 'user_team_memberships'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    is_primary = db.Column(db.Boolean, default=False, nullable=False)  # Primary team designation
    role = db.Column(db.String(64), default='member', nullable=False)  # Role within this team
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp(), nullable=False)
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())
    added_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Who added this membership
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref='team_memberships')
    team = db.relationship('Team', backref='user_memberships')
    account = db.relationship('Account')
    added_by = db.relationship('User', foreign_keys=[added_by_id])
    
    # Constraints
    __table_args__ = (
        db.UniqueConstraint('user_id', 'team_id', 'account_id', name='unique_user_team_per_account'),
        db.Index('idx_user_teams_active', 'user_id', 'is_active'),
        db.Index('idx_team_members_active', 'team_id', 'is_active'),
        db.Index('idx_primary_team', 'user_id', 'is_primary'),
    )
    
    def __repr__(self):
        return f'<UserTeamMembership user_id={self.user_id} team_id={self.team_id} primary={self.is_primary}>'

class TeamMember(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    employee_id = db.Column(db.String(32), nullable=True)  # Employee ID / UID for reports
    name = db.Column(db.String(64), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    contact_number = db.Column(db.String(32), nullable=False)
    role = db.Column(db.String(64))
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)  # Active/Inactive status
    
    # Check-in status fields
    availability_status = db.Column(db.String(32), default='offline')  # offline, oncall, online
    last_checkin = db.Column(db.DateTime, nullable=True)
    checkin_location = db.Column(db.String(128), nullable=True)  # Optional location info
    
    @property
    def display_name(self):
        """Return display name for team member"""
        return self.name
    
    @property
    def initials(self):
        """Return team member initials for avatar fallback"""
        if self.name:
            name_parts = self.name.split()
            if len(name_parts) >= 2:
                return f"{name_parts[0][0]}{name_parts[-1][0]}".upper()
            else:
                return self.name[:2].upper() if len(self.name) >= 2 else self.name.upper()
        else:
            return "TM"
    
    @property
    def status_badge_class(self):
        """Return CSS class for status badge"""
        status_classes = {
            'oncall': 'bg-success',      # Green for on call (active duty)
            'online': 'bg-primary',      # Blue for online (standby)
            'offline': 'bg-secondary'    # Gray for offline
        }
        return status_classes.get(self.availability_status, 'bg-secondary')
    
    @property
    def status_display(self):
        """Return human-readable status"""
        status_display = {
            'oncall': 'On Call',         # Active duty
            'online': 'Standby',         # Available but not on active duty
            'offline': 'Offline'         # Not available
        }
        return status_display.get(self.availability_status, 'Offline')

class CheckInLog(db.Model):
    """Track team member check-in/check-out history"""
    __tablename__ = 'checkin_log'
    
    id = db.Column(db.Integer, primary_key=True)
    team_member_id = db.Column(db.Integer, db.ForeignKey('team_member.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    status = db.Column(db.String(32), nullable=False)  # online, oncall, offline
    checkin_time = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    checkout_time = db.Column(db.DateTime, nullable=True)
    location = db.Column(db.String(128), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(256), nullable=True)
    
    # Relationships
    team_member = db.relationship('TeamMember', backref='checkin_logs')
    user = db.relationship('User', backref='checkin_logs')

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
    additional_notes = db.Column(db.Text, nullable=True)  # Additional notes for the handover

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
    created_at = db.Column(db.DateTime, nullable=True, default=db.func.current_timestamp())  # When key point was created
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Who created it
    # Relationships
    responsible_engineer = db.relationship('TeamMember', foreign_keys=[responsible_engineer_id], lazy='joined')
    shift = db.relationship('Shift', backref='key_points_list', lazy='joined')  # Link to shift for date/engineer info
    created_by = db.relationship('User', foreign_keys=[created_by_id], lazy='joined')  # Who created the key point

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


# Change Related Information model
class ShiftChangeInfo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    app_name = db.Column(db.String(255), nullable=False)
    change_number = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    change_datetime = db.Column(db.DateTime, nullable=True)
    responsible_engineer_id = db.Column(db.Integer, db.ForeignKey('team_member.id'), nullable=True)
    status = db.Column(db.String(16), nullable=False, default='New')  # New, In Progress, Scheduled, Postponed, Completed, Cancelled
    shift_id = db.Column(db.Integer, db.ForeignKey('shift.id'), nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())
    
    # Relationship to get responsible engineer details
    responsible_engineer = db.relationship('TeamMember', backref='change_infos')
    
    # Constraint to ensure change number is unique per shift
    __table_args__ = (db.UniqueConstraint('shift_id', 'change_number', name='_shift_change_number_uc'),)

    @property
    def responsible(self):
        """Return responsible engineer name for template compatibility"""
        if self.responsible_engineer:
            return self.responsible_engineer.name
        return None

    def __repr__(self):
        return f'<ShiftChangeInfo {self.change_number}: {self.app_name}>'


# Knowledge Base Updates model  
class ShiftKBUpdate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    app_name = db.Column(db.String(255), nullable=False)
    kb_number = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    responsible_engineer_id = db.Column(db.Integer, db.ForeignKey('team_member.id'), nullable=True)
    status = db.Column(db.String(16), nullable=False)  # Draft, Published, In Review
    shift_id = db.Column(db.Integer, db.ForeignKey('shift.id'), nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())
    
    # Relationship to get responsible engineer details
    responsible_engineer = db.relationship('TeamMember', backref='kb_updates')
    
    # Constraint to ensure KB number is unique per shift
    __table_args__ = (db.UniqueConstraint('shift_id', 'kb_number', name='_shift_kb_number_uc'),)

    @property
    def responsible(self):
        """Return responsible engineer name for template compatibility"""
        if self.responsible_engineer:
            return self.responsible_engineer.name
        return None

    def __repr__(self):
        return f'<ShiftKBUpdate {self.kb_number}: {self.app_name}>'

