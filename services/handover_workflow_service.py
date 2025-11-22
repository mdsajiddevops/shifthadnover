"""
Handover Workflow Service

A sophisticated workflow engine for managing incident handovers between shifts.
Implements state machine pattern for clean, scalable handover management.

Design Pattern: State Machine + Event-Driven Architecture
- States: N/A → Pending → Accepted/Rejected
- Events: initiate_handover, accept_incident, reject_incident
- Side Effects: Notifications, audit logging, metrics tracking
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from sqlalchemy import and_, or_
from models.models import (
    db, Incident, IncidentHandoverAction, HandoverNotification, 
    HandoverSummary, TeamMember, Shift
)
from services.audit_service import log_action
import logging

class HandoverWorkflowService:
    """
    Manages the complete incident handover workflow using state machine pattern.
    
    State Transitions:
    N/A → Pending (when incident is assigned to next shift)
    Pending → Accepted (incoming engineer accepts)
    Pending → Rejected (incoming engineer rejects with note)
    Accepted → Pending (if reassigned to different engineer)
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # State machine configuration
        self.valid_states = ['N/A', 'Pending', 'Accepted', 'Rejected']
        self.valid_transitions = {
            'N/A': ['Pending'],
            'Pending': ['Accepted', 'Rejected'],
            'Accepted': ['Pending'],  # Allow reassignment
            'Rejected': ['Pending']   # Allow re-handover after rejection
        }
        
        # Action types for audit trail
        self.action_types = {
            'initiate': 'initiated',
            'accept': 'accepted', 
            'reject': 'rejected',
            'reassign': 'reassigned',
            'escalate': 'escalated'
        }

    def initiate_handover(self, incident_id: int, assigned_to: str, assigned_to_id: int, 
                         initiated_by: str, account_id: int, team_id: int) -> Dict:
        """
        Initiate handover workflow for an incident.
        
        Args:
            incident_id: ID of incident to hand over
            assigned_to: Name of engineer to receive handover
            assigned_to_id: Team member ID of receiving engineer
            initiated_by: Name of engineer initiating handover
            account_id: Account context
            team_id: Team context
            
        Returns:
            Dict with success status and details
        """
        try:
            incident = Incident.query.get(incident_id)
            if not incident:
                return {'success': False, 'message': 'Incident not found'}
            
            # Validate state transition
            if not self._validate_transition(incident.handover_status or 'N/A', 'Pending'):
                return {
                    'success': False, 
                    'message': f'Invalid state transition from {incident.handover_status} to Pending'
                }
            
            # Update incident handover fields
            incident.handover_status = 'Pending'
            incident.handover_assigned_to = assigned_to
            incident.handover_assigned_to_id = assigned_to_id
            incident.handover_initiated_at = datetime.now()
            incident.handover_actioned_at = None  # Reset action timestamp
            incident.handover_actioned_by = None
            incident.handover_rejection_note = None
            
            # Create action record
            action = IncidentHandoverAction(
                incident_id=incident_id,
                action_type=self.action_types['initiate'],
                action_by=initiated_by,
                action_by_id=self._get_team_member_id_by_name(initiated_by),
                notes=f'Handover initiated to {assigned_to}',
                from_engineer=incident.assigned_to,
                to_engineer=assigned_to,
                account_id=account_id,
                team_id=team_id
            )
            
            db.session.add(action)
            db.session.commit()
            
            # Create notification
            self._create_notification(
                incident_id=incident_id,
                notification_type='pending_handover',
                recipient=assigned_to,
                recipient_id=assigned_to_id,
                account_id=account_id,
                team_id=team_id
            )
            
            # Log audit
            log_action(
                'Handover Initiated', 
                f'Incident {incident.title} handed over to {assigned_to}'
            )
            
            self.logger.info(f"Handover initiated for incident {incident_id} to {assigned_to}")
            
            return {
                'success': True,
                'message': f'Handover initiated successfully to {assigned_to}',
                'incident_id': incident_id,
                'assigned_to': assigned_to,
                'status': 'Pending'
            }
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Error initiating handover: {str(e)}")
            return {'success': False, 'message': f'Error initiating handover: {str(e)}'}

    def accept_incident(self, incident_id: int, accepted_by: str, notes: str = None,
                       account_id: int = None, team_id: int = None) -> Dict:
        """
        Accept an incident handover.
        
        Args:
            incident_id: ID of incident to accept
            accepted_by: Name of engineer accepting
            notes: Optional acceptance notes
            account_id: Account context
            team_id: Team context
            
        Returns:
            Dict with success status and details
        """
        try:
            incident = Incident.query.get(incident_id)
            if not incident:
                return {'success': False, 'message': 'Incident not found'}
            
            # Validate state transition
            if not self._validate_transition(incident.handover_status, 'Accepted'):
                return {
                    'success': False,
                    'message': f'Cannot accept incident with status {incident.handover_status}'
                }
            
            # Validate assignment
            if incident.handover_assigned_to != accepted_by:
                return {
                    'success': False,
                    'message': f'Incident is assigned to {incident.handover_assigned_to}, not {accepted_by}'
                }
            
            # Update incident
            incident.handover_status = 'Accepted'
            incident.handover_actioned_at = datetime.now()
            incident.handover_actioned_by = accepted_by
            incident.assigned_to = accepted_by  # Transfer ownership
            
            # Create action record
            action = IncidentHandoverAction(
                incident_id=incident_id,
                action_type=self.action_types['accept'],
                action_by=accepted_by,
                action_by_id=incident.handover_assigned_to_id,
                notes=notes or 'Incident accepted',
                to_engineer=accepted_by,
                account_id=account_id or incident.account_id,
                team_id=team_id or incident.team_id
            )
            
            db.session.add(action)
            db.session.commit()
            
            # Log audit
            log_action(
                'Handover Accepted',
                f'Incident {incident.title} accepted by {accepted_by}'
            )
            
            self.logger.info(f"Incident {incident_id} accepted by {accepted_by}")
            
            return {
                'success': True,
                'message': f'Incident accepted successfully by {accepted_by}',
                'incident_id': incident_id,
                'accepted_by': accepted_by,
                'status': 'Accepted'
            }
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Error accepting incident: {str(e)}")
            return {'success': False, 'message': f'Error accepting incident: {str(e)}'}

    def reject_incident(self, incident_id: int, rejected_by: str, rejection_note: str,
                       account_id: int = None, team_id: int = None) -> Dict:
        """
        Reject an incident handover with mandatory rejection note.
        
        Args:
            incident_id: ID of incident to reject
            rejected_by: Name of engineer rejecting
            rejection_note: Mandatory rejection explanation
            account_id: Account context
            team_id: Team context
            
        Returns:
            Dict with success status and details
        """
        try:
            if not rejection_note or not rejection_note.strip():
                return {'success': False, 'message': 'Rejection note is mandatory'}
            
            incident = Incident.query.get(incident_id)
            if not incident:
                return {'success': False, 'message': 'Incident not found'}
            
            # Validate state transition
            if not self._validate_transition(incident.handover_status, 'Rejected'):
                return {
                    'success': False,
                    'message': f'Cannot reject incident with status {incident.handover_status}'
                }
            
            # Validate assignment
            if incident.handover_assigned_to != rejected_by:
                return {
                    'success': False,
                    'message': f'Incident is assigned to {incident.handover_assigned_to}, not {rejected_by}'
                }
            
            # Update incident
            incident.handover_status = 'Rejected'
            incident.handover_actioned_at = datetime.now()
            incident.handover_actioned_by = rejected_by
            incident.handover_rejection_note = rejection_note
            # Keep assignment with original engineer
            
            # Create action record
            action = IncidentHandoverAction(
                incident_id=incident_id,
                action_type=self.action_types['reject'],
                action_by=rejected_by,
                action_by_id=incident.handover_assigned_to_id,
                notes=rejection_note,
                from_engineer=rejected_by,
                account_id=account_id or incident.account_id,
                team_id=team_id or incident.team_id
            )
            
            db.session.add(action)
            db.session.commit()
            
            # Log audit
            log_action(
                'Handover Rejected',
                f'Incident {incident.title} rejected by {rejected_by}: {rejection_note}'
            )
            
            self.logger.info(f"Incident {incident_id} rejected by {rejected_by}")
            
            return {
                'success': True,
                'message': f'Incident rejected by {rejected_by}',
                'incident_id': incident_id,
                'rejected_by': rejected_by,
                'rejection_note': rejection_note,
                'status': 'Rejected'
            }
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Error rejecting incident: {str(e)}")
            return {'success': False, 'message': f'Error rejecting incident: {str(e)}'}

    def get_pending_handovers(self, engineer_name: str = None, account_id: int = None, 
                            team_id: int = None) -> List[Dict]:
        """
        Get all pending handovers for an engineer or team.
        
        Args:
            engineer_name: Name of engineer (if None, gets all pending)
            account_id: Account filter
            team_id: Team filter
            
        Returns:
            List of pending handover dictionaries
        """
        try:
            query = Incident.query.filter_by(handover_status='Pending')
            
            if engineer_name:
                query = query.filter_by(handover_assigned_to=engineer_name)
            
            if account_id:
                query = query.filter_by(account_id=account_id)
                
            if team_id:
                query = query.filter_by(team_id=team_id)
            
            incidents = query.order_by(Incident.handover_initiated_at.desc()).all()
            
            pending_handovers = []
            for incident in incidents:
                # Calculate time pending
                time_pending = None
                if incident.handover_initiated_at:
                    time_pending = datetime.now() - incident.handover_initiated_at
                
                handover_data = {
                    'incident_id': incident.id,
                    'title': incident.title,
                    'description': incident.description,
                    'priority': incident.priority,
                    'status': incident.status,
                    'type': incident.type,
                    'handover_assigned_to': incident.handover_assigned_to,
                    'handover_initiated_at': incident.handover_initiated_at,
                    'time_pending_minutes': int(time_pending.total_seconds() / 60) if time_pending else 0,
                    'assigned_to_original': incident.assigned_to,
                    'shift_id': incident.shift_id
                }
                pending_handovers.append(handover_data)
            
            return pending_handovers
            
        except Exception as e:
            self.logger.error(f"Error getting pending handovers: {str(e)}")
            return []

    def get_handover_summary(self, shift_id: int = None, account_id: int = None, 
                           team_id: int = None) -> Dict:
        """
        Get handover statistics for reporting.
        
        Args:
            shift_id: Specific shift ID
            account_id: Account filter
            team_id: Team filter
            
        Returns:
            Dict with handover statistics
        """
        try:
            query = Incident.query.filter(Incident.handover_status.in_(['Pending', 'Accepted', 'Rejected']))
            
            if shift_id:
                query = query.filter_by(shift_id=shift_id)
            if account_id:
                query = query.filter_by(account_id=account_id)
            if team_id:
                query = query.filter_by(team_id=team_id)
            
            incidents = query.all()
            
            total_handovers = len(incidents)
            pending_count = len([i for i in incidents if i.handover_status == 'Pending'])
            accepted_count = len([i for i in incidents if i.handover_status == 'Accepted'])
            rejected_count = len([i for i in incidents if i.handover_status == 'Rejected'])
            
            # Calculate average response time for completed handovers
            completed_handovers = [i for i in incidents if i.handover_status in ['Accepted', 'Rejected'] 
                                 and i.handover_initiated_at and i.handover_actioned_at]
            
            avg_response_time = None
            if completed_handovers:
                total_response_time = sum([
                    (i.handover_actioned_at - i.handover_initiated_at).total_seconds() / 60
                    for i in completed_handovers
                ])
                avg_response_time = total_response_time / len(completed_handovers)
            
            return {
                'total_handovers': total_handovers,
                'pending_count': pending_count,
                'accepted_count': accepted_count,
                'rejected_count': rejected_count,
                'acceptance_rate': (accepted_count / total_handovers * 100) if total_handovers > 0 else 0,
                'rejection_rate': (rejected_count / total_handovers * 100) if total_handovers > 0 else 0,
                'avg_response_time_minutes': round(avg_response_time, 2) if avg_response_time else None
            }
            
        except Exception as e:
            self.logger.error(f"Error getting handover summary: {str(e)}")
            return {}

    def _validate_transition(self, current_state: str, new_state: str) -> bool:
        """Validate if state transition is allowed."""
        if current_state not in self.valid_states or new_state not in self.valid_states:
            return False
        return new_state in self.valid_transitions.get(current_state, [])

    def _create_notification(self, incident_id: int, notification_type: str,
                           recipient: str, recipient_id: int, account_id: int, team_id: int):
        """Create a handover notification record."""
        try:
            notification = HandoverNotification(
                incident_id=incident_id,
                notification_type=notification_type,
                recipient=recipient,
                recipient_id=recipient_id,
                account_id=account_id,
                team_id=team_id,
                email_sent=False,  # Will be updated by notification service
                in_app_notification=True
            )
            db.session.add(notification)
            # Don't commit here - let the calling method handle commit
            
        except Exception as e:
            self.logger.error(f"Error creating notification: {str(e)}")

    def _get_team_member_id_by_name(self, name: str) -> Optional[int]:
        """Get team member ID by name."""
        try:
            member = TeamMember.query.filter_by(name=name).first()
            return member.id if member else None
        except Exception:
            return None

    def get_handover_history(self, incident_id: int) -> List[Dict]:
        """Get complete handover history for an incident."""
        try:
            actions = IncidentHandoverAction.query.filter_by(incident_id=incident_id)\
                .order_by(IncidentHandoverAction.action_at.desc()).all()
            
            history = []
            for action in actions:
                history.append({
                    'action_type': action.action_type,
                    'action_by': action.action_by,
                    'action_at': action.action_at,
                    'notes': action.notes,
                    'from_engineer': action.from_engineer,
                    'to_engineer': action.to_engineer
                })
            
            return history
            
        except Exception as e:
            self.logger.error(f"Error getting handover history: {str(e)}")
            return []