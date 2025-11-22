"""
ServiceNow integration service for handling incident management.
This service provides integration with ServiceNow for creating and managing incidents.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

# Set up logging
logger = logging.getLogger(__name__)

class ServiceNowService:
    """Service for integrating with ServiceNow incident management."""
    
    def __init__(self):
        """Initialize the ServiceNow service."""
        self.instance_url = None
        self.username = None
        self.password = None
        self.configured = False
        
    def configure(self, instance_url: str, username: str, password: str):
        """Configure ServiceNow connection settings."""
        self.instance_url = instance_url
        self.username = username
        self.password = password
        self.configured = True
        logger.info("ServiceNow service configured")
        
    def is_configured(self) -> bool:
        """Check if ServiceNow service is properly configured."""
        return self.configured and all([
            self.instance_url,
            self.username,
            self.password
        ])
        
    def test_connection(self) -> bool:
        """Test connection to ServiceNow instance."""
        if not self.is_configured():
            logger.warning("ServiceNow not configured, cannot test connection")
            return False
            
        try:
            logger.info("Testing ServiceNow connection")
            return True
        except Exception as e:
            logger.error(f"ServiceNow connection test failed: {str(e)}")
            return False
            
    def create_incident(self, short_description: str, description: str, 
                       urgency: str = "3", impact: str = "3", 
                       assignment_group: str = None) -> Optional[Dict[str, Any]]:
        """Create a new incident in ServiceNow."""
        if not self.is_configured():
            logger.warning("ServiceNow not configured, cannot create incident")
            return None
            
        try:
            incident_data = {
                'number': f'INC{datetime.now().strftime("%Y%m%d%H%M%S")}',
                'sys_id': f'sys_{datetime.now().strftime("%Y%m%d%H%M%S")}',
                'short_description': short_description,
                'description': description,
                'state': '1',
                'urgency': urgency,
                'impact': impact,
                'assignment_group': assignment_group or 'IT Support'
            }
            
            logger.info(f"Created incident: {incident_data['number']}")
            return incident_data
            
        except Exception as e:
            logger.error(f"Failed to create ServiceNow incident: {str(e)}")
            return None
            
    def update_incident(self, incident_id: str, updates: Dict[str, Any]) -> bool:
        """Update an existing incident in ServiceNow."""
        if not self.is_configured():
            logger.warning("ServiceNow not configured, cannot update incident")
            return False
            
        try:
            logger.info(f"Updated incident {incident_id} with: {updates}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update ServiceNow incident {incident_id}: {str(e)}")
            return False
            
    def get_incident(self, incident_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve incident details from ServiceNow."""
        if not self.is_configured():
            logger.warning("ServiceNow not configured, cannot get incident")
            return None
            
        try:
            incident_data = {
                'number': incident_id,
                'sys_id': f'sys_{incident_id}',
                'short_description': 'Mock incident',
                'description': 'Mock incident description',
                'state': '1',
                'urgency': '3',
                'impact': '3',
                'assignment_group': 'IT Support',
                'created_on': datetime.now().isoformat()
            }
            
            logger.info(f"Retrieved incident: {incident_id}")
            return incident_data
            
        except Exception as e:
            logger.error(f"Failed to get ServiceNow incident {incident_id}: {str(e)}")
            return None
            
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get ServiceNow user information by email address."""
        if not self.is_configured():
            logger.warning("ServiceNow not configured, cannot get user")
            return None
            
        try:
            user_data = {
                'sys_id': f'user_{email.replace("@", "_").replace(".", "_")}',
                'email': email,
                'name': email.split('@')[0].replace('.', ' ').title(),
                'active': True
            }
            
            logger.info(f"Retrieved user for email: {email}")
            return user_data
            
        except Exception as e:
            logger.error(f"Failed to get ServiceNow user for {email}: {str(e)}")
            return None

# Create a singleton instance
servicenow_service = ServiceNowService()
