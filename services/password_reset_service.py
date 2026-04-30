"""
Password Reset Service

This service handles password reset functionality including email sending,
token management, and security validation.
"""

import logging
from datetime import datetime
from flask import current_app, render_template_string, request
from flask_mail import Message, Mail
from models.models import db, User
from models.password_reset import PasswordResetToken
from models.smtp_config import SMTPConfig

logger = logging.getLogger(__name__)

class PasswordResetService:
    """Service for handling password reset operations"""
    
    @staticmethod
    def initiate_password_reset(email, ip_address=None, user_agent=None):
        """
        Initiate password reset process for a user
        
        Args:
            email (str): User's email address
            ip_address (str): Client IP address
            user_agent (str): Client user agent
            
        Returns:
            dict: Result with success status and message
        """
        try:
            # Find user by email
            user = User.query.filter_by(email=email).first()
            
            if not user:
                # For security, don't reveal if email exists or not
                logger.warning(f"Password reset attempted for non-existent email: {email}")
                return {
                    'success': True,
                    'message': 'If an account with this email exists, you will receive a password reset link.'
                }
            
            if not user.is_active:
                logger.warning(f"Password reset attempted for inactive user: {email}")
                return {
                    'success': False,
                    'message': 'Account is not active. Please contact your administrator.'
                }
            
            # Create password reset token
            token = PasswordResetToken.create_token(
                user_id=user.id,
                ip_address=ip_address,
                user_agent=user_agent,
                expires_in_hours=1  # Token expires in 1 hour
            )
            
            if not token:
                logger.error(f"Failed to create password reset token for user: {email}")
                return {
                    'success': False,
                    'message': 'Unable to generate reset token. Please try again later.'
                }
            
            # Send password reset email
            email_result = PasswordResetService._send_reset_email(user, token)
            
            if email_result['success']:
                logger.info(f"Password reset email sent successfully to: {email}")
                return {
                    'success': True,
                    'message': 'If an account with this email exists, you will receive a password reset link.'
                }
            else:
                logger.error(f"Failed to send password reset email to: {email}")
                # Deactivate token if email failed
                token.deactivate()
                return {
                    'success': False,
                    'message': 'Unable to send reset email. Please check your email configuration or try again later.'
                }
                
        except Exception as e:
            logger.error(f"Error initiating password reset for {email}: {str(e)}")
            return {
                'success': False,
                'message': 'An error occurred while processing your request. Please try again later.'
            }
    
    @staticmethod
    def validate_reset_token(token_string):
        """
        Validate a password reset token
        
        Args:
            token_string (str): Token to validate
            
        Returns:
            dict: Result with success status, message, and user data if valid
        """
        try:
            token = PasswordResetToken.find_valid_token(token_string)
            
            if not token:
                logger.warning(f"Invalid or expired password reset token: {token_string[:8]}...")
                return {
                    'success': False,
                    'message': 'Invalid or expired reset token. Please request a new password reset.'
                }
            
            user = User.query.get(token.user_id)
            if not user or not user.is_active:
                logger.warning(f"Password reset token for inactive/deleted user: {token.user_id}")
                token.deactivate()
                return {
                    'success': False,
                    'message': 'Account is not active. Please contact your administrator.'
                }
            
            return {
                'success': True,
                'message': 'Valid reset token',
                'user': user,
                'token': token
            }
            
        except Exception as e:
            logger.error(f"Error validating reset token: {str(e)}")
            return {
                'success': False,
                'message': 'An error occurred while validating the reset token.'
            }
    
    @staticmethod
    def reset_password(token_string, new_password, confirm_password):
        """
        Reset user password using a valid token
        
        Args:
            token_string (str): Password reset token
            new_password (str): New password
            confirm_password (str): Password confirmation
            
        Returns:
            dict: Result with success status and message
        """
        try:
            # Validate passwords match
            if new_password != confirm_password:
                return {
                    'success': False,
                    'message': 'Passwords do not match.'
                }
            
            # Validate password strength
            if len(new_password) < 8:
                return {
                    'success': False,
                    'message': 'Password must be at least 8 characters long.'
                }
            
            # Validate token
            token_result = PasswordResetService.validate_reset_token(token_string)
            if not token_result['success']:
                return token_result
            
            user = token_result['user']
            token = token_result['token']
            
            # Update user password
            from werkzeug.security import generate_password_hash
            user.password = generate_password_hash(new_password)
            
            # Mark token as used
            token.mark_as_used()
            
            # Commit changes
            db.session.commit()
            
            logger.info(f"Password successfully reset for user: {user.email}")
            
            # Send confirmation email
            PasswordResetService._send_confirmation_email(user)
            
            return {
                'success': True,
                'message': 'Password has been successfully reset. You can now log in with your new password.'
            }
            
        except Exception as e:
            logger.error(f"Error resetting password: {str(e)}")
            db.session.rollback()
            return {
                'success': False,
                'message': 'An error occurred while resetting your password. Please try again.'
            }
    
    @staticmethod
    def _send_reset_email(user, token):
        """
        Send password reset email to user
        
        Args:
            user (User): User object
            token (PasswordResetToken): Reset token object
            
        Returns:
            dict: Result with success status and message
        """
        try:
            # Check if SMTP is configured
            if not SMTPConfig.is_configured():
                logger.error("SMTP not configured - cannot send password reset email")
                return {
                    'success': False,
                    'message': 'Email service not configured. Please contact your administrator.'
                }
            
            # Get Flask-Mail configuration
            mail_config = SMTPConfig.get_flask_mail_config()
            if not mail_config:
                logger.error("Failed to get SMTP configuration")
                return {
                    'success': False,
                    'message': 'Email configuration error. Please contact your administrator.'
                }
            
            # Temporarily update app config for this email
            original_config = {}
            for key, value in mail_config.items():
                original_config[key] = current_app.config.get(key)
                current_app.config[key] = value
            
            # Initialize mail
            mail = Mail(current_app)
            
            # Generate reset URL
            reset_url = f"{request.scheme}://{request.host}/auth/reset-password?token={token.token}"
            
            # Email template
            email_template = """
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Password Reset - Shift Handover App</title>
                <style>
                    body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }
                    .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }
                    .content { background: white; padding: 30px; border: 1px solid #ddd; border-radius: 0 0 8px 8px; }
                    .button { display: inline-block; background: #667eea; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }
                    .button:hover { background: #5a6fd8; }
                    .footer { text-align: center; color: #888; font-size: 12px; margin-top: 20px; }
                    .warning { background: #fff3cd; border: 1px solid #ffeaa7; padding: 10px; border-radius: 4px; margin: 15px 0; }
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>🔐 Password Reset Request</h1>
                    <p>Shift Handover Application</p>
                </div>
                <div class="content">
                    <h2>Hello {{ user.first_name or user.username }},</h2>
                    
                    <p>We received a request to reset your password for your Shift Handover Application account.</p>
                    
                    <p>Click the button below to reset your password:</p>
                    
                    <a href="{{ reset_url }}" class="button">Reset My Password</a>
                    
                    <p>Or copy and paste this link into your browser:</p>
                    <p style="word-break: break-all; background: #f8f9fa; padding: 10px; border-radius: 4px;">{{ reset_url }}</p>
                    
                    <div class="warning">
                        <strong>⚠️ Security Notice:</strong>
                        <ul>
                            <li>This link will expire in <strong>1 hour</strong></li>
                            <li>If you didn't request this reset, please ignore this email</li>
                            <li>Never share this link with anyone</li>
                        </ul>
                    </div>
                    
                    <p><strong>Account Details:</strong></p>
                    <ul>
                        <li>Username: {{ user.username }}</li>
                        <li>Email: {{ user.email }}</li>
                        <li>Request Time: {{ current_time }}</li>
                        <li>IP Address: {{ ip_address or 'Unknown' }}</li>
                    </ul>
                </div>
                <div class="footer">
                    <p>This is an automated message from the Shift Handover Application.<br>
                    Please do not reply to this email.</p>
                </div>
            </body>
            </html>
            """
            
            # Render email content
            html_content = render_template_string(email_template, 
                user=user,
                reset_url=reset_url,
                current_time=datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
                ip_address=token.ip_address
            )
            
            # Create and send message
            msg = Message(
                subject='🔐 Password Reset Request - Shift Handover App',
                recipients=[user.email],
                html=html_content,
                sender=mail_config.get('MAIL_DEFAULT_SENDER')
            )
            
            mail.send(msg)
            
            # Restore original config
            for key, value in original_config.items():
                if value is not None:
                    current_app.config[key] = value
                else:
                    current_app.config.pop(key, None)
            
            logger.info(f"Password reset email sent to: {user.email}")
            return {
                'success': True,
                'message': 'Password reset email sent successfully'
            }
            
        except Exception as e:
            logger.error(f"Error sending password reset email: {str(e)}")
            return {
                'success': False,
                'message': f'Failed to send email: {str(e)}'
            }
    
    @staticmethod
    def _send_confirmation_email(user):
        """Send password reset confirmation email"""
        try:
            if not SMTPConfig.is_configured():
                return
            
            mail_config = SMTPConfig.get_flask_mail_config()
            if not mail_config:
                return
            
            # Temporarily update app config
            original_config = {}
            for key, value in mail_config.items():
                original_config[key] = current_app.config.get(key)
                current_app.config[key] = value
            
            mail = Mail(current_app)
            
            # Confirmation email template
            email_template = """
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Password Reset Confirmed</title>
                <style>
                    body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }
                    .header { background: #28a745; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }
                    .content { background: white; padding: 30px; border: 1px solid #ddd; border-radius: 0 0 8px 8px; }
                    .footer { text-align: center; color: #888; font-size: 12px; margin-top: 20px; }
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>✅ Password Reset Successful</h1>
                    <p>Shift Handover Application</p>
                </div>
                <div class="content">
                    <h2>Hello {{ user.first_name or user.username }},</h2>
                    
                    <p>Your password has been successfully reset.</p>
                    
                    <p>You can now log in to your account using your new password.</p>
                    
                    <p><strong>If you did not make this change, please contact your administrator immediately.</strong></p>
                    
                    <p>Reset completed at: {{ current_time }}</p>
                </div>
                <div class="footer">
                    <p>This is an automated message from the Shift Handover Application.</p>
                </div>
            </body>
            </html>
            """
            
            html_content = render_template_string(email_template,
                user=user,
                current_time=datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
            )
            
            msg = Message(
                subject='✅ Password Reset Confirmed - Shift Handover App',
                recipients=[user.email],
                html=html_content,
                sender=mail_config.get('MAIL_DEFAULT_SENDER')
            )
            
            mail.send(msg)
            
            # Restore original config
            for key, value in original_config.items():
                if value is not None:
                    current_app.config[key] = value
                else:
                    current_app.config.pop(key, None)
                    
        except Exception as e:
            logger.error(f"Error sending password reset confirmation email: {str(e)}")
    
    @staticmethod
    def cleanup_expired_tokens():
        """Clean up expired password reset tokens"""
        return PasswordResetToken.cleanup_expired_tokens()
