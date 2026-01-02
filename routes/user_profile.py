from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from models.models import db, User, TeamMember
from werkzeug.security import generate_password_hash, check_password_hash
from services.audit_service import log_action
from datetime import datetime
import logging


# Module logger
logger = logging.getLogger(__name__)
user_profile_bp = Blueprint('user_profile', __name__)

@user_profile_bp.route('/profile')
@login_required
def profile():
    """User profile page"""
    # Get account and team information for the user
    account = current_user.account if current_user.account_id else None
    team = current_user.team if current_user.team_id else None
    
    return render_template('user_profile.html', 
                         user=current_user,
                         account=account,
                         team=team)

@user_profile_bp.route('/profile/debug', methods=['GET', 'POST'])
@login_required
def debug_profile():
    """Debug profile submission"""
    if request.method == 'POST':
        form_data = dict(request.form)
        flash(f'Form data received: {form_data}', 'info')
    return redirect(url_for('user_profile.profile'))

@user_profile_bp.route('/profile/edit', methods=['POST'])
@login_required
def edit_profile():
    """Update user profile"""
    try:
        # Get form data
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        email = request.form.get('email', '').strip()
        
        # Basic validation
        if email and '@' not in email:
            flash('Please enter a valid email address.', 'error')
            return redirect(url_for('user_profile.profile'))
        
        # Update user profile
        if first_name:
            current_user.first_name = first_name
        else:
            current_user.first_name = None
            
        if last_name:
            current_user.last_name = last_name
        else:
            current_user.last_name = None
        
        # Check if email is already taken by another user
        if email and email != current_user.email:
            existing_user = User.query.filter(User.email == email, User.id != current_user.id).first()
            if existing_user:
                flash('Email address is already in use by another user.', 'error')
                return redirect(url_for('user_profile.profile'))
            current_user.email = email
        elif email:
            current_user.email = email

        # Commit changes to database
        db.session.commit()
        
        # Log the action
        try:
            log_action('Update Profile', f'Updated profile information for user {current_user.username}')
        except:
            pass  # Don't fail if logging fails
            
        flash('Profile updated successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        logger.debug(f"Profile update error: {str(e)}")  # Debug logging
        flash(f'Failed to update profile: {str(e)}', 'error')
        
    return redirect(url_for('user_profile.profile'))

@user_profile_bp.route('/profile/change-password', methods=['POST'])
@login_required
def change_password():
    """Change user password"""
    try:
        current_password = request.form.get('current_password', '').strip()
        new_password = request.form.get('new_password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        
        # Validation checks
        if not current_password:
            flash('Current password is required.', 'error')
            return redirect(url_for('user_profile.profile'))
        
        if not new_password:
            flash('New password is required.', 'error')
            return redirect(url_for('user_profile.profile'))
        
        if not confirm_password:
            flash('Password confirmation is required.', 'error')
            return redirect(url_for('user_profile.profile'))
        
        # Validate current password
        if not check_password_hash(current_user.password, current_password):
            flash('Current password is incorrect.', 'error')
            return redirect(url_for('user_profile.profile'))
        
        # Validate new password
        if new_password != confirm_password:
            flash('New passwords do not match.', 'error')
            return redirect(url_for('user_profile.profile'))
        
        if len(new_password) < 6:
            flash('Password must be at least 6 characters long.', 'error')
            return redirect(url_for('user_profile.profile'))
        
        # Update password
        current_user.password = generate_password_hash(new_password)
        db.session.commit()
        
        # Log the action
        try:
            log_action('Password Change', f'Password changed successfully for user {current_user.username}')
        except:
            pass  # Don't fail if logging fails
            
        flash('Password changed successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        logger.debug(f"Password change error: {str(e)}")  # Debug logging
        flash(f'Failed to change password: {str(e)}', 'error')
        
    return redirect(url_for('user_profile.profile'))

@user_profile_bp.route('/account-settings')
@login_required
def account_settings():
    """Account settings page"""
    # Get account and team information for the user
    account = current_user.account if current_user.account_id else None
    team = current_user.team if current_user.team_id else None
    
    return render_template('account_settings.html', 
                         user=current_user,
                         account=account,
                         team=team)

@user_profile_bp.route('/notifications')
@login_required
def notifications():
    """Notifications page"""
    logger.debug(f"[NOTIFICATIONS DEBUG] User {current_user.username} (ID: {current_user.id}) accessing notifications")
    
    # Get notifications for the current user
    incident_assignments = []
    pending_assignments = []
    
    try:
        from models.handover_enhanced import HandoverNotification
        
        logger.debug(f"[NOTIFICATIONS DEBUG] Looking for HandoverNotification records for user_id: {current_user.id}")
        
        # Get all notifications for current user (both read and unread)
        all_notifications = HandoverNotification.query.filter_by(
            recipient_id=current_user.id
        ).order_by(HandoverNotification.created_at.desc()).all()
        
        logger.debug(f"[NOTIFICATIONS DEBUG] Found {len(all_notifications)} total notifications")
        
        # Count unread notifications (same logic as dashboard)
        unread_notifications = HandoverNotification.query.filter_by(
            recipient_id=current_user.id,
            is_read=False
        ).all()
        
        logger.debug(f"[NOTIFICATIONS DEBUG] Found {len(unread_notifications)} unread notifications (same as dashboard logic)")
        
        for unread in unread_notifications:
            logger.debug(f"[NOTIFICATIONS DEBUG] Unread notification ID {unread.id}: {unread.title} (Type: {unread.notification_type})")
        
        for notification in all_notifications:
            logger.debug(f"[NOTIFICATIONS DEBUG] Processing notification ID {notification.id}: {notification.title} (Read: {notification.is_read})")
            
            # Convert notification to display format
            priority_map = {'critical': 'high', 'high': 'high', 'medium': 'medium', 'low': 'low'}
            priority = 'medium'  # default
            
            # Try to extract priority from message or title
            if 'critical' in (notification.message or '').lower() or 'critical' in (notification.title or '').lower():
                priority = 'high'
            elif 'high' in (notification.message or '').lower() or 'high' in (notification.title or '').lower():
                priority = 'high'
            elif 'low' in (notification.message or '').lower() or 'low' in (notification.title or '').lower():
                priority = 'low'
            
            # Create notification item for display
            incident_assignments.append({
                'id': notification.id,
                'title': notification.title or 'Notification',
                'message': notification.message or 'No message',
                'type': 'incident' if notification.notification_type == 'incident_assigned' else 'notification',
                'priority': priority,
                'timestamp': notification.created_at,
                'read': notification.is_read,
                'assignment_data': {
                    'notification_id': notification.id,
                    'notification_type': notification.notification_type,
                    'action_url': notification.action_url,
                    'action_text': notification.action_text,
                    'status': 'read' if notification.is_read else 'unread',
                    'response_comments': None
                }
            })
            
            # If this is an unread incident assignment, add it to pending_assignments
            # Use the same logic as dashboard: unread incident_assigned notifications
            if (notification.notification_type == 'incident_assigned' and 
                not notification.is_read):
                
                pending_assignments.append({
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
            
    except Exception as e:
        logger.debug(f"[NOTIFICATIONS DEBUG] Error fetching notifications: {str(e)}")
        current_app.logger.error(f"Error fetching notifications: {str(e)}")
        import traceback
        traceback.print_exc()
    
    logger.debug(f"[NOTIFICATIONS DEBUG] Created {len(incident_assignments)} notification items")
    logger.debug(f"[NOTIFICATIONS DEBUG] Created {len(pending_assignments)} pending assignment items")
    
    # Log the pending assignments for comparison with dashboard
    if pending_assignments:
        logger.debug(f"[NOTIFICATIONS DEBUG] Pending assignments (should match dashboard):")
        for assignment in pending_assignments:
            logger.debug(f"  - ID {assignment['notification_id']}: {assignment['incident_title']}")
    else:
        logger.debug(f"[NOTIFICATIONS DEBUG] No pending assignments (dashboard should also show 0)")
    
    # Debug: Show exactly what's being passed to template
    logger.debug(f"[NOTIFICATIONS DEBUG] TEMPLATE DATA - pending_assignments length: {len(pending_assignments)}")
    logger.debug(f"[NOTIFICATIONS DEBUG] TEMPLATE DATA - notifications length: {len(incident_assignments)}")
    if pending_assignments:
        logger.debug(f"[NOTIFICATIONS DEBUG] TEMPLATE DATA - First pending assignment: {pending_assignments[0]}")
    
    # Static notifications for other system events
    static_notifications = [
        {
            'id': 1001,
            'title': 'Profile Updated',
            'message': 'Your profile was successfully updated',
            'type': 'success',
            'timestamp': datetime.now(),
            'read': False
        }
    ]
    
    # Combine incident assignments and static notifications
    all_notifications = incident_assignments + static_notifications
    # Sort by timestamp, newest first
    all_notifications.sort(key=lambda x: x['timestamp'], reverse=True)
    
    # Pass both notifications and pending_assignments to template
    return render_template('notifications_enhanced.html', 
                         notifications=all_notifications,
                         pending_assignments=pending_assignments)

@user_profile_bp.route('/alerts')
@login_required
def alerts():
    """System alerts page"""
    # This would typically fetch system alerts from database
    # For now, we'll show a placeholder page
    alerts_data = [
        {
            'id': 1,
            'title': 'High Priority Incident',
            'message': 'Multiple services experiencing degraded performance',
            'severity': 'high',
            'timestamp': datetime.now(),
            'status': 'active'
        },
        {
            'id': 2,
            'title': 'Database Connection Issues',
            'message': 'Intermittent database connection timeouts reported',
            'severity': 'medium',
            'timestamp': datetime.now(),
            'status': 'investigating'
        }
    ]
    return render_template('alerts.html', alerts=alerts_data)

@user_profile_bp.route('/help')
@login_required
def help_support():
    """Help and support page"""
    return render_template('help_support.html')

@user_profile_bp.route('/about')
@login_required
def about():
    """About page"""
    app_info = {
        'name': 'Shift Handover Application',
        'version': '2.0.0',
        'description': 'A comprehensive shift handover management system',
        'features': [
            'Shift scheduling and roster management',
            'Incident tracking and handover',
            'ServiceNow integration',
            'User and team management',
            'Audit logging and reporting',
            'SSO authentication support'
        ]
    }
    return render_template('about.html', app_info=app_info)

@user_profile_bp.route('/notifications/mark-read/<int:notification_id>', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    """Mark notification as read"""
    # This would typically update the notification in database
    # For now, just return success
    return jsonify({'status': 'success', 'message': 'Notification marked as read'})

@user_profile_bp.route('/notifications/mark-all-read', methods=['POST'])
@login_required
def mark_all_notifications_read():
    """Mark all notifications as read"""
    # This would typically update all notifications in database
    # For now, just return success
    log_action('Mark Notifications Read', 'Marked all notifications as read')
    return jsonify({'status': 'success', 'message': 'All notifications marked as read'})

@user_profile_bp.route('/assignment-action', methods=['POST'])
@login_required
def assignment_action():
    """Handle accept/reject actions for incident assignments"""
    try:
        # Handle both JSON and form data
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form
            
        assignment_id = data.get('assignment_id')
        action = data.get('action')  # 'accept' or 'reject'
        comments = data.get('comments', '').strip() if data.get('comments') else ''  # Get user comments
        
        if not assignment_id or not action:
            return jsonify({'success': False, 'message': 'Missing assignment ID or action'})
        
        if action not in ['accept', 'reject']:
            return jsonify({'success': False, 'message': 'Invalid action'})
        
        # Import the model here to avoid circular imports
        from models.handover_enhanced import IncidentAssignment, IncidentAssignmentResponse, HandoverIncidentResponseLog
        
        # Find the assignment
        assignment = IncidentAssignment.query.get(assignment_id)
        if not assignment:
            return jsonify({'success': False, 'message': 'Assignment not found'})
        
        # Check if user is authorized (assignment belongs to them)
        if assignment.assigned_to_id != current_user.id:
            return jsonify({'success': False, 'message': 'Unauthorized'})
        
        # Update assignment status
        assignment.assignment_status = 'accepted' if action == 'accept' else 'rejected'
        assignment.responded_at = datetime.utcnow()
        
        # Create or update response record
        existing_response = IncidentAssignmentResponse.query.filter_by(
            incident_assignment_id=assignment.id
        ).first()
        
        # Use user comments if provided, otherwise use default message
        response_comment = comments if comments else f'Assignment {action}ed via notification interface'
        
        if existing_response:
            existing_response.status = assignment.assignment_status
            existing_response.comments = response_comment
            existing_response.responded_at = datetime.utcnow()
        else:
            response = IncidentAssignmentResponse(
                incident_assignment_id=assignment.id,
                responder_id=current_user.id,
                status=assignment.assignment_status,
                comments=response_comment,
                responded_at=datetime.utcnow(),
                account_id=assignment.account_id,  # Required by database
                team_id=assignment.team_id        # Required by database
            )
            db.session.add(response)
        
        # Update existing log entry instead of creating a new one
        existing_log = HandoverIncidentResponseLog.query.filter_by(
            incident_assignment_id=assignment.id
        ).first()
        
        if existing_log:
            # Update the existing log entry with response information
            existing_log.assignment_status = assignment.assignment_status
            existing_log.response_status = assignment.assignment_status
            existing_log.response_comments = response_comment
            existing_log.responded_at = datetime.utcnow()
            existing_log.response_datetime = datetime.utcnow()
            existing_log.incident_assignment_response_id = existing_response.id if existing_response else response.id
            
            current_app.logger.info(f"Updated existing incident response log for assignment: {assignment.incident_title}")
        else:
            # Fallback: Create new log entry if none exists (shouldn't happen with new system)
            log_entry = HandoverIncidentResponseLog(
                response_date=datetime.utcnow().date(),
                response_datetime=datetime.utcnow(),
                
                # Shift information (we'll enhance this later with actual shift data)
                from_shift_type="Current",  # Can be enhanced with actual shift lookup
                to_shift_type="Incoming",  # Can be enhanced with actual shift lookup
                
                # Assignment details
                assigned_by_id=assignment.assigned_by_id,
                assigned_by_name=User.query.get(assignment.assigned_by_id).username if User.query.get(assignment.assigned_by_id) else "Unknown",
                accepted_by_id=current_user.id,
                accepted_by_name=current_user.username,
                
                # Incident information
                incident_number=assignment.incident_id,
                incident_title=assignment.incident_title,
                incident_description=assignment.incident_description,
                incident_priority=assignment.incident_priority,
                incident_type="handover",  # Since this comes from handover system
                incident_category="Application",  # Default, can be enhanced
                
                # Status and response
                assignment_status=assignment.assignment_status,
                response_status=assignment.assignment_status,
                response_comments=response_comment,
                assignment_notes=assignment.assignment_notes,
                
                # Timing information
                assigned_at=assignment.assigned_at,
                responded_at=datetime.utcnow(),
                
                # Context and references
                handover_request_id=assignment.handover_request_id,
                incident_assignment_id=assignment.id,
                incident_assignment_response_id=existing_response.id if existing_response else response.id,
                
                # Team and account context
                account_id=assignment.account_id,
                team_id=assignment.team_id
            )
            db.session.add(log_entry)
            current_app.logger.info(f"Created fallback incident response log for assignment: {assignment.incident_title}")
        
        # Commit changes
        db.session.commit()
        
        # Send email notification to the assigner
        try:
            from services.email_service import send_handover_email
            assigner = User.query.get(assignment.assigned_by_id)
            if assigner and assigner.email:
                status_display = action.title()
                subject = f"Incident Assignment {status_display}: {assignment.incident_title}"
                
                email_body = f"""
                <h3>Incident Assignment Response</h3>
                <p><strong>Incident:</strong> {assignment.incident_title}</p>
                <p><strong>Priority:</strong> {assignment.incident_priority}</p>
                <p><strong>Status:</strong> {status_display}</p>
                <p><strong>Responded by:</strong> {current_user.username} ({current_user.first_name} {current_user.last_name})</p>
                {f'<p><strong>Comments:</strong> {comments}</p>' if comments else ''}
                <p><strong>Response Time:</strong> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC</p>
                
                <hr>
                <p style="color: #6c757d; font-size: 0.9rem;">
                    This is an automated notification from the Shift Handover Application.
                </p>
                """
                
                # Note: send_handover_email is disabled for local development
                # send_handover_email(shift_object)  # This function only takes shift parameter
                current_app.logger.info(f"Email notification skipped for local development - would send to {assigner.email}")
                
        except Exception as email_error:
            current_app.logger.error(f"Failed to send assignment response email: {str(email_error)}")
            # Don't fail the request if email fails
        
        # Log the action
        log_action(
            f'Assignment {action.title()}',
            f'User {current_user.username} {action}ed incident assignment #{assignment_id}: {assignment.incident_title}'
        )
        
        return jsonify({
            'success': True,
            'message': f'Assignment {action}ed successfully',
            'new_status': assignment.assignment_status
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Assignment action error: {str(e)}")
        return jsonify({'success': False, 'message': f'Error processing request: {str(e)}'})

@user_profile_bp.route('/admin/incident-response-logs')
@login_required
def admin_incident_response_logs():
    """Admin-only view for comprehensive handover incident response logs"""
    logger.debug(f"\n🚨🚨🚨 INCIDENT RESPONSE LOGS ROUTE CALLED by {current_user.username} (Role: {current_user.role}) 🚨🚨🚨\n")
    import sys
    sys.stdout.flush()
    
    # Check if user has admin privileges
    if current_user.role not in ['super_admin', 'account_admin', 'team_admin']:
        logger.debug(f"[ADMIN_LOGS DEBUG] Access denied for user {current_user.username} with role {current_user.role}")
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('main.dashboard'))
    
    logger.debug(f"[ADMIN_LOGS DEBUG] User {current_user.username} has access (Role: {current_user.role})")
    
    try:
        from models.handover_enhanced import HandoverIncidentResponseLog
        from sqlalchemy import desc, func
        
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        
        # Get filter parameters
        incident_search = request.args.get('incident_search', '').strip()
        status_filter = request.args.get('status_filter', '').strip()
        date_from = request.args.get('date_from', '').strip()
        date_to = request.args.get('date_to', '').strip()
        
        # Debug logging for filters
        logger.debug("🔍 STARTING FILTER DEBUG SECTION 🔍")
        current_app.logger.info(f"[FILTER DEBUG] incident_search: '{incident_search}'")
        current_app.logger.info(f"[FILTER DEBUG] status_filter: '{status_filter}'")
        current_app.logger.info(f"[FILTER DEBUG] date_from: '{date_from}'")
        current_app.logger.info(f"[FILTER DEBUG] date_to: '{date_to}'")
        logger.debug(f"[FILTER DEBUG] incident_search: '{incident_search}'")
        logger.debug(f"[FILTER DEBUG] status_filter: '{status_filter}'")
        logger.debug(f"[FILTER DEBUG] date_from: '{date_from}'")
        logger.debug(f"[FILTER DEBUG] date_to: '{date_to}'")
        
        # Build query
        query = HandoverIncidentResponseLog.query
        
        # Apply filters independently
        if incident_search:
            query = query.filter(
                db.or_(
                    HandoverIncidentResponseLog.incident_number.ilike(f'%{incident_search}%'),
                    HandoverIncidentResponseLog.incident_title.ilike(f'%{incident_search}%')
                )
            )
            logger.debug(f"[FILTER DEBUG] Applied incident search filter")
            
        if status_filter:
            # Make sure we're comparing with exact status values
            logger.debug(f"[FILTER DEBUG] Applying status filter: '{status_filter}'")
            query = query.filter(HandoverIncidentResponseLog.assignment_status == status_filter)
            logger.debug(f"[FILTER DEBUG] Status filter applied successfully")
            
        if date_from:
            try:
                from datetime import datetime
                # Try different date formats
                date_from_obj = None
                for fmt in ['%d-%m-%Y', '%Y-%m-%d', '%m/%d/%Y']:
                    try:
                        date_from_obj = datetime.strptime(date_from, fmt).date()
                        break
                    except ValueError:
                        continue
                
                if date_from_obj:
                    # Use date comparison on the datetime field
                    query = query.filter(func.date(HandoverIncidentResponseLog.response_datetime) >= date_from_obj)
                    logger.debug(f"[FILTER DEBUG] Applied date_from filter: {date_from_obj}")
                else:
                    logger.debug(f"[FILTER DEBUG] Could not parse date_from: {date_from}")
            except Exception as e:
                logger.debug(f"[FILTER DEBUG] Error with date_from: {e}")
                
        if date_to:
            try:
                from datetime import datetime
                # Try different date formats
                date_to_obj = None
                for fmt in ['%d-%m-%Y', '%Y-%m-%d', '%m/%d/%Y']:
                    try:
                        date_to_obj = datetime.strptime(date_to, fmt).date()
                        break
                    except ValueError:
                        continue
                
                if date_to_obj:
                    # Use date comparison on the datetime field
                    query = query.filter(func.date(HandoverIncidentResponseLog.response_datetime) <= date_to_obj)
                    logger.debug(f"[FILTER DEBUG] Applied date_to filter: {date_to_obj}")
                else:
                    logger.debug(f"[FILTER DEBUG] Could not parse date_to: {date_to}")
            except Exception as e:
                logger.debug(f"[FILTER DEBUG] Error with date_to: {e}")
        
        # Order by most recent first
        query = query.order_by(desc(HandoverIncidentResponseLog.response_datetime))
        
        # Debug: Check what records exist and their status values
        all_logs = HandoverIncidentResponseLog.query.all()
        logger.debug(f"[FILTER DEBUG] Total logs in database: {len(all_logs)}")
        unique_statuses = set()
        for log in all_logs[:10]:  # Show first 10 records
            unique_statuses.add(log.assignment_status)
            logger.debug(f"[FILTER DEBUG] Log ID {log.id}: status='{log.assignment_status}', incident='{log.incident_number}', date='{log.response_datetime}'")
        
        logger.debug(f"[FILTER DEBUG] Unique status values in database: {list(unique_statuses)}")
        
        # Apply the final query and debug results
        final_logs = query.all()
        logger.debug(f"[FILTER DEBUG] Final query returned {len(final_logs)} records before pagination")
        for log in final_logs[:3]:  # Show first 3 filtered results
            logger.debug(f"[FILTER DEBUG] Filtered result: ID {log.id}, status='{log.assignment_status}', incident='{log.incident_number}'")
        
        # Paginate results
        logs = query.paginate(page=page, per_page=per_page, error_out=False)
        
        logger.debug(f"[FILTER DEBUG] Paginated results: {logs.total} total, showing {len(logs.items)} on page {page}")
        
        log_action('Admin View', f'Viewed incident response logs (Page {page})')
        
        return render_template('admin/incident_response_logs.html', 
                             logs=logs, 
                             title="Handover Incident Response Logs")
        
    except Exception as e:
        current_app.logger.error(f"Error loading incident response logs: {str(e)}")
        flash('Error loading incident response logs.', 'error')
        return redirect(url_for('main.dashboard'))