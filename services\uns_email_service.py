"""
UNS Email Service - Python Implementation
Replicates the Java Spring email functionality with STARTTLS configuration
"""

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from email.header import Header
from email.utils import formataddr
from dataclasses import dataclass
from typing import List, Optional, Union
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class EmailRequest:
    """Email request data class - matches Java EmailRequest structure"""
    to: Union[str, List[str]]
    subject: str
    body: str
    cc: Optional[Union[str, List[str]]] = None
    bcc: Optional[Union[str, List[str]]] = None
    attachments: Optional[List[str]] = None
    is_html: bool = True

class UNSEmailConfig:
    """UNS Email configuration - mirrors properties.yaml structure"""
    
    def __init__(self, host=None, port=None, username=None, password=None, 
                 sender_address=None, sender_name=None):
        # Load from parameters or environment variables (matching UNS configuration)
        self.host = host or os.getenv('EMAIL_NOTIFICATION_HOST', 'smtp.company.com')
        self.port = int(port or os.getenv('EMAIL_NOTIFICATION_PORT', '587'))
        self.username = username or os.getenv('EMAIL_NOTIFICATION_USERNAME', '')
        self.password = password or os.getenv('EMAIL_NOTIFICATION_PASSWORD', '')
        self.sender_address = sender_address or os.getenv('EMAIL_SENDER_ADDRESS', 'noreply@company.com')
        self.sender_name = sender_name or os.getenv('EMAIL_SENDER_NAME', 'UNS Notification System')
        
        # STARTTLS configuration (matching spring.mail.properties)
        self.starttls_enable = True
        self.timeout = 5  # Connection timeout in seconds (reduced from 30 for faster failure)
        self.use_ssl = False  # We use STARTTLS, not SSL
        
    def validate(self) -> bool:
        """Validate that all required configuration is present"""
        required_fields = [self.host, self.username, self.password, self.sender_address]
        return all(field and str(field).strip() for field in required_fields)
    
    def __str__(self):
        return f"UNSEmailConfig(host={self.host}, port={self.port}, sender={self.sender_address})"

class UNSEmailSender:
    """
    UNS Email Sender - Python equivalent of Java EmailSender component
    Implements the same STARTTLS authentication flow as Java Spring implementation
    """
    
    def __init__(self, config: Optional[UNSEmailConfig] = None):
        self.config = config or UNSEmailConfig()
        logger.info(f"Initialized UNS Email Sender: {self.config}")
    
    def send(self, email_request: EmailRequest) -> dict:
        """
        Send email using STARTTLS - mirrors Java javaMailSender.send() method
        
        Args:
            email_request: EmailRequest object containing email details
            
        Returns:
            dict: Result with success status and details
        """
        try:
            # Validate configuration
            if not self.config.validate():
                return {
                    'success': False,
                    'error': 'UNS Email configuration is incomplete. Check environment variables.',
                    'details': 'Missing required fields: host, username, password, or sender_address'
                }
            
            # Create email message (equivalent to MimeMessageHelper)
            message = self._create_mime_message(email_request)
            
            # Send email using STARTTLS (equivalent to javaMailSender.send())
            self._send_via_smtp(message, email_request)
            
            recipients_count = len(self._normalize_recipients(email_request.to))
            logger.info(f"UNS Email sent successfully to {recipients_count} recipients")
            
            return {
                'success': True,
                'message': f'Email sent successfully to {recipients_count} recipient(s)',
                'recipients': recipients_count,
                'subject': email_request.subject
            }
            
        except smtplib.SMTPAuthenticationError as e:
            error_msg = f"UNS SMTP Authentication failed: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': 'Authentication failed',
                'details': error_msg,
                'smtp_code': getattr(e, 'smtp_code', None)
            }
            
        except smtplib.SMTPConnectError as e:
            error_msg = f"UNS SMTP Connection failed: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': 'Connection failed',
                'details': error_msg,
                'smtp_code': getattr(e, 'smtp_code', None)
            }
            
        except smtplib.SMTPRecipientsRefused as e:
            error_msg = f"UNS SMTP Recipients refused: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': 'Invalid recipients',
                'details': error_msg,
                'refused_recipients': e.recipients
            }
            
        except smtplib.SMTPServerDisconnected as e:
            error_msg = f"UNS SMTP Server disconnected: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': 'Server disconnected',
                'details': error_msg
            }
            
        except Exception as e:
            error_msg = f"UNS Email sending failed: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': 'Unexpected error',
                'details': error_msg
            }
    
    def _create_mime_message(self, email_request: EmailRequest) -> MIMEMultipart:
        """Create MIME message - equivalent to MimeMessageHelper setup"""
        
        # Create message container
        message = MIMEMultipart('alternative')
        
        # Set headers (equivalent to helper.setFrom, setTo, setSubject)
        message['From'] = formataddr((self.config.sender_name, self.config.sender_address))
        message['To'] = self._format_recipients(email_request.to)
        message['Subject'] = Header(email_request.subject, 'utf-8')
        
        # Add CC and BCC if provided
        if email_request.cc:
            message['Cc'] = self._format_recipients(email_request.cc)
        if email_request.bcc:
            message['Bcc'] = self._format_recipients(email_request.bcc)
        
        # Add email body (equivalent to helper.setText with HTML support)
        if email_request.is_html:
            # Add both plain text and HTML versions for better compatibility
            plain_part = MIMEText(self._html_to_plain(email_request.body), 'plain', 'utf-8')
            html_part = MIMEText(email_request.body, 'html', 'utf-8')
            message.attach(plain_part)
            message.attach(html_part)
        else:
            text_part = MIMEText(email_request.body, 'plain', 'utf-8')
            message.attach(text_part)
        
        # Add attachments if provided
        if email_request.attachments:
            self._add_attachments(message, email_request.attachments)
        
        return message
    
    def _send_via_smtp(self, message: MIMEMultipart, email_request: EmailRequest):
        """Send email via SMTP with STARTTLS - replicates JavaMailSender behavior"""
        
        # Create SMTP connection
        server = smtplib.SMTP(self.config.host, self.config.port, timeout=self.config.timeout)
        
        try:
            # Enable debug logging if needed
            if logger.isEnabledFor(logging.DEBUG):
                server.set_debuglevel(1)
            
            # Start TLS encryption (equivalent to mail.smtp.starttls.enable: true)
            if self.config.starttls_enable:
                server.starttls(context=ssl.create_default_context())
                logger.debug("UNS STARTTLS enabled successfully")
            
            # Authenticate (equivalent to Spring Mail authentication)
            server.login(self.config.username, self.config.password)
            logger.debug("UNS SMTP authentication successful")
            
            # Get all recipients
            all_recipients = self._get_all_recipients(email_request)
            
            # Send email
            server.send_message(message, to_addrs=all_recipients)
            logger.debug(f"UNS Email sent to {len(all_recipients)} recipients")
            
        finally:
            # Always close the connection
            server.quit()
    
    def _normalize_recipients(self, recipients: Union[str, List[str]]) -> List[str]:
        """Normalize recipients to a list of email addresses"""
        if isinstance(recipients, str):
            return [email.strip() for email in recipients.split(',') if email.strip()]
        elif isinstance(recipients, list):
            return [email.strip() for email in recipients if email.strip()]
        return []
    
    def _format_recipients(self, recipients: Union[str, List[str]]) -> str:
        """Format recipients for email headers"""
        normalized = self._normalize_recipients(recipients)
        return ', '.join(normalized)
    
    def _get_all_recipients(self, email_request: EmailRequest) -> List[str]:
        """Get all recipients including TO, CC, and BCC"""
        all_recipients = []
        all_recipients.extend(self._normalize_recipients(email_request.to))
        
        if email_request.cc:
            all_recipients.extend(self._normalize_recipients(email_request.cc))
        if email_request.bcc:
            all_recipients.extend(self._normalize_recipients(email_request.bcc))
        
        return list(set(all_recipients))  # Remove duplicates
    
    def _html_to_plain(self, html_content: str) -> str:
        """Convert HTML to plain text for fallback"""
        # Simple HTML to text conversion
        # For production, consider using libraries like BeautifulSoup
        import re
        plain = re.sub(r'<[^>]+>', '', html_content)
        plain = re.sub(r'\s+', ' ', plain).strip()
        return plain
    
    def _add_attachments(self, message: MIMEMultipart, attachments: List[str]):
        """Add file attachments to the email"""
        for file_path in attachments:
            if Path(file_path).exists():
                try:
                    with open(file_path, 'rb') as attachment:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(attachment.read())
                    
                    encoders.encode_base64(part)
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename= {Path(file_path).name}'
                    )
                    message.attach(part)
                    logger.debug(f"Added attachment: {file_path}")
                    
                except Exception as e:
                    logger.warning(f"Failed to attach file {file_path}: {e}")
            else:
                logger.warning(f"Attachment file not found: {file_path}")
    
    def test_connection(self) -> dict:
        """Test SMTP connection and authentication - useful for diagnostics"""
        try:
            if not self.config.validate():
                return {
                    'success': False,
                    'error': 'Configuration validation failed',
                    'details': 'Missing required UNS email configuration'
                }
            
            # Test connection
            server = smtplib.SMTP(self.config.host, self.config.port, timeout=self.config.timeout)
            
            try:
                # Test STARTTLS
                if self.config.starttls_enable:
                    server.starttls(context=ssl.create_default_context())
                
                # Test authentication
                server.login(self.config.username, self.config.password)
                
                return {
                    'success': True,
                    'message': 'UNS SMTP connection and authentication successful',
                    'server_info': {
                        'host': self.config.host,
                        'port': self.config.port,
                        'starttls_enabled': self.config.starttls_enable
                    }
                }
                
            finally:
                server.quit()
                
        except Exception as e:
            return {
                'success': False,
                'error': f'UNS SMTP connection test failed: {str(e)}',
                'details': str(e)
            }

# Factory function for easy integration
def create_uns_email_sender(config: Optional[UNSEmailConfig] = None) -> UNSEmailSender:
    """Create UNS Email Sender instance"""
    return UNSEmailSender(config)

# Convenience function for quick sending
def send_uns_email(to: Union[str, List[str]], subject: str, body: str, 
                   is_html: bool = True, cc: Optional[Union[str, List[str]]] = None,
                   config: Optional[UNSEmailConfig] = None) -> dict:
    """
    Quick email sending function
    
    Usage:
        result = send_uns_email(
            to="user@company.com",
            subject="Test Email",
            body="<h1>Hello from UNS!</h1>",
            is_html=True
        )
    """
    email_request = EmailRequest(
        to=to,
        subject=subject,
        body=body,
        cc=cc,
        is_html=is_html
    )
    
    sender = create_uns_email_sender(config)
    return sender.send(email_request)