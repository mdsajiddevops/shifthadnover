"""
Handover Notification Service

Handles all notification logic for the handover workflow including:
- Email notifications to incoming shift engineers
- In-app notifications and badges
- Reminder notifications for pending handovers
- Escalation notifications for overdue handovers

Design Pattern: Strategy Pattern + Observer Pattern
- Different notification strategies (email, in-app, SMS)
- Event-driven notifications based on handover state changes
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional
from flask import current_app, render_template_string
from flask_mail import Message
from models.models import (
    db, Incident, HandoverNotification, TeamMember
)
from services.audit_service import log_action
import logging

class HandoverNotificationService:
    """
    Manages all notifications for the handover workflow.
    
    Notification Types:
    - pending_handover: Initial notification when handover is created
    - reminder: Reminder for pending handovers (after 30 mins)
    - escalation: Escalation for overdue handovers (after 2 hours)
    - acceptance_confirmation: Confirmation when handover is accepted
    - rejection_notification: Notification when handover is rejected
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Notification configuration
        self.reminder_threshold_minutes = 30
        self.escalation_threshold_minutes = 120
        
        # Email templates
        self.email_templates = {
            'pending_handover': self._get_pending_handover_template(),
            'reminder': self._get_reminder_template(),
            'escalation': self._get_escalation_template(),
            'acceptance_confirmation': self._get_acceptance_template(),
            'rejection_notification': self._get_rejection_template()
        }

    def send_pending_handover_notification(self, incident_id: int, recipient_email: str, 
                                         recipient_name: str) -> Dict:
        """
        Send initial notification when incident handover is created.
        
        Args:
            incident_id: ID of incident being handed over
            recipient_email: Email of incoming engineer
            recipient_name: Name of incoming engineer
            
        Returns:
            Dict with success status and details
        """
        try:
            incident = Incident.query.get(incident_id)
            if not incident:
                return {'success': False, 'message': 'Incident not found'}
            
            # Prepare email data
            email_data = {
                'recipient_name': recipient_name,
                'incident_title': incident.title,
                'incident_id': incident.id,
                'incident_priority': incident.priority,
                'incident_description': incident.description or incident.handover or 'No description provided',
                'assigned_from': incident.assigned_to or 'Previous shift',
                'handover_url': f"{current_app.config.get('BASE_URL', '')}/handover/pending",
                'initiated_at': incident.handover_initiated_at.strftime('%Y-%m-%d %H:%M:%S') if incident.handover_initiated_at else 'Unknown'
            }
            
            # Send email
            email_result = self._send_email(
                recipient_email=recipient_email,
                subject=f"🔄 Incident Handover Required: {incident.title}",
                template=self.email_templates['pending_handover'],
                template_data=email_data
            )
            
            # Update notification record
            if email_result['success']:
                self._update_notification_status(incident_id, 'pending_handover', recipient_name, True)
            
            # Log action
            log_action(
                'Handover Notification Sent',
                f'Pending handover notification sent to {recipient_name} for incident {incident.title}'
            )
            
            return {
                'success': email_result['success'],
                'message': f"Handover notification sent to {recipient_name}",
                'incident_id': incident_id,
                'recipient': recipient_name
            }
            
        except Exception as e:
            self.logger.error(f"Error sending pending handover notification: {str(e)}")
            return {'success': False, 'message': f'Error sending notification: {str(e)}'}

    def send_reminder_notifications(self) -> Dict:
        """
        Send reminder notifications for handovers pending beyond threshold.
        
        Returns:
            Dict with count of reminders sent
        """
        try:
            threshold_time = datetime.now() - timedelta(minutes=self.reminder_threshold_minutes)
            
            # Find incidents pending beyond threshold without recent reminders
            pending_incidents = db.session.query(Incident).filter(
                Incident.handover_status == 'Pending',
                Incident.handover_initiated_at <= threshold_time
            ).all()
            
            reminders_sent = 0
            
            for incident in pending_incidents:
                # Check if reminder was already sent in last 30 minutes
                recent_reminder = HandoverNotification.query.filter(
                    HandoverNotification.incident_id == incident.id,
                    HandoverNotification.notification_type == 'reminder',
                    HandoverNotification.sent_at >= datetime.now() - timedelta(minutes=30)
                ).first()
                
                if not recent_reminder and incident.handover_assigned_to:
                    # Get recipient email
                    member = TeamMember.query.filter_by(name=incident.handover_assigned_to).first()
                    if member and member.email:
                        email_data = {
                            'recipient_name': incident.handover_assigned_to,
                            'incident_title': incident.title,
                            'incident_id': incident.id,
                            'time_pending': self._format_time_pending(incident.handover_initiated_at),
                            'handover_url': f"{current_app.config.get('BASE_URL', '')}/handover/pending"
                        }
                        
                        email_result = self._send_email(
                            recipient_email=member.email,
                            subject=f"⏰ Reminder: Incident Handover Pending - {incident.title}",
                            template=self.email_templates['reminder'],
                            template_data=email_data
                        )
                        
                        if email_result['success']:
                            reminders_sent += 1
                            self._create_notification_record(
                                incident.id, 'reminder', incident.handover_assigned_to,
                                incident.handover_assigned_to_id, incident.account_id, incident.team_id
                            )
            
            self.logger.info(f"Sent {reminders_sent} handover reminder notifications")
            
            return {
                'success': True,
                'reminders_sent': reminders_sent,
                'message': f'Sent {reminders_sent} reminder notifications'
            }
            
        except Exception as e:
            self.logger.error(f"Error sending reminder notifications: {str(e)}")
            return {'success': False, 'message': f'Error sending reminders: {str(e)}'}

    def send_escalation_notifications(self) -> Dict:
        """
        Send escalation notifications for overdue handovers.
        
        Returns:
            Dict with count of escalations sent
        """
        try:
            threshold_time = datetime.now() - timedelta(minutes=self.escalation_threshold_minutes)
            
            # Find incidents pending beyond escalation threshold
            overdue_incidents = db.session.query(Incident).filter(
                Incident.handover_status == 'Pending',
                Incident.handover_initiated_at <= threshold_time
            ).all()
            
            escalations_sent = 0
            
            for incident in overdue_incidents:
                # Check if escalation was already sent
                existing_escalation = HandoverNotification.query.filter(
                    HandoverNotification.incident_id == incident.id,
                    HandoverNotification.notification_type == 'escalation'
                ).first()
                
                if not existing_escalation:
                    # Send to both assignee and team email
                    recipients = []
                    
                    # Add assigned engineer
                    if incident.handover_assigned_to:
                        member = TeamMember.query.filter_by(name=incident.handover_assigned_to).first()
                        if member and member.email:
                            recipients.append({'email': member.email, 'name': member.name})
                    
                    # Add team email
                    team_email = current_app.config.get('TEAM_EMAIL')
                    if team_email:
                        recipients.append({'email': team_email, 'name': 'Team'})
                    
                    for recipient in recipients:
                        email_data = {
                            'recipient_name': recipient['name'],
                            'incident_title': incident.title,
                            'incident_id': incident.id,
                            'time_overdue': self._format_time_pending(incident.handover_initiated_at),
                            'assigned_to': incident.handover_assigned_to,
                            'handover_url': f"{current_app.config.get('BASE_URL', '')}/handover/pending"
                        }
                        
                        email_result = self._send_email(
                            recipient_email=recipient['email'],
                            subject=f"🚨 ESCALATION: Overdue Incident Handover - {incident.title}",
                            template=self.email_templates['escalation'],
                            template_data=email_data
                        )
                        
                        if email_result['success']:
                            escalations_sent += 1
                    
                    # Create escalation notification record
                    self._create_notification_record(
                        incident.id, 'escalation', incident.handover_assigned_to or 'Team',
                        incident.handover_assigned_to_id, incident.account_id, incident.team_id
                    )
            
            self.logger.info(f"Sent {escalations_sent} handover escalation notifications")
            
            return {
                'success': True,
                'escalations_sent': escalations_sent,
                'message': f'Sent {escalations_sent} escalation notifications'
            }
            
        except Exception as e:
            self.logger.error(f"Error sending escalation notifications: {str(e)}")
            return {'success': False, 'message': f'Error sending escalations: {str(e)}'}

    def get_pending_notifications_count(self, engineer_name: str) -> int:
        """Get count of pending handover notifications for an engineer."""
        try:
            count = Incident.query.filter(
                Incident.handover_status == 'Pending',
                Incident.handover_assigned_to == engineer_name
            ).count()
            return count
        except Exception as e:
            self.logger.error(f"Error getting notification count: {str(e)}")
            return 0

    def _send_email(self, recipient_email: str, subject: str, template: str, 
                   template_data: Dict) -> Dict:
        """Send email using Flask-Mail."""
        try:
            mail = current_app.extensions.get('mail')
            if not mail:
                return {'success': False, 'message': 'Mail service not configured'}
            
            # Render template with data
            html_body = render_template_string(template, **template_data)
            
            # Create message
            msg = Message(
                subject=subject,
                recipients=[recipient_email],
                html=html_body,
                sender=current_app.config.get('MAIL_DEFAULT_SENDER')
            )
            
            # Send email
            mail.send(msg)
            
            return {'success': True, 'message': 'Email sent successfully'}
            
        except Exception as e:
            self.logger.error(f"Error sending email: {str(e)}")
            return {'success': False, 'message': f'Email error: {str(e)}'}

    def _format_time_pending(self, initiated_at: datetime) -> str:
        """Format time pending for display."""
        if not initiated_at:
            return 'Unknown'
        
        time_diff = datetime.now() - initiated_at
        hours = int(time_diff.total_seconds() // 3600)
        minutes = int((time_diff.total_seconds() % 3600) // 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"

    def _update_notification_status(self, incident_id: int, notification_type: str,
                                  recipient: str, email_sent: bool):
        """Update existing notification record."""
        try:
            notification = HandoverNotification.query.filter_by(
                incident_id=incident_id,
                notification_type=notification_type,
                recipient=recipient
            ).first()
            
            if notification:
                notification.email_sent = email_sent
                notification.status = 'sent' if email_sent else 'failed'
                db.session.commit()
                
        except Exception as e:
            self.logger.error(f"Error updating notification status: {str(e)}")

    def _create_notification_record(self, incident_id: int, notification_type: str,
                                  recipient: str, recipient_id: int, account_id: int, team_id: int):
        """Create new notification record."""
        try:
            notification = HandoverNotification(
                incident_id=incident_id,
                notification_type=notification_type,
                recipient=recipient,
                recipient_id=recipient_id,
                email_sent=True,
                status='sent',
                account_id=account_id,
                team_id=team_id
            )
            db.session.add(notification)
            db.session.commit()
            
        except Exception as e:
            self.logger.error(f"Error creating notification record: {str(e)}")

    def _get_pending_handover_template(self) -> str:
        """Get email template for pending handover notification."""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body { font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px 8px 0 0; }
                .content { background: #f8f9fa; padding: 30px; border-radius: 0 0 8px 8px; }
                .incident-details { background: white; padding: 20px; margin: 20px 0; border-radius: 8px; border-left: 4px solid #667eea; }
                .action-button { display: inline-block; background: #28a745; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin: 15px 0; }
                .priority-high { border-left-color: #dc3545; }
                .priority-critical { border-left-color: #721c24; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>🔄 Incident Handover Required</h2>
                    <p>You have been assigned a new incident for the incoming shift</p>
                </div>
                <div class="content">
                    <p>Hello <strong>{{ recipient_name }}</strong>,</p>
                    
                    <p>An incident has been handed over to you for the upcoming shift. Please review and take appropriate action.</p>
                    
                    <div class="incident-details {% if incident_priority in ['High', 'Critical'] %}priority-{{ incident_priority.lower() }}{% endif %}">
                        <h3>{{ incident_title }}</h3>
                        <p><strong>Incident ID:</strong> #{{ incident_id }}</p>
                        <p><strong>Priority:</strong> <span style="color: {% if incident_priority == 'Critical' %}#721c24{% elif incident_priority == 'High' %}#dc3545{% else %}#28a745{% endif %};">{{ incident_priority }}</span></p>
                        <p><strong>Handed over from:</strong> {{ assigned_from }}</p>
                        <p><strong>Initiated at:</strong> {{ initiated_at }}</p>
                        <p><strong>Description:</strong></p>
                        <div style="background: #f1f3f4; padding: 15px; border-radius: 4px; margin-top: 10px;">
                            {{ incident_description }}
                        </div>
                    </div>
                    
                    <p><strong>Actions Required:</strong></p>
                    <ul>
                        <li><strong>Accept:</strong> Take ownership of the incident</li>
                        <li><strong>Reject:</strong> Decline with mandatory explanation</li>
                    </ul>
                    
                    <a href="{{ handover_url }}" class="action-button">🎯 Review Handover</a>
                    
                    <p style="margin-top: 30px; color: #6c757d; font-size: 14px;">
                        Please respond as soon as possible to ensure smooth shift transition.<br>
                        This is an automated notification from the Shift Handover System.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """

    def _get_reminder_template(self) -> str:
        """Get email template for reminder notification."""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body { font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background: linear-gradient(135deg, #ffc107 0%, #ff8c00 100%); color: white; padding: 20px; border-radius: 8px 8px 0 0; }
                .content { background: #f8f9fa; padding: 30px; border-radius: 0 0 8px 8px; }
                .reminder-box { background: #fff3cd; border: 1px solid #ffeaa7; padding: 20px; margin: 20px 0; border-radius: 8px; }
                .action-button { display: inline-block; background: #ffc107; color: #212529; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin: 15px 0; font-weight: bold; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>⏰ Reminder: Incident Handover Pending</h2>
                    <p>Action required on pending incident handover</p>
                </div>
                <div class="content">
                    <p>Hello <strong>{{ recipient_name }}</strong>,</p>
                    
                    <div class="reminder-box">
                        <h3>⚠️ Pending Handover Reminder</h3>
                        <p><strong>Incident:</strong> {{ incident_title }}</p>
                        <p><strong>Incident ID:</strong> #{{ incident_id }}</p>
                        <p><strong>Time Pending:</strong> {{ time_pending }}</p>
                    </div>
                    
                    <p>This incident handover has been pending for some time. Please review and take action:</p>
                    
                    <ul>
                        <li><strong>Accept:</strong> If you can handle the incident</li>
                        <li><strong>Reject:</strong> If unable to handle (provide explanation)</li>
                    </ul>
                    
                    <a href="{{ handover_url }}" class="action-button">🎯 Take Action Now</a>
                    
                    <p style="margin-top: 30px; color: #6c757d; font-size: 14px;">
                        Prompt action helps ensure smooth shift operations.<br>
                        This is an automated reminder from the Shift Handover System.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """

    def _get_escalation_template(self) -> str:
        """Get email template for escalation notification."""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body { font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background: linear-gradient(135deg, #dc3545 0%, #c82333 100%); color: white; padding: 20px; border-radius: 8px 8px 0 0; }
                .content { background: #f8f9fa; padding: 30px; border-radius: 0 0 8px 8px; }
                .escalation-box { background: #f8d7da; border: 1px solid #f5c6cb; padding: 20px; margin: 20px 0; border-radius: 8px; }
                .action-button { display: inline-block; background: #dc3545; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin: 15px 0; font-weight: bold; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>🚨 ESCALATION: Overdue Incident Handover</h2>
                    <p>Immediate attention required for overdue handover</p>
                </div>
                <div class="content">
                    <p>Hello <strong>{{ recipient_name }}</strong>,</p>
                    
                    <div class="escalation-box">
                        <h3>🚨 OVERDUE HANDOVER ALERT</h3>
                        <p><strong>Incident:</strong> {{ incident_title }}</p>
                        <p><strong>Incident ID:</strong> #{{ incident_id }}</p>
                        <p><strong>Assigned to:</strong> {{ assigned_to }}</p>
                        <p><strong>Time Overdue:</strong> {{ time_overdue }}</p>
                    </div>
                    
                    <p><strong>This incident handover has exceeded the standard response time and requires immediate attention.</strong></p>
                    
                    <p>Required Actions:</p>
                    <ul>
                        <li>Review the incident details immediately</li>
                        <li>Accept ownership or reject with detailed explanation</li>
                        <li>Escalate to management if needed</li>
                    </ul>
                    
                    <a href="{{ handover_url }}" class="action-button">🚨 URGENT ACTION REQUIRED</a>
                    
                    <p style="margin-top: 30px; color: #721c24; font-size: 14px; font-weight: bold;">
                        This is an escalated notification. Please respond immediately.<br>
                        Management has been notified of this overdue handover.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """

    def _get_acceptance_template(self) -> str:
        """Get email template for acceptance confirmation."""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body { font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background: linear-gradient(135deg, #28a745 0%, #20c997 100%); color: white; padding: 20px; border-radius: 8px 8px 0 0; }
                .content { background: #f8f9fa; padding: 30px; border-radius: 0 0 8px 8px; }
                .success-box { background: #d4edda; border: 1px solid #c3e6cb; padding: 20px; margin: 20px 0; border-radius: 8px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>✅ Handover Accepted Successfully</h2>
                    <p>Incident ownership has been transferred</p>
                </div>
                <div class="content">
                    <div class="success-box">
                        <h3>✅ Handover Completed</h3>
                        <p>The incident handover has been successfully accepted.</p>
                    </div>
                    
                    <p style="color: #6c757d; font-size: 14px;">
                        This is a confirmation from the Shift Handover System.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """

    def _get_rejection_template(self) -> str:
        """Get email template for rejection notification."""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body { font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background: linear-gradient(135deg, #dc3545 0%, #c82333 100%); color: white; padding: 20px; border-radius: 8px 8px 0 0; }
                .content { background: #f8f9fa; padding: 30px; border-radius: 0 0 8px 8px; }
                .rejection-box { background: #f8d7da; border: 1px solid #f5c6cb; padding: 20px; margin: 20px 0; border-radius: 8px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>❌ Handover Rejected</h2>
                    <p>Incident handover has been declined</p>
                </div>
                <div class="content">
                    <div class="rejection-box">
                        <h3>❌ Handover Rejected</h3>
                        <p>The incident handover has been rejected. Please review the rejection reason and take appropriate action.</p>
                    </div>
                    
                    <p style="color: #6c757d; font-size: 14px;">
                        This is a notification from the Shift Handover System.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
