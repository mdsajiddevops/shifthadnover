#!/usr/bin/env python3
"""
Enhanced Handover Routes
Handles the enhanced handover workflow with incident assignment
"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, session
from flask_login import login_required, current_user
from datetime import datetime
from models.models import db, User, Team, TeamMember
from models.handover_enhanced import HandoverRequest, IncidentAssignment, IncidentAssignmentResponse, HandoverResponse, HandoverNotification, HandoverAuditLog
from services.handover_enhanced_service import HandoverWorkflowService
import json

def admin_required(f):
    """Decorator to require admin access"""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in ['super_admin', 'account_admin', 'team_admin']:
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('dashboard.dashboard'))
        return f(*args, **kwargs)
    return decorated

handover_enhanced_bp = Blueprint('handover_enhanced', __name__, url_prefix='/handover')

workflow_service = HandoverWorkflowService()

@handover_enhanced_bp.route('/enhanced', methods=['GET'])
@login_required
@admin_required
def enhanced_handover_form():
    """Redirect to incident response logs - ADMIN ONLY"""
    return redirect(url_for('user_profile.admin_incident_response_logs'))

@handover_enhanced_bp.route('/create', methods=['POST'])
@login_required
@admin_required
def create_handover():
    """Create a new handover request"""
    try:
        if not current_user.is_authenticated:
            return jsonify({'success': False, 'error': 'Not logged in'})
        
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['summary', 'detailed_notes', 'shift_end_time']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'Missing required field: {field}'})
        
        # Create handover request
        handover_data = {
            'submitter_id': current_user.id,
            'summary': data['summary'],
            'detailed_notes': data['detailed_notes'],
            'shift_end_time': datetime.fromisoformat(data['shift_end_time'].replace('Z', '+00:00')),
            'priority': data.get('priority', 'medium'),
            'incidents': data.get('incidents', [])
        }
        
        handover_request = workflow_service.create_handover_request(handover_data)
        
        return jsonify({
            'success': True, 
            'handover_id': handover_request.id,
            'message': 'Handover request created successfully'
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@handover_enhanced_bp.route('/submit/<int:handover_id>', methods=['POST'])
@login_required
@admin_required
def submit_handover(handover_id):
    """Submit a handover request for processing"""
    try:
        if not current_user.is_authenticated:
            return jsonify({'success': False, 'error': 'Not logged in'})
        
        data = request.get_json()
        incident_assignments = data.get('incident_assignments', [])
        
        result = workflow_service.submit_handover_request(handover_id, incident_assignments, current_user.id)
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': result['message'],
                'assignments_created': len(result.get('assignments', [])),
                'notifications_sent': result.get('notifications_sent', 0)
            })
        else:
            return jsonify({'success': False, 'error': result.get('error', 'Unknown error')})
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error submitting handover {handover_id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@handover_enhanced_bp.route('/assignments', methods=['GET'])
@login_required
@admin_required
def get_assignments():
    """Get incident assignments for current user"""
    try:
        if not current_user.is_authenticated:
            return jsonify({'success': False, 'error': 'Not logged in'})
        
        assignments = IncidentAssignment.query.filter_by(
            assigned_to_id=current_user.id,
            status='pending'
        ).all()
        
        assignments_data = []
        for assignment in assignments:
            assignments_data.append({
                'id': assignment.id,
                'handover_id': assignment.handover_request_id,
                'incident_description': assignment.incident_description,
                'priority': assignment.priority,
                'notes': assignment.notes,
                'assigned_at': assignment.assigned_at.isoformat(),
                'submitter_name': assignment.handover_request.submitter.full_name or assignment.handover_request.submitter.username
            })
        
        return jsonify({'success': True, 'assignments': assignments_data})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@handover_enhanced_bp.route('/assignments/<int:assignment_id>/respond', methods=['POST'])
@login_required
@admin_required
def respond_to_assignment(assignment_id):
    """Respond to an incident assignment"""
    try:
        if not current_user.is_authenticated:
            return jsonify({'success': False, 'error': 'Not logged in'})
        
        data = request.get_json()
        response_type = data.get('response_type')
        response_notes = data.get('response_notes', '')
        
        if response_type not in ['accepted', 'declined', 'needs_clarification']:
            return jsonify({'success': False, 'error': 'Invalid response type'})
        
        result = workflow_service.respond_to_incident_assignment(
            assignment_id, current_user.id, response_type, response_notes
        )
        
        return jsonify({
            'success': True,
            'message': f'Assignment {response_type} successfully'
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@handover_enhanced_bp.route('/complete/<int:handover_id>', methods=['POST'])
@login_required
@admin_required
def complete_handover(handover_id):
    """Complete a handover request"""
    try:
        if not current_user.is_authenticated:
            return jsonify({'success': False, 'error': 'Not logged in'})
        
        data = request.get_json()
        completion_notes = data.get('completion_notes', '')
        
        result = workflow_service.complete_handover(handover_id, current_user.id, completion_notes)
        
        return jsonify({
            'success': True,
            'message': 'Handover completed successfully'
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@handover_enhanced_bp.route('/history', methods=['GET'])
@login_required
@admin_required
def handover_history():
    """Redirect to incident response logs - ADMIN ONLY"""
    return redirect(url_for('user_profile.admin_incident_response_logs'))

# COMMENTED OUT - CONFLICTS WITH USER_PROFILE NOTIFICATIONS
# @handover_enhanced_bp.route('/notifications', methods=['GET'])
# @login_required
# @admin_required
def get_notifications_DISABLED():
    """Get notifications for current user"""
    try:
        if not current_user.is_authenticated:
            return jsonify({'success': False, 'error': 'Not logged in'})
        
        notifications = HandoverNotification.query.filter_by(
            user_id=current_user.id,
            is_read=False
        ).order_by(HandoverNotification.created_at.desc()).all()
        
        notifications_data = []
        for notification in notifications:
            notifications_data.append({
                'id': notification.id,
                'title': notification.title,
                'message': notification.message,
                'type': notification.notification_type,
                'created_at': notification.created_at.isoformat(),
                'handover_id': notification.handover_request_id
            })
        
        return jsonify({'success': True, 'notifications': notifications_data})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@handover_enhanced_bp.route('/notifications/<int:notification_id>/mark-read', methods=['POST'])
@login_required
@admin_required
def mark_notification_read(notification_id):
    """Mark notification as read"""
    try:
        if not current_user.is_authenticated:
            return jsonify({'success': False, 'error': 'Not logged in'})
        
        notification = HandoverNotification.query.filter_by(
            id=notification_id,
            user_id=current_user.id
        ).first()
        
        if not notification:
            return jsonify({'success': False, 'error': 'Notification not found'})
        
        notification.is_read = True
        notification.read_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Notification marked as read'})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})