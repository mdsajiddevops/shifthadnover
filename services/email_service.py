from flask_mail import Message
from flask import current_app
import logging

logger = logging.getLogger(__name__)

def send_handover_email(shift):
    logger.debug(f"[DEBUG] ✅ send_handover_email called from email_service.py for shift_id={shift.id}")
    
    # Import mail here to avoid circular import
    from flask import current_app
    import os
    import time
    from models.models import Team, User, Incident
    from models.models import Incident, ShiftKeyPoint, TeamMember, Team, User, Account
    from models.app_config import AppConfig
    from models.email_delivery_log import EmailDeliveryLog
    from models.models import db
    from datetime import datetime
    
    # Initialize email log variable for tracking
    email_log = None
    email_start_time = time.time()
    
    # Fix Flask-Mail configuration by loading SMTP settings from database
    mail = None
    try:
        # Use SQLAlchemy to get SMTP configuration from MySQL database
        from models.models import db
        
        # Use the existing MySQL database connection
        logger.debug(f"[EMAIL_SERVICE] 📍 Using MySQL database connection")
        
        # Query SMTP configuration from the database using SQLAlchemy
        try:
            # Try to get from smtp_config table first
            result = db.session.execute(db.text("SELECT config_key, config_value FROM smtp_config"))
            configs = dict(result.fetchall())
            logger.debug(f"[EMAIL_SERVICE] 🔍 Loaded configs from MySQL smtp_config: {list(configs.keys())}")
        except Exception as db_error:
            # Fallback: try to get from app_config table if smtp_config doesn't exist
            logger.debug(f"[EMAIL_SERVICE] ⚠️ smtp_config table not found, trying app_config: {db_error}")
            try:
                result = db.session.execute(db.text("SELECT config_key, config_value FROM app_config WHERE config_key LIKE 'smtp_%' OR config_key LIKE 'mail_%'"))
                configs = dict(result.fetchall())
                logger.debug(f"[EMAIL_SERVICE] � Loaded configs from MySQL app_config: {list(configs.keys())}")
            except Exception as fallback_error:
                logger.debug(f"[EMAIL_SERVICE] ❌ Could not load SMTP config from database: {fallback_error}")
                configs = {}
        
        if configs:
            logger.debug(f"[EMAIL_SERVICE] 🔍 Loaded configs from database: {list(configs.keys())}")
            
            # Update Flask app configuration with SMTP settings
            app = current_app._get_current_object()
            
            # Safely get port with proper error handling
            smtp_port = configs.get('smtp_port', '587')
            if smtp_port is None or smtp_port == '':
                smtp_port = '587'  # Default fallback
            
            try:
                smtp_port_int = int(smtp_port)
            except (ValueError, TypeError) as port_error:
                logger.debug(f"[EMAIL_SERVICE] ⚠️ Invalid port value '{smtp_port}', using default 587: {port_error}")
                smtp_port_int = 587
            
            smtp_mapping = {
                'MAIL_SERVER': configs.get('smtp_server'),
                'MAIL_PORT': smtp_port_int,
                'MAIL_USERNAME': configs.get('smtp_username'),
                'MAIL_PASSWORD': configs.get('smtp_password'),
                'MAIL_USE_TLS': configs.get('smtp_use_tls', 'false').lower() == 'true',
                'MAIL_USE_SSL': configs.get('smtp_use_ssl', 'false').lower() == 'true',
                'MAIL_DEFAULT_SENDER': configs.get('mail_default_sender'),
                'MAIL_TIMEOUT': 30,
                # Add additional Flask-Mail parameters with proper defaults
                'MAIL_MAX_EMAILS': None,  # No limit
                'MAIL_SUPPRESS_SEND': False,  # Don't suppress sending
                'MAIL_ASCII_ATTACHMENTS': False,  # Allow non-ASCII attachments
                'TESTING': False  # Not in testing mode
            }
            
            logger.debug(f"[EMAIL_SERVICE] 🔍 Raw config values: {configs}")
            logger.debug(f"[EMAIL_SERVICE] 🔍 Prepared SMTP mapping: {smtp_mapping}")
            
            # Check for None values that might cause Flask-Mail issues
            for key, value in smtp_mapping.items():
                if value is None:
                    logger.debug(f"[EMAIL_SERVICE] ⚠️ WARNING: {key} is None!")
                else:
                    logger.debug(f"[EMAIL_SERVICE] ✅ {key}: {value} (type: {type(value)})")
            
            # Only update if we have valid SMTP config
            if smtp_mapping['MAIL_SERVER'] and smtp_mapping['MAIL_USERNAME']:
                # Validate critical configuration values before updating
                required_configs = ['MAIL_SERVER', 'MAIL_PORT', 'MAIL_USERNAME', 'MAIL_PASSWORD']
                missing_configs = [key for key in required_configs if smtp_mapping.get(key) is None]
                
                if missing_configs:
                    logger.debug(f"[EMAIL_SERVICE] ❌ Missing required configs: {missing_configs}")
                    logger.debug(f"[EMAIL_SERVICE] 🚫 Skipping Flask-Mail configuration due to missing values")
                else:
                    logger.debug(f"[EMAIL_SERVICE] ✅ All required SMTP configs present")
                    
                    # Update app config directly
                    app.config.update(smtp_mapping)
                    
                    # Verify the values were set correctly
                    logger.debug(f"[EMAIL_SERVICE] 📋 Final app config check:")
                    for key in required_configs:
                        value = app.config.get(key)
                        logger.debug(f"[EMAIL_SERVICE]   {key}: {value} (type: {type(value)})")
                    
                    # Reinitialize Mail object with new configuration
                    from flask_mail import Mail
                    mail = Mail()
                    mail.init_app(app)
                    
                    # Update the current mail object in app extensions
                app.extensions['mail'] = mail
                
                logger.debug(f"[EMAIL_SERVICE] ✅ Flask-Mail reconfigured with: {smtp_mapping['MAIL_SERVER']}:{smtp_mapping['MAIL_PORT']}")
            else:
                logger.debug(f"[EMAIL_SERVICE] ⚠️ Incomplete SMTP configuration in database - Server: {smtp_mapping['MAIL_SERVER']}, Username: {smtp_mapping['MAIL_USERNAME']}")
                mail = current_app.extensions.get('mail')
        else:
            logger.debug(f"[EMAIL_SERVICE] ⚠️ No SMTP configuration found in database")
            mail = current_app.extensions.get('mail')
            
    except Exception as e:
        logger.debug(f"[EMAIL_SERVICE] ⚠️ Could not reconfigure Flask-Mail: {e}")
        import traceback
        logger.debug(f"[EMAIL_SERVICE] 🔍 Full error details: {traceback.format_exc()}")
        mail = current_app.extensions.get('mail')
    
    # Fallback to existing mail if reconfiguration failed
    if mail is None:
        mail = current_app.extensions.get('mail')
    
    # Quick bypass for local development to avoid email delays
    if os.environ.get('LOCAL_DEVELOPMENT') == 'True' and os.environ.get('SKIP_EMAIL_FOR_SPEED', 'false').lower() == 'true':
        logger.debug("[EMAIL_SERVICE] 🚀 Skipping email sending for local development (SKIP_EMAIL_FOR_SPEED=true)")
        return
    
    # Check if email notifications are enabled in SMTP configuration
    from models.smtp_config import SMTPConfig
    smtp_enabled = SMTPConfig.get_config('smtp_enabled', 'false').lower() == 'true'
    logger.debug(f"[EMAIL_SERVICE] 🔍 SMTP enabled check: {smtp_enabled}")
    if not smtp_enabled:
        logger.debug("[EMAIL_SERVICE] 📧 Email sending is disabled in SMTP configuration (smtp_enabled=false)")
        return
    
    # Check if email notifications are enabled in app configuration (backward compatibility)
    notifications_enabled = AppConfig.get_config('email_notifications_enabled', 'true').lower() == 'true'
    logger.debug(f"[EMAIL_SERVICE] 🔍 App notifications enabled: {notifications_enabled}")
    if not notifications_enabled:
        logger.debug("[EMAIL_SERVICE] 📧 Email notifications are disabled in app configuration")
        logging.info("[EMAIL_SERVICE] Email notifications are disabled in app configuration")
        return
    
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

    subject = f"{subject_prefix}🔄 {shift.current_shift_type} to {shift.next_shift_type} Shift Handover - {shift.date}"

    # Initialize variables for recipient tracking (to fix variable scoping issue)
    configured_recipients = None
    priority_alert_recipients = None
    
    # Build comprehensive recipient list using new EmailConfigService
    recipients = set()
    
    # 1. Try to use new Email Configuration Service first
    try:
        from services.email_config_service import EmailConfigService
        email_service = EmailConfigService()
        
        # Get recipients using the new service
        # We need a user_id for audit purposes - use the first available user or system user
        user_id = 1  # System/admin user for handover operations
        
        # Check if this is a priority handover (has high-priority incidents)
        priority_incidents = Incident.query.filter_by(shift_id=shift.id, type='Priority').all()
        escalated_incidents = Incident.query.filter_by(shift_id=shift.id, type='Escalated').all()
        high_priority_count = len([i for i in priority_incidents + escalated_incidents 
                                 if i.priority and i.priority.lower() in ['high', 'critical']])
        is_priority_handover = high_priority_count > 0
        
        recipient_result = email_service.get_recipients_for_handover(
            user_id=user_id,
            account_id=shift.account_id,
            team_id=shift.team_id,
            is_priority=is_priority_handover
        )
        
        if recipient_result['success']:
            # Add TO recipients
            for email in recipient_result['to_recipients']:
                recipients.add(email)
            
            # Add CC recipients
            for email in recipient_result['cc_recipients']:
                recipients.add(email)
            
            # Add priority recipients if it's a priority handover
            if is_priority_handover:
                for email in recipient_result['priority_recipients']:
                    recipients.add(email)
            
            # Set tracking variables for recipient_info() function
            if recipient_result['to_recipients'] or recipient_result['cc_recipients']:
                configured_recipients = f"{len(recipient_result['to_recipients']) + len(recipient_result['cc_recipients'])} configured recipients"
            if recipient_result['priority_recipients']:
                priority_alert_recipients = f"{len(recipient_result['priority_recipients'])} priority recipients"
            
            logger.debug(f"[EMAIL_SERVICE] ✅ Using new Email Configuration Service")
            logger.debug(f"[EMAIL_SERVICE] 📧 Recipients from config: TO={len(recipient_result['to_recipients'])}, CC={len(recipient_result['cc_recipients'])}, Priority={len(recipient_result['priority_recipients'])}")
            
    except Exception as config_error:
        logger.debug(f"[EMAIL_SERVICE] ⚠️ New Email Configuration Service failed: {config_error}")
        logger.debug(f"[EMAIL_SERVICE] 🔄 Falling back to legacy recipient configuration...")
        
        # 2. Fallback: Use legacy team-specific email recipients
        team_recipients = None
        if shift.team_id:
            team = Team.query.get(shift.team_id)
            if team and team.email_recipients:
                team_recipients = team.email_recipients.strip()
                configured_recipients = team_recipients  # Set for recipient_info() function
                logger.debug(f"[EMAIL_SERVICE] 🏢 Using team-specific recipients for {team.name}: {team_recipients}")
                for email in team_recipients.split(','):
                    email = email.strip()
                    if email:
                        recipients.add(email)
        
        # 3. Fallback: Use global handover email recipients if no team-specific config
        if not recipients:
            configured_recipients = AppConfig.get_config('handover_email_recipients', '')
            if configured_recipients:
                logger.debug(f"[EMAIL_SERVICE] 🌐 Using global recipients (no team-specific config): {configured_recipients}")
                for email in configured_recipients.split(','):
                    email = email.strip()
                    if email:
                        recipients.add(email)
    
    # Priority alert recipients are now handled by the EmailConfigService above
    
    # 3. Fallback: Add next shift engineers' emails if available
    if not recipients:
        for engineer in shift.next_engineers:
            if hasattr(engineer, 'email') and engineer.email:
                recipients.add(engineer.email)
    
    # 4. Fallback: Add team administrators for this team
    if not recipients and shift.team_id:
        team_admins = User.query.filter_by(team_id=shift.team_id, role='team_admin').all()
        for admin in team_admins:
            if admin.email:
                recipients.add(admin.email)
        
        # Also add account admins for this account
        if shift.account_id:
            account_admins = User.query.filter_by(account_id=shift.account_id, role='account_admin').all()
            for admin in account_admins:
                if admin.email:
                    recipients.add(admin.email)
    
    # 5. Final fallback: Add configured team email if available
    if not recipients:
        team_email = current_app.config.get('TEAM_EMAIL')
        if team_email:
            recipients.add(team_email)
    
    # Convert set to list
    recipients = list(recipients)
    
    logger.debug(f"[EMAIL_SERVICE] 🔍 Final recipients list: {recipients}")
    logger.debug(f"[EMAIL_SERVICE] 🔍 Total recipients count: {len(recipients)}")
    
    if not recipients:
        logger.debug("[EMAIL_SERVICE] ❌ No email recipients found for handover notification")
        logger.debug("[EMAIL_SERVICE] 💡 Please configure email recipients in Admin > Secrets Management > Email Recipients")
        logging.warning("No email recipients found for handover notification - please configure email recipients in admin settings")
        return

    # 🔧 FIX: Query engineers from roster with proper team filtering
    # Instead of using stored shift.current_engineers/next_engineers which may include all teams
    from models.models import ShiftRoster
    from datetime import timedelta
    
    def get_roster_engineers_for_email(shift_date, shift_type, account_id, team_id):
        """Get engineers from roster for a specific shift with team filtering"""
        shift_map = {'Morning': 'D', 'Evening': 'E', 'Night': 'N', 'OnShore': 'OS', 'OffShore': 'OF'}
        shift_code = shift_map.get(shift_type)
        if not shift_code:
            return []
        
        # Query roster with account and team filtering
        query = ShiftRoster.query.filter_by(date=shift_date, shift_code=shift_code)
        if account_id and team_id:
            query = query.filter_by(account_id=account_id, team_id=team_id)
        elif account_id:
            query = query.filter_by(account_id=account_id)
        
        entries = query.all()
        member_ids = [e.team_member_id for e in entries]
        
        if member_ids:
            engineers = TeamMember.query.filter(TeamMember.id.in_(member_ids)).all()
            return [e.name for e in engineers]
        return []
    
    # Get current shift engineers from roster
    current_engineer_names = get_roster_engineers_for_email(
        shift.date, shift.current_shift_type, shift.account_id, shift.team_id
    )
    current_engineers = ', '.join(current_engineer_names) if current_engineer_names else 'None assigned'
    
    # Get next shift engineers from roster
    # For Night->Morning transition, morning engineers come from next day
    next_shift_date = shift.date
    if shift.current_shift_type == 'Night' and shift.next_shift_type == 'Morning':
        next_shift_date = shift.date + timedelta(days=1)
    
    next_engineer_names = get_roster_engineers_for_email(
        next_shift_date, shift.next_shift_type, shift.account_id, shift.team_id
    )
    next_engineers = ', '.join(next_engineer_names) if next_engineer_names else 'None assigned'
    
    logger.debug(f"[EMAIL_SERVICE] 👥 Current shift engineers ({shift.current_shift_type}): {len(current_engineer_names)} found")
    logger.debug(f"[EMAIL_SERVICE] 👥 Next shift engineers ({shift.next_shift_type}): {len(next_engineer_names)} found")
    
    # Fix incident type queries (using correct types from database)
    open_incidents = Incident.query.filter_by(shift_id=shift.id, type='Open').all()
    closed_incidents = Incident.query.filter_by(shift_id=shift.id, type='Closed').all()
    priority_incidents = Incident.query.filter_by(shift_id=shift.id, type='Priority').all()
    handover_incidents = Incident.query.filter_by(shift_id=shift.id, type='Handover').all()
    escalated_incidents = Incident.query.filter_by(shift_id=shift.id, type='Escalated').all()
    # Query key points specific to this shift (entered in the submitted handover form)
    # 🔧 FIX: Only include Open and In Progress keypoints, exclude Closed ones
    key_points = ShiftKeyPoint.query.filter(
        ShiftKeyPoint.shift_id == shift.id,
        ShiftKeyPoint.status.in_(['Open', 'In Progress'])
    ).all()

    logger.debug(f"[EMAIL_SERVICE] 📋 Found {len(key_points)} active key_points for shift_id={shift.id}")
    
    # Query additional handover data for complete email content
    # 🔧 FIX: Filter out Published KBs and Completed/Cancelled Change Infos
    # These statuses indicate the item is "done" and shouldn't appear in new handover emails
    from models.models import ShiftChangeInfo, ShiftKBUpdate
    from datetime import timedelta
    
    # 🔧 FIX: Query change_infos by date/team/account with deduplication
    # This ensures ALL pending changes for this date appear in the email without duplicates
    raw_change_infos = ShiftChangeInfo.query.filter(
        ShiftChangeInfo.account_id == shift.account_id,
        ShiftChangeInfo.team_id == shift.team_id,
        ShiftChangeInfo.created_at >= shift.date,
        ShiftChangeInfo.created_at < shift.date + timedelta(days=1),
        ~ShiftChangeInfo.status.in_(['Completed', 'Cancelled', 'Implemented'])
    ).order_by(ShiftChangeInfo.id.desc()).all()
    
    # Deduplicate by change_number - keep most recent version
    change_map = {}
    for ci in raw_change_infos:
        key = ci.change_number.strip().lower() if ci.change_number else f"{ci.app_name}_{ci.description[:30] if ci.description else ''}"
        if key not in change_map:
            change_map[key] = ci
    change_infos = list(change_map.values())
    
    # 🔧 FIX: Same for kb_updates - query by date/team/account with deduplication
    raw_kb_updates = ShiftKBUpdate.query.filter(
        ShiftKBUpdate.account_id == shift.account_id,
        ShiftKBUpdate.team_id == shift.team_id,
        ShiftKBUpdate.created_at >= shift.date,
        ShiftKBUpdate.created_at < shift.date + timedelta(days=1),
        ShiftKBUpdate.status != 'Published'
    ).order_by(ShiftKBUpdate.id.desc()).all()
    
    # Deduplicate by kb_number
    kb_map = {}
    for kb in raw_kb_updates:
        key = kb.kb_number.strip().lower() if kb.kb_number else f"{kb.app_name}_{kb.description[:30] if kb.description else ''}"
        if key not in kb_map:
            kb_map[key] = kb
    kb_updates = list(kb_map.values())
    
    additional_notes = getattr(shift, 'additional_notes', None) or getattr(shift, 'notes', None) or ''
    
    # Get team name for context
    team_name = "Team"
    if shift.team_id:
        team = Team.query.get(shift.team_id)
        if team:
            team_name = team.name

    # Get account name for context
    account_name = "Account"
    if shift.account_id:
        account = Account.query.get(shift.account_id)
        if account:
            account_name = account.name

    # Get submitted by information
    submitted_by = "Unknown"
    try:
        from models.handover_enhanced import HandoverRequest
        
        # Find the corresponding handover request
        handover_req = HandoverRequest.query.filter_by(
            shift_date=shift.date,
            current_shift_type=shift.current_shift_type,
            account_id=shift.account_id,
            team_id=shift.team_id
        ).first()
        
        if handover_req and handover_req.created_by_id:
            user = User.query.get(handover_req.created_by_id)
            if user:
                submitted_by = user.display_name or user.username
                logger.debug(f"[EMAIL_SERVICE] 👤 Found submitter: {submitted_by}")
        else:
            # Fallback: Try to find from audit log
            from models.audit_log import AuditLog
            audit_entry = AuditLog.query.filter(
                AuditLog.action.like('%Create Handover%'),
                AuditLog.details.like(f'%Team: {shift.team_id}%'),
                AuditLog.details.like(f'%Date: {shift.date}%')
            ).order_by(AuditLog.id.desc()).first()
            
            if audit_entry and audit_entry.user_id:
                user = User.query.get(audit_entry.user_id)
                if user:
                    submitted_by = user.display_name or user.username
            elif audit_entry:
                submitted_by = audit_entry.username or 'Unknown User'
                
    except Exception as e:
        logger.debug(f"[EMAIL_SERVICE] ⚠️ Error finding submitter: {e}")
        submitted_by = "Unknown"

    def parse_incident_title(title):
        """
        Parse incident title to extract application name and incident ID.
        Handles multiple formats:
        - "[AppName] INC123456" - bracket format from edit mode
        - "AppName - INC123456" - dash format from create mode
        - "INC123456" - incident ID only
        """
        import re
        
        if not title:
            return '-', '-'
        
        title = title.strip()
        
        # Format 1: [AppName] IncidentID
        bracket_match = re.match(r'^\[([^\]]+)\]\s*(.+)$', title)
        if bracket_match:
            return bracket_match.group(1).strip(), bracket_match.group(2).strip()
        
        # Format 2: AppName - IncidentID
        if ' - ' in title:
            parts = title.split(' - ', 1)
            return parts[0].strip(), parts[1].strip()
        
        # Format 3: Just incident ID or unformatted title
        return '-', title

    def detailed_incidents_section():
        sections = ""
        
        # Open Incidents
        if open_incidents:
            sections += '<h4 style="color: #dc3545; margin-top: 20px;">🔴 Open Incidents</h4>'
            sections += '<table border="1" cellpadding="8" cellspacing="0" style="border-collapse:collapse; width:100%; margin-bottom: 15px;">'
            sections += '<tr style="background-color: #f8f9fa;"><th>Application</th><th>Incident ID</th><th>Priority</th><th>Assigned To</th><th>Description</th></tr>'
            for inc in open_incidents:
                app_name, inc_id = parse_incident_title(inc.title)
                sections += f'<tr><td>{app_name}</td><td>{inc_id}</td><td>{inc.priority or "Medium"}</td><td>{inc.assigned_to or "-"}</td><td>{inc.description or "-"}</td></tr>'
            sections += '</table>'
        
        # Closed Incidents  
        if closed_incidents:
            sections += '<h4 style="color: #198754; margin-top: 20px;">✅ Closed Incidents</h4>'
            sections += '<table border="1" cellpadding="8" cellspacing="0" style="border-collapse:collapse; width:100%; margin-bottom: 15px;">'
            sections += '<tr style="background-color: #f8f9fa;"><th>Application</th><th>Incident ID</th><th>Resolution</th></tr>'
            for inc in closed_incidents:
                app_name, inc_id = parse_incident_title(inc.title)
                sections += f'<tr><td>{app_name}</td><td>{inc_id}</td><td>{inc.description or "Resolved"}</td></tr>'
            sections += '</table>'
        
        # Priority Incidents
        if priority_incidents:
            sections += '<h4 style="color: #fd7e14; margin-top: 20px;">⚡ Priority Incidents</h4>'
            sections += '<table border="1" cellpadding="8" cellspacing="0" style="border-collapse:collapse; width:100%; margin-bottom: 15px;">'
            sections += '<tr style="background-color: #f8f9fa;"><th>Application</th><th>Incident ID</th><th>Priority Level</th><th>Escalated To</th><th>Impact</th></tr>'
            for inc in priority_incidents:
                app_name, inc_id = parse_incident_title(inc.title)
                sections += f'<tr><td>{app_name}</td><td>{inc_id}</td><td>{inc.priority or "High"}</td><td>{inc.escalated_to or "-"}</td><td>{inc.description or "-"}</td></tr>'
            sections += '</table>'
        
        # Escalated Incidents
        if escalated_incidents:
            sections += '<h4 style="color: #6f42c1; margin-top: 20px;">🚨 Escalated Incidents</h4>'
            sections += '<table border="1" cellpadding="8" cellspacing="0" style="border-collapse:collapse; width:100%; margin-bottom: 15px;">'
            sections += '<tr style="background-color: #f8f9fa;"><th>Application</th><th>Incident ID</th><th>Priority Level</th><th>Escalated To</th><th>Impact</th></tr>'
            for inc in escalated_incidents:
                app_name, inc_id = parse_incident_title(inc.title)
                sections += f'<tr><td>{app_name}</td><td>{inc_id}</td><td>{inc.priority or "High"}</td><td>{inc.escalated_to or "-"}</td><td>{inc.description or "-"}</td></tr>'
            sections += '</table>'
        
        # Handover Incidents
        if handover_incidents:
            sections += '<h4 style="color: #0d6efd; margin-top: 20px;">🔄 Handover Incidents</h4>'
            sections += '<table border="1" cellpadding="8" cellspacing="0" style="border-collapse:collapse; width:100%; margin-bottom: 15px;">'
            sections += '<tr style="background-color: #f8f9fa;"><th>Application</th><th>Incident ID</th><th>Status</th><th>Next Action By</th><th>Notes</th></tr>'
            for inc in handover_incidents:
                app_name, inc_id = parse_incident_title(inc.title)
                sections += f'<tr><td>{app_name}</td><td>{inc_id}</td><td>{inc.status or "Active"}</td><td>{inc.assigned_to or "-"}</td><td>{inc.description or "-"}</td></tr>'
            sections += '</table>'
        
        if not sections:
            sections = '<h4>📋 Incidents</h4><p style="color: #6c757d; font-style: italic;">No incidents reported for this shift.</p>'
        
        return sections

    def key_points_section():
        if not key_points:
            return '<h4>🎯 Key Points</h4><p style="color: #6c757d; font-style: italic;">No key points reported for this shift.</p>'
        
        section = '<h4 style="margin-top: 20px;">🎯 Key Points</h4>'
        section += '<table border="1" cellpadding="8" cellspacing="0" style="border-collapse:collapse; width:100%; margin-bottom: 15px;">'
        section += '<tr style="background-color: #f8f9fa;"><th>Description</th><th>Status</th><th>Responsible</th></tr>'
        
        for kp in key_points:
            responsible = TeamMember.query.get(kp.responsible_engineer_id).name if kp.responsible_engineer_id else "-"
            status_color = "#198754" if kp.status == "Closed" else "#ffc107" if kp.status == "In Progress" else "#dc3545"
            section += f'<tr><td>{kp.description}</td><td style="color: {status_color}; font-weight: bold;">{kp.status}</td><td>{responsible}</td></tr>'
        
        section += '</table>'
        return section

    def additional_notes_section():
        if not additional_notes or additional_notes.strip() == '':
            return ''
        
        section = '<h4 style="margin-top: 20px;">📝 Additional Notes</h4>'
        section += '<div style="padding: 15px; background-color: #f8f9fa; border-left: 4px solid #007bff; margin-bottom: 15px;">'
        section += f'<p style="margin: 0; white-space: pre-line;">{additional_notes.strip()}</p>'
        section += '</div>'
        return section

    def change_info_section():
        if not change_infos:
            return ''
        
        section = '<h4 style="margin-top: 20px;">🔧 Change Information</h4>'
        section += '<table border="1" cellpadding="8" cellspacing="0" style="border-collapse:collapse; width:100%; margin-bottom: 15px;">'
        section += '<tr style="background-color: #f8f9fa;"><th>Application</th><th>Change Number</th><th>Description</th><th>Date/Time</th><th>Responsible Engineer</th><th>Status</th></tr>'
        
        for change in change_infos:
            section += f'<tr>'
            section += f'<td>{change.app_name or "-"}</td>'
            section += f'<td>{change.change_number or "-"}</td>'
            section += f'<td>{change.description or "-"}</td>'
            section += f'<td>{change.change_datetime or "-"}</td>'
            section += f'<td>{change.responsible or "-"}</td>'
            section += f'<td>{change.status or "-"}</td>'
            section += f'</tr>'
        
        section += '</table>'
        return section

    def kb_updates_section():
        if not kb_updates:
            return ''
        
        section = '<h4 style="margin-top: 20px;">📚 KB Updates</h4>'
        section += '<table border="1" cellpadding="8" cellspacing="0" style="border-collapse:collapse; width:100%; margin-bottom: 15px;">'
        section += '<tr style="background-color: #f8f9fa;"><th>Application</th><th>KB Number</th><th>Description</th><th>Responsible Person</th><th>Status</th></tr>'
        
        for kb in kb_updates:
            section += f'<tr>'
            section += f'<td>{kb.app_name or "-"}</td>'
            section += f'<td>{kb.kb_number or "-"}</td>'
            section += f'<td>{kb.description or "-"}</td>'
            section += f'<td>{kb.responsible or "-"}</td>'
            section += f'<td>{kb.status or "-"}</td>'
            section += f'</tr>'
        
        section += '</table>'
        return section

    def recipient_info():
        recipient_types = []
        if configured_recipients:
            recipient_types.append("Configured Recipients")
        if priority_alert_recipients and len([i for i in priority_incidents + escalated_incidents if i.priority and i.priority.lower() in ['high', 'critical']]) > 0:
            recipient_types.append("Priority Alert Recipients")
        if not configured_recipients and not priority_alert_recipients:
            recipient_types.append("Team Members & Administrators")
        
        return " + ".join(recipient_types) if recipient_types else "Default Recipients"

    # Create comprehensive HTML email
    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; }}
            .summary-table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
            .summary-table th {{ background-color: #e9ecef; padding: 12px; text-align: left; border: 1px solid #dee2e6; }}
            .summary-table td {{ padding: 12px; border: 1px solid #dee2e6; }}
            h3 {{ color: #495057; border-bottom: 2px solid #007bff; padding-bottom: 10px; text-align: center; }}
            h4 {{ color: #495057; margin-top: 25px; margin-bottom: 15px; }}
            .footer {{ margin-top: 30px; padding: 15px; background-color: #f8f9fa; border-radius: 5px; font-size: 0.9em; color: #6c757d; }}
            .alert {{ padding: 10px; margin: 10px 0; border-radius: 5px; }}
            .alert-warning {{ background-color: #fff3cd; border-left: 4px solid #ffc107; }}
            .alert-danger {{ background-color: #f8d7da; border-left: 4px solid #dc3545; }}
        </style>
    </head>
    <body>
        <h3>📋 Shift Handover Details</h3>
        <table class="summary-table">
            <tr><th style="width: 30%;">Date</th><td>{shift.date}</td></tr>
            <tr><th>From</th><td>{shift.current_shift_type}</td></tr>
            <tr><th>To</th><td>{shift.next_shift_type}</td></tr>
            <tr><th>Account</th><td>{account_name}</td></tr>
            <tr><th>Team</th><td>{team_name}</td></tr>
            <tr><th>Current Shift Engineers</th><td>{current_engineers}</td></tr>
            <tr><th>Next Shift Engineers</th><td>{next_engineers}</td></tr>
            <tr><th>Submission Time</th><td>{shift.submitted_at.strftime('%Y-%m-%d %H:%M:%S') if shift.submitted_at else 'Just submitted'}</td></tr>
            <tr><th>Submitted By</th><td><span style="color: #0d6efd; font-weight: bold;">👤 {submitted_by}</span></td></tr>
            <tr><th>Status</th><td><span style="color: #198754; font-weight: bold;">✅ Completed</span></td></tr>
        </table>
        
        {detailed_incidents_section()}
        
        {change_info_section()}
        
        {kb_updates_section()}
        
        {key_points_section()}
        
        {additional_notes_section()}
        
        <div class="footer" style="text-align: center; padding: 15px; background-color: #f8f9fa; border-top: 1px solid #dee2e6; color: #6c757d; font-size: 12px;">
            <p style="margin: 0;"><em>Generated by Shift Handover Management System</em></p>
        </div>
    </body>
    </html>
    """
    
    # Create plain text version for email clients that don't support HTML
    text_content = f"""
SHIFT HANDOVER REPORT
=====================
Team: {team_name}
Date: {shift.date}
Transition: {shift.current_shift_type} to {shift.next_shift_type}

TEAM INFORMATION:
Current Shift Engineers: {current_engineers}
Next Shift Engineers: {next_engineers}

INCIDENTS SUMMARY:
- Open Incidents: {len(open_incidents)}
- Priority Incidents: {len(priority_incidents)}
- Escalated Incidents: {len(escalated_incidents)}
- Handover Incidents: {len(handover_incidents)}
- Closed Incidents: {len(closed_incidents)}
- Change Requests: {len(change_infos)}
- KB Updates: {len(kb_updates)}
- Key Points: {len(key_points)}

KEY POINTS: {len(key_points)} items

CHANGE INFORMATION: {len(change_infos)} items

KB UPDATES: {len(kb_updates)} items

ADDITIONAL NOTES: {'Yes' if additional_notes and additional_notes.strip() else 'None'}

RECIPIENT INFO:
- Category: {recipient_info()}
- Count: {len(recipients)} recipients

Please view this email in HTML format for detailed incident and key point information.

This is an automated notification from the Shift Handover Management System.
Configure email recipients in Admin > Secrets Management > Email Recipients.
    """
    
    # Get the configured default sender
    sender = current_app.config.get('MAIL_DEFAULT_SENDER')
    if not sender:
        sender = current_app.config.get('MAIL_USERNAME')
    
    # If Flask config doesn't have sender, try to load from SMTPConfig directly
    if not sender:
        try:
            from models.smtp_config import SMTPConfig
            sender = SMTPConfig.get_config('mail_default_sender')
            logger.debug(f"[EMAIL_SERVICE] ✅ Loaded sender from SMTPConfig: {sender}")
        except Exception as e:
            logger.debug(f"[EMAIL_SERVICE] ❌ Failed to load sender from SMTPConfig: {e}")
            sender = 'noreply@shift-handover.local'  # Final fallback
            logger.debug(f"[EMAIL_SERVICE] ⚠️ Using fallback sender: {sender}")
    
    logger.debug(f"[EMAIL_SERVICE] 📧 Using sender: {sender}")
    
    # Debug the message parameters before creating the Message
    logger.debug(f"[EMAIL_SERVICE] 🔍 Message parameters:")
    logger.debug(f"  - Subject: {subject}")
    logger.debug(f"  - Recipients: {recipients} (type: {type(recipients)})")
    logger.debug(f"  - Sender: {sender} (type: {type(sender)})")
    logger.debug(f"  - Recipients length: {len(recipients) if recipients else 'None'}")
    
    # Validate parameters before creating Message
    if not subject:
        raise ValueError("Subject cannot be None or empty")
    if not recipients:
        raise ValueError("Recipients cannot be None or empty")
    if not sender:
        raise ValueError("Sender cannot be None or empty")
    
    try:
        # Create Message with explicit parameter validation
        from flask_mail import Message
        
        # Ensure recipients is a proper list
        if isinstance(recipients, str):
            recipients = [recipients]
        elif not isinstance(recipients, list):
            recipients = list(recipients)
        
        # Ensure all recipients are strings
        recipients = [str(recipient).strip() for recipient in recipients if recipient]
        
        # Create message step by step
        logger.debug(f"[EMAIL_SERVICE] 🔧 Creating Message object...")
        msg = Message()
        msg.subject = str(subject)
        msg.recipients = recipients
        msg.sender = str(sender)
        
        logger.debug(f"[EMAIL_SERVICE] ✅ Message object created successfully")
        logger.debug(f"[EMAIL_SERVICE]   Subject: '{msg.subject}'")
        logger.debug(f"[EMAIL_SERVICE]   Recipients: {msg.recipients}")
        logger.debug(f"[EMAIL_SERVICE]   Sender: '{msg.sender}'")
        logger.debug(f"[EMAIL_SERVICE] ✅ Message object created successfully")
    except Exception as msg_error:
        logger.debug(f"[EMAIL_SERVICE] ❌ Failed to create Message object: {msg_error}")
        logger.debug(f"[EMAIL_SERVICE] 🔍 Message creation error type: {type(msg_error)}")
        raise msg_error
    
    msg.body = text_content
    msg.html = html
    
    logging.basicConfig(level=logging.DEBUG, force=True)
    logger.debug(f"[EMAIL_SERVICE] Sending handover email to {len(recipients)} recipients via configured settings")
    logging.debug(f"[EMAIL_SERVICE] Enhanced handover email details - Recipients: {recipients}, Team: {team_name}")
    
    # 📊 Create email delivery log entry for monitoring
    try:
        smtp_server = current_app.config.get('MAIL_SERVER')
        smtp_port = current_app.config.get('MAIL_PORT')
        
        email_log = EmailDeliveryLog.log_email_attempt(
            subject=subject,
            recipients=recipients,
            source_type='handover',
            source_id=shift.id,
            sender=sender,
            account_id=shift.account_id,
            team_id=shift.team_id,
            triggered_by_id=None,  # Will be updated if we can get current user
            smtp_server=smtp_server,
            smtp_port=smtp_port
        )
        logger.debug(f"[EMAIL_SERVICE] 📊 Email delivery log created: ID={email_log.id}")
    except Exception as log_error:
        logger.debug(f"[EMAIL_SERVICE] ⚠️ Could not create email log: {log_error}")
        email_log = None
    
    try:
        import time
        
        # Set up timeout for Flask-Mail sending (5 seconds max for better UX)
        logger.debug(f"[EMAIL_SERVICE] 🕐 Attempting Flask-Mail send with 5-second timeout...")
        start_time = time.time()
        
        # Use simple socket-based timeout approach (works in any thread)
        import socket
        original_timeout = socket.getdefaulttimeout()
        try:
            socket.setdefaulttimeout(5)  # 5 second timeout for better user experience
            
            # Final validation before attempting send
            from flask import current_app
            app = current_app._get_current_object()
            critical_configs = ['MAIL_SERVER', 'MAIL_PORT', 'MAIL_USERNAME', 'MAIL_PASSWORD']
            logger.debug(f"[EMAIL_SERVICE] 🔍 Pre-send config validation:")
            for config in critical_configs:
                value = app.config.get(config)
                logger.debug(f"[EMAIL_SERVICE]   {config}: {value} (type: {type(value)})")
                if value is None:
                    logger.debug(f"[EMAIL_SERVICE] ❌ CRITICAL: {config} is None - this will cause Flask-Mail failure!")
            
            # Also check all Flask-Mail related configs
            all_mail_configs = {k: v for k, v in app.config.items() if k.startswith('MAIL_')}
            logger.debug(f"[EMAIL_SERVICE] 📋 All MAIL_ configurations:")
            for key, value in all_mail_configs.items():
                logger.debug(f"[EMAIL_SERVICE]   {key}: {value} (type: {type(value)})")
            
            # Try recreating the mail instance to ensure it uses the latest config
            from flask_mail import Mail
            fresh_mail = Mail()
            fresh_mail.init_app(app)
            logger.debug(f"[EMAIL_SERVICE] � Created fresh Mail instance")
            
            # Use the fresh mail instance
            fresh_mail.send(msg)
            logger.debug(f"[EMAIL_SERVICE] ✅ Flask-Mail sent successfully after {time.time() - start_time:.2f}s")
        finally:
            socket.setdefaulttimeout(original_timeout)  # Restore original timeout
        
        elapsed = time.time() - start_time
        logger.debug(f"[EMAIL_SERVICE] ✅ Enhanced handover email sent successfully to {len(recipients)} recipients in {elapsed:.2f}s")
        logging.debug(f"[EMAIL_SERVICE] ✅ Enhanced handover email sent successfully")
        
        # 📊 Mark email as sent in delivery log
        if email_log:
            try:
                email_log.mark_sent(duration=elapsed)
                logger.debug(f"[EMAIL_SERVICE] 📊 Email delivery log updated: SENT (ID={email_log.id})")
            except Exception as log_error:
                logger.debug(f"[EMAIL_SERVICE] ⚠️ Could not update email log: {log_error}")
        
        return  # Success - exit function
        
    except (Exception, TimeoutError) as e:
        error_message = str(e)
        elapsed = time.time() - start_time if 'start_time' in locals() else 0
        logger.debug(f"[EMAIL_SERVICE] ❌ Flask-Mail failed to send enhanced handover email after {elapsed:.2f}s: {e}")
        logging.error(f"[EMAIL_SERVICE] ❌ Flask-Mail failed to send enhanced handover email: {e}")
        
        # Provide helpful context for common network issues
        if "getaddrinfo failed" in error_message:
            logger.debug(f"[EMAIL_SERVICE] 💡 Network Issue: Cannot resolve SMTP server hostname")
            logger.debug(f"[EMAIL_SERVICE] 💡 This is common in local development when EPAM internal servers are not accessible")
            logger.debug(f"[EMAIL_SERVICE] 💡 Handover data has been saved successfully - only email delivery failed")
        elif "Authentication Required" in error_message:
            logger.debug(f"[EMAIL_SERVICE] 💡 Auth Issue: SMTP authentication failed - check credentials")
        elif "Connection refused" in error_message or "timed out" in error_message or "Connection unexpectedly closed" in error_message:
            logger.debug(f"[EMAIL_SERVICE] 💡 Connection Issue: Cannot reach SMTP server or service unavailable")
            logger.debug(f"[EMAIL_SERVICE] 💡 For local development, this is expected if EPAM SMTP service is down")
        
        # Try UNS Email Service as fallback
        logger.debug(f"[EMAIL_SERVICE] 🔄 Attempting UNS Email Service as fallback...")
        try:
            from services.flask_uns_email import FlaskUNSEmailIntegration
            from flask import current_app
            
            # Try to send via UNS Email Service using the correct method
            uns_integration = FlaskUNSEmailIntegration(current_app)
            
            # Initialize if not already done
            if not hasattr(uns_integration, '_email_sender') or uns_integration._email_sender is None:
                uns_integration.init_app(current_app)
            
            uns_result = uns_integration.send_handover_email(
                shift=shift,
                recipients=recipients
            )
            
            if uns_result.get('success'):
                logger.debug(f"[EMAIL_SERVICE] ✅ UNS Email fallback successful! Sent to {len(recipients)} recipients")
                logging.info(f"[EMAIL_SERVICE] ✅ UNS Email fallback successful")
                
                # 📊 Mark email as sent via UNS fallback
                if email_log:
                    try:
                        total_elapsed = time.time() - email_start_time
                        email_log.status = 'sent'
                        email_log.sent_at = datetime.now()
                        email_log.duration_seconds = total_elapsed
                        email_log.error_message = f"Flask-Mail failed, sent via UNS fallback. Original error: {error_message[:500]}"
                        db.session.commit()
                        logger.debug(f"[EMAIL_SERVICE] 📊 Email delivery log updated: SENT via UNS (ID={email_log.id})")
                    except Exception as log_error:
                        logger.debug(f"[EMAIL_SERVICE] ⚠️ Could not update email log: {log_error}")
                
                return  # Success with UNS Email - don't raise exception
            else:
                logger.debug(f"[EMAIL_SERVICE] ❌ UNS Email fallback also failed: {uns_result.get('error', 'Unknown error')}")
                
        except Exception as uns_e:
            logger.debug(f"[EMAIL_SERVICE] ❌ UNS Email fallback error: {uns_e}")
        
        # 📊 Mark email as failed in delivery log
        if email_log:
            try:
                total_elapsed = time.time() - email_start_time
                email_log.mark_failed(f"Flask-Mail and UNS fallback both failed. Error: {error_message}", duration=total_elapsed)
                logger.debug(f"[EMAIL_SERVICE] 📊 Email delivery log updated: FAILED (ID={email_log.id})")
            except Exception as log_error:
                logger.debug(f"[EMAIL_SERVICE] ⚠️ Could not update email log: {log_error}")
        
        logger.debug(f"[EMAIL_SERVICE] 💡 All email methods failed - handover data saved successfully anyway")
        raise


def send_incident_assignment_notification(incident_id, incident_description, assigned_engineer, incident_type, shift_date):
    """Send notification email when an incident is assigned to an engineer"""
    from flask import current_app
    mail = current_app.extensions.get('mail')
    from models.models import TeamMember, User
    
    # Check if email is configured before attempting to send
    smtp_server = current_app.config.get('MAIL_SERVER')
    if not smtp_server:
        logging.info("[EMAIL_SERVICE] Email not configured - skipping incident assignment notification")
        return
    
    # Find the assigned engineer's email
    try:
        # First try to find by name in TeamMember table
        team_member = TeamMember.query.filter_by(name=assigned_engineer).first()
        engineer_email = team_member.email if team_member else None
        
        # If not found in TeamMember, try User table
        if not engineer_email:
            user = User.query.filter_by(username=assigned_engineer).first()
            if not user:
                # Try by display name parts
                name_parts = assigned_engineer.split()
                if len(name_parts) >= 2:
                    user = User.query.filter(
                        User.first_name.ilike(name_parts[0]),
                        User.last_name.ilike(name_parts[-1])
                    ).first()
            engineer_email = user.email if user else None
        
        # Get team email for CC
        team_email = current_app.config.get('TEAM_EMAIL', '')
        
        if not engineer_email:
            logging.warning(f"Could not find email for engineer: {assigned_engineer}")
            # Send only to team email if engineer email not found
            recipients = [team_email] if team_email else []
        else:
            recipients = [engineer_email]
            if team_email and team_email != engineer_email:
                recipients.append(team_email)
        
        if not recipients:
            logging.warning("No email recipients found for incident assignment notification")
            return
        
        subject = f"Incident Assignment: {incident_id} - {incident_type}"
        
        html = f"""
        <html>
        <head></head>
        <body>
            <h2>Incident Assignment Notification</h2>
            <p>Dear {assigned_engineer},</p>
            
            <p>You have been assigned a new {incident_type.lower()} incident for shift on <strong>{shift_date}</strong>.</p>
            
            <table border="1" cellpadding="8" cellspacing="0" style="border-collapse:collapse; width:100%; margin: 20px 0;">
                <tr>
                    <th style="background-color: #f8f9fa; text-align: left;">Incident ID</th>
                    <td>{incident_id}</td>
                </tr>
                <tr>
                    <th style="background-color: #f8f9fa; text-align: left;">Type</th>
                    <td>{incident_type}</td>
                </tr>
                <tr>
                    <th style="background-color: #f8f9fa; text-align: left;">Assigned To</th>
                    <td>{assigned_engineer}</td>
                </tr>
                <tr>
                    <th style="background-color: #f8f9fa; text-align: left;">Description</th>
                    <td>{incident_description}</td>
                </tr>
                <tr>
                    <th style="background-color: #f8f9fa; text-align: left;">Shift Date</th>
                    <td>{shift_date}</td>
                </tr>
            </table>
            
            <p>Please take appropriate action and update the incident status in the shift handover system.</p>
            
            <p>Best regards,<br>
            Shift Handover System</p>
        </body>
        </html>
        """
        
        # Get the configured default sender
        sender = current_app.config.get('MAIL_DEFAULT_SENDER')
        if not sender:
            sender = current_app.config.get('MAIL_USERNAME')
        
        # If Flask config doesn't have sender, try to load from SMTPConfig directly
        if not sender:
            try:
                from models.smtp_config import SMTPConfig
                sender = SMTPConfig.get_config('mail_default_sender')
                logger.debug(f"[EMAIL_SERVICE] ✅ Loaded sender from SMTPConfig: {sender}")
            except Exception as e:
                logger.debug(f"[EMAIL_SERVICE] ❌ Failed to load sender from SMTPConfig: {e}")
                sender = 'noreply@shift-handover.local'  # Final fallback
                logger.debug(f"[EMAIL_SERVICE] ⚠️ Using fallback sender: {sender}")
        
        logger.debug(f"[EMAIL_SERVICE] 📧 Using sender for incident notification: {sender}")
        
        msg = Message(subject=subject, recipients=recipients, sender=sender)
        msg.body = "Please view this email in HTML format."
        msg.html = html
        
        logging.info(f"[INCIDENT_ASSIGNMENT] Sending notification to {recipients} for incident {incident_id}")
        try:
            mail.send(msg)
            logging.info(f"[INCIDENT_ASSIGNMENT] Email sent successfully to {recipients}")
        except Exception as e:
            logging.error(f"[INCIDENT_ASSIGNMENT] Failed to send email to {recipients}: {e}")
            raise
            
    except Exception as e:
        logging.error(f"[INCIDENT_ASSIGNMENT] Error in send_incident_assignment_notification: {e}")
        raise

def send_assignment_response_email(notification, responder, action, comments):
    """
    Send follow-up email when an assignment is accepted or rejected
    
    Args:
        notification: HandoverNotification object
        responder: User who responded
        action: 'accept' or 'reject'
        comments: User's comments
    """
    try:
        from flask_mail import Mail
        import os
        from models.models import db, User, Team, Account
        
        # Get SMTP configuration
        mail = None
        try:
            result = db.session.execute(db.text("SELECT config_key, config_value FROM smtp_config"))
            configs = dict(result.fetchall())
        except Exception:
            try:
                result = db.session.execute(db.text("SELECT config_key, config_value FROM app_config WHERE config_key LIKE 'smtp_%' OR config_key LIKE 'mail_%'"))
                configs = dict(result.fetchall())
            except Exception:
                configs = {}
        
        if not configs:
            return {'success': False, 'error': 'SMTP configuration not found'}
        
        # Configure Flask-Mail
        app = current_app._get_current_object()
        smtp_port = configs.get('smtp_port', '587')
        if smtp_port is None or smtp_port == '':
            smtp_port = '587'
        
        app.config.update({
            'MAIL_SERVER': configs.get('smtp_server', 'localhost'),
            'MAIL_PORT': int(smtp_port),
            'MAIL_USE_TLS': configs.get('smtp_use_tls', 'true').lower() == 'true',
            'MAIL_USE_SSL': configs.get('smtp_use_ssl', 'false').lower() == 'true',
            'MAIL_USERNAME': configs.get('smtp_username', ''),
            'MAIL_PASSWORD': configs.get('smtp_password', ''),
            'MAIL_DEFAULT_SENDER': configs.get('smtp_default_sender', 'noreply@company.com')
        })
        
        mail = Mail(app)
        
        # Get team email or configured recipients
        recipients = []
        
        # Get team email if available
        if notification.team_id:
            team = Team.query.get(notification.team_id)
            if team and hasattr(team, 'email') and team.email:
                recipients.append(team.email)
        
        # Get configured team email from configs
        team_email = configs.get('team_email')
        if team_email and team_email not in recipients:
            recipients.append(team_email)
        
        # Fallback to default recipient
        if not recipients:
            recipients = ['admin@company.com']  # Configure this appropriately
        
        # Create email subject and body
        action_text = 'Accepted' if action == 'accept' else 'Rejected'
        subject = f"Assignment Response: {notification.title} - {action_text}"
        
        # Create the email body
        body = f"""
Assignment Response Notification

Assignment Details:
- Title: {notification.title}
- Response: {action_text}
- Responded by: {responder.first_name} {responder.last_name} ({responder.username})
- Response Date: {notification.read_at or 'Just now'}

"""
        
        if comments:
            body += f"Comments:\n{comments}\n\n"
        
        body += f"""
Original Assignment:
- Type: {notification.notification_type}
- Created: {notification.created_at}
- Message: {notification.message}

This is an automated notification from the Shift Handover System.
"""
        
        # Create and send the email
        msg = Message(
            subject=subject,
            sender=app.config['MAIL_DEFAULT_SENDER'],
            recipients=recipients,
            body=body
        )
        
        mail.send(msg)
        
        return {
            'success': True, 
            'message': f'Follow-up email sent to {", ".join(recipients)}'
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': f'Failed to send follow-up email: {str(e)}'
        }


def send_ops_alert(subject: str, body: str) -> None:
    """Send an operations alert email to configured admin recipients.

    Used by the DLQ handler (tasks/dlq_handler.py) when a Celery task
    exhausts all retries.  Raises on failure so the caller can fall back.
    """
    from flask import current_app
    from flask_mail import Message
    from app import mail

    recipients = current_app.config.get(
        'OPS_ALERT_RECIPIENTS',
        current_app.config.get('MAIL_DEFAULT_SENDER', ''),
    )
    if isinstance(recipients, str):
        recipients = [r.strip() for r in recipients.split(',') if r.strip()]

    if not recipients:
        raise RuntimeError('OPS_ALERT_RECIPIENTS is not configured — cannot send ops alert')

    msg = Message(
        subject=subject,
        sender=current_app.config.get('MAIL_DEFAULT_SENDER', 'noreply@shifthandover'),
        recipients=recipients,
        body=body,
    )
    mail.send(msg)
