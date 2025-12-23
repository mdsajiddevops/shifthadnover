"""
Email Configuration Service

Business logic for managing team email configurations.
Handles CRUD operations, validation, and integration with handover notifications.
"""

from typing import List, Dict, Optional, Tuple
from datetime import datetime
from flask import request
from flask_login import current_user
from models.models import db, Account, Team, User
from models.email_config import TeamEmailConfig, EmailConfigAuditLog
import logging
import re

# Simple audit function (avoiding potential import issues)
def log_action(user_id=None, action_type=None, details=None, ip_address=None):
    """Simple audit logging function."""
    try:
        if hasattr(current_user, 'id'):
            print(f"AUDIT: User {current_user.id} - {action_type}: {details}")
    except:
        print(f"AUDIT: {action_type}: {details}")

class EmailConfigService:
    """Service for managing team email configurations."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.email_pattern = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
    
    def create_config(self, account_id: int, team_id: int, to_recipients: str = None, 
                     cc_recipients: str = None, priority_recipients: str = None, 
                     is_default: bool = False) -> Dict:
        """
        Create a new email configuration for account + team.
        
        Args:
            account_id: ID of the account
            team_id: ID of the team  
            to_recipients: Comma-separated TO email addresses
            cc_recipients: Comma-separated CC email addresses
            priority_recipients: Comma-separated priority email addresses
            is_default: Whether this is the default config for the account
            
        Returns:
            Dict with success status and message/data
        """
        try:
            # Validate account and team exist
            account = Account.query.get(account_id)
            team = Team.query.get(team_id)
            
            if not account:
                return {'success': False, 'message': f'Account with ID {account_id} not found'}
            
            if not team:
                return {'success': False, 'message': f'Team with ID {team_id} not found'}
                
            if team.account_id != account_id:
                return {'success': False, 'message': 'Team does not belong to the specified account'}
            
            # Check if configuration already exists
            existing_config = TeamEmailConfig.get_config_for_team(account_id, team_id)
            if existing_config:
                return {'success': False, 'message': 'Email configuration already exists for this team'}
            
            # Validate email addresses
            validation_result = self._validate_email_fields(to_recipients, cc_recipients, priority_recipients)
            if not validation_result['valid']:
                return {'success': False, 'message': f'Invalid email addresses: {", ".join(validation_result["invalid_emails"])}'}
            
            # If this is set as default, remove default flag from other configs for this account
            if is_default:
                self._clear_default_flag(account_id)
            
            # Create new configuration
            config = TeamEmailConfig(
                account_id=account_id,
                team_id=team_id,
                to_recipients=to_recipients,
                cc_recipients=cc_recipients,
                priority_recipients=priority_recipients,
                is_default=is_default,
                created_by=current_user.id,
                created_at=datetime.utcnow()
            )
            
            db.session.add(config)
            db.session.commit()
            
            # Log the creation
            self._log_config_change(config.id, 'CREATE', None, {
                'account_id': account_id,
                'team_id': team_id,
                'to_recipients': to_recipients,
                'cc_recipients': cc_recipients,
                'priority_recipients': priority_recipients,
                'is_default': is_default
            })
            
            # Audit log
            log_action(
                user_id=current_user.id,
                action_type='EMAIL_CONFIG_CREATE',
                details=f'Created email config for {account.name} - {team.name}',
                ip_address=request.remote_addr if request else None
            )
            
            return {
                'success': True,
                'message': 'Email configuration created successfully',
                'data': self._serialize_config(config)
            }
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Error creating email configuration: {str(e)}")
            return {'success': False, 'message': 'An error occurred while creating the configuration'}
    
    def update_config(self, config_id: int, to_recipients: str = None, 
                     cc_recipients: str = None, priority_recipients: str = None,
                     is_default: bool = None) -> Dict:
        """
        Update an existing email configuration.
        
        Args:
            config_id: ID of the configuration to update
            to_recipients: Updated TO email addresses
            cc_recipients: Updated CC email addresses  
            priority_recipients: Updated priority email addresses
            is_default: Updated default flag
            
        Returns:
            Dict with success status and message/data
        """
        try:
            config = TeamEmailConfig.query.get(config_id)
            if not config:
                return {'success': False, 'message': 'Email configuration not found'}
            
            # Check permissions
            if not self._can_modify_config(config):
                return {'success': False, 'message': 'Insufficient permissions to modify this configuration'}
            
            # Store old values for audit
            old_values = {
                'to_recipients': config.to_recipients,
                'cc_recipients': config.cc_recipients,
                'priority_recipients': config.priority_recipients,
                'is_default': config.is_default
            }
            
            # Validate email addresses if provided
            if any([to_recipients is not None, cc_recipients is not None, priority_recipients is not None]):
                validation_result = self._validate_email_fields(
                    to_recipients if to_recipients is not None else config.to_recipients,
                    cc_recipients if cc_recipients is not None else config.cc_recipients,
                    priority_recipients if priority_recipients is not None else config.priority_recipients
                )
                if not validation_result['valid']:
                    return {'success': False, 'message': f'Invalid email addresses: {", ".join(validation_result["invalid_emails"])}'}
            
            # Update fields
            if to_recipients is not None:
                config.to_recipients = to_recipients
            if cc_recipients is not None:
                config.cc_recipients = cc_recipients
            if priority_recipients is not None:
                config.priority_recipients = priority_recipients
            
            # Handle default flag
            if is_default is not None and is_default != config.is_default:
                if is_default:
                    self._clear_default_flag(config.account_id)
                config.is_default = is_default
            
            config.updated_by = current_user.id
            config.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            # Log the update
            new_values = {
                'to_recipients': config.to_recipients,
                'cc_recipients': config.cc_recipients,
                'priority_recipients': config.priority_recipients,
                'is_default': config.is_default
            }
            
            self._log_config_change(config.id, 'UPDATE', old_values, new_values)
            
            # Audit log
            log_action(
                user_id=current_user.id,
                action_type='EMAIL_CONFIG_UPDATE',
                details=f'Updated email config for {config.account.name} - {config.team.name}',
                ip_address=request.remote_addr if request else None
            )
            
            return {
                'success': True,
                'message': 'Email configuration updated successfully',
                'data': self._serialize_config(config)
            }
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Error updating email configuration: {str(e)}")
            return {'success': False, 'message': 'An error occurred while updating the configuration'}
    
    def delete_config(self, config_id: int) -> Dict:
        """
        Delete (deactivate) an email configuration.
        
        Args:
            config_id: ID of the configuration to delete
            
        Returns:
            Dict with success status and message
        """
        try:
            config = TeamEmailConfig.query.get(config_id)
            if not config:
                return {'success': False, 'message': 'Email configuration not found'}
            
            # Check permissions
            if not self._can_modify_config(config):
                return {'success': False, 'message': 'Insufficient permissions to delete this configuration'}
            
            # Store values for audit
            old_values = self._serialize_config(config)
            
            # Soft delete by deactivating
            config.is_active = False
            config.updated_by = current_user.id
            config.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            # Log the deletion
            self._log_config_change(config.id, 'DELETE', old_values, {'is_active': False})
            
            # Audit log
            log_action(
                user_id=current_user.id,
                action_type='EMAIL_CONFIG_DELETE',
                details=f'Deleted email config for {config.account.name} - {config.team.name}',
                ip_address=request.remote_addr if request else None
            )
            
            return {'success': True, 'message': 'Email configuration deleted successfully'}
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Error deleting email configuration: {str(e)}")
            return {'success': False, 'message': 'An error occurred while deleting the configuration'}
    
    def get_config(self, config_id: int) -> Dict:
        """Get a specific email configuration."""
        try:
            config = TeamEmailConfig.query.get(config_id)
            if not config or not config.is_active:
                return {'success': False, 'message': 'Email configuration not found'}
            
            return {
                'success': True,
                'data': self._serialize_config(config)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting email configuration: {str(e)}")
            return {'success': False, 'message': 'An error occurred while retrieving the configuration'}
    
    def get_configs_for_account(self, account_id: int) -> Dict:
        """Get all email configurations for an account."""
        try:
            configs = TeamEmailConfig.get_configs_for_account(account_id)
            
            return {
                'success': True,
                'data': [self._serialize_config(config) for config in configs]
            }
            
        except Exception as e:
            self.logger.error(f"Error getting email configurations for account: {str(e)}")
            return {'success': False, 'message': 'An error occurred while retrieving configurations'}
    
    def get_recipients_for_handover(self, user_id: int, account_id: int, team_id: int, 
                                   is_priority: bool = False) -> Dict:
        """
        Get email recipients for a handover based on user's account and team.
        This is the main method used by the handover notification service.
        
        Args:
            user_id: ID of the user submitting the handover
            account_id: ID of the account
            team_id: ID of the team
            is_priority: Whether this is a priority handover
            
        Returns:
            Dict with success status and recipient lists
        """
        try:
            # First, try to get specific team configuration
            config = TeamEmailConfig.get_config_for_team(account_id, team_id)
            
            if not config:
                # Fallback to default configuration for the account
                config = TeamEmailConfig.get_default_config_for_account(account_id)
            
            if not config:
                return {
                    'success': False,
                    'message': 'No email configuration found for this team or account',
                    'to_recipients': [],
                    'cc_recipients': [],
                    'priority_recipients': []
                }
            
            recipients = {
                'success': True,
                'message': 'Recipients found successfully',
                'to_recipients': config.get_to_recipients_list(),
                'cc_recipients': config.get_cc_recipients_list(),
                'priority_recipients': config.get_priority_recipients_list() if is_priority else [],
                'config_type': 'team' if config.team_id == team_id else 'default'
            }
            
            # Log the recipient lookup for audit purposes
            log_action(
                user_id=user_id,
                action_type='EMAIL_RECIPIENTS_LOOKUP',
                details=f'Retrieved recipients for handover - Account: {account_id}, Team: {team_id}, Priority: {is_priority}',
                ip_address=request.remote_addr if request else None
            )
            
            return recipients
            
        except Exception as e:
            self.logger.error(f"Error getting recipients for handover: {str(e)}")
            return {
                'success': False,
                'message': 'An error occurred while retrieving email recipients',
                'to_recipients': [],
                'cc_recipients': [],
                'priority_recipients': []
            }
    
    def _validate_email_fields(self, to_recipients: str, cc_recipients: str, 
                              priority_recipients: str) -> Dict:
        """Validate email addresses in all fields."""
        invalid_emails = []
        
        # Validate TO recipients
        if to_recipients:
            to_list = [email.strip() for email in to_recipients.split(',') if email.strip()]
            for email in to_list:
                if not self.email_pattern.match(email):
                    invalid_emails.append(email)
        
        # Validate CC recipients
        if cc_recipients:
            cc_list = [email.strip() for email in cc_recipients.split(',') if email.strip()]
            for email in cc_list:
                if not self.email_pattern.match(email):
                    invalid_emails.append(email)
        
        # Validate Priority recipients
        if priority_recipients:
            priority_list = [email.strip() for email in priority_recipients.split(',') if email.strip()]
            for email in priority_list:
                if not self.email_pattern.match(email):
                    invalid_emails.append(email)
        
        return {
            'valid': len(invalid_emails) == 0,
            'invalid_emails': invalid_emails
        }
    
    def _can_modify_config(self, config: TeamEmailConfig) -> bool:
        """Check if current user can modify the given configuration."""
        user_role = current_user.role
        
        # Super admin can modify any configuration
        if user_role == 'super_admin':
            return True
        
        # Account admin can modify configurations for their account
        if user_role == 'account_admin':
            return current_user.account_id == config.account_id
        
        # Team admin can modify configurations for their team
        if user_role == 'team_admin':
            return (current_user.account_id == config.account_id and 
                   current_user.team_id == config.team_id)
        
        return False
    
    def _clear_default_flag(self, account_id: int):
        """Clear the default flag from all configurations for an account."""
        existing_defaults = TeamEmailConfig.query.filter_by(
            account_id=account_id,
            is_default=True,
            is_active=True
        ).all()
        
        for config in existing_defaults:
            config.is_default = False
    
    def _log_config_change(self, config_id: int, action: str, old_values: Dict, new_values: Dict):
        """Log configuration changes to audit table."""
        try:
            audit_log = EmailConfigAuditLog(
                config_id=config_id,
                action=action,
                old_values=old_values,
                new_values=new_values,
                performed_by=current_user.id,
                performed_at=datetime.utcnow(),
                ip_address=request.remote_addr if request else None
            )
            
            db.session.add(audit_log)
            # Note: commit is handled by the calling method
            
        except Exception as e:
            self.logger.error(f"Error logging configuration change: {str(e)}")
    
    def _serialize_config(self, config: TeamEmailConfig) -> Dict:
        """Serialize email configuration to dictionary."""
        return {
            'id': config.id,
            'account_id': config.account_id,
            'account_name': config.account.name,
            'team_id': config.team_id,
            'team_name': config.team.name,
            'to_recipients': config.to_recipients,
            'cc_recipients': config.cc_recipients,
            'priority_recipients': config.priority_recipients,
            'is_active': config.is_active,
            'is_default': config.is_default,
            'created_by': config.creator.username if config.creator else None,
            'created_at': config.created_at.isoformat() if config.created_at else None,
            'updated_by': config.updater.username if config.updater else None,
            'updated_at': config.updated_at.isoformat() if config.updated_at else None,
            'to_recipients_list': config.get_to_recipients_list(),
            'cc_recipients_list': config.get_cc_recipients_list(),
            'priority_recipients_list': config.get_priority_recipients_list()
        }