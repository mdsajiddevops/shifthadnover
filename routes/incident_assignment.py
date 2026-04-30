"""
Incident Assignment API Routes
Handles accept/reject functionality for incident assignments in the main handover form
"""

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime
from models.models import db, Incident, TeamMember
from models.handover_enhanced import IncidentAssignment, IncidentAssignmentResponse
from services.handover_enhanced_service import HandoverWorkflowService
from services.email_service import send_handover_email
import json
import logging


# Module logger
logger = logging.getLogger(__name__)
incident_assignment_bp = Blueprint('incident_assignment', __name__)

@incident_assignment_bp.route('/api/get_pending_assignments', methods=['GET'])
@login_required
def get_pending_assignments():
    """Get pending incident assignments for the current user"""
    try:
        logger.debug(f"[DEBUG] get_pending_assignments called for user ID: {current_user.id}")
        
        # Get pending assignments from enhanced handover system
        pending_assignments = IncidentAssignment.query.filter_by(
            assigned_to_id=current_user.id,
            assignment_status='pending'
        ).all()
        
        logger.debug(f"[DEBUG] Found {len(pending_assignments)} pending assignments for user {current_user.id}")
        for assignment in pending_assignments:
            logger.debug(f"[DEBUG] Assignment: {assignment.incident_id} - {assignment.incident_title}")
        
        # Also check legacy incidents assigned to user by name
        team_member = TeamMember.query.filter_by(user_id=current_user.id).first()
        legacy_incidents = []
        if team_member:
            legacy_incidents = Incident.query.filter_by(
                assigned_to=team_member.name,
                status='Active'
            ).filter(Incident.type.in_(['Open', 'Priority'])).all()
        
        logger.debug(f"[DEBUG] Found {len(legacy_incidents)} legacy incidents for user {current_user.id}")
        
        assignments_data = []
        
        # Process enhanced assignments
        for assignment in pending_assignments:
            assignments_data.append({
                'id': assignment.id,
                'type': 'enhanced',
                'incident_id': assignment.incident_id,
                'incident_title': assignment.incident_title,
                'incident_description': assignment.incident_description,
                'incident_priority': assignment.incident_priority,
                'assignment_notes': assignment.assignment_notes,
                'handover_context': assignment.handover_context,
                'assigned_by': assignment.assigned_by.display_name if assignment.assigned_by else 'Unknown',
                'created_at': assignment.assigned_at.strftime('%Y-%m-%d %H:%M:%S') if assignment.assigned_at else 'Unknown',
                'can_respond': True
            })
        
        # Process legacy incidents
        for incident in legacy_incidents:
            assignments_data.append({
                'id': incident.id,
                'type': 'legacy',
                'incident_id': incident.title,
                'incident_title': incident.title,
                'incident_description': incident.description or incident.handover or '',
                'incident_priority': incident.priority,
                'assignment_notes': '',
                'handover_context': incident.handover or '',
                'assigned_by': 'Previous Shift',
                'created_at': 'Legacy Assignment',
                'can_respond': False  # Legacy incidents can't be responded to through this system
            })
        
        return jsonify({
            'success': True,
            'assignments': assignments_data,
            'total_count': len(assignments_data),
            'pending_count': len([a for a in assignments_data if a['can_respond']])
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting pending assignments: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'assignments': []
        })

@incident_assignment_bp.route('/api/respond_to_assignment', methods=['POST'])
@login_required
def respond_to_assignment():
    """Accept or reject an incident assignment"""
    try:
        data = request.get_json()
        assignment_id = data.get('assignment_id')
        response_status = data.get('status')  # 'accepted', 'rejected', 'needs_clarification'
        response_comments = data.get('comments', '')
        estimated_completion = data.get('estimated_completion')
        
        if not assignment_id or not response_status:
            return jsonify({'success': False, 'error': 'Missing required fields'})
        
        if response_status not in ['accepted', 'rejected', 'needs_clarification']:
            return jsonify({'success': False, 'error': 'Invalid response status'})
        
        # Parse estimated completion time if provided
        estimated_completion_time = None
        if estimated_completion:
            try:
                estimated_completion_time = datetime.fromisoformat(estimated_completion.replace('Z', '+00:00'))
            except ValueError:
                pass
        
        # Use the enhanced handover service
        workflow_service = HandoverWorkflowService()
        success = workflow_service.respond_to_incident_assignment(
            incident_assignment_id=assignment_id,
            status=response_status,
            response_comments=response_comments,
            estimated_completion_time=estimated_completion_time
        )
        
        if success:
            # Get assignment details for response
            assignment = IncidentAssignment.query.get(assignment_id)
            if assignment:
                # Send notification email to the original requester
                try:
                    assigned_by_user = assignment.assigned_by
                    if assigned_by_user and assigned_by_user.email:
                        status_display = response_status.replace('_', ' ').title()
                        subject = f"Incident Assignment {status_display}: {assignment.incident_title}"
                        
                        email_body = f"""
                        <h3>Incident Assignment Response</h3>
                        <p><strong>Incident:</strong> {assignment.incident_title}</p>
                        <p><strong>Status:</strong> {status_display}</p>
                        <p><strong>Responded by:</strong> {current_user.display_name}</p>
                        {f'<p><strong>Comments:</strong> {response_comments}</p>' if response_comments else ''}
                        {f'<p><strong>Estimated Completion:</strong> {estimated_completion_time.strftime("%Y-%m-%d %H:%M")}</p>' if estimated_completion_time else ''}
                        """
                        
                        send_handover_email(
                            to_email=assigned_by_user.email,
                            subject=subject,
                            body=email_body,
                            cc_emails=[]
                        )
                except Exception as email_error:
                    current_app.logger.error(f"Failed to send response notification email: {str(email_error)}")
            
            return jsonify({
                'success': True,
                'message': f'Assignment {response_status} successfully',
                'status': response_status
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to process response'
            })
    
    except Exception as e:
        current_app.logger.error(f"Error responding to assignment: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@incident_assignment_bp.route('/api/get_notifications_count', methods=['GET'])
@login_required
def get_notifications_count():
    """Get count of pending notifications for current user"""
    try:
        # Count pending assignments
        pending_count = IncidentAssignment.query.filter_by(
            assigned_to_id=current_user.id,
            assignment_status='pending'
        ).count()
        
        return jsonify({
            'success': True,
            'pending_count': pending_count
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting notifications count: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'pending_count': 0
        })