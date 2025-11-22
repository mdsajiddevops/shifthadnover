"""
ServiceNow Integration Service

This service handles all ServiceNow API interactions including:
- Fetching incidents assigned to service groups
- Filtering incidents by shift time
- Handling authentication and error management
- Data transformation for the application
"""

import requests
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from flask import current_app
import json
from urllib.parse import urljoin


class ServiceNowService:
    """ServiceNow API integration service"""
    
    def __init__(self):
        self.instance_url = None
        self.username = None
        self.password = None
        self.timeout = 30
        self.session = None
        self.logger = logging.getLogger(__name__)
        
    def initialize(self, app=None):
        """Initialize ServiceNow service with configuration from database first, then environment variables"""
        if app:
            try:
                # First, try to load configuration from database
                from models.servicenow_config import ServiceNowConfig
                
                self.logger.info("Loading ServiceNow configuration from database...")
                db_config = ServiceNowConfig.get_connection_config()
                
                if db_config and ServiceNowConfig.is_configured():
                    # Use database configuration
                    self.instance_url = db_config.get('instance_url')
                    self.username = db_config.get('username')
                    self.password = db_config.get('password')
                    self.timeout = db_config.get('timeout', 30)
                    self.assignment_groups = db_config.get('assignment_groups', [])
                    
                    self.logger.info("✅ ServiceNow configuration loaded from database")
                    self.logger.info(f"Instance: {self.instance_url}, Username: {self.username}, Password configured: {bool(self.password)}")
                    
                else:
                    # Fallback to secrets manager, then environment variables
                    self.logger.info("Database configuration not complete, trying secrets manager...")
                    
                    try:
                        from models.secrets_manager import HybridSecretsManager
                        from models.models import db
                        secrets_manager = HybridSecretsManager(db.session)
                        
                        if secrets_manager:
                            self.instance_url = secrets_manager.get_secret('SERVICENOW_INSTANCE')
                            self.username = secrets_manager.get_secret('SERVICENOW_USERNAME') 
                            self.password = secrets_manager.get_secret('SERVICENOW_PASSWORD')
                            self.timeout = int(secrets_manager.get_secret('SERVICENOW_TIMEOUT') or 30)
                            assignment_groups_str = secrets_manager.get_secret('SERVICENOW_ASSIGNMENT_GROUPS') or ''
                            
                            # Parse assignment groups from comma-separated string
                            if assignment_groups_str:
                                self.assignment_groups = [group.strip() for group in assignment_groups_str.split(',') if group.strip()]
                            else:
                                self.assignment_groups = []
                            
                            self.logger.info("✅ ServiceNow configuration loaded from secrets manager")
                            self.logger.info(f"Instance: {self.instance_url}, Username: {self.username}, Password configured: {bool(self.password)}")
                        else:
                            raise Exception("Secrets manager not available")
                            
                    except Exception as secrets_error:
                        # Final fallback to environment variables (Flask config)
                        self.logger.info(f"Secrets manager failed ({secrets_error}), falling back to environment variables...")
                        self.instance_url = app.config.get('SERVICENOW_INSTANCE')
                        self.username = app.config.get('SERVICENOW_USERNAME')
                        self.password = app.config.get('SERVICENOW_PASSWORD')
                        self.timeout = app.config.get('SERVICENOW_TIMEOUT', 30)
                        self.assignment_groups = app.config.get('SERVICENOW_ASSIGNMENT_GROUPS', '')
                        
                        # Parse assignment groups from comma-separated string
                        if self.assignment_groups:
                            self.assignment_groups = [group.strip() for group in self.assignment_groups.split(',') if group.strip()]
                        else:
                            self.assignment_groups = []  # Empty list means monitor all groups
                        
                        self.logger.info("📄 ServiceNow configuration loaded from environment variables")
                        self.logger.info(f"Instance: {self.instance_url}, Username: {self.username}, Password configured: {bool(self.password)}")
                    
            except Exception as e:
                # Fallback to secrets manager, then environment variables if database error
                self.logger.warning(f"Error loading database configuration: {str(e)}")
                
                try:
                    self.logger.info("Trying secrets manager as fallback...")
                    from config import get_secrets_manager
                    secrets_manager = get_secrets_manager()
                    
                    if secrets_manager:
                        self.instance_url = secrets_manager.get_secret('SERVICENOW_INSTANCE')
                        self.username = secrets_manager.get_secret('SERVICENOW_USERNAME') 
                        self.password = secrets_manager.get_secret('SERVICENOW_PASSWORD')
                        self.timeout = int(secrets_manager.get_secret('SERVICENOW_TIMEOUT') or 30)
                        assignment_groups_str = secrets_manager.get_secret('SERVICENOW_ASSIGNMENT_GROUPS') or ''
                        
                        # Parse assignment groups from comma-separated string
                        if assignment_groups_str:
                            self.assignment_groups = [group.strip() for group in assignment_groups_str.split(',') if group.strip()]
                        else:
                            self.assignment_groups = []
                        
                        self.logger.info("✅ ServiceNow configuration loaded from secrets manager (fallback)")
                        self.logger.info(f"Instance: {self.instance_url}, Username: {self.username}, Password configured: {bool(self.password)}")
                    else:
                        raise Exception("Secrets manager not available")
                        
                except Exception as secrets_error:
                    # Final fallback to environment variables
                    self.logger.warning(f"Secrets manager also failed ({secrets_error}), using environment variables")
                    self.instance_url = app.config.get('SERVICENOW_INSTANCE')
                    self.username = app.config.get('SERVICENOW_USERNAME')
                    self.password = app.config.get('SERVICENOW_PASSWORD')
                    self.timeout = app.config.get('SERVICENOW_TIMEOUT', 30)
                    self.assignment_groups = app.config.get('SERVICENOW_ASSIGNMENT_GROUPS', '')
                    
                    # Parse assignment groups from comma-separated string
                    if self.assignment_groups:
                        self.assignment_groups = [group.strip() for group in self.assignment_groups.split(',') if group.strip()]
                    else:
                        self.assignment_groups = []
            
            # Log final configuration status
            self.logger.info(f"Assignment Groups Filter: {self.assignment_groups if self.assignment_groups else 'ALL GROUPS'}")
            
            # Create session if properly configured
            if self.instance_url and self.username and self.password:
                # Ensure proper URL format
                if not self.instance_url.startswith('https://') and not self.instance_url.startswith('http://'):
                    self.instance_url = f"https://{self.instance_url}"
                    
                self._create_session()
                self.logger.info("✅ ServiceNow session created successfully")
            else:
                self.logger.warning(f"⚠️ ServiceNow configuration incomplete - Instance: {bool(self.instance_url)}, Username: {bool(self.username)}, Password: {bool(self.password)}")
    
    def is_enabled_and_configured(self) -> bool:
        """Check if ServiceNow integration is both enabled and configured"""
        try:
            from models.app_config import AppConfig
            from models.servicenow_config import ServiceNowConfig
            
            # Check feature toggle
            feature_enabled = AppConfig.is_enabled('feature_servicenow_integration')
            
            # Check configuration completeness
            config_complete = self.is_configured()
            
            return feature_enabled and config_complete
        except Exception as e:
            self.logger.error(f"Error checking ServiceNow enabled/configured status: {str(e)}")
            return False
                
    def _create_session(self):
        """Create authenticated session for ServiceNow API"""
        self.session = requests.Session()
        self.session.auth = (self.username, self.password)
        self.session.headers.update({
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
        
    def is_configured(self) -> bool:
        """Check if ServiceNow integration is properly configured"""
        return all([self.instance_url, self.username, self.password, self.session])
        
    def test_connection(self) -> Dict:
        """Test ServiceNow connection and authentication"""
        if not self.is_configured():
            return {
                'success': False,
                'error': "ServiceNow credentials not configured"
            }
            
        try:
            url = urljoin(self.instance_url, "/api/now/table/incident")
            params = {
                'sysparm_limit': 1,
                'sysparm_fields': 'sys_id,number'
            }
            
            response = self.session.get(url, params=params, timeout=self.timeout)
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'message': "Connection successful",
                    'status_code': response.status_code
                }
            elif response.status_code == 401:
                return {
                    'success': False,
                    'error': "Authentication failed - check credentials"
                }
            else:
                return {
                    'success': False,
                    'error': f"Connection failed with status {response.status_code}"
                }
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"ServiceNow connection test failed: {str(e)}")
            return {
                'success': False,
                'error': f"Connection error: {str(e)}"
            }
            
    def get_incidents_for_shift(self, 
                               service_groups: List[str], 
                               shift_start: datetime, 
                               shift_end: datetime,
                               include_closed: bool = True) -> List[Dict]:
        """
        Fetch incidents assigned to service groups during shift time
        
        Args:
            service_groups: List of service group names (overrides instance assignment_groups if provided)
            shift_start: Start time of the shift
            shift_end: End time of the shift
            include_closed: Whether to include closed incidents
            
        Returns:
            List of incident dictionaries
        """
        if not self.is_configured():
            self.logger.warning("ServiceNow not configured, returning empty list")
            return []
            
        try:
            # Build query for assignment group filtering
            query_parts = ["ORDERBYDESCsys_created_on"]
            
            # Use parameter assignment groups if provided, otherwise use instance variable
            assignment_groups_to_use = service_groups if service_groups else self.assignment_groups
            
            # Add assignment group filter if configured
            if assignment_groups_to_use:
                # Create query to filter by assignment group names
                group_filters = []
                for group in assignment_groups_to_use:
                    group_filters.append(f"assignment_group.name={group}")
                
                if group_filters:
                    assignment_query = "^OR".join(group_filters)
                    query_parts.insert(0, f"({assignment_query})")
                    
                self.logger.info(f"Filtering incidents by assignment groups: {assignment_groups_to_use}")
            else:
                self.logger.info("No assignment group filter - fetching incidents from all groups")
            
            # Add time filtering for shift window
            if shift_start and shift_end:
                # Format datetime for ServiceNow query
                start_str = self._format_servicenow_datetime(shift_start)
                end_str = self._format_servicenow_datetime(shift_end)
                
                # Add time filter (incidents created during shift)
                time_filter = f"sys_created_onBETWEENjavascript:gs.dateGenerate('{start_str}')@javascript:gs.dateGenerate('{end_str}')"
                query_parts.insert(-1, time_filter)  # Insert before ORDER BY
                
                self.logger.info(f"Filtering incidents by time window: {start_str} to {end_str}")
            else:
                self.logger.warning("No time filtering applied - shift_start or shift_end not provided")
            
            query = "^".join(query_parts) if len(query_parts) > 1 else query_parts[0]
            
            self.logger.info(f"Final ServiceNow query: {query}")
            
            # API parameters
            params = {
                'sysparm_query': query,
                'sysparm_fields': ','.join([
                    'sys_id', 'number', 'short_description', 'description',
                    'state', 'priority', 'urgency', 'impact', 'category',
                    'subcategory', 'assignment_group.name', 'assigned_to.name',
                    'caller_id.name', 'opened_by.name', 'sys_created_on',
                    'sys_updated_on', 'resolved_at', 'closed_at',
                    'close_notes', 'work_notes', 'comments'
                ]),
                'sysparm_limit': 50,  # Increased limit to account for filtering
                'sysparm_offset': 0
            }
            
            url = urljoin(self.instance_url, "/api/now/table/incident")
            response = self.session.get(url, params=params, timeout=self.timeout)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    incidents = data.get('result', [])
                    
                    # Transform incidents for our application
                    transformed_incidents = []
                    for incident in incidents:
                        transformed = self._transform_incident(incident)
                        transformed_incidents.append(transformed)
                    
                    self.logger.info(f"Fetched {len(transformed_incidents)} incidents from ServiceNow")
                except ValueError as json_error:
                    # Check if response contains hibernation page
                    if 'hibernating' in response.text.lower() or 'instance' in response.text.lower():
                        self.logger.warning("ServiceNow instance is hibernating")
                        return []
                    else:
                        self.logger.error(f"Invalid JSON response from ServiceNow: {json_error}")
                        return []
                return transformed_incidents
                
            else:
                self.logger.error(f"Failed to fetch incidents: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            self.logger.error(f"Error fetching ServiceNow incidents: {str(e)}")
            return []
            
    def get_incident_by_number(self, incident_number: str) -> Optional[Dict]:
        """Fetch a specific incident by its number"""
        if not self.is_configured():
            return None
            
        try:
            params = {
                'sysparm_query': f'number={incident_number}',
                'sysparm_fields': ','.join([
                    'sys_id', 'number', 'short_description', 'description',
                    'state', 'priority', 'urgency', 'impact', 'category',
                    'subcategory', 'assignment_group.name', 'assigned_to.name',
                    'caller_id.name', 'opened_by.name', 'sys_created_on',
                    'sys_updated_on', 'resolved_at', 'closed_at',
                    'close_notes', 'work_notes', 'comments'
                ])
            }
            
            url = urljoin(self.instance_url, "/api/now/table/incident")
            response = self.session.get(url, params=params, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                incidents = data.get('result', [])
                if incidents:
                    return self._transform_incident(incidents[0])
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error fetching incident {incident_number}: {str(e)}")
            return None
            
    def get_service_groups(self) -> List[str]:
        """Fetch available service groups from ServiceNow"""
        if not self.is_configured():
            return []
            
        try:
            params = {
                'sysparm_fields': 'name',
                'sysparm_query': 'active=true',
                'sysparm_limit': 500
            }
            
            url = urljoin(self.instance_url, "/api/now/table/sys_user_group")
            response = self.session.get(url, params=params, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                groups = data.get('result', [])
                return [group['name'] for group in groups if group.get('name')]
            
            return []
            
        except Exception as e:
            self.logger.error(f"Error fetching service groups: {str(e)}")
            return []
            
    def _transform_incident(self, incident: Dict) -> Dict:
        """Transform ServiceNow incident data to our application format"""
        # Map ServiceNow states to readable text
        state_mapping = {
            '1': 'New',
            '2': 'In Progress', 
            '3': 'On Hold',
            '6': 'Resolved',
            '7': 'Closed',
            '8': 'Cancelled'
        }
        
        # Map ServiceNow priorities
        priority_mapping = {
            '1': 'Critical',
            '2': 'High',
            '3': 'Medium',
            '4': 'Low',
            '5': 'Planning'
        }
        
        return {
            'sys_id': incident.get('sys_id', ''),
            'number': incident.get('number', ''),
            'title': incident.get('short_description', ''),
            'description': incident.get('description', ''),
            'state': state_mapping.get(incident.get('state', ''), incident.get('state', '')),
            'priority': priority_mapping.get(incident.get('priority', ''), incident.get('priority', '')),
            'urgency': incident.get('urgency', ''),
            'impact': incident.get('impact', ''),
            'category': incident.get('category', ''),
            'subcategory': incident.get('subcategory', ''),
            'assignment_group': incident.get('assignment_group', {}).get('name', '') if isinstance(incident.get('assignment_group'), dict) else incident.get('assignment_group', ''),
            'assigned_to': incident.get('assigned_to', {}).get('name', '') if isinstance(incident.get('assigned_to'), dict) else incident.get('assigned_to', ''),
            'caller': incident.get('caller_id', {}).get('name', '') if isinstance(incident.get('caller_id'), dict) else incident.get('caller_id', ''),
            'opened_by': incident.get('opened_by', {}).get('name', '') if isinstance(incident.get('opened_by'), dict) else incident.get('opened_by', ''),
            'created_on': self._parse_servicenow_datetime(incident.get('sys_created_on')),
            'updated_on': self._parse_servicenow_datetime(incident.get('sys_updated_on')),
            'resolved_at': self._parse_servicenow_datetime(incident.get('resolved_at')),
            'closed_at': self._parse_servicenow_datetime(incident.get('closed_at')),
            'close_notes': incident.get('close_notes', ''),
            'work_notes': incident.get('work_notes', ''),
            'comments': incident.get('comments', ''),
            'source': 'ServiceNow'
        }
        
    def _extract_display_value(self, field_value):
        """
        Extract display value from ServiceNow field that could be string or object
        
        Args:
            field_value: Field value that could be string, dict with display_value, or empty
            
        Returns:
            String display value or empty string
        """
        if not field_value:
            return ''
        
        # If it's already a string, return it
        if isinstance(field_value, str):
            return field_value
        
        # If it's a dict with display_value, extract it
        if isinstance(field_value, dict) and 'display_value' in field_value:
            return field_value['display_value']
        
        # Otherwise convert to string
        return str(field_value)

    def _format_servicenow_datetime(self, dt: datetime) -> str:
        """Format datetime for ServiceNow API query"""
        return dt.strftime('%Y-%m-%d %H:%M:%S')
        
    def _parse_servicenow_datetime(self, dt_string: str) -> Optional[datetime]:
        """Parse ServiceNow datetime string"""
        if not dt_string:
            return None
            
        try:
            # ServiceNow typically returns: "2023-10-08 10:30:00"
            return datetime.strptime(dt_string, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            try:
                # Try with ISO format: "2023-10-08T10:30:00Z"
                return datetime.fromisoformat(dt_string.replace('Z', '+00:00'))
            except ValueError:
                self.logger.warning(f"Could not parse datetime: {dt_string}")
                return None

    def get_shift_times(self, shift_type: str, date_str: str) -> Dict:
        """
        Calculate shift start and end times based on shift type and date
        
        Args:
            shift_type: 'Morning', 'Evening', or 'Night'
            date_str: Date string in format 'YYYY-MM-DD'
            
        Returns:
            Dict with 'start_time' and 'end_time' datetime objects
        """
        try:
            # Parse the date
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            # Define shift schedules
            shift_schedules = {
                'Morning': {'start_hour': 6, 'end_hour': 14},
                'Day': {'start_hour': 6, 'end_hour': 14},  # Alias for Morning
                'Evening': {'start_hour': 14, 'end_hour': 22},
                'Night': {'start_hour': 22, 'end_hour': 6}  # Crosses midnight
            }
            
            if shift_type not in shift_schedules:
                # Default to current time range
                now = datetime.now()
                start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
                end_time = now
                return {
                    'start_time': start_time,
                    'end_time': end_time
                }
            
            schedule = shift_schedules[shift_type]
            
            if shift_type == 'Night':
                # Night shift spans across two days (22:00 to 06:00 next day)
                start_time = datetime.combine(date, datetime.min.time().replace(hour=schedule['start_hour']))
                end_time = datetime.combine(date + timedelta(days=1), datetime.min.time().replace(hour=schedule['end_hour']))
            else:
                # Regular shifts within the same day
                start_time = datetime.combine(date, datetime.min.time().replace(hour=schedule['start_hour']))
                end_time = datetime.combine(date, datetime.min.time().replace(hour=schedule['end_hour']))
            
            return {
                'start_time': start_time,
                'end_time': end_time
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating shift times: {e}")
            # Return current day as fallback
            now = datetime.now()
            return {
                'start_time': now.replace(hour=0, minute=0, second=0, microsecond=0),
                'end_time': now
            }

    def get_shift_incidents(self, 
                          assignment_groups: List[str],
                          shift_start: datetime,
                          shift_end: datetime) -> Dict:
        """
        Get incidents for a specific shift period
        
        Returns both:
        - Incidents created during shift
        - Incidents assigned to groups that were active during shift
        """
        if not self.is_configured():
            return {
                'success': False,
                'error': 'ServiceNow not configured',
                'open_incidents': [],
                'closed_incidents': [],
                'total_incidents': []
            }
        
        try:
            # Get all incidents for the shift period
            all_incidents = self.get_incidents_for_shift(
                assignment_groups, shift_start, shift_end, include_closed=True
            )
            
            # Categorize incidents
            open_incidents = []
            closed_incidents = []
            
            for incident in all_incidents:
                # Get the state value - could be numeric string or text
                state = incident.get('state', '0')
                
                # Debug logging
                self.logger.info(f"Processing incident {incident.get('number', 'N/A')}: state='{state}', type={type(state)}")
                
                # Check if incident is open (states 1-3 or text equivalents)
                if (str(state) in ['1', '2', '3'] or 
                    str(state).lower() in ['new', 'in progress', 'on hold']):
                    open_incidents.append(incident)
                    self.logger.info(f"  -> Categorized as OPEN")
                # Check if incident is closed (states 6-8 or text equivalents)
                elif (str(state) in ['6', '7', '8'] or 
                      str(state).lower() in ['resolved', 'closed', 'cancelled']):
                    closed_incidents.append(incident)
                    self.logger.info(f"  -> Categorized as CLOSED")
                else:
                    # Default to open if state is unclear
                    open_incidents.append(incident)
                    self.logger.info(f"  -> Categorized as OPEN (default)")
            
            return {
                'success': True,
                'open_incidents': open_incidents,
                'closed_incidents': closed_incidents,
                'total_incidents': all_incidents,
                'summary': {
                    'total_count': len(all_incidents),
                    'open_count': len(open_incidents),
                    'closed_count': len(closed_incidents),
                    'shift_period': f"{shift_start.strftime('%Y-%m-%d %H:%M')} - {shift_end.strftime('%Y-%m-%d %H:%M')}"
                }
            }
        
        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"Failed to get shift incidents: {error_msg}")
            
            # Check for hibernation-related errors
            if 'Expecting value' in error_msg or 'JSON' in error_msg:
                hibernation_msg = 'ServiceNow instance appears to be hibernating. Please wake it up by visiting https://dev284357.service-now.com and try again.'
                return {
                    'success': False,
                    'error': hibernation_msg,
                    'open_incidents': [],
                    'closed_incidents': [],
                    'total_incidents': []
                }
            
            return {
                'success': False,
                'error': f'Failed to get shift incidents: {error_msg}',
                'open_incidents': [],
                'closed_incidents': [],
                'total_incidents': []
            }

    def get_configured_assignment_groups(self) -> List[str]:
        """Get the list of configured assignment groups"""
        return self.assignment_groups if hasattr(self, 'assignment_groups') else []
    
    def is_assignment_group_filtered(self) -> bool:
        """Check if assignment group filtering is enabled"""
        return bool(self.get_configured_assignment_groups())

    def get_assignment_groups(self, search_term: str = "") -> Dict:
        """Get list of assignment groups from ServiceNow"""
        if not self.is_configured():
            return {
                'success': False,
                'error': 'ServiceNow not configured',
                'groups': []
            }
        
        try:
            url = urljoin(self.instance_url, "/api/now/table/sys_user_group")
            params = {
                'sysparm_fields': 'sys_id,name,description,active',
                'sysparm_limit': 100,
                'sysparm_query': 'active=true'
            }
            
            if search_term:
                params['sysparm_query'] += f'^nameLIKE{search_term}^ORdescriptionLIKE{search_term}'
            
            response = self.session.get(url, params=params, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                groups = [
                    {
                        'sys_id': group['sys_id'],
                        'name': group['name'],
                        'description': group.get('description', ''),
                        'active': group.get('active', 'false') == 'true'
                    }
                    for group in data.get('result', [])
                ]
                
                return {
                    'success': True,
                    'groups': groups,
                    'count': len(groups)
                }
            else:
                return {
                    'success': False,
                    'error': f'Failed to fetch assignment groups: {response.status_code}',
                    'groups': []
                }
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to fetch assignment groups: {str(e)}")
            return {
                'success': False,
                'error': f'Failed to fetch assignment groups: {str(e)}',
                'groups': []
            }

    def get_change_requests_for_assignment_group(self, assignment_groups: List[str] = None, filters: Dict = None, page: int = 1, per_page: int = 10) -> Dict:
        """
        Fetch change requests and their tasks assigned to assignment groups with optional filtering
        
        Args:
            assignment_groups: List of assignment group names (defaults to configured groups)
            filters: Dict containing filter parameters (state, priority, risk, category, date ranges, search, etc.)
            
        Returns:
            Dict containing change requests, change tasks, and metadata
        """
        try:
            if not self.session:
                self.logger.error("ServiceNow session not established")
                return {'error': 'ServiceNow connection not available'}
            
            # Use provided assignment groups or fall back to configured ones
            if not assignment_groups:
                assignment_groups = self.assignment_groups
            
            if not assignment_groups:
                return {
                    'error': 'No assignment groups configured',
                    'change_requests': [],
                    'change_tasks': []
                }
            
            self.logger.info(f"Fetching changes for assignment groups: {assignment_groups}")
            print(f"DEBUG: ServiceNow method called with assignment groups: {assignment_groups}")
            
            # Build query for change requests assigned to assignment groups
            cr_query_params = []
            
            # Query for CRs where assignment_group contains our groups (more flexible)
            group_queries = []
            for group in assignment_groups:
                # Try exact match and partial matches
                group_queries.append(f"assignment_group.name={group}")
                group_queries.append(f"assignment_group.nameLIKE{group}")
                # Also try without the space and dash variations
                group_clean = group.replace(" - ", "-").replace(" ", "")
                if group_clean != group:
                    group_queries.append(f"assignment_group.name={group_clean}")
                    group_queries.append(f"assignment_group.nameLIKE{group_clean}")
            
            if group_queries:
                cr_query_params.append(f"({'^OR'.join(group_queries)})")
            
            # Also include CRs where approval is required from assignment groups
            approval_queries = []
            for group in assignment_groups:
                approval_queries.append(f"approval_group.name={group}")
                approval_queries.append(f"approval_group.nameLIKE{group}")
            
            if approval_queries:
                cr_query_params.append(f"({'^OR'.join(approval_queries)})")
            
            # Add some sample record searches for debugging
            cr_query_params.append("(numberLIKECHG)")  # Find any change starting with CHG
            
            # Apply simplified filters if provided
            if filters:
                filter_conditions = []
                
                # State filter
                if filters.get('state'):
                    filter_conditions.append(f"state={filters['state']}")
                
                # Start date filter
                if filters.get('start_date'):
                    filter_conditions.append(f"start_date>={filters['start_date']}")
                
                # End date filter  
                if filters.get('end_date'):
                    filter_conditions.append(f"end_date<={filters['end_date']}")
                
                # Add filter conditions to main query
                if filter_conditions:
                    cr_query_params.extend(filter_conditions)
                    self.logger.info(f"Applied simplified filters: {filter_conditions}")
            
            cr_query = "^".join(cr_query_params) if cr_query_params else ""
            
            # Fetch change requests (get all first, then apply pagination after filtering)
            cr_url = urljoin(self.instance_url, '/api/now/table/change_request')
            cr_params = {
                'sysparm_query': cr_query,
                'sysparm_fields': 'number,short_description,description,state,risk,impact,priority,category,assignment_group,assigned_to,requested_by,start_date,end_date,work_start,work_end,planned_start_date,planned_end_date,scheduled_start_time,scheduled_end_time,implementation_plan,backout_plan,test_plan,sys_created_on,sys_updated_on',
                'sysparm_limit': 200,  # Get more records to filter from
                'sysparm_display_value': 'true'  # Get display values for reference fields
            }
            
            self.logger.info(f"Fetching change requests with query: {cr_query}")
            cr_response = self.session.get(cr_url, params=cr_params, timeout=self.timeout)
            cr_response.raise_for_status()
            cr_data = cr_response.json()
            
            change_requests = []
            change_numbers = []
            
            for cr in cr_data.get('result', []):
                # Debug: Log first record to see structure
                if len(change_requests) == 0:
                    self.logger.info(f"Sample CR record structure: {cr}")
                    print(f"DEBUG: Sample CR keys: {list(cr.keys())}")
                    for key in ['planned_start_date', 'planned_end_date', 'start_date', 'end_date', 'work_start', 'work_end']:
                        if key in cr:
                            print(f"DEBUG: {key} = '{cr.get(key)}' (type: {type(cr.get(key))})")
                
                change_requests.append({
                    'number': cr.get('number', ''),
                    'short_description': cr.get('short_description', ''),
                    'description': cr.get('description', ''),
                    'state': cr.get('state', ''),
                    'risk': cr.get('risk', ''),
                    'impact': cr.get('impact', ''),
                    'priority': cr.get('priority', ''),
                    'category': cr.get('category', ''),
                    'assignment_group': self._extract_display_value(cr.get('assignment_group', '')),
                    'assigned_to': self._extract_display_value(cr.get('assigned_to', '')),
                    'requested_by': self._extract_display_value(cr.get('requested_by', '')),
                    'start_date': cr.get('start_date', ''),
                    'end_date': cr.get('end_date', ''),
                    'work_start': cr.get('work_start', ''),
                    'work_end': cr.get('work_end', ''),
                    'planned_start_date': cr.get('planned_start_date', ''),
                    'planned_end_date': cr.get('planned_end_date', ''),
                    'scheduled_start_time': cr.get('scheduled_start_time', ''),
                    'scheduled_end_time': cr.get('scheduled_end_time', ''),
                    'sys_created_on': cr.get('sys_created_on', ''),
                    'sys_updated_on': cr.get('sys_updated_on', '')
                })
                change_numbers.append(cr.get('number', ''))
            
            # Fetch change tasks for the assignment groups
            change_tasks = []
            
            # Build query for change tasks
            ct_query_params = []
            
            # Query for tasks assigned to assignment groups (more flexible)
            task_group_queries = []
            for group in assignment_groups:
                # Try exact match and partial matches
                task_group_queries.append(f"assignment_group.name={group}")
                task_group_queries.append(f"assignment_group.nameLIKE{group}")
                # Also try without the space and dash variations
                group_clean = group.replace(" - ", "-").replace(" ", "")
                if group_clean != group:
                    task_group_queries.append(f"assignment_group.name={group_clean}")
                    task_group_queries.append(f"assignment_group.nameLIKE{group_clean}")
            
            if task_group_queries:
                ct_query_params.append(f"({'^OR'.join(task_group_queries)})")
            
            # Also include tasks where approval is required from assignment groups
            task_approval_queries = []
            for group in assignment_groups:
                task_approval_queries.append(f"approval_group.name={group}")
                task_approval_queries.append(f"approval_group.nameLIKE{group}")
            
            if task_approval_queries:
                ct_query_params.append(f"({'^OR'.join(task_approval_queries)})")
            
            # If we have change requests, also get their related tasks
            if change_numbers:
                cr_task_query = "^OR".join([f"change_request.number={cr_num}" for cr_num in change_numbers])
                ct_query_params.append(f"({cr_task_query})")
            
            # Add some sample record searches for debugging
            ct_query_params.append("(numberLIKECTASK)")  # Find any task starting with CTASK
            
            ct_query = "^OR".join(ct_query_params) if ct_query_params else ""
            
            # Fetch change tasks
            ct_url = urljoin(self.instance_url, '/api/now/table/change_task')
            ct_params = {
                'sysparm_query': ct_query,
                'sysparm_fields': 'number,short_description,description,state,assignment_group,assigned_to,change_request,planned_start_date,planned_end_date,work_start,work_end,sys_created_on,sys_updated_on',
                'sysparm_limit': 200,
                'sysparm_display_value': 'true'  # Get display values for reference fields
            }
            
            self.logger.info(f"Fetching change tasks with query: {ct_query}")
            ct_response = self.session.get(ct_url, params=ct_params, timeout=self.timeout)
            ct_response.raise_for_status()
            ct_data = ct_response.json()
            
            for ct in ct_data.get('result', []):
                # Debug: Log first record to see structure
                if len(change_tasks) == 0:
                    self.logger.info(f"Sample CT record structure: {ct}")
                
                change_tasks.append({
                    'number': ct.get('number', ''),
                    'short_description': ct.get('short_description', ''),
                    'description': ct.get('description', ''),
                    'state': ct.get('state', ''),
                    'assignment_group': self._extract_display_value(ct.get('assignment_group', '')),
                    'assigned_to': self._extract_display_value(ct.get('assigned_to', '')),
                    'change_request': self._extract_display_value(ct.get('change_request', '')),
                    'planned_start_date': ct.get('planned_start_date', ''),
                    'planned_end_date': ct.get('planned_end_date', ''),
                    'work_start': ct.get('work_start', ''),
                    'work_end': ct.get('work_end', ''),
                    'created_on': ct.get('sys_created_on', ''),
                    'updated_on': ct.get('sys_updated_on', '')
                })
            
            self.logger.info(f"Fetched {len(change_requests)} change requests and {len(change_tasks)} change tasks")
            
            # STEP 2: Find additional change requests based on change tasks assigned to our groups
            additional_cr_numbers = set()
            
            for ct in change_tasks:
                ct_assignment_group = ct.get('assignment_group', '').strip()
                ct_change_request = ct.get('change_request', '').strip()
                ct_number = ct.get('number', '')
                
                # Check if this change task is assigned to one of our groups
                is_our_task = False
                for group in assignment_groups:
                    group_variations = [
                        group.lower(),
                        group.replace(" - ", "-").lower(),
                        group.replace(" ", "").lower(),
                        group.replace("-", " ").lower()
                    ]
                    
                    for variation in group_variations:
                        if ct_assignment_group.lower() == variation or variation in ct_assignment_group.lower():
                            is_our_task = True
                            if ct_change_request and ct_change_request not in ['', 'None', 'null']:
                                additional_cr_numbers.add(ct_change_request)
                                self.logger.info(f"🔗 Found CR {ct_change_request} via change task {ct_number} assigned to {ct_assignment_group}")
                            break
                    if is_our_task:
                        break
            
            # STEP 3: Mark existing CRs that were found through change tasks
            if additional_cr_numbers:
                # Check which of the additional CRs already exist in our list
                existing_cr_numbers = {cr.get('number', '') for cr in change_requests}
                new_cr_numbers = additional_cr_numbers - existing_cr_numbers
                existing_additional_cr_numbers = additional_cr_numbers & existing_cr_numbers
                
                # Mark existing CRs that were found via change tasks
                if existing_additional_cr_numbers:
                    for cr in change_requests:
                        if cr.get('number') in existing_additional_cr_numbers:
                            cr['source'] = 'via_change_task'
                            self.logger.info(f"🏷️ Marked CR {cr.get('number')} as via_change_task")
                
                # Fetch any truly new CRs
                if new_cr_numbers:
                    self.logger.info(f"🔍 Fetching {len(new_cr_numbers)} additional change requests: {list(new_cr_numbers)}")
                    
                    # Build query for additional CRs
                    additional_cr_query = "^OR".join([f"number={cr_num}" for cr_num in new_cr_numbers])
                    
                    additional_cr_params = {
                        'sysparm_query': additional_cr_query,
                        'sysparm_fields': 'number,short_description,description,state,risk,impact,priority,category,assignment_group,assigned_to,requested_by,start_date,end_date,work_start,work_end,planned_start_date,planned_end_date,scheduled_start_time,scheduled_end_time,implementation_plan,backout_plan,test_plan,sys_created_on,sys_updated_on',
                        'sysparm_limit': 100,
                        'sysparm_display_value': 'true'
                    }
                    
                    additional_cr_response = self.session.get(cr_url, params=additional_cr_params, timeout=self.timeout)
                    additional_cr_response.raise_for_status()
                    additional_cr_data = additional_cr_response.json()
                    
                    # Add the additional change requests
                    for cr in additional_cr_data.get('result', []):
                        change_requests.append({
                            'number': cr.get('number', ''),
                            'short_description': cr.get('short_description', ''),
                            'description': cr.get('description', ''),
                            'state': cr.get('state', ''),
                            'risk': cr.get('risk', ''),
                            'impact': cr.get('impact', ''),
                            'priority': cr.get('priority', ''),
                            'category': cr.get('category', ''),
                            'assignment_group': self._extract_display_value(cr.get('assignment_group', '')),
                            'assigned_to': self._extract_display_value(cr.get('assigned_to', '')),
                            'requested_by': self._extract_display_value(cr.get('requested_by', '')),
                            'start_date': cr.get('start_date', ''),
                            'end_date': cr.get('end_date', ''),
                            'work_start': cr.get('work_start', ''),
                            'work_end': cr.get('work_end', ''),
                            'planned_start_date': cr.get('planned_start_date', ''),
                            'planned_end_date': cr.get('planned_end_date', ''),
                            'scheduled_start_time': cr.get('scheduled_start_time', ''),
                            'scheduled_end_time': cr.get('scheduled_end_time', ''),
                            'sys_created_on': cr.get('sys_created_on', ''),
                            'sys_updated_on': cr.get('sys_updated_on', ''),
                            'source': 'via_change_task'  # Mark these for identification
                        })
                    
                    self.logger.info(f"✅ Added {len(additional_cr_data.get('result', []))} additional change requests")
            
            self.logger.info(f"📊 TOTAL AFTER EXPANSION: {len(change_requests)} change requests, {len(change_tasks)} change tasks")
            
            # Check what records we actually found
            self.logger.info("=== CHANGE REQUESTS DEBUG ===")
            for i, cr in enumerate(change_requests[:10]):  # Log first 10
                self.logger.info(f"CR {i+1}: {cr.get('number')} - Assignment Group: '{cr.get('assignment_group')}' - Description: {cr.get('short_description', '')[:50]}")
            
            self.logger.info("=== CHANGE TASKS DEBUG ===")
            for i, ct in enumerate(change_tasks[:10]):  # Log first 10
                self.logger.info(f"CT {i+1}: {ct.get('number')} - Assignment Group: '{ct.get('assignment_group')}' - Description: {ct.get('short_description', '')[:50]}")
            
            self.logger.info(f"� TOTAL FOUND: {len(change_requests)} change requests, {len(change_tasks)} change tasks")
            
            # NOW FILTER: More flexible assignment group matching
            filtered_change_requests = []
            filtered_change_tasks = []
            
            self.logger.info(f"🔍 FILTERING for assignment groups: {assignment_groups}")
            
            # Create variations of the target assignment group names for flexible matching
            target_groups = []
            for group in assignment_groups:
                target_groups.append(group.lower())  # lowercase
                target_groups.append(group.replace(" - ", "-").lower())  # remove spaces around dash
                target_groups.append(group.replace(" ", "").lower())  # remove all spaces
                target_groups.append(group.replace("-", " ").lower())  # replace dash with space
            
            self.logger.info(f"🔍 Target group variations: {target_groups}")
            
            # Apply assignment group filter from filters if provided
            assignment_group_filter = filters.get('assignment_group_filter') if filters else None
            
            for cr in change_requests:
                cr_assignment_group = cr.get('assignment_group', '').strip()
                cr_number = cr.get('number', '')
                cr_source = cr.get('source', '')
                
                # Apply assignment group filter first
                if assignment_group_filter:
                    if assignment_group_filter == 'via_task_only' and cr_source != 'via_change_task':
                        continue  # Skip if only showing via task CRs
                    elif assignment_group_filter == 'direct_only' and cr_source == 'via_change_task':
                        continue  # Skip if only showing direct CRs
                    elif assignment_group_filter not in ['via_task_only', 'direct_only', ''] and cr_assignment_group != assignment_group_filter:
                        continue  # Skip if specific group filter doesn't match
                
                # Always include CRs that were added via change tasks
                if cr_source == 'via_change_task':
                    should_include = True
                    self.logger.info(f"✅ INCLUDING CR {cr_number} - Added via change task")
                else:
                    # Check if assignment group matches any of our target variations
                    should_include = False
                    if cr_assignment_group:
                        cr_group_lower = cr_assignment_group.lower()
                        for target in target_groups:
                            if target in cr_group_lower or cr_group_lower in target:
                                should_include = True
                                break
                
                # Add to filtered list if should be included
                if should_include:
                    filtered_change_requests.append(cr)
                    self.logger.info(f"✅ INCLUDING CR {cr_number} - Assignment Group: '{cr_assignment_group}', Source: '{cr_source}'")
                else:
                    self.logger.debug(f"❌ EXCLUDING CR {cr_number} - Assignment Group: '{cr_assignment_group}', Source: '{cr_source}'")
            
            for ct in change_tasks:
                ct_assignment_group = ct.get('assignment_group', '').strip()
                ct_number = ct.get('number', '')
                
                # Check if assignment group matches any of our target variations
                should_include = False
                if ct_assignment_group:
                    ct_group_lower = ct_assignment_group.lower()
                    for target in target_groups:
                        if target in ct_group_lower or ct_group_lower in target:
                            should_include = True
                            break
                
                # Special handling for specific records to debug
                if ct_number in ['CTASK0010001'] or ct_number.startswith('CTASK'):
                    self.logger.info(f"🎯 SPECIAL CT: {ct_number} has assignment group: '{ct_assignment_group}'")
                    if should_include:
                        filtered_change_tasks.append(ct)
                        self.logger.info(f"✅ INCLUDING SPECIAL CT {ct_number}")
                elif should_include:
                    filtered_change_tasks.append(ct)
                    self.logger.info(f"✅ INCLUDING CT {ct.get('number')} - Assignment Group: '{ct_assignment_group}'")
                else:
                    self.logger.debug(f"❌ EXCLUDING CT {ct.get('number')} - Assignment Group: '{ct_assignment_group}'")
            
            self.logger.info(f"🎯 FINAL RESULTS: {len(filtered_change_requests)} change requests and {len(filtered_change_tasks)} change tasks for '{assignment_groups[0] if assignment_groups else 'Unknown'}'")
            
            print(f"DEBUG FINAL: Returning {len(filtered_change_requests)} CRs to route:")
            for i, cr in enumerate(filtered_change_requests):
                print(f"  {i+1}. {cr.get('number')} - Source: {cr.get('source', 'direct')}")
            
            # Apply pagination to the filtered results
            total_filtered_records = len(filtered_change_requests)
            total_pages = (total_filtered_records + per_page - 1) // per_page if total_filtered_records > 0 else 1
            start_index = (page - 1) * per_page
            end_index = start_index + per_page
            paginated_change_requests = filtered_change_requests[start_index:end_index]
            
            self.logger.info(f"📄 PAGINATION: Page {page} of {total_pages}, showing {len(paginated_change_requests)} of {total_filtered_records} total records")
            
            return {
                'change_requests': paginated_change_requests,
                'change_tasks': filtered_change_tasks,
                'total_crs': len(paginated_change_requests),
                'total_tasks': len(filtered_change_tasks),
                'assignment_groups': assignment_groups,
                'pagination': {
                    'current_page': page,
                    'per_page': per_page,
                    'total': total_filtered_records,
                    'total_pages': total_pages
                }
            }
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"ServiceNow API request failed: {str(e)}")
            return {
                'error': f'ServiceNow API request failed: {str(e)}',
                'change_requests': [],
                'change_tasks': []
            }
        except Exception as e:
            self.logger.error(f"Failed to fetch change requests: {str(e)}")
            return {
                'error': f'Failed to fetch change requests: {str(e)}',
                'change_requests': [],
                'change_tasks': []
            }

    def assign_change_task(self, ctask_number: str, assigned_to_email: str) -> Dict:
        """
        Assign a change task to a specific user in ServiceNow
        
        Args:
            ctask_number: Change task number (e.g., 'CTASK0010001')
            assigned_to_email: Email of the user to assign the task to
            
        Returns:
            Dict with assignment result
        """
        try:
            if not self.session:
                self.logger.error("ServiceNow session not established")
                return {'success': False, 'message': 'ServiceNow connection not available'}
            
            # First, get the sys_id of the change task
            ctask_url = urljoin(self.instance_url, '/api/now/table/change_task')
            ctask_params = {
                'sysparm_query': f'number={ctask_number}',
                'sysparm_fields': 'sys_id,number,short_description,assigned_to',
                'sysparm_display_value': 'false'  # Get actual sys_id values
            }
            
            self.logger.info(f"Looking up change task {ctask_number}")
            ctask_response = self.session.get(ctask_url, params=ctask_params, timeout=self.timeout)
            ctask_response.raise_for_status()
            ctask_data = ctask_response.json()
            
            if not ctask_data.get('result'):
                return {
                    'success': False,
                    'message': f'Change task {ctask_number} not found'
                }
            
            ctask_record = ctask_data['result'][0]
            ctask_sys_id = ctask_record['sys_id']
            
            # Next, find the user by email
            user_url = urljoin(self.instance_url, '/api/now/table/sys_user')
            user_params = {
                'sysparm_query': f'email={assigned_to_email}',
                'sysparm_fields': 'sys_id,name,email',
                'sysparm_display_value': 'false'
            }
            
            self.logger.info(f"Looking up user with email {assigned_to_email}")
            user_response = self.session.get(user_url, params=user_params, timeout=self.timeout)
            user_response.raise_for_status()
            user_data = user_response.json()
            
            if not user_data.get('result'):
                return {
                    'success': False,
                    'message': f'User with email {assigned_to_email} not found in ServiceNow'
                }
            
            user_record = user_data['result'][0]
            user_sys_id = user_record['sys_id']
            user_name = user_record['name']
            
            # Update the change task with the assigned user
            update_url = urljoin(self.instance_url, f'/api/now/table/change_task/{ctask_sys_id}')
            update_data = {
                'assigned_to': user_sys_id
            }
            
            self.logger.info(f"Assigning change task {ctask_number} to {user_name} ({assigned_to_email})")
            update_response = self.session.patch(update_url, json=update_data, timeout=self.timeout)
            update_response.raise_for_status()
            
            # Verify the assignment was successful
            updated_data = update_response.json()
            if 'result' in updated_data:
                self.logger.info(f"Successfully assigned {ctask_number} to {user_name}")
                return {
                    'success': True,
                    'message': f'Successfully assigned {ctask_number} to {user_name}',
                    'ctask_number': ctask_number,
                    'assigned_to': user_name,
                    'assigned_to_email': assigned_to_email
                }
            else:
                return {
                    'success': False,
                    'message': f'Assignment update failed for {ctask_number}'
                }
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"ServiceNow API request failed during assignment: {str(e)}")
            return {
                'success': False,
                'message': f'ServiceNow API request failed: {str(e)}'
            }
        except Exception as e:
            self.logger.error(f"Error assigning change task: {str(e)}")
            return {
                'success': False,
                'message': f'Error assigning change task: {str(e)}'
            }

    def get_unassigned_change_tasks(self, assignment_groups: List[str] = None) -> Dict:
        """
        Get change tasks assigned to assignment groups but not to specific users
        
        Args:
            assignment_groups: List of assignment group names
            
        Returns:
            Dict containing unassigned change tasks
        """
        try:
            if not self.session:
                self.logger.error("ServiceNow session not established")
                return {'error': 'ServiceNow connection not available', 'change_tasks': []}
            
            if not assignment_groups:
                assignment_groups = self.assignment_groups
            
            # Build query for unassigned change tasks
            ct_query_params = []
            
            # Query for tasks assigned to assignment groups but not to specific users
            group_queries = []
            for group in assignment_groups:
                group_queries.append(f"assignment_group.name={group}")
                group_queries.append(f"assignment_group.nameLIKE{group}")
            
            if group_queries:
                ct_query_params.append(f"({'^OR'.join(group_queries)})")
            
            # Add condition for unassigned tasks (no assigned_to user)
            ct_query_params.append("assigned_to=NULL")
            
            # Add condition for active states (not closed/cancelled)
            ct_query_params.append("state!=4^state!=7")  # 4=Closed, 7=Cancelled
            
            ct_query = "^".join(ct_query_params) if ct_query_params else ""
            
            # Fetch unassigned change tasks
            ct_url = urljoin(self.instance_url, '/api/now/table/change_task')
            ct_params = {
                'sysparm_query': ct_query,
                'sysparm_fields': 'sys_id,number,short_description,state,assignment_group,change_request,planned_start_date,planned_end_date,work_start,work_end',
                'sysparm_limit': 100,
                'sysparm_display_value': 'true'
            }
            
            self.logger.info(f"Fetching unassigned change tasks with query: {ct_query}")
            ct_response = self.session.get(ct_url, params=ct_params, timeout=self.timeout)
            ct_response.raise_for_status()
            ct_data = ct_response.json()
            
            change_tasks = []
            for ct in ct_data.get('result', []):
                change_tasks.append({
                    'sys_id': ct.get('sys_id', ''),
                    'number': ct.get('number', ''),
                    'short_description': ct.get('short_description', ''),
                    'state': ct.get('state', ''),
                    'assignment_group': self._extract_display_value(ct.get('assignment_group', '')),
                    'change_request': self._extract_display_value(ct.get('change_request', '')),
                    'planned_start_date': ct.get('planned_start_date', ''),
                    'planned_end_date': ct.get('planned_end_date', ''),
                    'work_start': ct.get('work_start', ''),
                    'work_end': ct.get('work_end', '')
                })
            
            self.logger.info(f"Found {len(change_tasks)} unassigned change tasks")
            return {
                'change_tasks': change_tasks,
                'total_tasks': len(change_tasks)
            }
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"ServiceNow API request failed: {str(e)}")
            return {
                'error': f'ServiceNow API request failed: {str(e)}',
                'change_tasks': []
            }
        except Exception as e:
            self.logger.error(f"Failed to fetch unassigned change tasks: {str(e)}")
            return {
                'error': f'Failed to fetch unassigned change tasks: {str(e)}',
                'change_tasks': []
            }

    def get_change_states(self) -> Dict[str, str]:
        """Get mapping of change request states"""
        return {
            '-5': 'New',
            '-4': 'Assessment',
            '-3': 'Authorized',
            '-2': 'Scheduled',
            '-1': 'Implementation',
            '0': 'Review',
            '3': 'Closed',
            '4': 'Cancelled'
        }

    def get_change_task_states(self) -> Dict[str, str]:
        """Get mapping of change task states"""
        return {
            '-5': 'Pending',
            '1': 'Open',
            '2': 'Work in Progress',
            '3': 'Closed Complete',
            '4': 'Closed Incomplete',
            '7': 'Closed Skipped'
        }


# Global ServiceNow service instance
servicenow_service = ServiceNowService()


def init_servicenow(app):
    """Initialize ServiceNow service with Flask app"""
    servicenow_service.initialize(app)
    return servicenow_service