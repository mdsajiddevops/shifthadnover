"""
Enhanced Handover Workflow Service
Handles the complete handover workflow with incident assignments
"""

from models.models import db, User, TeamMember
from models.handover_enhanced import (
    HandoverRequest, IncidentAssignment, IncidentAssignmentResponse,
    HandoverResponse, HandoverNotification, HandoverAuditLog
)
from services.email_service import send_handover_email
from datetime import datetime, timedelta
from flask import current_app
from flask_login import current_user
import json
from typing import List, Dict, Optional


class HandoverWorkflowService:
    """Service to manage the enhanced handover workflow"""
    
    def __init__(self):
        pass
    
    def create_handover_request(self, 
                               shift_date: str,
                               current_shift_type: str,
                               next_shift_type: str,
                               general_notes: str,
                               shift_summary: str,
                               incidents_data: List[Dict],
                               account_id: int,
                               team_id: int) -> HandoverRequest:
        """
        Create a new handover request with incident assignments
        
        Args:
            shift_date: Date of the shift
            current_shift_type: Current shift type (Morning/Evening/Night)
            next_shift_type: Next shift type
            general_notes: General handover notes
            shift_summary: Summary of the shift
            incidents_data: List of incidents with assignment data
            account_id: Account ID
            team_id: Team ID
            
        Returns:
            Created HandoverRequest object
        """
        try:
            # Create the main handover request
            handover_request = HandoverRequest(
                shift_date=datetime.strptime(shift_date, '%Y-%m-%d').date(),
                current_shift_type=current_shift_type,
                next_shift_type=next_shift_type,
                created_by_id=current_user.id,
                general_notes=general_notes,
                shift_summary=shift_summary,
                account_id=account_id,
                team_id=team_id,
                expires_at=datetime.utcnow() + timedelta(hours=24)  # Expire after 24 hours
            )
            
            db.session.add(handover_request)
            db.session.flush()  # Get the ID
            
            # Create incident assignments
            for incident_data in incidents_data:
                if incident_data.get('assigned_to_id'):
                    incident_assignment = IncidentAssignment(
                        handover_request_id=handover_request.id,
                        incident_id=incident_data['incident_id'],
                        incident_title=incident_data['incident_title'],
                        incident_description=incident_data.get('incident_description', ''),
                        incident_priority=incident_data['incident_priority'],
                        incident_status=incident_data['incident_status'],
                        incident_url=incident_data.get('incident_url', ''),
                        assigned_to_id=incident_data['assigned_to_id'],
                        assigned_by_id=current_user.id,
                        assignment_notes=incident_data.get('assignment_notes', ''),
                        handover_context=incident_data.get('handover_context', ''),
                        account_id=account_id,
                        team_id=team_id
                    )
                    db.session.add(incident_assignment)
            
            db.session.commit()
            
            # Log the action
            self._log_audit_action(
                handover_request_id=handover_request.id,
                action_type='handover_created',
                description=f'Handover request created for {current_shift_type} to {next_shift_type} shift',
                details={
                    'shift_date': shift_date,
                    'incidents_count': len(incidents_data),
                    'assigned_incidents': len([i for i in incidents_data if i.get('assigned_to_id')])
                },
                account_id=account_id,
                team_id=team_id
            )
            
            return handover_request
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating handover request: {str(e)}")
            raise
    
    def submit_handover_request(self, handover_request_id: int, incident_assignments=None, submitter_id=None) -> dict:
        """
        Submit handover request and send notifications to assigned engineers
        
        Args:
            handover_request_id: ID of the handover request
            incident_assignments: List of incident assignment data from frontend
            submitter_id: ID of the user submitting the handover
            
        Returns:
            Dictionary with success status and details
        """
        try:
            handover_request = HandoverRequest.query.get(handover_request_id)
            if not handover_request:
                raise ValueError("Handover request not found")
            
            # Update status
            handover_request.status = 'pending'
            handover_request.submitted_at = datetime.utcnow()
            
            assignments_created = []
            
            # Process incident assignments if provided
            if incident_assignments:
                for assignment_data in incident_assignments:
                    if assignment_data.get('assigned_to_id'):
                        # Create incident assignment
                        incident_assignment = IncidentAssignment(
                            handover_request_id=handover_request_id,
                            incident_description=assignment_data.get('incident_description', ''),
                            priority=assignment_data.get('priority', 'Medium'),
                            notes=assignment_data.get('notes', ''),
                            assigned_to_id=assignment_data['assigned_to_id'],
                            assigned_at=datetime.utcnow(),
                            status='pending',
                            account_id=handover_request.account_id,
                            team_id=handover_request.team_id
                        )
                        db.session.add(incident_assignment)
                        db.session.flush()  # To get the ID
                        assignments_created.append(incident_assignment)
                        
                        # Create notification for the assigned engineer
                        self._create_notification(
                            recipient_id=assignment_data['assigned_to_id'],
                            handover_request_id=handover_request.id,
                            notification_type='incident_assignment',
                            title=f'New Incident Assignment from {current_user.display_name}',
                            message=f'You have been assigned: {assignment_data.get("incident_description", "Incident")}',
                            action_url=f'/assignment/response/{incident_assignment.id}',
                            action_text='Accept/Reject',
                            account_id=handover_request.account_id,
                            team_id=handover_request.team_id
                        )
            
            # Get all assigned engineers for summary notification
            assigned_engineers = set()
            for assignment in handover_request.incident_assignments:
                if assignment.assigned_to_id:
                    assigned_engineers.add(assignment.assigned_to_id)
            
            # Add any new assignments
            for assignment in assignments_created:
                assigned_engineers.add(assignment.assigned_to_id)
            
            db.session.commit()
            
            # Log the action
            self._log_audit_action(
                handover_request_id=handover_request.id,
                action_type='handover_submitted',
                description=f'Handover request submitted to {len(assigned_engineers)} engineers with {len(assignments_created)} new assignments',
                details={
                    'assigned_engineers': list(assigned_engineers),
                    'new_assignments': len(assignments_created),
                    'total_assignments': len(handover_request.incident_assignments) + len(assignments_created)
                },
                account_id=handover_request.account_id,
                team_id=handover_request.team_id
            )
            
            return {
                'success': True,
                'message': f'Handover submitted successfully to {len(assigned_engineers)} engineers',
                'assignments': [{'id': a.id, 'description': a.incident_description} for a in assignments_created],
                'notifications_sent': len(assigned_engineers)
            }
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error submitting handover request: {str(e)}")
            return False
    
    def respond_to_incident_assignment(self,
                                     incident_assignment_id: int,
                                     status: str,
                                     response_comments: str = '',
                                     estimated_completion_time: Optional[datetime] = None) -> bool:
        """
        Engineer responds to incident assignment
        
        Args:
            incident_assignment_id: ID of the incident assignment
            status: accepted, rejected, needs_clarification
            response_comments: Comments from the engineer
            estimated_completion_time: When they expect to complete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            incident_assignment = IncidentAssignment.query.get(incident_assignment_id)
            if not incident_assignment:
                raise ValueError("Incident assignment not found")
            
            # Create response
            response = IncidentAssignmentResponse(
                incident_assignment_id=incident_assignment_id,
                responder_id=current_user.id,
                status=status,
                comments=response_comments,  # Fixed: changed from response_comments to comments
                estimated_completion_time=estimated_completion_time,
                account_id=incident_assignment.account_id,
                team_id=incident_assignment.team_id
            )
            db.session.add(response)
            
            # Update assignment status
            incident_assignment.assignment_status = status
            incident_assignment.responded_at = datetime.utcnow()
            
            # Send notification to the original requester
            self._create_notification(
                recipient_id=incident_assignment.assigned_by_id,
                handover_request_id=incident_assignment.handover_request_id,
                notification_type='incident_' + status,
                title=f'Incident Assignment {status.title()}',
                message=f'{current_user.display_name} has {status} the assignment for incident {incident_assignment.incident_id}',
                action_url=f'/handover/view/{incident_assignment.handover_request_id}',
                action_text='View Details',
                account_id=incident_assignment.account_id,
                team_id=incident_assignment.team_id
            )
            
            db.session.commit()
            
            # Update the handover incident response log table for admin reports
            from models.handover_enhanced import HandoverIncidentResponseLog
            existing_log = HandoverIncidentResponseLog.query.filter_by(
                incident_assignment_id=incident_assignment_id
            ).first()
            
            if existing_log:
                # Update the existing log entry with response information
                existing_log.assignment_status = status
                existing_log.response_status = status
                existing_log.response_comments = response_comments
                existing_log.responded_at = datetime.utcnow()
                existing_log.response_datetime = datetime.utcnow()
                existing_log.incident_assignment_response_id = response.id
                existing_log.accepted_by_id = current_user.id
                existing_log.accepted_by_name = current_user.username
                # Note: accepted_by_email field doesn't exist in model - removed
                
                db.session.commit()
                current_app.logger.info(f"Updated handover incident response log for assignment {incident_assignment_id}")
            else:
                current_app.logger.warning(f"No existing handover incident response log found for assignment {incident_assignment_id}")
            
            # Log the action
            self._log_audit_action(
                handover_request_id=incident_assignment.handover_request_id,
                incident_assignment_id=incident_assignment_id,
                action_type='incident_response_submitted',
                description=f'Incident assignment {status} for {incident_assignment.incident_id}',
                details={
                    'incident_id': incident_assignment.incident_id,
                    'status': status,
                    'has_comments': bool(response_comments),
                    'estimated_completion': estimated_completion_time.isoformat() if estimated_completion_time else None
                },
                account_id=incident_assignment.account_id,
                team_id=incident_assignment.team_id
            )
            
            # Check if all incidents are responded and update handover status
            self._update_handover_status(incident_assignment.handover_request_id)
            
            return True
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error responding to incident assignment: {str(e)}")
            return False
    
    def respond_to_handover_request(self,
                                  handover_request_id: int,
                                  status: str,
                                  response_comments: str = '',
                                  available_from: Optional[datetime] = None,
                                  available_until: Optional[datetime] = None) -> bool:
        """
        Overall response to handover request
        
        Args:
            handover_request_id: ID of the handover request
            status: accepted, rejected, partial
            response_comments: General comments
            available_from: When engineer is available from
            available_until: When engineer is available until
            
        Returns:
            True if successful, False otherwise
        """
        try:
            handover_request = HandoverRequest.query.get(handover_request_id)
            if not handover_request:
                raise ValueError("Handover request not found")
            
            # Create handover response
            handover_response = HandoverResponse(
                handover_request_id=handover_request_id,
                responder_id=current_user.id,
                status=status,
                response_comments=response_comments,
                available_from=available_from,
                available_until=available_until,
                account_id=handover_request.account_id,
                team_id=handover_request.team_id
            )
            db.session.add(handover_response)
            
            # Send notification to requester
            self._create_notification(
                recipient_id=handover_request.created_by_id,
                handover_request_id=handover_request_id,
                notification_type='handover_' + status,
                title=f'Handover Response: {status.title()}',
                message=f'{current_user.display_name} has {status} your handover request',
                action_url=f'/handover/view/{handover_request_id}',
                action_text='View Response',
                account_id=handover_request.account_id,
                team_id=handover_request.team_id
            )
            
            db.session.commit()
            
            # Log the action
            self._log_audit_action(
                handover_request_id=handover_request_id,
                action_type='handover_response_submitted',
                description=f'Handover request {status}',
                details={
                    'status': status,
                    'has_comments': bool(response_comments),
                    'availability_specified': bool(available_from or available_until)
                },
                account_id=handover_request.account_id,
                team_id=handover_request.team_id
            )
            
            # Update overall handover status
            self._update_handover_status(handover_request_id)
            
            return True
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error responding to handover request: {str(e)}")
            return False
    
    def complete_handover(self, handover_request_id: int, send_team_email: bool = True) -> bool:
        """
        Mark handover as complete and send team notification
        
        Args:
            handover_request_id: ID of the handover request
            send_team_email: Whether to send email notification to team
            
        Returns:
            True if successful, False otherwise
        """
        try:
            handover_request = HandoverRequest.query.get(handover_request_id)
            if not handover_request:
                raise ValueError("Handover request not found")
            
            # Update status
            handover_request.status = 'fully_accepted'
            
            # Send team email if requested
            if send_team_email:
                self._send_team_completion_email(handover_request)
            
            # Create notifications for all team members
            team_members = User.query.filter_by(
                team_id=handover_request.team_id,
                is_active=True
            ).all()
            
            for member in team_members:
                if member.id != current_user.id:  # Don't notify the person completing
                    self._create_notification(
                        recipient_id=member.id,
                        handover_request_id=handover_request_id,
                        notification_type='handover_completed',
                        title='Handover Completed',
                        message=f'Handover for {handover_request.shift_date} has been completed',
                        action_url=f'/handover/view/{handover_request_id}',
                        action_text='View Details',
                        account_id=handover_request.account_id,
                        team_id=handover_request.team_id
                    )
            
            db.session.commit()
            
            # Log the action
            self._log_audit_action(
                handover_request_id=handover_request_id,
                action_type='handover_completed',
                description='Handover request marked as completed',
                details={'team_email_sent': send_team_email},
                account_id=handover_request.account_id,
                team_id=handover_request.team_id
            )
            
            return True
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error completing handover: {str(e)}")
            return False
    
    def get_user_notifications(self, user_id: int, limit: int = 20, unread_only: bool = False) -> List[HandoverNotification]:
        """
        Get notifications for a user
        
        Args:
            user_id: User ID
            limit: Maximum number of notifications
            unread_only: Whether to return only unread notifications
            
        Returns:
            List of notifications
        """
        query = HandoverNotification.query.filter_by(recipient_id=user_id)
        
        if unread_only:
            query = query.filter_by(is_read=False)
        
        query = query.filter(
            db.or_(
                HandoverNotification.expires_at.is_(None),
                HandoverNotification.expires_at > datetime.utcnow()
            )
        )
        
        return query.order_by(HandoverNotification.created_at.desc()).limit(limit).all()
    
    def get_pending_assignments(self, user_id: int) -> List[IncidentAssignment]:
        """
        Get pending incident assignments for a user
        
        Args:
            user_id: User ID
            
        Returns:
            List of pending assignments
        """
        return IncidentAssignment.query.filter_by(
            assigned_to_id=user_id,
            assignment_status='pending'
        ).join(HandoverRequest).filter(
            HandoverRequest.status.in_(['pending', 'partially_accepted'])
        ).all()
    
    def _update_handover_status(self, handover_request_id: int):
        """Update handover status based on responses"""
        handover_request = HandoverRequest.query.get(handover_request_id)
        if not handover_request:
            return
        
        # Count incident responses
        total_assignments = len(handover_request.incident_assignments)
        accepted_assignments = len([
            a for a in handover_request.incident_assignments 
            if a.assignment_status == 'accepted'
        ])
        rejected_assignments = len([
            a for a in handover_request.incident_assignments 
            if a.assignment_status == 'rejected'
        ])
        
        # Update status based on responses
        if total_assignments > 0:
            if accepted_assignments == total_assignments:
                handover_request.status = 'fully_accepted'
            elif accepted_assignments > 0:
                handover_request.status = 'partially_accepted'
            elif rejected_assignments == total_assignments:
                handover_request.status = 'rejected'
    
    def _create_notification(self, **kwargs):
        """Helper to create notifications"""
        notification = HandoverNotification(**kwargs)
        db.session.add(notification)
    
    def _log_audit_action(self, **kwargs):
        """Helper to log audit actions"""
        audit_log = HandoverAuditLog(
            performed_by_id=current_user.id,
            performed_at=datetime.utcnow(),
            **kwargs
        )
        db.session.add(audit_log)
    
    def _send_team_completion_email(self, handover_request: HandoverRequest):
        """Send completion email to team"""
        try:
            # Get team email addresses
            team_members = User.query.filter_by(
                team_id=handover_request.team_id,
                is_active=True
            ).all()
            
            team_emails = [member.email for member in team_members if member.email]
            
            if team_emails:
                subject = f"Handover Completed - {handover_request.shift_date}"
                
                # Prepare email content
                accepted_incidents = [
                    a for a in handover_request.incident_assignments 
                    if a.assignment_status == 'accepted'
                ]
                
                email_content = f"""
                Handover Summary for {handover_request.shift_date}
                
                From: {handover_request.current_shift_type} shift
                To: {handover_request.next_shift_type} shift
                
                Status: Completed
                
                Incidents Assigned: {len(accepted_incidents)}
                
                General Notes: {handover_request.general_notes or 'None'}
                
                Shift Summary: {handover_request.shift_summary or 'None'}
                """
                
                # Send email using the existing email service
                send_handover_email(
                    to_emails=team_emails,
                    subject=subject,
                    content=email_content,
                    handover_data={
                        'date': handover_request.shift_date.isoformat(),
                        'from_shift': handover_request.current_shift_type,
                        'to_shift': handover_request.next_shift_type,
                        'incidents': len(accepted_incidents)
                    }
                )
                
                # Log email sent
                self._log_audit_action(
                    handover_request_id=handover_request.id,
                    action_type='email_sent',
                    description=f'Team completion email sent to {len(team_emails)} recipients',
                    details={'recipients': team_emails},
                    account_id=handover_request.account_id,
                    team_id=handover_request.team_id
                )
                
        except Exception as e:
            current_app.logger.error(f"Error sending team completion email: {str(e)}")


class NotificationService:
    """Service for managing notifications"""
    
    @staticmethod
    def get_unread_count(user_id: int) -> int:
        """Get count of unread notifications for user"""
        return HandoverNotification.query.filter_by(
            recipient_id=user_id,
            is_read=False
        ).filter(
            db.or_(
                HandoverNotification.expires_at.is_(None),
                HandoverNotification.expires_at > datetime.utcnow()
            )
        ).count()
    
    @staticmethod
    def mark_as_read(notification_id: int, user_id: int) -> bool:
        """Mark notification as read"""
        try:
            notification = HandoverNotification.query.filter_by(
                id=notification_id,
                recipient_id=user_id
            ).first()
            
            if notification:
                notification.mark_as_read()
                return True
            return False
            
        except Exception as e:
            current_app.logger.error(f"Error marking notification as read: {str(e)}")
            return False