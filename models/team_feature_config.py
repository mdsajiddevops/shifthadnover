"""
Team and Account Feature Configuration Model
Allows superadmin to control which tabs/features are visible for specific teams and accounts
"""

from models.models import db
from datetime import datetime

class TeamFeatureConfig(db.Model):
    """
    Stores feature/tab visibility configuration for teams and accounts.
    Supports hierarchy: Account-level defaults → Team-level overrides → Global defaults
    """
    __tablename__ = 'team_feature_config'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Scope: 'account' or 'team'
    scope_type = db.Column(db.String(20), nullable=False, index=True)  # 'account' or 'team'
    scope_id = db.Column(db.Integer, nullable=False, index=True)  # account_id or team_id
    
    # Feature/tab identifier (e.g., 'tab_problem_tickets', 'tab_vendor_details')
    feature_key = db.Column(db.String(128), nullable=False, index=True)
    
    # Whether the feature is enabled for this scope
    is_enabled = db.Column(db.Boolean, default=True, nullable=False)
    
    # Metadata
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp(), nullable=False)
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())
    created_by = db.Column(db.String(255), nullable=True)
    updated_by = db.Column(db.String(255), nullable=True)
    
    # Unique constraint: one config per scope+feature combination
    __table_args__ = (
        db.UniqueConstraint('scope_type', 'scope_id', 'feature_key', name='uq_scope_feature'),
    )
    
    def __repr__(self):
        return f'<TeamFeatureConfig {self.scope_type}:{self.scope_id}:{self.feature_key}={self.is_enabled}>'
    
    @staticmethod
    def get_feature_status(feature_key, account_id=None, team_id=None, default=True):
        """
        Get feature status with hierarchy: Team > Account > Global Default
        
        Args:
            feature_key: The feature/tab identifier (e.g., 'tab_problem_tickets')
            account_id: User's account ID
            team_id: User's team ID
            default: Default value if no configuration found
            
        Returns:
            bool: Whether the feature is enabled
        """
        # Priority 1: Check team-level configuration
        if team_id:
            team_config = TeamFeatureConfig.query.filter_by(
                scope_type='team',
                scope_id=team_id,
                feature_key=feature_key
            ).first()
            if team_config:
                return team_config.is_enabled
        
        # Priority 2: Check account-level configuration
        if account_id:
            account_config = TeamFeatureConfig.query.filter_by(
                scope_type='account',
                scope_id=account_id,
                feature_key=feature_key
            ).first()
            if account_config:
                return account_config.is_enabled
        
        # Priority 3: Check global default from AppConfig
        try:
            from models.app_config import AppConfig
            global_value = AppConfig.get_config(feature_key, 'true' if default else 'false')
            return global_value.lower() in ['true', '1', 'yes', 'enabled']
        except:
            return default
    
    @staticmethod
    def set_feature_status(scope_type, scope_id, feature_key, is_enabled, description=None, updated_by=None):
        """
        Set feature status for a specific scope (account or team)
        
        Args:
            scope_type: 'account' or 'team'
            scope_id: The account_id or team_id
            feature_key: The feature/tab identifier
            is_enabled: Whether to enable the feature
            description: Optional description
            updated_by: Username of person making the change
        """
        config = TeamFeatureConfig.query.filter_by(
            scope_type=scope_type,
            scope_id=scope_id,
            feature_key=feature_key
        ).first()
        
        if config:
            config.is_enabled = is_enabled
            if description:
                config.description = description
            if updated_by:
                config.updated_by = updated_by
            config.updated_at = datetime.utcnow()
        else:
            config = TeamFeatureConfig(
                scope_type=scope_type,
                scope_id=scope_id,
                feature_key=feature_key,
                is_enabled=is_enabled,
                description=description,
                created_by=updated_by,
                updated_by=updated_by
            )
            db.session.add(config)
        
        db.session.commit()
        return config
    
    @staticmethod
    def get_all_features_for_scope(scope_type, scope_id):
        """Get all feature configurations for a specific scope"""
        return TeamFeatureConfig.query.filter_by(
            scope_type=scope_type,
            scope_id=scope_id
        ).all()
    
    @staticmethod
    def get_all_available_features():
        """Get list of all available features/tabs that can be configured"""
        return [
            # Operations tabs
            ('tab_handover_form', 'Handover Form', 'Operations'),
            ('tab_shift_reports', 'Shift Reports', 'Operations'),
            ('tab_change_info', 'Change Info', 'Operations'),
            ('tab_kb_updates', 'KB Updates', 'Operations'),
            ('tab_key_points', 'Key Points', 'Operations'),
            ('tab_problem_tickets', 'Problem Tickets', 'Operations'),
            
            # Team Management tabs
            ('tab_shift_roster', 'Shift Roster', 'Team Management'),
            ('tab_roster_upload', 'Roster Upload', 'Team Management'),
            ('tab_team_details', 'Team Details', 'Team Management'),
            ('tab_oncall_dashboard', 'On-Call Dashboard', 'Team Management'),
            
            # Tools tabs
            ('tab_servicenow', 'ServiceNow Integration', 'Tools'),
            ('tab_escalation_matrix', 'Escalation Matrix', 'Tools'),
            ('tab_vendor_details', 'Vendor Details', 'Tools'),
            ('tab_ctask_assignment', 'CTask Assignment', 'Tools'),
            ('tab_audit_logs', 'Audit Logs', 'Tools'),
            ('tab_shift_management', 'Shift Management', 'Tools'),
            
            # Knowledge Base tabs
            ('tab_kb_articles', 'KB Articles', 'Knowledge Base'),
            ('tab_applications', 'Applications', 'Knowledge Base'),
            
            # Advanced tabs
            ('tab_change_management', 'Change Management', 'Advanced'),
            ('tab_post_mortems', 'Post-mortems', 'Advanced'),
        ]
    
    @staticmethod
    def bulk_update_features(scope_type, scope_id, feature_updates, updated_by=None):
        """
        Bulk update multiple features for a scope
        
        Args:
            scope_type: 'account' or 'team'
            scope_id: The account_id or team_id
            feature_updates: Dict of {feature_key: is_enabled}
            updated_by: Username of person making the change
        """
        for feature_key, is_enabled in feature_updates.items():
            TeamFeatureConfig.set_feature_status(
                scope_type=scope_type,
                scope_id=scope_id,
                feature_key=feature_key,
                is_enabled=is_enabled,
                updated_by=updated_by
            )
