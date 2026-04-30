"""
Multi-Team Support Service
Provides utilities for managing multi-team user access and filtering
"""

from flask import session, request
from flask_login import current_user
from models.models import UserTeamMembership, Team, Account
import logging
logger = logging.getLogger(__name__)


class MultiTeamService:
    """Service class to handle multi-team user operations"""
    
    @staticmethod
    def get_user_teams(user, account_id=None, active_only=True):
        """Get all teams for a user with enhanced filtering"""
        try:
            query = UserTeamMembership.query.filter_by(user_id=user.id)
            
            if account_id:
                query = query.filter_by(account_id=account_id)
            
            if active_only:
                query = query.filter_by(is_active=True)
            
            memberships = query.all()
            team_ids = [m.team_id for m in memberships]
            
            if team_ids:
                teams = Team.query.filter(Team.id.in_(team_ids)).all()
                return teams
            
            return []
        except Exception as e:
            logger.debug(f"[MultiTeamService] Error getting user teams: {str(e)}")
            return []
    
    @staticmethod
    def get_user_team_ids(user, account_id=None, active_only=True):
        """Get list of team IDs for a user"""
        teams = MultiTeamService.get_user_teams(user, account_id, active_only)
        return [team.id for team in teams]
    
    @staticmethod
    def has_multiple_teams(user, account_id=None):
        """Check if user belongs to multiple teams"""
        teams = MultiTeamService.get_user_teams(user, account_id)
        return len(teams) > 1
    
    @staticmethod
    def get_selected_team_id(session_key='selected_team_id'):
        """Get the currently selected team ID from session or request"""
        # Check URL parameter first, then session
        selected_team_id = request.args.get('team_id') or session.get(session_key)
        
        if selected_team_id:
            try:
                return int(selected_team_id)
            except (ValueError, TypeError):
                return None
        return None
    
    @staticmethod
    def set_selected_team_id(team_id, session_key='selected_team_id'):
        """Store selected team ID in session"""
        if team_id:
            session[session_key] = str(team_id)
        elif session_key in session:
            del session[session_key]
    
    @staticmethod
    def validate_team_access(user, team_id, account_id=None):
        """Validate if user has access to a specific team"""
        if not team_id:
            return True  # No team filter means access granted
        
        user_team_ids = MultiTeamService.get_user_team_ids(user, account_id)
        return int(team_id) in user_team_ids
    
    @staticmethod
    def get_filter_team_ids(user, selected_team_id=None, account_id=None):
        """
        Get team IDs for filtering based on selection
        Returns:
        - [selected_team_id] if a specific team is selected
        - all_user_team_ids if no team selected (show all user's teams)
        - [] if user has no teams
        """
        user_team_ids = MultiTeamService.get_user_team_ids(user, account_id)
        
        if not user_team_ids:
            return []
        
        # If specific team selected and user has access, use that
        if selected_team_id and MultiTeamService.validate_team_access(user, selected_team_id, account_id):
            return [int(selected_team_id)]
        
        # Otherwise, show data from all user's teams
        return user_team_ids
    
    @staticmethod
    def get_primary_team_id(user, account_id=None):
        """Get user's primary team ID"""
        try:
            membership = UserTeamMembership.query.filter_by(
                user_id=user.id,
                is_primary=True,
                is_active=True
            )
            
            if account_id:
                membership = membership.filter_by(account_id=account_id)
            
            membership = membership.first()
            return membership.team_id if membership else None
        except Exception as e:
            logger.debug(f"[MultiTeamService] Error getting primary team: {str(e)}")
            return None
    
    @staticmethod
    def get_team_filter_context(user, account_id=None, session_key='selected_team_id'):
        """
        Get complete context for team filtering UI
        Returns dict with:
        - user_teams: List of Team objects user belongs to
        - has_multiple_teams: Boolean
        - selected_team_id: Currently selected team ID
        - primary_team_id: User's primary team ID
        """
        user_teams = MultiTeamService.get_user_teams(user, account_id)
        selected_team_id = MultiTeamService.get_selected_team_id(session_key)
        primary_team_id = MultiTeamService.get_primary_team_id(user, account_id)
        
        # Validate selected team
        if selected_team_id and not MultiTeamService.validate_team_access(user, selected_team_id, account_id):
            selected_team_id = None
        
        # Default to primary team if no selection and user has primary team
        if not selected_team_id and primary_team_id:
            selected_team_id = primary_team_id
        
        return {
            'user_teams': user_teams,
            'has_multiple_teams': len(user_teams) > 1,
            'selected_team_id': selected_team_id,
            'primary_team_id': primary_team_id,
            'user_team_ids': [team.id for team in user_teams]
        }


def apply_team_filtering(query, model_class, user, selected_team_id=None, account_id=None, 
                        team_field='team_id', account_field='account_id'):
    """
    Apply team-based filtering to any SQLAlchemy query
    
    Args:
        query: SQLAlchemy query object
        model_class: The model class being queried  
        user: Current user object
        selected_team_id: Selected team ID (optional)
        account_id: Account ID for filtering (optional)
        team_field: Name of team ID field in the model (default: 'team_id')
        account_field: Name of account ID field in the model (default: 'account_id')
    
    Returns:
        Filtered query object
    """
    # Admin users see everything within their scope
    if user.role in ['super_admin']:
        if account_id:
            query = query.filter(getattr(model_class, account_field) == account_id)
        return query
    
    if user.role == 'account_admin':
        # Account admin sees everything in their account
        if user.account_id:
            query = query.filter(getattr(model_class, account_field) == user.account_id)
        if selected_team_id:
            query = query.filter(getattr(model_class, team_field) == selected_team_id)
        return query
    
    # Regular users: filter by their team memberships
    filter_team_ids = MultiTeamService.get_filter_team_ids(user, selected_team_id, account_id or user.account_id)
    
    if filter_team_ids:
        query = query.filter(
            getattr(model_class, account_field) == (account_id or user.account_id),
            getattr(model_class, team_field).in_(filter_team_ids)
        )
    else:
        # User has no teams - no data visible
        query = query.filter(False)
    
    return query