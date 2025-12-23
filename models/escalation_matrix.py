"""
Escalation Matrix Model
Stores escalation matrix entries in the database with full CRUD support.
"""
from datetime import datetime
from models.models import db


class EscalationMatrixEntry(db.Model):
    """Model for storing escalation matrix entries"""
    __tablename__ = 'escalation_matrix_entry'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Application/Team identification
    application_name = db.Column(db.String(256), nullable=False)  # Sheet name or application identifier
    
    # Core contact information
    team_email_id = db.Column(db.Text, nullable=True)
    contact_details = db.Column(db.Text, nullable=True)
    support_coverage = db.Column(db.Text, nullable=True)
    sla = db.Column(db.Text, nullable=True)
    servicenow_assignment_group = db.Column(db.String(256), nullable=True)
    
    # Escalation levels
    escalation_level_1 = db.Column(db.Text, nullable=True)
    escalation_level_2 = db.Column(db.Text, nullable=True)
    escalation_level_3 = db.Column(db.Text, nullable=True)
    escalation_level_4 = db.Column(db.Text, nullable=True)
    escalation_level_5 = db.Column(db.Text, nullable=True)
    
    # Additional fields that may exist in Excel
    notes = db.Column(db.Text, nullable=True)
    additional_info = db.Column(db.Text, nullable=True)
    
    # Multi-tenancy
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=True)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=True)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    account = db.relationship('Account', backref='escalation_entries', lazy=True, foreign_keys=[account_id])
    team = db.relationship('Team', backref='escalation_entries', lazy=True, foreign_keys=[team_id])
    
    def to_dict(self):
        """Convert entry to dictionary for JSON responses"""
        return {
            'id': self.id,
            'application_name': self.application_name,
            'team_email_id': self.team_email_id,
            'contact_details': self.contact_details,
            'support_coverage': self.support_coverage,
            'sla': self.sla,
            'servicenow_assignment_group': self.servicenow_assignment_group,
            'escalation_level_1': self.escalation_level_1,
            'escalation_level_2': self.escalation_level_2,
            'escalation_level_3': self.escalation_level_3,
            'escalation_level_4': self.escalation_level_4,
            'escalation_level_5': self.escalation_level_5,
            'notes': self.notes,
            'additional_info': self.additional_info,
            'account_id': self.account_id,
            'team_id': self.team_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_active': self.is_active
        }
    
    @classmethod
    def from_excel_row(cls, row_data, application_name, account_id=None, team_id=None, created_by=None):
        """Create an entry from an Excel row dictionary"""
        # Map common Excel column names to model fields
        # Supports various column name formats (with spaces, hyphens, underscores)
        column_mapping = {
            # Team Email mappings
            'Team Email ID': 'team_email_id',
            'Team Email': 'team_email_id',
            'Email': 'team_email_id',
            'Email ID': 'team_email_id',
            # Contact Details mappings
            'Contact Details': 'contact_details',
            'Contact': 'contact_details',
            'Phone': 'contact_details',
            # Support Coverage mappings
            'Support Coverage': 'support_coverage',
            'Coverage': 'support_coverage',
            # SLA mappings
            'SLA': 'sla',
            # ServiceNow mappings
            'ServiceNow Assignment Group': 'servicenow_assignment_group',
            'Assignment Group': 'servicenow_assignment_group',
            'SNOW Group': 'servicenow_assignment_group',
            # Escalation Level 1 - various formats
            'Escalation Level 1': 'escalation_level_1',
            'Escalation Level-1': 'escalation_level_1',
            'Escalation_Level_1': 'escalation_level_1',
            'EscalationLevel1': 'escalation_level_1',
            'Level 1': 'escalation_level_1',
            'Level-1': 'escalation_level_1',
            'L1': 'escalation_level_1',
            # Escalation Level 2 - various formats
            'Escalation Level 2': 'escalation_level_2',
            'Escalation Level-2': 'escalation_level_2',
            'Escalation_Level_2': 'escalation_level_2',
            'EscalationLevel2': 'escalation_level_2',
            'Level 2': 'escalation_level_2',
            'Level-2': 'escalation_level_2',
            'L2': 'escalation_level_2',
            # Escalation Level 3 - various formats
            'Escalation Level 3': 'escalation_level_3',
            'Escalation Level-3': 'escalation_level_3',
            'Escalation_Level_3': 'escalation_level_3',
            'EscalationLevel3': 'escalation_level_3',
            'Level 3': 'escalation_level_3',
            'Level-3': 'escalation_level_3',
            'L3': 'escalation_level_3',
            # Escalation Level 4 - various formats
            'Escalation Level 4': 'escalation_level_4',
            'Escalation Level-4': 'escalation_level_4',
            'Escalation_Level_4': 'escalation_level_4',
            'EscalationLevel4': 'escalation_level_4',
            'Level 4': 'escalation_level_4',
            'Level-4': 'escalation_level_4',
            'L4': 'escalation_level_4',
            # Escalation Level 5 - various formats
            'Escalation Level 5': 'escalation_level_5',
            'Escalation Level-5': 'escalation_level_5',
            'Escalation_Level_5': 'escalation_level_5',
            'EscalationLevel5': 'escalation_level_5',
            'Level 5': 'escalation_level_5',
            'Level-5': 'escalation_level_5',
            'L5': 'escalation_level_5',
            # Notes mappings
            'Notes': 'notes',
            'Note': 'notes',
            'Additional Info': 'additional_info',
            'AdditionalInfo': 'additional_info',
            'Comments': 'additional_info',
        }
        
        entry = cls(
            application_name=application_name,
            account_id=account_id,
            team_id=team_id,
            created_by=created_by
        )
        
        for excel_col, model_field in column_mapping.items():
            if excel_col in row_data and row_data[excel_col]:
                setattr(entry, model_field, str(row_data[excel_col]))
        
        return entry

