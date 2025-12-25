#!/usr/bin/env python3
"""
Enhanced Assignment Response Routes

Handles Accept/Reject actions for incident assignments with proper logging
and notification functionality.
"""

from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
from models.models import db, User
from models.handover_enhanced import HandoverNotification, HandoverIncidentResponseLog
from services.notification_service_fix import notification_fix
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

assignment_response_bp = Blueprint('assignment_response', __name__, url_prefix='/assignment')

@assignment_response_bp.route('/test', methods=['GET'])
@login_required
def test_endpoint():
    """Test endpoint to verify the blueprint is working"""
    return jsonify({
        'success': True,
        'message': 'Assignment response blueprint is working',
        'user': current_user.username,
        'timestamp': datetime.utcnow().isoformat()
    })

@assignment_response_bp.route('/assignment-response', methods=['POST'])
@login_required  
def handle_notification_response():
    """Handle Accept/Reject actions for notification-based incident assignments"""
    try:
        # Log the incoming request
        logger.info(f"Processing notification response from user {current_user.id} ({current_user.username})")
        
        # Get JSON data with proper error handling
        try:
            data = request.get_json(force=True)
        except Exception as json_error:
            logger.error(f"Failed to parse JSON data: {str(json_error)}")
            return jsonify({'success': False, 'error': 'Invalid JSON data'}), 400
        
        notification_id = data.get('notification_id')
        action = data.get('action')  # 'accept' or 'reject'
        comments = data.get('comments', '')
        
        logger.info(f"Request data: notification_id={notification_id}, action={action}")
        
        # Validate required fields
        if not notification_id or not action:
            logger.error("Missing required fields in request")
            return jsonify({'success': False, 'error': 'Missing required fields: notification_id and action are required'}), 400
        
        if action not in ['accept', 'reject']:
            logger.error(f"Invalid action: {action}")
            return jsonify({'success': False, 'error': 'Invalid action. Must be "accept" or "reject"'}), 400
        
        # Get the notification with error handling
        try:
            notification = HandoverNotification.query.get(notification_id)
        except Exception as db_error:
            logger.error(f"Database error fetching notification {notification_id}: {str(db_error)}")
            return jsonify({'success': False, 'error': 'Database error occurred'}), 500
        
        if not notification:
            logger.error(f"Notification {notification_id} not found")
            return jsonify({'success': False, 'error': f'Notification {notification_id} not found'}), 404
        
        # Verify the notification belongs to the current user
        if notification.recipient_id != current_user.id:
            logger.error(f"Unauthorized access: notification {notification_id} belongs to user {notification.recipient_id}, not {current_user.id}")
            return jsonify({'success': False, 'error': 'Unauthorized: This notification does not belong to you'}), 403
        
        # Check if notification is already processed
        if notification.is_read:
            logger.warning(f"Notification {notification_id} already processed")
            return jsonify({'success': False, 'error': 'This notification has already been processed'}), 409
        
        # Find existing log entry based on notification data
        # Extract incident number from notification title
        incident_number = None
        if notification.title and ':' in notification.title:
            incident_number = notification.title.split(':', 1)[1].strip()
        
        log_entry = None
        if incident_number:
            # Try to find existing log entry by incident number and user
            log_entry = HandoverIncidentResponseLog.query.filter_by(
                incident_number=incident_number,
                accepted_by_id=current_user.id
            ).first()
        
        if not log_entry:
            # Create new log entry with all required fields
            try:
                logger.info(f"Creating new HandoverIncidentResponseLog for notification {notification_id}")
                
                # Try to get the original assigner's information
                assigner_id = current_user.id  # Default to current user
                assigner_name = current_user.display_name or current_user.username or 'Unknown'
                from_shift = 'Current'
                to_shift = 'Incoming'
                
                # Try to get assigner info from the handover request
                if notification.handover_request_id:
                    from models.handover_enhanced import HandoverRequest
                    handover_req = HandoverRequest.query.get(notification.handover_request_id)
                    if handover_req and handover_req.created_by:
                        assigner_id = handover_req.created_by_id
                        assigner_name = handover_req.created_by.display_name or handover_req.created_by.username or 'Unknown'
                    # Get shift info from the handover request's shift
                    if handover_req and handover_req.shift:
                        from_shift = handover_req.shift.current_shift_type or 'Current'
                        to_shift = handover_req.shift.next_shift_type or 'Incoming'
                
                log_entry = HandoverIncidentResponseLog(
                    response_date=datetime.utcnow().date(),
                    response_datetime=datetime.utcnow(),
                    incident_title=notification.title or 'Incident Assignment',
                    incident_number=incident_number or f"NOTIF-{notification_id}",
                    incident_description=notification.message or 'Assignment from notification',
                    accepted_by_id=current_user.id,
                    accepted_by_name=current_user.display_name or current_user.username or 'Unknown',
                    assigned_by_id=assigner_id,
                    assigned_by_name=assigner_name,
                    assigned_at=notification.created_at,
                    responded_at=datetime.utcnow(),  # Set initial value to avoid null constraint
                    handover_request_id=notification.handover_request_id,
                    account_id=notification.account_id or 1,
                    team_id=notification.team_id or 1,
                    incident_type='Open',
                    incident_category='Application',
                    incident_priority='Medium',
                    assignment_status='pending',
                    response_status='pending',
                    from_shift_type=from_shift,
                    to_shift_type=to_shift
                )
                logger.info(f"HandoverIncidentResponseLog created successfully")
                db.session.add(log_entry)
                logger.info(f"HandoverIncidentResponseLog added to session")
            except Exception as create_error:
                logger.error(f"Error creating HandoverIncidentResponseLog: {str(create_error)}")
                raise create_error
        
        # Update log entry with response
        log_entry.response_status = 'accepted' if action == 'accept' else 'rejected'
        log_entry.assignment_status = 'completed'
        log_entry.response_comments = comments
        log_entry.responded_at = datetime.utcnow()
        log_entry.response_datetime = datetime.utcnow()
        
        # Calculate response time in minutes
        if log_entry.assigned_at:
            time_diff = datetime.utcnow() - log_entry.assigned_at
            response_time = int(time_diff.total_seconds() / 60)
            # Store response time in assignment_notes if no specific field exists
            if log_entry.assignment_notes:
                log_entry.assignment_notes += f" | Response time: {response_time} minutes"
            else:
                log_entry.assignment_notes = f"Response time: {response_time} minutes"
        
        # Mark notification as read and commit all changes
        try:
            logger.info(f"Updating notification {notification_id} status")
            notification.is_read = True
            notification.read_at = datetime.utcnow()
            
            logger.info(f"Committing all changes to database")
            db.session.commit()
            logger.info(f"Database commit successful")
            
        except Exception as commit_error:
            logger.error(f"Error during database commit: {str(commit_error)}")
            db.session.rollback()
            
            # Handle specific foreign key constraint errors
            if 'foreign key constraint fails' in str(commit_error).lower():
                error_msg = 'Database constraint error: Invalid user reference. Please contact administrator.'
            elif 'duplicate entry' in str(commit_error).lower():
                error_msg = 'This notification has already been processed.'
            else:
                error_msg = f'Database error: {str(commit_error)}'
                
            return jsonify({'success': False, 'error': error_msg}), 500
        
        logger.info(f"Notification {notification_id} {action}ed successfully by user {current_user.id} ({current_user.username})")
        logger.info(f"Created/Updated log entry ID: {log_entry.id} for incident: {log_entry.incident_number}")
        
        # Send success response
        return jsonify({
            'success': True,
            'message': f'Assignment {action}ed successfully',
            'action': action,
            'log_id': log_entry.id,
            'notification_id': notification_id
        })
        
    except Exception as e:
        logger.error(f"Unexpected error handling notification response: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Ensure rollback
        try:
            db.session.rollback()
        except:
            pass
            
        # Return detailed error for debugging (consider removing in production)
        return jsonify({
            'success': False, 
            'error': f'Server error: {str(e)}',
            'error_type': type(e).__name__
        }), 500

@assignment_response_bp.route('/respond', methods=['POST'])
@login_required
def respond_to_assignment():
    """Handle Accept/Reject actions for incident assignments"""
    try:
        data = request.get_json()
        
        assignment_id = data.get('assignment_id')
        action = data.get('action')  # 'accepted' or 'rejected'
        comments = data.get('comments', '')
        
        if not assignment_id or not action:
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        if action not in ['accepted', 'rejected']:
            return jsonify({'success': False, 'error': 'Invalid action'}), 400
        
        # Update the incident response log
        log_entry = HandoverIncidentResponseLog.query.filter_by(
            incident_number=assignment_id,
            accepted_by_id=current_user.id
        ).first()
        
        if not log_entry:
            return jsonify({'success': False, 'error': 'Assignment not found'}), 404
        
        # Update log entry
        log_entry.response_status = action
        log_entry.response_comments = comments
        log_entry.responded_at = datetime.utcnow()
        
        # Calculate response time in minutes (response_time_minutes is a property, not a field)
        # The response time will be calculated automatically by the model property
        # No need to set it as it's computed from assigned_at and responded_at
        
        db.session.commit()
        
        # Send notification to the original assigner
        if log_entry.assigned_by_id:
            try:
                notification = HandoverNotification(
                    recipient_id=log_entry.assigned_by_id,
                    notification_type=f'incident_{action}',
                    title=f'Incident Assignment {action.title()}: {log_entry.incident_title}',
                    message=f'{current_user.first_name} {current_user.last_name} has {action} the assignment for {log_entry.incident_title}. Comments: {comments}' if comments else f'{current_user.first_name} {current_user.last_name} has {action} the assignment for {log_entry.incident_title}',
                    action_url='/admin/incident-response-logs',
                    action_text='View Details',
                    account_id=log_entry.account_id,
                    team_id=log_entry.team_id
                )
                
                db.session.add(notification)
                db.session.commit()
                
            except Exception as notify_error:
                logger.error(f"Failed to send response notification: {str(notify_error)}")
        
        # Send email notification to team
        try:
            from services.email_service import send_incident_assignment_notification
            # This would need to be modified to send response notifications
            # For now, we'll log it
            logger.info(f"Assignment {action} by {current_user.username}: {assignment_id}")
            
        except Exception as email_error:
            logger.error(f"Failed to send email notification: {str(email_error)}")
        
        return jsonify({
            'success': True,
            'message': f'Assignment {action} successfully',
            'action': action
        })
        
    except Exception as e:
        logger.error(f"Error handling assignment response: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@assignment_response_bp.route('/notifications', methods=['GET'])
@login_required
def get_user_notifications():
    """Get current user's notifications - synchronized with dashboard logic"""
    try:
        print(f"[AJAX DEBUG] User {current_user.username} (ID: {current_user.id}) requesting notifications via AJAX", flush=True)
        
        # Get ALL notifications for current user (both read and unread) - same as template route
        all_notifications = HandoverNotification.query.filter_by(
            recipient_id=current_user.id
        ).order_by(HandoverNotification.created_at.desc()).all()
        
        print(f"[AJAX DEBUG] Found {len(all_notifications)} total notifications", flush=True)
        
        # Get unread notifications for display
        unread_notifications = [n for n in all_notifications if not n.is_read]
        print(f"[AJAX DEBUG] Found {len(unread_notifications)} unread notifications", flush=True)
        
        notifications_data = []
        assignments_data = []
        
        for notification in all_notifications:
            # Add to notifications list
            priority_map = {'critical': 'high', 'high': 'high', 'medium': 'medium', 'low': 'low'}
            priority = 'medium'  # default
            
            # Try to extract priority from message or title
            if 'critical' in (notification.message or '').lower() or 'critical' in (notification.title or '').lower():
                priority = 'high'
            elif 'high' in (notification.message or '').lower() or 'high' in (notification.title or '').lower():
                priority = 'high'
            elif 'low' in (notification.message or '').lower() or 'low' in (notification.title or '').lower():
                priority = 'low'
                
            notifications_data.append({
                'id': notification.id,
                'type': notification.notification_type,
                'title': notification.title,
                'message': notification.message,
                'action_url': notification.action_url,
                'action_text': notification.action_text,
                'created_at': notification.created_at.isoformat(),
                'is_assignment': notification.notification_type == 'incident_assigned',
                'is_read': notification.is_read,
                'priority': priority
            })
            
            # If this is an unread incident assignment, add it to pending_assignments
            # Use the same logic as template route and dashboard
            if (notification.notification_type == 'incident_assigned' and 
                not notification.is_read):
                
                assignments_data.append({
                    'incident_id': f"NOTIF-{notification.id}",
                    'incident_title': notification.title or 'Incident Assignment',
                    'incident_description': notification.message or 'No description',
                    'incident_priority': priority.title(),
                    'assigned_at': notification.created_at.isoformat(),
                    'from_shift': 'Previous Shift',
                    'to_shift': 'Current Shift',
                    'assignment_notes': getattr(notification, 'additional_notes', None),
                    'notification_id': notification.id  # Add this for the Accept/Reject functionality
                })
        
        print(f"[AJAX DEBUG] Created {len(assignments_data)} pending assignment items (should match template route)", flush=True)
        
        return jsonify({
            'success': True,
            'notifications': notifications_data,
            'pending_assignments': assignments_data
        })
        
    except Exception as e:
        logger.error(f"Error getting user notifications: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@assignment_response_bp.route('/mark-read/<int:notification_id>', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    """Mark a notification as read"""
    try:
        notification = HandoverNotification.query.filter_by(
            id=notification_id,
            recipient_id=current_user.id
        ).first()
        
        if not notification:
            return jsonify({'success': False, 'error': 'Notification not found'}), 404
        
        notification.mark_as_read()
        
        return jsonify({'success': True, 'message': 'Notification marked as read'})
        
    except Exception as e:
        logger.error(f"Error marking notification as read: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Additional routes for dashboard notification functionality
from flask import Blueprint as DashboardBlueprint
notification_dashboard_bp = DashboardBlueprint('notification_dashboard', __name__)

@notification_dashboard_bp.route('/mark-notification-read', methods=['POST'])
@login_required
def mark_notification_read_dashboard():
    """Mark a notification as read from the dashboard"""
    try:
        data = request.get_json()
        notification_id = data.get('notification_id')
        
        if not notification_id:
            return jsonify({'success': False, 'error': 'Missing notification ID'}), 400
        
        notification = HandoverNotification.query.get(notification_id)
        if not notification:
            return jsonify({'success': False, 'error': 'Notification not found'}), 404
            
        # Verify the notification belongs to the current user
        if notification.recipient_id != current_user.id:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
        notification.is_read = True
        notification.read_at = datetime.utcnow()
        db.session.commit()
        
        logger.info(f"Notification {notification_id} marked as read by user {current_user.id}")
        
        return jsonify({'success': True, 'message': 'Notification marked as read'})
        
    except Exception as e:
        logger.error(f"Error marking notification as read: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@notification_dashboard_bp.route('/send-followup-email', methods=['POST'])
@login_required
def send_followup_email():
    """Send follow-up email after assignment response"""
    try:
        data = request.get_json()
        notification_id = data.get('notification_id')
        action = data.get('action')
        comments = data.get('comments', '')
        
        if not notification_id or not action:
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        notification = HandoverNotification.query.get(notification_id)
        if not notification:
            return jsonify({'success': False, 'error': 'Notification not found'}), 404
        
        # Import email service
        try:
            from services.email_service import send_assignment_response_email
            
            # Send email to team or configured recipients
            email_result = send_assignment_response_email(
                notification=notification,
                responder=current_user,
                action=action,
                comments=comments
            )
            
            if email_result.get('success'):
                logger.info(f"Follow-up email sent for notification {notification_id}")
                return jsonify({'success': True, 'message': 'Follow-up email sent'})
            else:
                logger.error(f"Failed to send follow-up email: {email_result.get('error')}")
                return jsonify({'success': False, 'error': 'Failed to send email'}), 500
                
        except ImportError:
            # Email service not available, log and return success
            logger.info(f"Email service not available, logging follow-up for notification {notification_id}")
            return jsonify({'success': True, 'message': 'Response logged (email service unavailable)'})
        
    except Exception as e:
        logger.error(f"Error sending follow-up email: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500