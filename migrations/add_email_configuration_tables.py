"""
Migration: Add Team Email Configuration Tables

This migration creates the tables for managing team-based email configurations:
- team_email_configs: Main configuration table
- email_config_audit_logs: Audit trail for configuration changes

Run this migration after backing up your database.
"""

from models.models import db
from models.email_config import TeamEmailConfig, EmailConfigAuditLog
from datetime import datetime
import logging

def upgrade():
    """Create the new email configuration tables."""
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("Starting email configuration tables migration...")
        
        # Create all tables defined in the email_config models
        db.create_all()
        
        logger.info("Email configuration tables created successfully")
        
        # Optional: Create a default configuration for existing accounts/teams
        create_default_configs()
        
        logger.info("Migration completed successfully")
        
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        raise e

def downgrade():
    """Drop the email configuration tables."""
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("Starting email configuration tables rollback...")
        
        # Drop tables in reverse order due to foreign key constraints
        db.engine.execute("DROP TABLE IF EXISTS email_config_audit_logs")
        db.engine.execute("DROP TABLE IF EXISTS team_email_configs")
        
        logger.info("Email configuration tables dropped successfully")
        
    except Exception as e:
        logger.error(f"Rollback failed: {str(e)}")
        raise e

def create_default_configs():
    """
    Create default email configurations for existing accounts.
    This helps with backward compatibility.
    """
    from models.models import Account, Team, User
    
    logger = logging.getLogger(__name__)
    
    try:
        # Get all accounts
        accounts = Account.query.all()
        
        for account in accounts:
            # Check if account already has a default configuration
            existing_default = TeamEmailConfig.query.filter_by(
                account_id=account.id,
                is_default=True,
                is_active=True
            ).first()
            
            if existing_default:
                logger.info(f"Default configuration already exists for account {account.name}")
                continue
            
            # Get the first team for this account to use as default
            first_team = Team.query.filter_by(account_id=account.id).first()
            
            if not first_team:
                logger.warning(f"No teams found for account {account.name}, skipping default config creation")
                continue
            
            # Get account admin or first user as creator
            creator = User.query.filter_by(
                account_id=account.id,
                role='account_admin'
            ).first()
            
            if not creator:
                creator = User.query.filter_by(account_id=account.id).first()
            
            if not creator:
                logger.warning(f"No users found for account {account.name}, skipping default config creation")
                continue
            
            # Use existing email_recipients from team if available
            default_emails = None
            if hasattr(first_team, 'email_recipients') and first_team.email_recipients:
                default_emails = first_team.email_recipients
            
            # Create default configuration
            default_config = TeamEmailConfig(
                account_id=account.id,
                team_id=first_team.id,
                to_recipients=default_emails,
                cc_recipients=None,
                priority_recipients=None,
                is_active=True,
                is_default=True,
                created_by=creator.id,
                created_at=datetime.utcnow()
            )
            
            db.session.add(default_config)
            
            logger.info(f"Created default email configuration for account {account.name}")
        
        db.session.commit()
        logger.info("Default configurations created successfully")
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating default configurations: {str(e)}")
        # Don't raise here as this is optional

if __name__ == "__main__":
    # This allows running the migration directly
    from app import app
    
    with app.app_context():
        upgrade()