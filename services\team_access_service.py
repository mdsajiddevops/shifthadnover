"""
Team Access Service - Manages multi-team access and filtering for users
"""

from flask_login import current_user
from flask import session
from models.models import UserTeamMembership, Team, Account


class TeamAccessService:
    """Service to handle multi-team user access and filtering"""
    
    @staticmethod
    def get_user_team_ids(user=None, account_id=None):
        """Get all team IDs for the current user or specified user"""
        if user is None:
            user = current_user
            
        if not user or not user.is_authenticated:
            return []
            
        # Super admin has access to all teams
        if user.role == 'super_admin':
            query = Team.query.filter_by(is_active=True)
            if account_id:
                query = query.filter_by(account_id=account_id)
            return [team.id for team in query.all()]
        
        # Account admin has access to all teams in their account
        if user.role == 'account_admin' and user.account_id:
            account_filter = account_id if account_id else user.account_id
            teams = Team.query.filter_by(account_id=account_filter, is_active=True).all()
            return [team.id for team in teams]
        
        # Regular users: get teams from UserTeamMembership
        user_teams = user.get_teams(account_id=account_id, active_only=True)
        team_ids = [membership.team_id for membership in user_teams]
        
        # Fallback: if no team memberships but user has team_id, include it
        if not team_ids and user.team_id and (not account_id or user.account_id == account_id):
            team_ids = [user.team_id]
            
        return team_ids
    
    @staticmethod
    def get_user_accounts():
        """Get all accounts the current user has access to"""
        if not current_user.is_authenticated:
            return []
        
        if current_user.role == 'super_admin':
            return Account.query.filter_by(is_active=True).all()
        
        if current_user.account_id:
            return [Account.query.get(current_user.account_id)]
        
        return []
    
    @staticmethod
    def get_user_teams_for_account(account_id, user=None):
        """Get all teams for the user in a specific account"""
        if user is None:
            user = current_user
            
        team_ids = TeamAccessService.get_user_team_ids(user, account_id)
        return Team.query.filter(Team.id.in_(team_ids), Team.is_active == True).all()
    
    @staticmethod
    def get_primary_team_id(user=None, account_id=None):
        """Get the primary team ID for the user"""
        if user is None:
            user = current_user
            
        if not user or not user.is_authenticated:
            return None
            
        # Super admin and account admin don't have primary teams in the same way
        if user.role in ['super_admin', 'account_admin']:
            return None
            
        # Get primary team membership
        primary_membership = user.get_primary_team_membership(account_id=account_id)
        if primary_membership:
            return primary_membership.team_id
            
        # Fallback: if no primary team set, get the first team
        user_teams = user.get_teams(account_id=account_id, active_only=True)
        if user_teams:
            return user_teams[0].team_id
            
        # Final fallback: legacy team_id field
        if user.team_id and (not account_id or user.account_id == account_id):
            return user.team_id
            
        return None
    
    @staticmethod
    def get_selected_team_id():
        """Get the currently selected team ID from session"""
        return session.get('selected_team_id')
    
    @staticmethod
    def get_selected_account_id():
        """Get the currently selected account ID from session"""
        if current_user.role == 'super_admin':
            return session.get('selected_account_id')
        elif current_user.role == 'account_admin':
            return current_user.account_id
        else:
            return current_user.account_id
    
    @staticmethod
    def set_selected_team(team_id):
        """Set the selected team in session"""
        # Validate user has access to this team
        user_team_ids = TeamAccessService.get_user_team_ids()
        if team_id in user_team_ids or team_id is None:
            session['selected_team_id'] = team_id
            return True
        return False
    
    @staticmethod
    def reset_to_primary_team(account_id=None):
        """Reset selected team to user's primary team"""
        primary_team_id = TeamAccessService.get_primary_team_id(account_id=account_id)
        if primary_team_id:
            session['selected_team_id'] = primary_team_id
            return primary_team_id
        return None
    
    @staticmethod
    def get_effective_team_ids():
        """Get the team IDs to use for filtering based on current selection"""
        selected_team_id = TeamAccessService.get_selected_team_id()
        user_team_ids = TeamAccessService.get_user_team_ids()
        
        # If a specific team is selected and user has access to it
        if selected_team_id and selected_team_id in user_team_ids:
            return [selected_team_id]
        
        # Otherwise return all user's team IDs
        return user_team_ids
    
    @staticmethod
    def get_effective_account_id():
        """Get the account ID to use for filtering"""
        return TeamAccessService.get_selected_account_id()
    
    @staticmethod
    def can_access_team(team_id, account_id=None):
        """Check if current user can access a specific team"""
        user_team_ids = TeamAccessService.get_user_team_ids(account_id=account_id)
        return team_id in user_team_ids
    
    @staticmethod
    def apply_team_filter(query, model_class, team_field='team_id', account_field='account_id'):
        """Apply team-based filtering to a SQLAlchemy query
        
        Args:
            query: SQLAlchemy query object
            model_class: The model class being queried
            team_field: Name of the team_id field in the model
            account_field: Name of the account_id field in the model
        """
        account_id = TeamAccessService.get_effective_account_id()
        team_ids = TeamAccessService.get_effective_team_ids()
        
        if not team_ids:
            # No teams accessible - return empty result
            return query.filter(getattr(model_class, team_field) == -1)  # Impossible condition
        
        # Apply account filter if available
        if account_id and hasattr(model_class, account_field):
            query = query.filter(getattr(model_class, account_field) == account_id)
        
        # Apply team filter
        if hasattr(model_class, team_field):
            query = query.filter(getattr(model_class, team_field).in_(team_ids))
        
        return query
    
    @staticmethod
    def get_team_filter_context(url_team_id=None):
        """Get context data for team filter UI components
        
        Args:
            url_team_id: Optional team ID from URL query parameter (overrides session)
        """
        if not current_user.is_authenticated:
            return {
                'show_team_filter': False,
                'user_teams': [],
                'selected_team_id': None,
                'primary_team_id': None,
                'accounts': []
            }
        
        account_id = TeamAccessService.get_effective_account_id()
        user_teams = TeamAccessService.get_user_teams_for_account(account_id) if account_id else []
        selected_team_id = TeamAccessService.get_selected_team_id()
        primary_team_id = TeamAccessService.get_primary_team_id(account_id=account_id)
        
        # URL parameter takes precedence over session
        if url_team_id is not None:
            # Validate that user has access to this team
            user_team_ids = [t.id for t in user_teams]
            if url_team_id in user_team_ids:
                selected_team_id = url_team_id
                session['selected_team_id'] = url_team_id
        
        # If no team is selected in session, default to primary team
        if selected_team_id is None and primary_team_id:
            selected_team_id = primary_team_id
            # Set it in session for consistency
            session['selected_team_id'] = primary_team_id
        
        # If user has only one team, auto-select it
        if len(user_teams) == 1 and not selected_team_id:
            selected_team_id = user_teams[0].id
            session['selected_team_id'] = selected_team_id
        
        return {
            'show_team_filter': len(user_teams) > 1,  # Show filter only if user has multiple teams
            'user_teams': user_teams,
            'selected_team_id': selected_team_id,
            'primary_team_id': primary_team_id,
            'accounts': TeamAccessService.get_user_accounts(),
            'selected_account_id': account_id
        }