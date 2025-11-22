"""
Handover Management Routes

Handles all routes related to the enhanced shift handover workflow:
- /handover/pending - View and manage pending handovers
- /handover/accept/<incident_id> - Accept a handover
- /handover/reject/<incident_id> - Reject a handover with note
- /handover/history/<incident_id> - View handover history

Integrates with HandoverWorkflowService and HandoverNotificationService
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from functools import wraps
from models.models import (
    db, Incident, IncidentHandoverAction, HandoverNotification, 
    TeamMember, Shift
)
from services.handover_workflow_service import HandoverWorkflowService
from services.handover_notification_service import HandoverNotificationService
from services.audit_service import log_action
import logging

handover_management_bp = Blueprint('handover_management', __name__)
logger = logging.getLogger(__name__)

def admin_required(f):
    """Decorator to require admin privileges"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('auth.login'))
        
        if not current_user.role or current_user.role not in ['super_admin', 'account_admin', 'team_admin']:
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('dashboard.dashboard'))
        
        return f(*args, **kwargs)
    return decorated_function

@handover_management_bp.route('/handover/pending')
@login_required
def pending_handovers():
    """Display pending handovers for the current user."""
    try:
        workflow_service = HandoverWorkflowService()
        
        # Get current user's team member record
        team_member = TeamMember.query.filter_by(user_id=current_user.id).first()
        engineer_name = team_member.name if team_member else current_user.username
        
        # Get pending handovers for this engineer
        pending_handovers = workflow_service.get_pending_handovers(
            engineer_name=engineer_name,
            account_id=current_user.account_id,
            team_id=current_user.team_id
        )
        
        # Get summary statistics
        summary = workflow_service.get_handover_summary(
            account_id=current_user.account_id,
            team_id=current_user.team_id
        )
        
        # Calculate urgency levels
        for handover in pending_handovers:
            minutes_pending = handover.get('time_pending_minutes', 0)
            if minutes_pending > 120:  # 2 hours
                handover['urgency'] = 'critical'
            elif minutes_pending > 30:  # 30 minutes
                handover['urgency'] = 'warning'
            else:
                handover['urgency'] = 'normal'
        
        return render_template(
            'handover/pending_handovers.html',
            pending_handovers=pending_handovers,
            summary=summary,
            engineer_name=engineer_name,
            current_time=datetime.now()
        )
        
    except Exception as e:
        logger.error(f"Error loading pending handovers: {str(e)}")
        flash('Error loading pending handovers. Please try again.', 'error')
        return redirect(url_for('main.dashboard'))

@handover_management_bp.route('/handover/accept/<int:incident_id>', methods=['POST'])
@login_required
def accept_handover(incident_id):
    """Accept a handover for an incident."""
    try:
        workflow_service = HandoverWorkflowService()
        
        # Get current user details
        team_member = TeamMember.query.filter_by(user_id=current_user.id).first()
        engineer_name = team_member.name if team_member else current_user.username
        
        # Get optional acceptance notes
        notes = request.form.get('acceptance_notes', '').strip()
        
        # Accept the handover
        result = workflow_service.accept_incident(
            incident_id=incident_id,
            accepted_by=engineer_name,
            notes=notes,
            account_id=current_user.account_id,
            team_id=current_user.team_id
        )
        
        if result['success']:
            flash(f'✅ Incident accepted successfully! You are now responsible for this incident.', 'success')
            
            # Send confirmation notification if configured
            notification_service = HandoverNotificationService()
            if team_member and team_member.email:
                notification_service.send_pending_handover_notification(
                    incident_id=incident_id,
                    recipient_email=team_member.email,
                    recipient_name=engineer_name
                )
        else:
            flash(f'❌ Error accepting handover: {result["message"]}', 'error')
        
        return redirect(url_for('handover_management.pending_handovers'))
        
    except Exception as e:
        logger.error(f"Error accepting handover: {str(e)}")
        flash('Error accepting handover. Please try again.', 'error')
        return redirect(url_for('handover_management.pending_handovers'))

@handover_management_bp.route('/handover/reject/<int:incident_id>', methods=['POST'])
@login_required
def reject_handover(incident_id):
    """Reject a handover for an incident with mandatory note."""
    try:
        workflow_service = HandoverWorkflowService()
        
        # Get current user details
        team_member = TeamMember.query.filter_by(user_id=current_user.id).first()
        engineer_name = team_member.name if team_member else current_user.username
        
        # Get mandatory rejection note
        rejection_note = request.form.get('rejection_note', '').strip()
        
        if not rejection_note:
            flash('❌ Rejection note is mandatory. Please provide a reason for rejecting this handover.', 'error')
            return redirect(url_for('handover_management.pending_handovers'))
        
        # Reject the handover
        result = workflow_service.reject_incident(
            incident_id=incident_id,
            rejected_by=engineer_name,
            rejection_note=rejection_note,
            account_id=current_user.account_id,
            team_id=current_user.team_id
        )
        
        if result['success']:
            flash(f'❌ Incident rejected. The rejection has been logged and the previous engineer notified.', 'warning')
        else:
            flash(f'❌ Error rejecting handover: {result["message"]}', 'error')
        
        return redirect(url_for('handover_management.pending_handovers'))
        
    except Exception as e:
        logger.error(f"Error rejecting handover: {str(e)}")
        flash('Error rejecting handover. Please try again.', 'error')
        return redirect(url_for('handover_management.pending_handovers'))

@handover_management_bp.route('/handover/history/<int:incident_id>')
@login_required
@admin_required
def handover_history(incident_id):
    """View complete handover history for an incident."""
    try:
        workflow_service = HandoverWorkflowService()
        
        # Get incident details
        incident = Incident.query.get_or_404(incident_id)
        
        # Verify user has access to this incident
        if (current_user.account_id and incident.account_id != current_user.account_id) or \
           (current_user.team_id and incident.team_id != current_user.team_id):
            flash('Access denied to this incident.', 'error')
            return redirect(url_for('handover_management.pending_handovers'))
        
        # Get handover history
        history = workflow_service.get_handover_history(incident_id)
        
        return render_template(
            'handover/handover_history.html',
            incident=incident,
            history=history
        )
        
    except Exception as e:
        logger.error(f"Error loading handover history: {str(e)}")
        flash('Error loading handover history. Please try again.', 'error')
        return redirect(url_for('handover_management.pending_handovers'))

@handover_management_bp.route('/api/handover/quick-action', methods=['POST'])
@login_required
def quick_action():
    """Handle quick accept/reject actions via AJAX."""
    try:
        data = request.get_json()
        incident_id = data.get('incident_id')
        action = data.get('action')  # 'accept' or 'reject'
        notes = data.get('notes', '').strip()
        
        if not incident_id or not action:
            return jsonify({'success': False, 'message': 'Missing required parameters'})
        
        workflow_service = HandoverWorkflowService()
        team_member = TeamMember.query.filter_by(user_id=current_user.id).first()
        engineer_name = team_member.name if team_member else current_user.username
        
        if action == 'accept':
            result = workflow_service.accept_incident(
                incident_id=incident_id,
                accepted_by=engineer_name,
                notes=notes,
                account_id=current_user.account_id,
                team_id=current_user.team_id
            )
        elif action == 'reject':
            if not notes:
                return jsonify({'success': False, 'message': 'Rejection note is mandatory'})
            
            result = workflow_service.reject_incident(
                incident_id=incident_id,
                rejected_by=engineer_name,
                rejection_note=notes,
                account_id=current_user.account_id,
                team_id=current_user.team_id
            )
        else:
            return jsonify({'success': False, 'message': 'Invalid action'})
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in quick action: {str(e)}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@handover_management_bp.route('/api/handover/stats')
@login_required
def handover_stats():
    """Get handover statistics for dashboard widgets."""
    try:
        workflow_service = HandoverWorkflowService()
        notification_service = HandoverNotificationService()
        
        # Get current user details
        team_member = TeamMember.query.filter_by(user_id=current_user.id).first()
        engineer_name = team_member.name if team_member else current_user.username
        
        # Get personal pending count
        pending_count = notification_service.get_pending_notifications_count(engineer_name)
        
        # Get team summary
        team_summary = workflow_service.get_handover_summary(
            account_id=current_user.account_id,
            team_id=current_user.team_id
        )
        
        # Calculate urgent count (pending > 30 minutes)
        urgent_threshold = datetime.now() - timedelta(minutes=30)
        urgent_count = Incident.query.filter(
            Incident.handover_status == 'Pending',
            Incident.handover_assigned_to == engineer_name,
            Incident.handover_initiated_at <= urgent_threshold
        ).count()
        
        return jsonify({
            'success': True,
            'personal_pending': pending_count,
            'personal_urgent': urgent_count,
            'team_summary': team_summary
        })
        
    except Exception as e:
        logger.error(f"Error getting handover stats: {str(e)}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@handover_management_bp.route('/handover/bulk-action', methods=['POST'])
@login_required
def bulk_action():
    """Handle bulk accept/reject actions."""
    try:
        incident_ids = request.form.getlist('incident_ids')
        action = request.form.get('bulk_action')
        notes = request.form.get('bulk_notes', '').strip()
        
        if not incident_ids or not action:
            flash('Please select incidents and action.', 'error')
            return redirect(url_for('handover_management.pending_handovers'))
        
        workflow_service = HandoverWorkflowService()
        team_member = TeamMember.query.filter_by(user_id=current_user.id).first()
        engineer_name = team_member.name if team_member else current_user.username
        
        success_count = 0
        error_count = 0
        
        for incident_id in incident_ids:
            try:
                if action == 'accept':
                    result = workflow_service.accept_incident(
                        incident_id=int(incident_id),
                        accepted_by=engineer_name,
                        notes=notes,
                        account_id=current_user.account_id,
                        team_id=current_user.team_id
                    )
                elif action == 'reject':
                    if not notes:
                        flash('Rejection note is mandatory for bulk reject.', 'error')
                        return redirect(url_for('handover_management.pending_handovers'))
                    
                    result = workflow_service.reject_incident(
                        incident_id=int(incident_id),
                        rejected_by=engineer_name,
                        rejection_note=notes,
                        account_id=current_user.account_id,
                        team_id=current_user.team_id
                    )
                
                if result['success']:
                    success_count += 1
                else:
                    error_count += 1
                    
            except Exception as e:
                logger.error(f"Error in bulk action for incident {incident_id}: {str(e)}")
                error_count += 1
        
        if success_count > 0:
            flash(f'✅ Successfully processed {success_count} incidents.', 'success')
        if error_count > 0:
            flash(f'❌ Failed to process {error_count} incidents.', 'error')
        
        return redirect(url_for('handover_management.pending_handovers'))
        
    except Exception as e:
        logger.error(f"Error in bulk action: {str(e)}")
        flash('Error processing bulk action. Please try again.', 'error')
        return redirect(url_for('handover_management.pending_handovers'))