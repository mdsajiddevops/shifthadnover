"""
Email Service for Shift Swap & Leave Management
Handles email notifications for all shift swap and leave workflow events
"""

from flask import current_app
from flask_mail import Message
from models.models import db, User, Team, Account, TeamMember
from models.shift_swap_leave import ShiftSwapRequest, LeaveRequest
from typing import List, Dict, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class ShiftEmailService:
    """Service for sending email notifications for shift swap and leave management"""

    @staticmethod
    def _get_mail_instance():
        """Get Flask-Mail instance with proper configuration"""
        try:
            # Load SMTP configuration from database
            try:
                result = db.session.execute(db.text("SELECT config_key, config_value FROM smtp_config"))
                configs = dict(result.fetchall())
            except Exception:
                # Fallback to app_config table if smtp_config doesn't exist
                result = db.session.execute(db.text("SELECT config_key, config_value FROM app_config WHERE config_key LIKE 'smtp_%' OR config_key LIKE 'mail_%'"))
                configs = dict(result.fetchall())

            if configs:
                # Update Flask app configuration with SMTP settings
                app = current_app._get_current_object()
                
                # Map database config keys to Flask-Mail config keys
                smtp_mapping = {
                    'MAIL_SERVER': configs.get('smtp_server', configs.get('mail_server')),
                    'MAIL_PORT': int(configs.get('smtp_port', configs.get('mail_port', 587))),
                    'MAIL_USE_TLS': configs.get('smtp_use_tls', configs.get('mail_use_tls', 'true')).lower() == 'true',
                    'MAIL_USE_SSL': configs.get('smtp_use_ssl', configs.get('mail_use_ssl', 'false')).lower() == 'true',
                    'MAIL_USERNAME': configs.get('smtp_username', configs.get('mail_username')),
                    'MAIL_PASSWORD': configs.get('smtp_password', configs.get('mail_password')),
                    'MAIL_DEFAULT_SENDER': configs.get('smtp_sender', configs.get('mail_default_sender'))
                }
                
                # Update Flask configuration
                for key, value in smtp_mapping.items():
                    if value is not None:
                        app.config[key] = value

                # Reinitialize Mail
                from flask_mail import Mail
                mail = Mail()
                mail.init_app(app)
                app.extensions['mail'] = mail
                
                return mail
            else:
                return current_app.extensions.get('mail')
        except Exception as e:
            logger.error(f"Error configuring mail: {e}")
            return current_app.extensions.get('mail')

    @staticmethod
    def _get_admins_for_team(account_id: int, team_id: int) -> List[User]:
        """Get admin users for email notifications"""
        try:
            admins = User.query.filter(
                db.or_(
                    User.role == 'super_admin',
                    db.and_(User.role == 'account_admin', User.account_id == account_id),
                    db.and_(User.role == 'team_admin', User.account_id == account_id, User.team_id == team_id)
                ),
                User.is_active == True,
                User.email.isnot(None),
                User.email != ''
            ).all()
            
            return admins
        except Exception as e:
            logger.error(f"Error getting admins: {e}")
            return []

    @staticmethod 
    def _get_team_distribution_list(account_id: int, team_id: int) -> List[str]:
        """Get team distribution list for roster update notifications"""
        try:
            # Get team members with email addresses
            team_members = db.session.query(User).join(TeamMember, User.id == TeamMember.user_id).filter(
                TeamMember.account_id == account_id,
                TeamMember.team_id == team_id,
                User.is_active == True,
                User.email.isnot(None),
                User.email != ''
            ).all()
            
            emails = [member.email for member in team_members if member.email]
            
            # Also include admins
            admins = ShiftEmailService._get_admins_for_team(account_id, team_id)
            for admin in admins:
                if admin.email and admin.email not in emails:
                    emails.append(admin.email)
                    
            return emails
        except Exception as e:
            logger.error(f"Error getting team distribution list: {e}")
            return []

    @staticmethod
    def _get_shift_display_name(shift_code: str) -> str:
        """Convert shift code to display name"""
        shift_names = {
            'D': 'Day Shift',
            'N': 'Night Shift', 
            'E': 'Evening Shift',
            'M': 'Morning Shift',
            'A': 'Afternoon Shift'
        }
        return shift_names.get(shift_code, f'{shift_code} Shift')

    @staticmethod
    def _get_shift_time_range(shift_code: str) -> str:
        """Get time range for shift code"""
        shift_times = {
            'D': '(09:00 - 17:00)',
            'N': '(21:00 - 09:00)', 
            'E': '(17:00 - 01:00)',
            'M': '(06:00 - 14:00)',
            'A': '(13:00 - 21:00)'
        }
        return shift_times.get(shift_code, '')

    @staticmethod
    def send_swap_request_submitted_email(swap_request: ShiftSwapRequest):
        """Send email to admins when a swap request is submitted"""
        try:
            # Get admin recipients
            admins = ShiftEmailService._get_admins_for_team(swap_request.account_id, swap_request.team_id)
            if not admins:
                logger.warning("No admin recipients found for swap request notification")
                return

            recipients = [admin.email for admin in admins if admin.email]
            if not recipients:
                logger.warning("No admin email addresses found for swap request notification")
                return

            # Get team and account info
            team = Team.query.get(swap_request.team_id)
            account = Account.query.get(swap_request.account_id)
            
            # Get shift display names
            original_shift_name = ShiftEmailService._get_shift_display_name(swap_request.original_shift_code)
            original_shift_time = ShiftEmailService._get_shift_time_range(swap_request.original_shift_code)
            swap_shift_name = ShiftEmailService._get_shift_display_name(swap_request.swap_shift_code)
            swap_shift_time = ShiftEmailService._get_shift_time_range(swap_request.swap_shift_code)

            subject = f"Shift Swap Request Submitted – Pending Approval"
            
            html_content = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
                    .content {{ margin: 20px 0; }}
                    .details-table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                    .details-table th {{ background-color: #f8f9fa; padding: 12px; text-align: left; border: 1px solid #dee2e6; }}
                    .details-table td {{ padding: 12px; border: 1px solid #dee2e6; }}
                    .footer {{ margin-top: 30px; padding: 15px; background-color: #f8f9fa; border-radius: 5px; font-size: 0.9em; color: #6c757d; }}
                    .action-button {{ background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block; margin: 10px 5px; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h2>🔄 New Shift Swap Request Submitted</h2>
                    <p style="margin: 10px 0 0 0;">Pending your approval</p>
                </div>
                
                <div class="content">
                    <h3>Request Details</h3>
                    <table class="details-table">
                        <tr><th>Request Type</th><td><strong>Shift Swap</strong></td></tr>
                        <tr><th>Requested By</th><td>{swap_request.requester.first_name} {swap_request.requester.last_name} ({swap_request.requester.username})</td></tr>
                        <tr><th>Swap With</th><td>{swap_request.swap_with.first_name} {swap_request.swap_with.last_name} ({swap_request.swap_with.username})</td></tr>
                        <tr><th>Team</th><td>{team.name if team else 'Unknown'}</td></tr>
                        <tr><th>Account</th><td>{account.name if account else 'Unknown'}</td></tr>
                        <tr><th>Original Date</th><td>{swap_request.original_date}</td></tr>
                        <tr><th>Original Shift</th><td>{original_shift_name} {original_shift_time}</td></tr>
                        <tr><th>Swap Date</th><td>{swap_request.swap_date}</td></tr>
                        <tr><th>Swap Shift</th><td>{swap_shift_name} {swap_shift_time}</td></tr>
                        <tr><th>Reason</th><td>{swap_request.reason}</td></tr>
                        <tr><th>Status</th><td><span style="color: #ffc107; font-weight: bold;">⏳ Pending Approval</span></td></tr>
                        <tr><th>Submitted</th><td>{swap_request.created_at.strftime('%Y-%m-%d %H:%M:%S')}</td></tr>
                    </table>
                </div>
                
                <div class="footer">
                    <p><strong>📧 This is an automated notification.</strong></p>
                    <p>🔗 <strong>Action Required:</strong> Please login to the Shift Management Portal to review and approve/reject this request.</p>
                    <p><em>Shift Handover Management System</em></p>
                </div>
            </body>
            </html>
            """

            # Send email
            mail = ShiftEmailService._get_mail_instance()
            if mail:
                sender = current_app.config.get('MAIL_DEFAULT_SENDER') or current_app.config.get('MAIL_USERNAME')
                msg = Message(subject=subject, recipients=recipients, sender=sender)
                msg.html = html_content
                msg.body = f"""
New Shift Swap Request Submitted - Pending Approval

Request Type: Shift Swap
Requested By: {swap_request.requester.first_name} {swap_request.requester.last_name} ({swap_request.requester.username})
Swap With: {swap_request.swap_with.first_name} {swap_request.swap_with.last_name} ({swap_request.swap_with.username})
Original Date: {swap_request.original_date}
Original Shift: {original_shift_name} {original_shift_time}
Swap Date: {swap_request.swap_date}
Swap Shift: {swap_shift_name} {swap_shift_time}
Reason: {swap_request.reason}
Status: Pending Approval

Please login to the Shift Management Portal to take action.
                """
                
                mail.send(msg)
                logger.info(f"Swap request submission email sent to {len(recipients)} admins")
            else:
                logger.warning("Mail instance not available for swap request submission email")
                
        except Exception as e:
            logger.error(f"Error sending swap request submission email: {e}")

    @staticmethod
    def send_leave_request_submitted_email(leave_request: LeaveRequest):
        """Send email to admins when a leave request is submitted"""
        try:
            # Get admin recipients
            admins = ShiftEmailService._get_admins_for_team(leave_request.account_id, leave_request.team_id)
            if not admins:
                logger.warning("No admin recipients found for leave request notification")
                return

            recipients = [admin.email for admin in admins if admin.email]
            if not recipients:
                logger.warning("No admin email addresses found for leave request notification")
                return

            # Get team and account info
            team = Team.query.get(leave_request.team_id)
            account = Account.query.get(leave_request.account_id)
            
            # Get shift display names
            shift_name = ShiftEmailService._get_shift_display_name(leave_request.shift_code)
            shift_time = ShiftEmailService._get_shift_time_range(leave_request.shift_code)

            subject = f"Leave Request Submitted – Pending Approval"
            
            html_content = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
                    .content {{ margin: 20px 0; }}
                    .details-table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                    .details-table th {{ background-color: #f8f9fa; padding: 12px; text-align: left; border: 1px solid #dee2e6; }}
                    .details-table td {{ padding: 12px; border: 1px solid #dee2e6; }}
                    .footer {{ margin-top: 30px; padding: 15px; background-color: #f8f9fa; border-radius: 5px; font-size: 0.9em; color: #6c757d; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h2>🏖️ New Leave Request Submitted</h2>
                    <p style="margin: 10px 0 0 0;">Pending your approval</p>
                </div>
                
                <div class="content">
                    <h3>Request Details</h3>
                    <table class="details-table">
                        <tr><th>Request Type</th><td><strong>Leave Request</strong></td></tr>
                        <tr><th>Requested By</th><td>{leave_request.requester.first_name} {leave_request.requester.last_name} ({leave_request.requester.username})</td></tr>
                        <tr><th>Team</th><td>{team.name if team else 'Unknown'}</td></tr>
                        <tr><th>Account</th><td>{account.name if account else 'Unknown'}</td></tr>
                        <tr><th>Date</th><td>{leave_request.leave_date}</td></tr>
                        <tr><th>Shift</th><td>{shift_name} {shift_time}</td></tr>
                        <tr><th>Leave Type</th><td>{leave_request.leave_type}</td></tr>
                        <tr><th>Reason</th><td>{leave_request.reason or 'Not provided'}</td></tr>
                        <tr><th>Status</th><td><span style="color: #ffc107; font-weight: bold;">⏳ Pending Approval</span></td></tr>
                        <tr><th>Submitted</th><td>{leave_request.created_at.strftime('%Y-%m-%d %H:%M:%S')}</td></tr>
                    </table>
                </div>
                
                <div class="footer">
                    <p><strong>📧 This is an automated notification.</strong></p>
                    <p>🔗 <strong>Action Required:</strong> Please login to the Shift Management Portal to review and approve/reject this request.</p>
                    <p><em>Shift Handover Management System</em></p>
                </div>
            </body>
            </html>
            """

            # Send email
            mail = ShiftEmailService._get_mail_instance()
            if mail:
                sender = current_app.config.get('MAIL_DEFAULT_SENDER') or current_app.config.get('MAIL_USERNAME')
                msg = Message(subject=subject, recipients=recipients, sender=sender)
                msg.html = html_content
                msg.body = f"""
New Leave Request Submitted - Pending Approval

Request Type: Leave Request
Requested By: {leave_request.requester.first_name} {leave_request.requester.last_name} ({leave_request.requester.username})
Date: {leave_request.leave_date}
Shift: {shift_name} {shift_time}
Leave Type: {leave_request.leave_type}
Reason: {leave_request.reason or 'Not provided'}
Status: Pending Approval

Please login to the Shift Management Portal to take action.
                """
                
                mail.send(msg)
                logger.info(f"Leave request submission email sent to {len(recipients)} admins")
            else:
                logger.warning("Mail instance not available for leave request submission email")
                
        except Exception as e:
            logger.error(f"Error sending leave request submission email: {e}")

    @staticmethod
    def send_swap_decision_email(swap_request: ShiftSwapRequest, approved: bool, approver_comments: str = ''):
        """Send email to requester when swap request is approved/rejected"""
        try:
            if not swap_request.requester.email:
                logger.warning(f"No email address for requester {swap_request.requester.username}")
                return

            recipient = swap_request.requester.email
            status = 'Approved' if approved else 'Rejected'
            status_color = '#28a745' if approved else '#dc3545'
            status_icon = '✅' if approved else '❌'
            
            # Get shift display names
            original_shift_name = ShiftEmailService._get_shift_display_name(swap_request.original_shift_code)
            original_shift_time = ShiftEmailService._get_shift_time_range(swap_request.original_shift_code)
            swap_shift_name = ShiftEmailService._get_shift_display_name(swap_request.swap_shift_code)
            swap_shift_time = ShiftEmailService._get_shift_time_range(swap_request.swap_shift_code)

            subject = f"Your Shift Swap Request Has Been {status}"
            
            html_content = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .header {{ background: linear-gradient(135deg, {status_color} 0%, {status_color}aa 100%); color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
                    .content {{ margin: 20px 0; }}
                    .details-table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                    .details-table th {{ background-color: #f8f9fa; padding: 12px; text-align: left; border: 1px solid #dee2e6; }}
                    .details-table td {{ padding: 12px; border: 1px solid #dee2e6; }}
                    .footer {{ margin-top: 30px; padding: 15px; background-color: #f8f9fa; border-radius: 5px; font-size: 0.9em; color: #6c757d; }}
                    .status {{ color: {status_color}; font-weight: bold; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h2>{status_icon} Your Shift Swap Request Has Been {status}</h2>
                </div>
                
                <div class="content">
                    <p>Dear {swap_request.requester.first_name},</p>
                    <p>Your shift swap request has been <span class="status">{status.lower()}</span>.</p>
                    
                    <h3>Request Details</h3>
                    <table class="details-table">
                        <tr><th>Request Type</th><td>Shift Swap</td></tr>
                        <tr><th>Swap With</th><td>{swap_request.swap_with.first_name} {swap_request.swap_with.last_name}</td></tr>
                        <tr><th>Original Date</th><td>{swap_request.original_date}</td></tr>
                        <tr><th>Original Shift</th><td>{original_shift_name} {original_shift_time}</td></tr>
                        <tr><th>Swap Date</th><td>{swap_request.swap_date}</td></tr>
                        <tr><th>Swap Shift</th><td>{swap_shift_name} {swap_shift_time}</td></tr>
                        <tr><th>Status</th><td><span class="status">{status_icon} {status}</span></td></tr>
                        {'<tr><th>Admin Comment</th><td>' + approver_comments + '</td></tr>' if approver_comments else ''}
                        <tr><th>Decision Date</th><td>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</td></tr>
                    </table>
                </div>
                
                <div class="footer">
                    <p><strong>📧 This is an automated notification.</strong></p>
                    <p>🔗 Login to the Shift Management Portal for full details.</p>
                    <p><em>Shift Handover Management System</em></p>
                </div>
            </body>
            </html>
            """

            # Send email
            mail = ShiftEmailService._get_mail_instance()
            if mail:
                sender = current_app.config.get('MAIL_DEFAULT_SENDER') or current_app.config.get('MAIL_USERNAME')
                msg = Message(subject=subject, recipients=[recipient], sender=sender)
                msg.html = html_content
                msg.body = f"""
Your Shift Swap Request Has Been {status}

Request Type: Shift Swap
Swap With: {swap_request.swap_with.first_name} {swap_request.swap_with.last_name}
Original Date: {swap_request.original_date}
Original Shift: {original_shift_name} {original_shift_time}
Swap Date: {swap_request.swap_date}
Swap Shift: {swap_shift_name} {swap_shift_time}
Status: {status}
{f'Admin Comment: {approver_comments}' if approver_comments else ''}

Login to the Shift Management Portal for full details.
                """
                
                mail.send(msg)
                logger.info(f"Swap decision email sent to {recipient}")
            else:
                logger.warning("Mail instance not available for swap decision email")
                
        except Exception as e:
            logger.error(f"Error sending swap decision email: {e}")

    @staticmethod
    def send_leave_decision_email(leave_request: LeaveRequest, approved: bool, approver_comments: str = ''):
        """Send email to requester when leave request is approved/rejected"""
        try:
            if not leave_request.requester.email:
                logger.warning(f"No email address for requester {leave_request.requester.username}")
                return

            recipient = leave_request.requester.email
            status = 'Approved' if approved else 'Rejected'
            status_color = '#28a745' if approved else '#dc3545'
            status_icon = '✅' if approved else '❌'
            
            # Get shift display names
            shift_name = ShiftEmailService._get_shift_display_name(leave_request.shift_code)
            shift_time = ShiftEmailService._get_shift_time_range(leave_request.shift_code)

            subject = f"Your Leave Request Has Been {status}"
            
            html_content = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .header {{ background: linear-gradient(135deg, {status_color} 0%, {status_color}aa 100%); color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
                    .content {{ margin: 20px 0; }}
                    .details-table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                    .details-table th {{ background-color: #f8f9fa; padding: 12px; text-align: left; border: 1px solid #dee2e6; }}
                    .details-table td {{ padding: 12px; border: 1px solid #dee2e6; }}
                    .footer {{ margin-top: 30px; padding: 15px; background-color: #f8f9fa; border-radius: 5px; font-size: 0.9em; color: #6c757d; }}
                    .status {{ color: {status_color}; font-weight: bold; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h2>{status_icon} Your Leave Request Has Been {status}</h2>
                </div>
                
                <div class="content">
                    <p>Dear {leave_request.requester.first_name},</p>
                    <p>Your leave request has been <span class="status">{status.lower()}</span>.</p>
                    
                    <h3>Request Details</h3>
                    <table class="details-table">
                        <tr><th>Request Type</th><td>Leave Request</td></tr>
                        <tr><th>Date</th><td>{leave_request.leave_date}</td></tr>
                        <tr><th>Shift</th><td>{shift_name} {shift_time}</td></tr>
                        <tr><th>Leave Type</th><td>{leave_request.leave_type}</td></tr>
                        <tr><th>Reason</th><td>{leave_request.reason or 'Not provided'}</td></tr>
                        <tr><th>Status</th><td><span class="status">{status_icon} {status}</span></td></tr>
                        {'<tr><th>Admin Comment</th><td>' + approver_comments + '</td></tr>' if approver_comments else ''}
                        <tr><th>Decision Date</th><td>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</td></tr>
                    </table>
                </div>
                
                <div class="footer">
                    <p><strong>📧 This is an automated notification.</strong></p>
                    <p>🔗 Login to the Shift Management Portal for full details.</p>
                    <p><em>Shift Handover Management System</em></p>
                </div>
            </body>
            </html>
            """

            # Send email
            mail = ShiftEmailService._get_mail_instance()
            if mail:
                sender = current_app.config.get('MAIL_DEFAULT_SENDER') or current_app.config.get('MAIL_USERNAME')
                msg = Message(subject=subject, recipients=[recipient], sender=sender)
                msg.html = html_content
                msg.body = f"""
Your Leave Request Has Been {status}

Request Type: Leave Request
Date: {leave_request.leave_date}
Shift: {shift_name} {shift_time}
Leave Type: {leave_request.leave_type}
Reason: {leave_request.reason or 'Not provided'}
Status: {status}
{f'Admin Comment: {approver_comments}' if approver_comments else ''}

Login to the Shift Management Portal for full details.
                """
                
                mail.send(msg)
                logger.info(f"Leave decision email sent to {recipient}")
            else:
                logger.warning("Mail instance not available for leave decision email")
                
        except Exception as e:
            logger.error(f"Error sending leave decision email: {e}")

    @staticmethod
    def send_roster_update_notification(request_type: str, swap_request: ShiftSwapRequest = None, leave_request: LeaveRequest = None):
        """Send team notification when roster is updated after approval"""
        try:
            if request_type == 'swap' and swap_request:
                account_id = swap_request.account_id
                team_id = swap_request.team_id
                
                # Get team distribution list
                recipients = ShiftEmailService._get_team_distribution_list(account_id, team_id)
                if not recipients:
                    logger.warning("No team recipients found for swap roster update notification")
                    return

                # Get team info
                team = Team.query.get(team_id)
                team_name = team.name if team else 'Team'
                
                # Get shift display names
                original_shift_name = ShiftEmailService._get_shift_display_name(swap_request.original_shift_code)
                swap_shift_name = ShiftEmailService._get_shift_display_name(swap_request.swap_shift_code)
                
                subject = f"Shift Roster Updated – Swap Approved"
                
                html_content = f"""
                <html>
                <head>
                    <style>
                        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                        .header {{ background: linear-gradient(135deg, #28a745 0%, #20c997 100%); color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
                        .content {{ margin: 20px 0; }}
                        .swap-details {{ border: 2px solid #28a745; border-radius: 8px; padding: 15px; margin: 20px 0; background-color: #f8fff8; }}
                        .footer {{ margin-top: 30px; padding: 15px; background-color: #f8f9fa; border-radius: 5px; font-size: 0.9em; color: #6c757d; }}
                    </style>
                </head>
                <body>
                    <div class="header">
                        <h2>🔄 Shift Roster Updated</h2>
                        <p style="margin: 10px 0 0 0;">Shift swap has been approved and roster updated</p>
                    </div>
                    
                    <div class="content">
                        <p><strong>Team {team_name}</strong>,</p>
                        <p>The following shift swap has been approved and the roster has been updated:</p>
                        
                        <div class="swap-details">
                            <h3>Shift Swap Details</h3>
                            <p><strong>{swap_request.requester.first_name} {swap_request.requester.last_name}</strong> has swapped shifts with <strong>{swap_request.swap_with.first_name} {swap_request.swap_with.last_name}</strong></p>
                            
                            <table style="width: 100%; margin-top: 15px;">
                                <tr>
                                    <td style="width: 50%; padding: 10px; border-right: 1px solid #dee2e6;">
                                        <strong>{swap_request.requester.first_name} {swap_request.requester.last_name}:</strong><br>
                                        <span style="text-decoration: line-through; color: #6c757d;">{swap_request.original_date} - {original_shift_name}</span><br>
                                        <span style="color: #28a745; font-weight: bold;">→ {swap_request.swap_date} - {swap_shift_name}</span>
                                    </td>
                                    <td style="width: 50%; padding: 10px;">
                                        <strong>{swap_request.swap_with.first_name} {swap_request.swap_with.last_name}:</strong><br>
                                        <span style="text-decoration: line-through; color: #6c757d;">{swap_request.swap_date} - {swap_shift_name}</span><br>
                                        <span style="color: #28a745; font-weight: bold;">→ {swap_request.original_date} - {original_shift_name}</span>
                                    </td>
                                </tr>
                            </table>
                        </div>
                        
                        <p><strong>✅ Roster Status:</strong> Updated and confirmed</p>
                        <p><strong>📅 Effective Date:</strong> {min(swap_request.original_date, swap_request.swap_date)}</p>
                    </div>
                    
                    <div class="footer">
                        <p><strong>📧 This is an automated team notification.</strong></p>
                        <p>📋 Please update your personal calendars and handover schedules accordingly.</p>
                        <p><em>Shift Handover Management System</em></p>
                    </div>
                </body>
                </html>
                """
                
                # Send email
                mail = ShiftEmailService._get_mail_instance()
                if mail:
                    sender = current_app.config.get('MAIL_DEFAULT_SENDER') or current_app.config.get('MAIL_USERNAME')
                    msg = Message(subject=subject, recipients=recipients, sender=sender)
                    msg.html = html_content
                    msg.body = f"""
Shift Roster Updated - Swap Approved

Team {team_name},

{swap_request.requester.first_name} {swap_request.requester.last_name} has swapped shifts with {swap_request.swap_with.first_name} {swap_request.swap_with.last_name}.

{swap_request.requester.first_name}: {swap_request.original_date} {original_shift_name} → {swap_request.swap_date} {swap_shift_name}
{swap_request.swap_with.first_name}: {swap_request.swap_date} {swap_shift_name} → {swap_request.original_date} {original_shift_name}

Roster Status: Updated and confirmed

This is an automated team notification.
                    """
                    
                    mail.send(msg)
                    logger.info(f"Swap roster update notification sent to {len(recipients)} team members")
                else:
                    logger.warning("Mail instance not available for swap roster update notification")
                    
            elif request_type == 'leave' and leave_request:
                account_id = leave_request.account_id
                team_id = leave_request.team_id
                
                # Get team distribution list
                recipients = ShiftEmailService._get_team_distribution_list(account_id, team_id)
                if not recipients:
                    logger.warning("No team recipients found for leave roster update notification")
                    return

                # Get team info
                team = Team.query.get(team_id)
                team_name = team.name if team else 'Team'
                
                # Get shift display names
                shift_name = ShiftEmailService._get_shift_display_name(leave_request.shift_code)
                shift_time = ShiftEmailService._get_shift_time_range(leave_request.shift_code)
                
                subject = f"Shift Roster Updated – Leave Approved"
                
                html_content = f"""
                <html>
                <head>
                    <style>
                        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                        .header {{ background: linear-gradient(135deg, #17a2b8 0%, #20c997 100%); color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
                        .content {{ margin: 20px 0; }}
                        .leave-details {{ border: 2px solid #17a2b8; border-radius: 8px; padding: 15px; margin: 20px 0; background-color: #f0f9ff; }}
                        .footer {{ margin-top: 30px; padding: 15px; background-color: #f8f9fa; border-radius: 5px; font-size: 0.9em; color: #6c757d; }}
                    </style>
                </head>
                <body>
                    <div class="header">
                        <h2>🏖️ Shift Roster Updated</h2>
                        <p style="margin: 10px 0 0 0;">Leave request has been approved and roster updated</p>
                    </div>
                    
                    <div class="content">
                        <p><strong>Team {team_name}</strong>,</p>
                        <p>The following leave request has been approved and the roster has been updated:</p>
                        
                        <div class="leave-details">
                            <h3>Leave Details</h3>
                            <p><strong>{leave_request.requester.first_name} {leave_request.requester.last_name}</strong> is on <strong>{leave_request.leave_type}</strong> leave</p>
                            
                            <ul style="margin: 15px 0;">
                                <li><strong>Date:</strong> {leave_request.leave_date}</li>
                                <li><strong>Shift Impacted:</strong> {shift_name} {shift_time}</li>
                                <li><strong>Leave Type:</strong> {leave_request.leave_type}</li>
                                {f'<li><strong>Coverage:</strong> {leave_request.covered_by.first_name} {leave_request.covered_by.last_name}</li>' if leave_request.covered_by else ''}
                            </ul>
                        </div>
                        
                        <p><strong>✅ Roster Status:</strong> Updated and confirmed</p>
                        <p><strong>📅 Effective Date:</strong> {leave_request.leave_date}</p>
                    </div>
                    
                    <div class="footer">
                        <p><strong>📧 This is an automated team notification.</strong></p>
                        <p>📋 Please adjust your schedules and handover plans accordingly.</p>
                        <p><em>Shift Handover Management System</em></p>
                    </div>
                </body>
                </html>
                """
                
                # Send email
                mail = ShiftEmailService._get_mail_instance()
                if mail:
                    sender = current_app.config.get('MAIL_DEFAULT_SENDER') or current_app.config.get('MAIL_USERNAME')
                    msg = Message(subject=subject, recipients=recipients, sender=sender)
                    msg.html = html_content
                    msg.body = f"""
Shift Roster Updated - Leave Approved

Team {team_name},

{leave_request.requester.first_name} {leave_request.requester.last_name} is on {leave_request.leave_type} leave.

Date: {leave_request.leave_date}
Shift: {shift_name} {shift_time}
Leave Type: {leave_request.leave_type}
{f'Coverage: {leave_request.covered_by.first_name} {leave_request.covered_by.last_name}' if leave_request.covered_by else ''}

Roster Status: Updated and confirmed

This is an automated team notification.
                    """
                    
                    mail.send(msg)
                    logger.info(f"Leave roster update notification sent to {len(recipients)} team members")
                else:
                    logger.warning("Mail instance not available for leave roster update notification")
                    
        except Exception as e:
            logger.error(f"Error sending roster update notification: {e}")

# Service instance
shift_email_service = ShiftEmailService()