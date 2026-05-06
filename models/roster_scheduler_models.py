"""
Models for the auto-roster scheduler.

Three new tables:
  - shift_coverage_requirements  per-team required headcount per shift code
  - public_holidays              account-scoped public holidays
  - scheduled_shifts             generated (or manually set) shift assignments per member per day

Also adds scheduling_role to TeamMember (via migration, not here — see
migrations/versions/*_add_roster_scheduler_tables.py).
"""
from datetime import datetime

from models.models import db


class ShiftCoverageRequirement(db.Model):
    """
    How many people a team needs on each shift code per day.
    Value is a string: '0'..'N' or '*' (fill remaining slots).
    """
    __tablename__ = 'shift_coverage_requirements'

    id             = db.Column(db.Integer, primary_key=True)
    team_id        = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    account_id     = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    shift_code     = db.Column(db.String(10), nullable=False)
    required_count = db.Column(db.String(4), nullable=False, default='1')
    is_active      = db.Column(db.Boolean, default=True, nullable=False)
    created_at     = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at     = db.Column(db.DateTime, default=datetime.utcnow,
                               onupdate=datetime.utcnow, nullable=False)

    team    = db.relationship('Team', backref='coverage_requirements')
    account = db.relationship('Account')

    __table_args__ = (
        db.UniqueConstraint('team_id', 'shift_code', name='uq_team_shift_req'),
        db.Index('idx_coverage_req_team', 'team_id', 'is_active'),
    )

    def __repr__(self):
        return f'<ShiftCoverageRequirement team={self.team_id} {self.shift_code}={self.required_count}>'

    def parsed_count(self):
        """Return integer count or the sentinel string '*'."""
        if self.required_count == '*':
            return '*'
        return int(self.required_count) if self.required_count.isdigit() else 0

    @classmethod
    def get_team_requirements(cls, team_id: int) -> dict:
        """Return {shift_code: parsed_count} for active requirements of a team."""
        rows = cls.query.filter_by(team_id=team_id, is_active=True).all()
        return {r.shift_code: r.parsed_count() for r in rows}

    @classmethod
    def default_requirements(cls) -> dict:
        """Sensible defaults used when no requirements are configured."""
        return {'D': 1, 'E': '*', 'N': 1, 'OS': 1, 'OF': 1}


class PublicHoliday(db.Model):
    """Account-scoped public holidays. PH days are protected — scheduler never overwrites them."""
    __tablename__ = 'public_holidays'

    id         = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    date       = db.Column(db.Date, nullable=False)
    name       = db.Column(db.String(128), nullable=False)
    is_active  = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    account = db.relationship('Account')

    __table_args__ = (
        db.UniqueConstraint('account_id', 'date', name='uq_account_holiday'),
        db.Index('idx_public_holiday_account_date', 'account_id', 'date'),
    )

    def __repr__(self):
        return f'<PublicHoliday {self.date} {self.name!r}>'

    @classmethod
    def get_for_month(cls, account_id: int, year: int, month: int) -> set:
        """Return set of day-integers that are public holidays in the given month."""
        import calendar
        from datetime import date
        start = date(year, month, 1)
        end = date(year, month, calendar.monthrange(year, month)[1])
        rows = cls.query.filter(
            cls.account_id == account_id,
            cls.date >= start,
            cls.date <= end,
            cls.is_active == True,
        ).all()
        return {r.date.day for r in rows}


class ScheduledShift(db.Model):
    """
    One row per team-member per calendar day.  The scheduler writes rows with
    source='auto'; human edits use source='manual'; leave imports use source='import'.

    Protected rows (is_protected=True) are never overwritten by the auto-scheduler.
    Leave codes (VL/SL/HL/CO) are always protected on creation.
    """
    __tablename__ = 'scheduled_shifts'

    id              = db.Column(db.Integer, primary_key=True)
    team_member_id  = db.Column(db.Integer, db.ForeignKey('team_member.id'), nullable=False)
    team_id         = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    account_id      = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    shift_date      = db.Column(db.Date, nullable=False)
    shift_code      = db.Column(db.String(10), nullable=False)
    is_protected    = db.Column(db.Boolean, default=False, nullable=False)
    source          = db.Column(db.String(16), default='auto', nullable=False)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at      = db.Column(db.DateTime, default=datetime.utcnow,
                                onupdate=datetime.utcnow, nullable=False)

    team_member = db.relationship('TeamMember', backref='scheduled_shifts')
    team        = db.relationship('Team', backref='scheduled_shifts')
    account     = db.relationship('Account')

    __table_args__ = (
        db.UniqueConstraint('team_member_id', 'shift_date', name='uq_member_shift_date'),
        db.Index('idx_scheduled_shift_team_date', 'team_id', 'shift_date'),
        db.Index('idx_scheduled_shift_account_date', 'account_id', 'shift_date'),
    )

    _LEAVE_CODES = {'VL', 'SL', 'HL', 'CO'}

    def __repr__(self):
        return f'<ScheduledShift member={self.team_member_id} {self.shift_date} {self.shift_code}>'

    @classmethod
    def upsert(cls, team_member_id: int, team_id: int, account_id: int,
               shift_date, shift_code: str, source: str = 'auto') -> 'ScheduledShift':
        """
        Insert or update a scheduled shift.  Never overwrites a protected row when
        called with source='auto'.
        """
        existing = cls.query.filter_by(
            team_member_id=team_member_id, shift_date=shift_date
        ).first()
        if existing:
            if existing.is_protected and source == 'auto':
                return existing
            existing.shift_code = shift_code
            existing.source = source
            existing.is_protected = shift_code in cls._LEAVE_CODES
        else:
            existing = cls(
                team_member_id=team_member_id,
                team_id=team_id,
                account_id=account_id,
                shift_date=shift_date,
                shift_code=shift_code,
                source=source,
                is_protected=shift_code in cls._LEAVE_CODES,
            )
            db.session.add(existing)
        return existing

    @classmethod
    def get_month_grid(cls, team_id: int, year: int, month: int) -> dict:
        """
        Return {team_member_id: {day_int: shift_code}} for the full month.
        day_int is 1-based.
        """
        import calendar
        from datetime import date
        start = date(year, month, 1)
        end = date(year, month, calendar.monthrange(year, month)[1])
        rows = cls.query.filter(
            cls.team_id == team_id,
            cls.shift_date >= start,
            cls.shift_date <= end,
        ).all()
        grid: dict = {}
        for r in rows:
            grid.setdefault(r.team_member_id, {})[r.shift_date.day] = r.shift_code
        return grid
