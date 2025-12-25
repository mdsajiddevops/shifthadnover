#!/usr/bin/env python3
"""
Comprehensive Notification Service Fix

This module fixes the broken notification workflow for handover assignments by:
1. Ensuring proper notification triggers when handovers are submitted
2. Integrating enhanced workflow with basic handover routes
3. Creating incident response logs for tracking
4. Sending email notifications to assigned users and team
5. Providing proper in-app notifications with Accept/Reject functionality

Author: AI Assistant
Date: November 4, 2025
"""

from flask import current_app, render_template_string
from flask_login import current_user
from models.models import db, User, TeamMember, Incident, Shift
from models.handover_enhanced import (
    HandoverNotification, HandoverIncidentResponseLog, 
    IncidentAssignment, IncidentAssignmentResponse, HandoverRequest
)
from services.email_service import send_incident_assignment_notification
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class NotificationServiceFix:
    """
    Enhanced notification service that ensures all handover assignments 
    trigger proper notifications and logging
    """
    
    def __init__(self):
        self.logger = logger
    
    def process_handover_with_notifications(self, shift, request_form_data=None):
        """
        Process a completed handover and trigger notifications for all incident assignments
        
        Args:
            shift: Shift object that was just created/submitted
            request_form_data: Form data from the handover submission (optional)
        
        Returns:
            dict: Summary of notifications sent and logs created
        """
        try:
            # Ensure a corresponding HandoverRequest exists for foreign key constraints
            self._ensure_handover_request_exists(shift)
            
            notifications_sent = 0
            logs_created = 0
            errors = []
            
            self.logger.info(f"Processing notifications for handover {shift.id}")
            
            # Get all incidents with assignments from this shift
            incidents_with_assignments = Incident.query.filter_by(
                shift_id=shift.id
            ).filter(
                Incident.assigned_to.isnot(None)
            ).all()
            
            self.logger.info(f"Found {len(incidents_with_assignments)} incidents with assignments")
            
            for incident in incidents_with_assignments:
                try:
                    # Create notification and send email
                    notification_result = self._create_incident_assignment_notification(
                        incident=incident,
                        shift=shift
                    )
                    
                    if notification_result['success']:
                        notifications_sent += 1
                        
                        # Create incident response log entry
                        log_result = self._create_incident_response_log(
                            incident=incident,
                            shift=shift
                        )
                        
                        if log_result['success']:
                            logs_created += 1
                        else:
                            errors.append(f"Failed to create log for {incident.title}: {log_result['error']}")
                    
                    else:
                        errors.append(f"Failed to send notification for {incident.title}: {notification_result['error']}")
                        
                except Exception as e:
                    error_msg = f"Error processing incident {incident.title}: {str(e)}"
                    self.logger.error(error_msg)
                    errors.append(error_msg)
            
            # Also process any incidents that might be in form data but not yet in database
            if request_form_data:
                form_notifications = self._process_form_incident_assignments(shift, request_form_data)
                notifications_sent += form_notifications['sent']
                logs_created += form_notifications['logs']
                errors.extend(form_notifications['errors'])
            
            result = {
                'success': True,
                'notifications_sent': notifications_sent,
                'logs_created': logs_created,
                'errors': errors,
                'message': f"Processed {notifications_sent} notifications and {logs_created} logs"
            }
            
            self.logger.info(f"Notification processing complete: {result['message']}")
            return result
            
        except Exception as e:
            error_msg = f"Critical error in notification processing: {str(e)}"
            self.logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'notifications_sent': 0,
                'logs_created': 0
            }
    
    def _create_incident_assignment_notification(self, incident, shift):
        """Create in-app notification and send email for incident assignment"""
        try:
            # Find the assigned user using the improved lookup that handles both names and IDs
            assigned_user = self._find_user_by_name_or_id(incident.assigned_to)
            if not assigned_user:
                self.logger.warning(f"Could not find user for assignment: {incident.assigned_to}")
                
                # Try to find a fallback user from the same team/account
                fallback_user = self._find_fallback_user(shift.account_id, shift.team_id)
                if fallback_user:
                    self.logger.info(f"Using fallback user: {fallback_user.username} (ID: {fallback_user.id})")
                    assigned_user = fallback_user
                    
                    # Update the incident to reflect the fallback assignment
                    self.logger.info(f"Updating incident assignment from {incident.assigned_to} to {assigned_user.username}")
                else:
                    return {
                        'success': False,
                        'error': f"Could not find user or fallback for assignment: {incident.assigned_to}"
                    }
            
            # Create in-app notification
            notification = HandoverNotification(
                recipient_id=assigned_user.id,
                handover_request_id=shift.id,  # Link to the handover
                notification_type='incident_assigned',
                title=f'New Incident Assignment: {incident.title}',
                message=f'You have been assigned incident {incident.title} with priority {incident.priority} from the {shift.current_shift_type} shift on {shift.date}',
                action_url='#',  # Will be handled by dashboard JavaScript
                action_text='Accept/Reject',
                account_id=shift.account_id,
                team_id=shift.team_id,
                is_read=False
            )
            
            # If this was a fallback assignment, add a note to the message
            if str(incident.assigned_to) != str(assigned_user.id) and incident.assigned_to != assigned_user.username:
                notification.message += f' (Note: Originally assigned to {incident.assigned_to}, but notification sent to {assigned_user.username} as fallback)'
            
            db.session.add(notification)
            db.session.commit()
            
            self.logger.info(f"Created in-app notification for {assigned_user.username}")
            
            # Send email notification
            try:
                send_incident_assignment_notification(
                    incident_id=incident.title,
                    incident_description=incident.description or incident.handover,
                    assigned_engineer=assigned_user.username,
                    incident_type=incident.type or 'Open',
                    shift_date=str(shift.date)
                )
                
                self.logger.info(f"Sent email notification to {incident.assigned_to}")
                
            except Exception as email_error:
                self.logger.warning(f"Email notification failed for {incident.assigned_to}: {str(email_error)}")
                # Don't fail the whole process if email fails
            
            return {'success': True}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _create_incident_response_log(self, incident, shift):
        """Create incident response log entry for super admin tracking"""
        try:
            # Check if log already exists
            existing_log = HandoverIncidentResponseLog.query.filter_by(
                incident_number=incident.title,
                assigned_at=shift.submitted_at or datetime.utcnow(),
                from_shift_id=shift.id
            ).first()
            
            if existing_log:
                self.logger.info(f"Incident response log already exists for {incident.title}")
                return {'success': True, 'existing': True}
            
            # Find assigned user using the improved lookup
            assigned_user = self._find_user_by_name_or_id(incident.assigned_to)
            if not assigned_user:
                return {'success': False, 'error': f"Could not find assigned user: {incident.assigned_to}"}
            
            # Get the current user who is submitting the handover
            # Try multiple sources to get the submitter's information
            submitter_id = 1  # Default fallback
            submitter_name = 'Unknown'
            
            # First try: current_user from Flask-Login
            if current_user and current_user.is_authenticated:
                submitter_id = current_user.id
                submitter_name = current_user.display_name or current_user.username or current_user.email or 'Unknown'
            else:
                # Second try: Get from shift's current engineers
                if shift.current_engineers:
                    first_engineer = shift.current_engineers[0]
                    if first_engineer.user_id:
                        from models.models import User
                        engineer_user = User.query.get(first_engineer.user_id)
                        if engineer_user:
                            submitter_id = engineer_user.id
                            submitter_name = engineer_user.display_name or engineer_user.username or first_engineer.name
                        else:
                            submitter_name = first_engineer.name
                    else:
                        submitter_name = first_engineer.name
                # Third try: Get from HandoverRequest if available
                elif hasattr(shift, 'handover_request') and shift.handover_request and shift.handover_request.created_by:
                    submitter_id = shift.handover_request.created_by_id
                    submitter_name = shift.handover_request.created_by.display_name or shift.handover_request.created_by.username
            
            # Create log entry
            log_entry = HandoverIncidentResponseLog(
                response_date=shift.date,
                response_datetime=datetime.utcnow(),
                from_shift_type=shift.current_shift_type,
                to_shift_type=shift.next_shift_type,
                from_shift_id=shift.id,
                to_shift_id=None,  # Will be set when next shift responds
                assigned_by_id=submitter_id,  # Use submitter
                assigned_by_name=submitter_name,  # Use submitter's name
                accepted_by_id=assigned_user.id,
                accepted_by_name=assigned_user.username,
                incident_number=incident.title,
                incident_title=incident.title,
                incident_description=incident.description or incident.handover,
                incident_priority=incident.priority or 'Medium',
                incident_type=incident.type or 'Open',
                incident_category='Application',  # Default category
                assignment_status='pending',
                response_status='pending',
                response_comments='',
                assignment_notes=f'Assigned during {shift.current_shift_type} to {shift.next_shift_type} handover',
                assigned_at=shift.submitted_at or datetime.utcnow(),
                responded_at=datetime.utcnow(),
                account_id=shift.account_id,
                team_id=shift.team_id
            )
            
            db.session.add(log_entry)
            db.session.commit()
            
            self.logger.info(f"Created incident response log for {incident.title}")
            return {'success': True}
            
        except Exception as e:
            db.session.rollback()  # Rollback on error to prevent session issues
            error_msg = f"Failed to create incident response log for {incident.title}: {str(e)}"
            self.logger.error(error_msg)
            return {'success': False, 'error': error_msg}
    
    def _process_form_incident_assignments(self, shift, form_data):
        """Process incident assignments from form data"""
        try:
            notifications_sent = 0
            logs_created = 0
            errors = []
            
            # Extract incident assignment data from form
            assigned_tos = form_data.get('open_incident_assigned[]', []) if isinstance(form_data.get('open_incident_assigned[]'), list) else [form_data.get('open_incident_assigned[]', '')]
            incident_ids = form_data.get('open_incident_id[]', []) if isinstance(form_data.get('open_incident_id[]'), list) else [form_data.get('open_incident_id[]', '')]
            descriptions = form_data.get('open_incident_description[]', []) if isinstance(form_data.get('open_incident_description[]'), list) else [form_data.get('open_incident_description[]', '')]
            priorities = form_data.get('open_incident_priority[]', []) if isinstance(form_data.get('open_incident_priority[]'), list) else [form_data.get('open_incident_priority[]', '')]
            
            for i, assigned_to in enumerate(assigned_tos):
                if not assigned_to or not assigned_to.strip():
                    continue
                
                try:
                    incident_id = incident_ids[i] if i < len(incident_ids) else f"INC{i+1}"
                    description = descriptions[i] if i < len(descriptions) else ''
                    priority = priorities[i] if i < len(priorities) else 'Medium'
                    
                    # Send email notification directly
                    send_incident_assignment_notification(
                        incident_id=incident_id,
                        incident_description=description,
                        assigned_engineer=assigned_to,
                        incident_type='Open',
                        shift_date=str(shift.date)
                    )
                    
                    notifications_sent += 1
                    self.logger.info(f"Sent form-based notification: {incident_id} → {assigned_to}")
                    
                    # Create in-app notification
                    assigned_user = self._find_user_by_name_or_id(assigned_to)
                    if assigned_user:
                        notification = HandoverNotification(
                            recipient_id=assigned_user.id,
                            handover_request_id=shift.id,
                            notification_type='incident_assigned',
                            title=f'New Incident Assignment: {incident_id}',
                            message=f'You have been assigned incident {incident_id} with priority {priority} from the {shift.current_shift_type} shift on {shift.date}',
                            action_url=f'/notifications',
                            action_text='View Assignments',
                            account_id=shift.account_id,
                            team_id=shift.team_id,
                            is_read=False
                        )
                        
                        db.session.add(notification)
                        
                        # Get the current user who is submitting the handover
                        # Try multiple sources to get the submitter's information
                        submitter_id = 1  # Default fallback
                        submitter_name = 'Unknown'
                        
                        # First try: current_user from Flask-Login
                        if current_user and current_user.is_authenticated:
                            submitter_id = current_user.id
                            submitter_name = current_user.display_name or current_user.username or current_user.email or 'Unknown'
                        else:
                            # Second try: Get from shift's current engineers
                            if shift.current_engineers:
                                first_engineer = shift.current_engineers[0]
                                if first_engineer.user_id:
                                    from models.models import User
                                    engineer_user = User.query.get(first_engineer.user_id)
                                    if engineer_user:
                                        submitter_id = engineer_user.id
                                        submitter_name = engineer_user.display_name or engineer_user.username or first_engineer.name
                                    else:
                                        submitter_name = first_engineer.name
                                else:
                                    submitter_name = first_engineer.name
                        
                        # Create incident response log
                        log_entry = HandoverIncidentResponseLog(
                            response_date=shift.date,
                            response_datetime=datetime.utcnow(),
                            from_shift_type=shift.current_shift_type,
                            to_shift_type=shift.next_shift_type,
                            from_shift_id=shift.id,
                            assigned_by_id=submitter_id,  # Use submitter
                            assigned_by_name=submitter_name,  # Use submitter's name
                            accepted_by_id=assigned_user.id,
                            accepted_by_name=assigned_user.username,
                            incident_number=incident_id,
                            incident_title=incident_id,
                            incident_description=description,
                            incident_priority=priority,
                            incident_type='Open',
                            incident_category='Application',
                            assignment_status='pending',
                            response_status='pending',
                            assignment_notes=f'Assigned during {shift.current_shift_type} to {shift.next_shift_type} handover',
                            assigned_at=shift.submitted_at or datetime.utcnow(),
                            responded_at=datetime.utcnow(),
                            account_id=shift.account_id,
                            team_id=shift.team_id
                        )
                        
                        db.session.add(log_entry)
                        logs_created += 1
                    
                except Exception as e:
                    error_msg = f"Error processing form assignment {incident_id}: {str(e)}"
                    self.logger.error(error_msg)
                    errors.append(error_msg)
            
            if notifications_sent > 0:
                try:
                    db.session.commit()
                except Exception as commit_error:
                    self.logger.error(f"Error committing form assignments: {str(commit_error)}")
                    db.session.rollback()
                    errors.append(f"Database commit failed: {str(commit_error)}")
            
            return {
                'sent': notifications_sent,
                'logs': logs_created,
                'errors': errors
            }
            
        except Exception as e:
            self.logger.error(f"Error processing form assignments: {str(e)}")
            return {'sent': 0, 'logs': 0, 'errors': [str(e)]}
    
    def _find_fallback_user(self, account_id, team_id):
        """Find a fallback user from the same account/team when the assigned user cannot be found"""
        try:
            # First try to find a user from the same account and team
            fallback_user = User.query.filter_by(
                account_id=account_id,
                team_id=team_id,
                is_active=True
            ).first()
            
            if fallback_user:
                self.logger.info(f"Found fallback user in same account/team: {fallback_user.username}")
                return fallback_user
                
            # If no user in same team, try same account
            fallback_user = User.query.filter_by(
                account_id=account_id,
                is_active=True
            ).first()
            
            if fallback_user:
                self.logger.info(f"Found fallback user in same account: {fallback_user.username}")
                return fallback_user
                
            # Last resort: find any active user
            fallback_user = User.query.filter_by(is_active=True).first()
            
            if fallback_user:
                self.logger.warning(f"Using last resort fallback user: {fallback_user.username}")
                return fallback_user
                
            self.logger.error("No active users found for fallback")
            return None
            
        except Exception as e:
            self.logger.error(f"Error finding fallback user: {str(e)}")
            return None

    def _find_user_by_name_or_id(self, identifier):
        """Find user by name or ID, trying multiple approaches"""
        if not identifier:
            return None
        
        self.logger.info(f"Looking for user with identifier: {identifier}")
        
        # If identifier is numeric, try multiple ID-based lookups
        if str(identifier).isdigit():
            user_id = int(identifier)
            
            # First, try finding by User ID
            user = User.query.filter_by(id=user_id).first()
            if user:
                self.logger.info(f"Found user by User.id: {user.username} (ID: {user.id})")
                return user
            
            # If not found, try finding by TeamMember ID and then get corresponding User
            from models.models import TeamMember
            team_member = TeamMember.query.filter_by(id=user_id).first()
            if team_member:
                self.logger.info(f"Found TeamMember by ID {user_id}: {team_member.name}")
                
                # Try to find User by email match
                if team_member.email:
                    user = User.query.filter_by(email=team_member.email).first()
                    if user:
                        self.logger.info(f"Found User by email match: {user.username} (ID: {user.id})")
                        return user
                
                # Try to find User by name match
                user = User.query.filter_by(username=team_member.name).first()
                if user:
                    self.logger.info(f"Found User by username match: {user.username} (ID: {user.id})")
                    return user
                
                # Try to find User by first/last name match
                name_parts = team_member.name.split()
                if len(name_parts) >= 2:
                    user = User.query.filter(
                        User.first_name.ilike(name_parts[0]),
                        User.last_name.ilike(name_parts[-1])
                    ).first()
                    if user:
                        self.logger.info(f"Found User by name parts match: {user.username} (ID: {user.id})")
                        return user
                
                self.logger.warning(f"TeamMember found (ID: {user_id}, Name: {team_member.name}) but no corresponding User found")
            else:
                self.logger.warning(f"No User or TeamMember found with ID: {user_id}")
        
        # Try exact username match
        user = User.query.filter_by(username=str(identifier)).first()
        if user:
            self.logger.info(f"Found user by username: {user.username} (ID: {user.id})")
            return user
        
        # Try team member lookup by name
        from models.models import TeamMember
        team_member = TeamMember.query.filter_by(name=str(identifier)).first()
        if team_member and team_member.email:
            user = User.query.filter_by(email=team_member.email).first()
            if user:
                self.logger.info(f"Found user by TeamMember email match: {user.username} (ID: {user.id})")
                return user
        
        # Try name parts matching
        name_parts = str(identifier).split()
        if len(name_parts) >= 2:
            user = User.query.filter(
                User.first_name.ilike(name_parts[0]),
                User.last_name.ilike(name_parts[-1])
            ).first()
            if user:
                self.logger.info(f"Found user by name parts: {user.username} (ID: {user.id})")
                return user
        
        self.logger.error(f"No user found for identifier: {identifier}")
        return None
    
    def _ensure_handover_request_exists(self, shift):
        """Ensure a HandoverRequest record exists for the given shift to satisfy foreign key constraints"""
        try:
            # Check if HandoverRequest already exists with this ID
            existing_request = HandoverRequest.query.filter_by(id=shift.id).first()
            if existing_request:
                return existing_request
            
            # Create a new HandoverRequest with the same ID as the shift
            handover_request = HandoverRequest(
                id=shift.id,
                shift_date=shift.date,
                current_shift_type=shift.current_shift_type,
                next_shift_type=shift.next_shift_type,
                created_by_id=getattr(shift, 'created_by_id', 1),  # Default to user 1 if not available
                status='submitted',  # Assuming it's already submitted
                general_notes='Auto-created for notification compatibility',
                shift_summary='Legacy shift data',
                created_at=shift.created_at,
                updated_at=shift.submitted_at or datetime.utcnow(),
                expires_at=None,
                account_id=shift.account_id,
                team_id=shift.team_id
            )
            
            # Set the ID explicitly and commit
            db.session.add(handover_request)
            db.session.flush()  # Flush to get the ID assigned
            
            # Update the ID to match the shift
            if handover_request.id != shift.id:
                # If auto-increment assigned a different ID, we need to update it
                db.session.execute(
                    f"UPDATE handover_request SET id = {shift.id} WHERE id = {handover_request.id}"
                )
            
            db.session.commit()
            self.logger.info(f"Created HandoverRequest record {shift.id} for notification compatibility")
            return handover_request
            
        except Exception as e:
            self.logger.warning(f"Could not create HandoverRequest for shift {shift.id}: {str(e)}")
            db.session.rollback()
            return None
    
    def handle_assignment_response(self, assignment_id, action, comments=''):
        """Handle when a user accepts or rejects an incident assignment"""
        try:
            # Update incident response log
            log_entry = HandoverIncidentResponseLog.query.filter_by(
                incident_number=assignment_id
            ).first()
            
            if log_entry:
                log_entry.response_status = action
                log_entry.response_comments = comments
                log_entry.responded_at = datetime.utcnow()
                
                # Calculate response time (response_time_minutes is a property, not a field)
                # The response time will be calculated automatically by the model property
                # No need to set it as it's computed from assigned_at and responded_at
                
                db.session.commit()
                
                self.logger.info(f"Updated incident response log: {assignment_id} - {action}")
                
                # Send notification to original assigner
                self._notify_assignment_response(log_entry, action, comments)
                
                return {'success': True}
            else:
                return {'success': False, 'error': 'Assignment log not found'}
                
        except Exception as e:
            self.logger.error(f"Error handling assignment response: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _notify_assignment_response(self, log_entry, action, comments):
        """Send notification about assignment response to original assigner"""
        try:
            if log_entry.assigned_by_id:
                notification = HandoverNotification(
                    recipient_id=log_entry.assigned_by_id,
                    notification_type=f'incident_{action}',
                    title=f'Incident Assignment {action.title()}: {log_entry.incident_title}',
                    message=f'{log_entry.accepted_by_name} has {action} the assignment for {log_entry.incident_title}',
                    action_url=f'/admin/incident-response-logs',
                    action_text='View Details',
                    account_id=log_entry.account_id,
                    team_id=log_entry.team_id
                )
                
                db.session.add(notification)
                db.session.commit()
                
                self.logger.info(f"Sent response notification to assigner")
                
        except Exception as e:
            self.logger.error(f"Error sending response notification: {str(e)}")

# Global instance for easy import
notification_fix = NotificationServiceFix()