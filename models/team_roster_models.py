from datetime import datetime, time
from flask_sqlalchemy import SQLAlchemy
from models.models import db
import logging
logger = logging.getLogger(__name__)

class TeamShiftConfig(db.Model):
    """Configuration for team shift patterns"""
    __tablename__ = 'team_shift_configs'
    
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    shift_name = db.Column(db.String(64), nullable=False)  # e.g., "Morning", "Evening", "Night", "Onshore", "Offshore", "Late Evening", "General"
    start_time = db.Column(db.Time, nullable=False)  # e.g., 09:00:00
    end_time = db.Column(db.Time, nullable=False)    # e.g., 17:00:00
    order_index = db.Column(db.Integer, default=0)   # For ordering shifts
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    team = db.relationship('Team', backref='shift_configs')
    account = db.relationship('Account')
    
    def __repr__(self):
        return f'<TeamShiftConfig {self.shift_name} for Team {self.team_id}>'
    
    @classmethod
    def get_team_shifts(cls, team_id, active_only=True):
        """Get all shifts for a team ordered by order_index"""
        query = cls.query.filter_by(team_id=team_id)
        if active_only:
            query = query.filter_by(is_active=True)
        return query.order_by(cls.order_index).all()
    
    def is_time_in_shift(self, check_time):
        """Check if a given time falls within this shift"""
        if isinstance(check_time, datetime):
            check_time = check_time.time()
        
        # Handle overnight shifts (e.g., Night: 21:00 - 09:00)
        if self.start_time <= self.end_time:
            # Normal shift (e.g., 09:00 - 17:00)
            result = self.start_time <= check_time <= self.end_time
        else:
            # Overnight shift (e.g., 21:00 - 09:00)
            result = check_time >= self.start_time or check_time <= self.end_time
        
        return result
    
    @classmethod
    def get_current_shift(cls, team_id, current_time=None):
        """Get the current shift for a team based on time"""
        if current_time is None:
            current_time = datetime.now()
        
        shifts = cls.get_team_shifts(team_id)
        if not shifts:
            return None
            
        # Debug: Print current time and shift analysis
        time_str = current_time.time().strftime('%H:%M:%S') if isinstance(current_time, datetime) else current_time.strftime('%H:%M:%S')
        logger.debug(f"[SHIFT DEBUG] Checking shifts for team {team_id} at time {time_str}")
        
        matched_shift = None
        for shift in shifts:
            is_match = shift.is_time_in_shift(current_time)
            start_str = shift.start_time.strftime('%H:%M')
            end_str = shift.end_time.strftime('%H:%M')
            overnight = ' (overnight)' if shift.start_time > shift.end_time else ''
            logger.debug(f"[SHIFT DEBUG]   {shift.shift_name} ({start_str}-{end_str}){overnight}: {'MATCH ✅' if is_match else 'no match ❌'}")
            
            if is_match:
                matched_shift = shift
                break
        
        if matched_shift:
            logger.debug(f"[SHIFT DEBUG] Selected shift: {matched_shift.shift_name}")
            return matched_shift
        
        # Better fallback: find the most recent shift that has ended
        current_time_obj = current_time.time() if isinstance(current_time, datetime) else current_time
        
        # Sort shifts by order_index to get logical sequence
        sorted_shifts = sorted(shifts, key=lambda s: s.order_index)
        
        # If no shift matches, it might be in a gap between shifts
        # Return the shift that most recently ended
        for shift in reversed(sorted_shifts):
            if shift.start_time <= shift.end_time:
                # Normal shift - check if current time is after this shift
                if current_time_obj >= shift.end_time:
                    logger.debug(f"[SHIFT DEBUG] Fallback: Using most recent ended shift: {shift.shift_name}")
                    return shift
            else:
                # Overnight shift - more complex logic
                if current_time_obj <= shift.end_time:
                    logger.debug(f"[SHIFT DEBUG] Fallback: Using overnight shift: {shift.shift_name}")
                    return shift
        
        # Ultimate fallback: return first shift
        logger.debug(f"[SHIFT DEBUG] Ultimate fallback: Using first shift: {sorted_shifts[0].shift_name}")
        return sorted_shifts[0]
    
    @classmethod
    def get_next_shift(cls, team_id, current_time=None):
        """Get the next shift for a team based on time"""
        if current_time is None:
            current_time = datetime.now()
        
        shifts = cls.get_team_shifts(team_id)
        if not shifts:
            return None
        
        current_shift = cls.get_current_shift(team_id, current_time)
        if not current_shift:
            return shifts[0]
        
        # Find index of current shift
        try:
            current_index = shifts.index(current_shift)
            # Get next shift (wrap around to first if at end)
            next_index = (current_index + 1) % len(shifts)
            return shifts[next_index]
        except ValueError:
            return shifts[0]


class RosterAssignment(db.Model):
    """Assignment of team members to shifts"""
    __tablename__ = 'roster_assignments'
    
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    shift_config_id = db.Column(db.Integer, db.ForeignKey('team_shift_configs.id'), nullable=False)
    assignment_date = db.Column(db.Date, nullable=False)  # Date for which this assignment is valid
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    # Relationships
    team = db.relationship('Team', backref='roster_assignments')
    account = db.relationship('Account')
    user = db.relationship('User', foreign_keys=[user_id], backref='roster_assignments')
    shift_config = db.relationship('TeamShiftConfig', backref='assignments')
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    
    # Unique constraint to prevent duplicate assignments
    __table_args__ = (
        db.UniqueConstraint('team_id', 'user_id', 'shift_config_id', 'assignment_date', 
                           name='unique_assignment_per_shift_date'),
        db.Index('idx_roster_assignment_date', 'assignment_date'),
        db.Index('idx_roster_assignment_team_date', 'team_id', 'assignment_date'),
    )
    
    def __repr__(self):
        return f'<RosterAssignment User {self.user_id} to Shift {self.shift_config_id} on {self.assignment_date}>'
    
    @classmethod
    def get_team_assignments_for_date(cls, team_id, assignment_date, active_only=True):
        """Get all roster assignments for a team on a specific date"""
        query = cls.query.filter_by(team_id=team_id, assignment_date=assignment_date)
        if active_only:
            query = query.filter_by(is_active=True)
        return query.all()
    
    @classmethod
    def get_shift_members(cls, shift_config_id, assignment_date, active_only=True):
        """Get all members assigned to a specific shift on a date"""
        from models.models import User
        query = cls.query.filter_by(
            shift_config_id=shift_config_id, 
            assignment_date=assignment_date
        )
        if active_only:
            query = query.filter_by(is_active=True)
        
        assignments = query.all()
        user_ids = [a.user_id for a in assignments]
        
        if user_ids:
            return User.query.filter(User.id.in_(user_ids)).all()
        return []
    
    @classmethod
    def get_current_shift_members(cls, team_id, assignment_date=None):
        """Get members currently on shift for a team"""
        if assignment_date is None:
            assignment_date = datetime.now().date()
        
        current_shift = TeamShiftConfig.get_current_shift(team_id)
        if not current_shift:
            return []
        
        return cls.get_shift_members(current_shift.id, assignment_date)
    
    @classmethod
    def get_next_shift_members(cls, team_id, assignment_date=None):
        """Get members on next shift for a team"""
        if assignment_date is None:
            assignment_date = datetime.now().date()
        
        next_shift = TeamShiftConfig.get_next_shift(team_id)
        if not next_shift:
            return []
        
        return cls.get_shift_members(next_shift.id, assignment_date)