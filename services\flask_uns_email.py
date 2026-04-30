"""
UNS Email Integration for Flask Application
Integrates the UNS email service with the existing shift handover application
"""

import os
import logging
from flask import current_app
from typing import List, Optional, Union
from services.uns_email_service import UNSEmailSender, UNSEmailConfig, EmailRequest, send_uns_email

logger = logging.getLogger(__name__)

class FlaskUNSEmailIntegration:
    """Integration layer between Flask app and UNS Email Service"""
    
    def __init__(self, app=None):
        self.app = app
        self._email_sender = None
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the extension with Flask app"""
        self.app = app
        
        # Load UNS configuration from the database SMTPConfig table (same as Flask-Mail)
        logger.debug(f"[UNS_EMAIL] 📧 Loading configuration from database SMTPConfig table...")
        
        try:
            from models.smtp_config import SMTPConfig
            
            # Use the same database SMTP settings as Flask-Mail for consistency
            uns_config = UNSEmailConfig()
            uns_config.host = SMTPConfig.get_config('smtp_server')
            uns_config.port = int(SMTPConfig.get_config('smtp_port', 587))
            uns_config.username = SMTPConfig.get_config('smtp_username')
            uns_config.password = SMTPConfig.get_config('smtp_password')
            uns_config.sender_address = SMTPConfig.get_config('mail_default_sender')
            uns_config.sender_name = app.config.get('UNS_EMAIL_SENDER_NAME', 'Shift Handover System')
            
            # Validate configuration
            if not uns_config.host:
                logger.debug(f"[UNS_EMAIL] ❌ No SMTP server configured in database")
            if not uns_config.username:
                logger.debug(f"[UNS_EMAIL] ❌ No SMTP username configured in database")
            if not uns_config.password:
                logger.debug(f"[UNS_EMAIL] ❌ No SMTP password configured in database")
            if not uns_config.sender_address:
                logger.debug(f"[UNS_EMAIL] ❌ No sender address configured in database")
                
            logger.debug(f"[UNS_EMAIL] ✅ Configuration loaded from database: {uns_config.host}:{uns_config.port}")
            
        except Exception as e:
            logger.debug(f"[UNS_EMAIL] ❌ Failed to load from database: {e}")
            logger.debug(f"[UNS_EMAIL] ⚠️ UNS Email will not work without database configuration")
            uns_config = UNSEmailConfig()  # Empty config - will fail validation
        if 'UNS_EMAIL_SENDER_NAME' in app.config:
            uns_config.sender_name = app.config['UNS_EMAIL_SENDER_NAME']
        
        # Store configuration in app context
        app.config['UNS_EMAIL_CONFIG'] = uns_config
        
        # Initialize email sender
        self._email_sender = UNSEmailSender(uns_config)
        
        logger.info("UNS Email Integration initialized successfully")
    
    @property
    def email_sender(self) -> UNSEmailSender:
        """Get the UNS email sender instance"""
        if self._email_sender is None:
            raise RuntimeError("UNS Email not initialized. Call init_app() first.")
        return self._email_sender
    
    def send_handover_email(self, shift, recipients: Optional[List[str]] = None) -> dict:
        """
        Send shift handover email using UNS service
        Replaces the existing send_handover_email function
        """
        logger.debug(f"[DEBUG] ⚠️ send_handover_email called from UNS service for shift_id={shift.id}")
        
        try:
            from models.models import Incident, ShiftKeyPoint, TeamMember, Team, User, Account
            from models.app_config import AppConfig
            
            # Get recipients (same logic as original function)
            if not recipients:
                recipients = self._get_handover_recipients(shift)
            
            if not recipients:
                return {
                    'success': False,
                    'error': 'No recipients configured for handover emails',
                    'details': 'Configure recipients in Admin > Secrets Management > Email Recipients'
                }
            
            # Get Account and Team names for email subject prefix
            account_name = ""
            team_name = ""
            if shift.account_id:
                account = Account.query.get(shift.account_id)
                if account:
                    account_name = account.name
            if shift.team_id:
                team = Team.query.get(shift.team_id)
                if team:
                    team_name = team.name
            
            # Build subject with Account-Team prefix (e.g., "CTC-Supply Chain-L2 🔄 Night to Morning Shift Handover - 2026-02-03")
            subject_prefix = ""
            if account_name and team_name:
                subject_prefix = f"{account_name}-{team_name} "
            elif account_name:
                subject_prefix = f"{account_name} "
            elif team_name:
                subject_prefix = f"{team_name} "
            
            # Generate email content
            subject = f"{subject_prefix}🔄 {shift.current_shift_type} to {shift.next_shift_type} Shift Handover - {shift.date}"
            html_content = self._generate_handover_html(shift)
            
            # Create email request
            email_request = EmailRequest(
                to=recipients,
                subject=subject,
                body=html_content,
                is_html=True
            )
            
            # Send via UNS
            result = self.email_sender.send(email_request)
            
            if result['success']:
                logger.info(f"UNS Handover email sent successfully to {result['recipients']} recipients")
            else:
                logger.error(f"UNS Handover email failed: {result['error']}")
            
            return result
            
        except Exception as e:
            error_msg = f"UNS Handover email error: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': 'Handover email failed',
                'details': error_msg
            }
    
    def send_incident_assignment_notification(self, incident_id: str, recipient_email: str, recipient_name: str) -> dict:
        """Send incident assignment notification using UNS service"""
        try:
            from models.models import Incident
            
            incident = Incident.query.get(incident_id)
            if not incident:
                return {
                    'success': False,
                    'error': 'Incident not found',
                    'details': f'No incident found with ID: {incident_id}'
                }
            
            subject = f"🔄 Incident Assignment: {incident.title}"
            html_content = self._generate_incident_assignment_html(incident, recipient_name)
            
            email_request = EmailRequest(
                to=recipient_email,
                subject=subject,
                body=html_content,
                is_html=True
            )
            
            result = self.email_sender.send(email_request)
            
            if result['success']:
                logger.info(f"UNS Incident assignment email sent to {recipient_email}")
            else:
                logger.error(f"UNS Incident assignment email failed: {result['error']}")
            
            return result
            
        except Exception as e:
            error_msg = f"UNS Incident assignment email error: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': 'Incident assignment email failed',
                'details': error_msg
            }
    
    def send_test_email(self, recipients: List[str]) -> dict:
        """Send test email using UNS service"""
        try:
            subject = "🧪 UNS Email Service Test - Shift Handover System"
            html_content = self._generate_test_email_html()
            
            email_request = EmailRequest(
                to=recipients,
                subject=subject,
                body=html_content,
                is_html=True
            )
            
            result = self.email_sender.send(email_request)
            
            if result['success']:
                logger.info(f"UNS Test email sent successfully to {result['recipients']} recipients")
            else:
                logger.error(f"UNS Test email failed: {result['error']}")
            
            return result
            
        except Exception as e:
            error_msg = f"UNS Test email error: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': 'Test email failed',
                'details': error_msg
            }
    
    def test_connection(self) -> dict:
        """Test UNS SMTP connection"""
        return self.email_sender.test_connection()
    
    def _get_handover_recipients(self, shift) -> List[str]:
        """Get handover email recipients (same logic as original function)"""
        from models.app_config import AppConfig
        from models.models import User
        
        recipients = set()
        
        # 1. Add configured handover email recipients
        configured_recipients = AppConfig.get_config('handover_email_recipients', '')
        if configured_recipients:
            for email in configured_recipients.split(','):
                email = email.strip()
                if email:
                    recipients.add(email)
        
        # 2. Add next shift engineers
        if hasattr(shift, 'next_engineers'):
            for engineer in shift.next_engineers:
                if hasattr(engineer, 'email') and engineer.email:
                    recipients.add(engineer.email)
        
        # 3. Add current shift engineers
        if hasattr(shift, 'current_engineers'):
            for engineer in shift.current_engineers:
                if hasattr(engineer, 'email') and engineer.email:
                    recipients.add(engineer.email)
        
        # 4. Fallback: Add team administrators
        if not recipients and shift.team_id:
            team_admins = User.query.filter_by(team_id=shift.team_id, role='team_admin').all()
            for admin in team_admins:
                if admin.email:
                    recipients.add(admin.email)
        
        return list(recipients)
    
    def _generate_handover_html(self, shift) -> str:
        """Generate HTML content for handover email"""
        from models.models import Incident, ShiftKeyPoint
        
        # Get incidents for this shift
        open_incidents = Incident.query.filter_by(shift_id=shift.id).filter(
            Incident.status == 'Active'
        ).all()
        
        # Get key points for this shift - only Open and In Progress, exclude Closed
        key_points = ShiftKeyPoint.query.filter(
            ShiftKeyPoint.shift_id == shift.id,
            ShiftKeyPoint.status.in_(['Open', 'In Progress'])
        ).all()
        
        # Generate HTML
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .content {{ padding: 20px; }}
                .section {{ margin-bottom: 30px; }}
                .incident {{ background: #f8f9fa; border-left: 4px solid #007bff; padding: 15px; margin: 10px 0; }}
                .priority-high {{ border-left-color: #dc3545; }}
                .priority-critical {{ border-left-color: #6f42c1; }}
                .keypoint {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 10px 0; }}
                .footer {{ background: #f8f9fa; padding: 15px; text-align: center; font-size: 0.9em; color: #6c757d; }}
                h2 {{ color: #495057; border-bottom: 2px solid #007bff; padding-bottom: 10px; text-align: center; }}
                h3 {{ color: #495057; margin-top: 25px; }}
            </style>
        </head>
        <body>
            <div class="content">
                <div class="section">
                    <h2>📊 Shift Handover Summary</h2>
                    <p><strong>Date:</strong> {shift.date}</p>
                    <p><strong>Shift Transition:</strong> {shift.current_shift_type} to {shift.next_shift_type}</p>
                    <p><strong>Total Incidents:</strong> {len(open_incidents)}</p>
                    <p><strong>Key Points:</strong> {len(key_points)}</p>
                </div>
        """
        
        # Add incidents section
        if open_incidents:
            html += """
                <div class="section">
                    <h2>🚨 Active Incidents</h2>
            """
            
            for incident in open_incidents:
                priority_class = ""
                if hasattr(incident, 'priority') and incident.priority:
                    priority_class = f"priority-{incident.priority.lower()}"
                
                html += f"""
                    <div class="incident {priority_class}">
                        <h3>{incident.title}</h3>
                        <p><strong>ID:</strong> {incident.id}</p>
                        <p><strong>Priority:</strong> {getattr(incident, 'priority', 'Normal')}</p>
                        <p><strong>Status:</strong> {incident.status}</p>
                        <p><strong>Assigned To:</strong> {getattr(incident, 'assigned_to', 'Unassigned')}</p>
                        {f'<p><strong>Description:</strong> {incident.description}</p>' if hasattr(incident, 'description') and incident.description else ''}
                    </div>
                """
            
            html += "</div>"
        
        # Add key points section
        if key_points:
            html += """
                <div class="section">
                    <h2>🔑 Key Points</h2>
            """
            
            for kp in key_points:
                html += f"""
                    <div class="keypoint">
                        <p><strong>{kp.description}</strong></p>
                        <p><strong>Status:</strong> {kp.status}</p>
                        <p><strong>Responsible:</strong> {getattr(kp, 'responsible_engineer', 'Unassigned')}</p>
                    </div>
                """
            
            html += "</div>"
        
        # Close HTML
        html += """
            </div>
            
            <div class="footer">
                <p><strong>📧 Generated by UNS Email Service</strong></p>
                <p>Shift Handover Management System</p>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _generate_incident_assignment_html(self, incident, recipient_name: str) -> str:
        """Generate HTML content for incident assignment email"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .header {{ background: linear-gradient(135deg, #ff6b6b, #ee5a24); color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                .incident {{ background: #fff5f5; border: 2px solid #ff6b6b; padding: 20px; border-radius: 8px; }}
                .footer {{ background: #f8f9fa; padding: 15px; text-align: center; font-size: 0.9em; color: #6c757d; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🔄 Incident Assignment</h1>
                <p>New incident assigned to {recipient_name}</p>
            </div>
            
            <div class="content">
                <div class="incident">
                    <h2>{incident.title}</h2>
                    <p><strong>Incident ID:</strong> {incident.id}</p>
                    <p><strong>Priority:</strong> {getattr(incident, 'priority', 'Normal')}</p>
                    <p><strong>Status:</strong> {incident.status}</p>
                    <p><strong>Assigned To:</strong> {recipient_name}</p>
                    {f'<p><strong>Description:</strong> {incident.description}</p>' if hasattr(incident, 'description') and incident.description else ''}
                </div>
                
                <p style="margin-top: 20px;">Please take ownership of this incident and update its status accordingly.</p>
            </div>
            
            <div class="footer">
                <p><strong>📧 Generated by UNS Email Service</strong></p>
                <p>Shift Handover Management System</p>
            </div>
        </body>
        </html>
        """
        return html
    
    def _generate_test_email_html(self) -> str:
        """Generate HTML content for test email"""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .header { background: linear-gradient(135deg, #28a745, #20c997); color: white; padding: 20px; text-align: center; }
                .content { padding: 20px; }
                .success { background: #d4edda; border: 2px solid #28a745; padding: 20px; border-radius: 8px; }
                .footer { background: #f8f9fa; padding: 15px; text-align: center; font-size: 0.9em; color: #6c757d; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🧪 UNS Email Service Test</h1>
                <p>Email Configuration Verification</p>
            </div>
            
            <div class="content">
                <div class="success">
                    <h2>✅ Test Successful!</h2>
                    <p>If you received this email, your UNS email configuration is working correctly!</p>
                    <p>The system can now send shift handover notifications, incident assignments, and other automated emails.</p>
                </div>
                
                <h3>📋 Configuration Details:</h3>
                <ul>
                    <li>✅ SMTP Connection: Successful</li>
                    <li>✅ STARTTLS Encryption: Enabled</li>
                    <li>✅ Authentication: Successful</li>
                    <li>✅ Email Delivery: Successful</li>
                </ul>
            </div>
            
            <div class="footer">
                <p><strong>📧 Generated by UNS Email Service</strong></p>
                <p>Shift Handover Management System</p>
            </div>
        </body>
        </html>
        """
        return html

# Global instance for Flask integration
uns_email = FlaskUNSEmailIntegration()

def init_uns_email(app):
    """Initialize UNS Email with Flask app"""
    uns_email.init_app(app)

# Convenience functions for easy use
def send_handover_email(shift, recipients: Optional[List[str]] = None) -> dict:
    """Send handover email using UNS service"""
    logger.debug(f"[DEBUG] 🔄 send_handover_email wrapper called from UNS service for shift_id={shift.id}")
    return uns_email.send_handover_email(shift, recipients)

def send_incident_assignment_notification(incident_id: str, recipient_email: str, recipient_name: str) -> dict:
    """Send incident assignment notification using UNS service"""
    return uns_email.send_incident_assignment_notification(incident_id, recipient_email, recipient_name)

def send_test_email(recipients: List[str]) -> dict:
    """Send test email using UNS service"""
    return uns_email.send_test_email(recipients)

def test_uns_connection() -> dict:
    """Test UNS SMTP connection"""
    return uns_email.test_connection()