"""
Team Shift Timing Configuration Model
Manages team-specific shift timing patterns
"""

from datetime import datetime, time
from flask_sqlalchemy import SQLAlchemy
from models.models import db

class TeamShiftTimingConfig(db.Model):
    """Team-specific shift timing configurations"""
    __tablename__ = 'team_shift_timing_configs'
    
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    
    # Shift definition
    shift_code = db.Column(db.String(10), nullable=False)  # D, E, N, LE, G, O
    shift_name = db.Column(db.String(100), nullable=False)  # Day Shift, Evening Shift, etc.
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    
    # Display settings
    color_code = db.Column(db.String(7), default='#007bff')  # Hex color for UI
    order_index = db.Column(db.Integer, default=0)  # Display order
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    is_default = db.Column(db.Boolean, default=False)  # Default shift for new users
    
    # Audit fields
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.String(255))
    updated_by = db.Column(db.String(255))
    
    # Relationships
    team = db.relationship('Team', backref='shift_timing_configs')
    account = db.relationship('Account')
    
    def __repr__(self):
        return f'<TeamShiftTimingConfig {self.shift_code}-{self.shift_name} for Team {self.team_id}>'
    
    @property
    def formatted_time_range(self):
        """Format time range for display"""
        start_str = self.start_time.strftime('%I:%M %p') if self.start_time else 'N/A'
        end_str = self.end_time.strftime('%I:%M %p') if self.end_time else 'N/A'
        return f"{start_str} - {end_str}"
    
    @property
    def is_overnight_shift(self):
        """Check if this is an overnight shift"""
        if not self.start_time or not self.end_time:
            return False
        return self.start_time > self.end_time
    
    def is_time_in_shift(self, check_time):
        """Check if a given time falls within this shift"""
        if isinstance(check_time, datetime):
            check_time = check_time.time()
        
        if not self.start_time or not self.end_time:
            return False
        
        # Handle overnight shifts (e.g., Night: 22:00 - 06:00)
        if self.is_overnight_shift:
            return check_time >= self.start_time or check_time <= self.end_time
        else:
            # Normal shift (e.g., Day: 06:30 - 15:30)
            return self.start_time <= check_time <= self.end_time
    
    @classmethod
    def get_team_shifts(cls, team_id, active_only=True):
        """Get all shifts for a team ordered by order_index"""
        query = cls.query.filter_by(team_id=team_id)
        if active_only:
            query = query.filter_by(is_active=True)
        return query.order_by(cls.order_index, cls.shift_name).all()
    
    @classmethod
    def get_account_team_shifts(cls, account_id, team_id=None, active_only=True):
        """Get shifts for account, optionally filtered by team"""
        query = cls.query.filter_by(account_id=account_id)
        if team_id:
            query = query.filter_by(team_id=team_id)
        if active_only:
            query = query.filter_by(is_active=True)
        return query.order_by(cls.order_index, cls.shift_name).all()
    
    @classmethod
    def get_current_shift_for_team(cls, team_id, current_time=None):
        """Get the current shift for a team based on time"""
        if current_time is None:
            current_time = datetime.now().time()
        
        shifts = cls.get_team_shifts(team_id, active_only=True)
        for shift in shifts:
            if shift.is_time_in_shift(current_time):
                return shift
        return None
    
    @classmethod
    def get_next_shift_for_team(cls, team_id, current_time=None):
        """Get the next shift for a team based on time"""
        if current_time is None:
            current_time = datetime.now().time()
        elif isinstance(current_time, datetime):
            current_time = current_time.time()
        
        shifts = cls.get_team_shifts(team_id, active_only=True)
        if not shifts:
            return None
        
        # Sort shifts by order_index
        sorted_shifts = sorted(shifts, key=lambda s: s.order_index)
        
        # Find the next shift after current time
        for shift in sorted_shifts:
            if shift.start_time > current_time:
                return shift
        
        # If no shift found after current time, return first shift of next day
        return sorted_shifts[0] if sorted_shifts else None
    
    @classmethod
    def create_default_shifts_for_team(cls, team_id, account_id, shift_pattern='standard'):
        """Create default shift patterns for a team"""
        default_patterns = {
            'standard': [
                {'code': 'D', 'name': 'Day Shift', 'start': '06:30', 'end': '15:30', 'color': '#ffc107', 'order': 1},
                {'code': 'E', 'name': 'Evening Shift', 'start': '15:00', 'end': '00:00', 'color': '#28a745', 'order': 2},
                {'code': 'N', 'name': 'Night Shift', 'start': '22:00', 'end': '07:00', 'color': '#dc3545', 'order': 3},
            ],
            'devops': [
                {'code': 'D', 'name': 'Day Shift (Onshore)', 'start': '06:30', 'end': '15:30', 'color': '#007bff', 'order': 1},
                {'code': 'N', 'name': 'Night Shift (Offshore)', 'start': '22:00', 'end': '07:00', 'color': '#6f42c1', 'order': 2},
            ],
            'extended': [
                {'code': 'D', 'name': 'Day Shift', 'start': '06:30', 'end': '15:30', 'color': '#ffc107', 'order': 1},
                {'code': 'E', 'name': 'Evening Shift', 'start': '15:00', 'end': '00:00', 'color': '#28a745', 'order': 2},
                {'code': 'N', 'name': 'Night Shift', 'start': '22:00', 'end': '07:00', 'color': '#dc3545', 'order': 3},
                {'code': 'LE', 'name': 'Late Evening Shift', 'start': '18:00', 'end': '03:00', 'color': '#fd7e14', 'order': 4},
                {'code': 'G', 'name': 'General Shift', 'start': '10:00', 'end': '19:00', 'color': '#20c997', 'order': 5},
            ]
        }
        
        pattern = default_patterns.get(shift_pattern, default_patterns['standard'])
        created_shifts = []
        
        for shift_def in pattern:
            # Parse time strings
            start_time = datetime.strptime(shift_def['start'], '%H:%M').time()
            end_time = datetime.strptime(shift_def['end'], '%H:%M').time()
            
            shift_config = cls(
                team_id=team_id,
                account_id=account_id,
                shift_code=shift_def['code'],
                shift_name=shift_def['name'],
                start_time=start_time,
                end_time=end_time,
                color_code=shift_def['color'],
                order_index=shift_def['order'],
                is_active=True
            )
            
            db.session.add(shift_config)
            created_shifts.append(shift_config)
        
        try:
            db.session.commit()
            return created_shifts
        except Exception as e:
            db.session.rollback()
            raise e
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'team_id': self.team_id,
            'account_id': self.account_id,
            'shift_code': self.shift_code,
            'shift_name': self.shift_name,
            'start_time': self.start_time.strftime('%H:%M') if self.start_time else None,
            'end_time': self.end_time.strftime('%H:%M') if self.end_time else None,
            'formatted_time_range': self.formatted_time_range,
            'color_code': self.color_code,
            'order_index': self.order_index,
            'is_active': self.is_active,
            'is_default': self.is_default,
            'is_overnight_shift': self.is_overnight_shift,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }