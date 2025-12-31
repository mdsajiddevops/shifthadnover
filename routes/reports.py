
from flask import Blueprint, render_template, request, send_file, session, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from sqlalchemy import func
from collections import OrderedDict
from models.models import Shift, Incident, ShiftKeyPoint, TeamMember, Account, Team, User, ShiftChangeInfo, ShiftKBUpdate, db
from models.audit_log import AuditLog
from services.export_service import export_incidents_csv, export_keypoints_pdf
from services.team_access_service import TeamAccessService
from services.multi_team_service import MultiTeamService
from services.audit_service import log_action
import logging

# Module logger
logger = logging.getLogger(__name__)

reports_bp = Blueprint('reports', __name__)


@reports_bp.route('/reports', methods=['GET'])
@login_required
def reports():
    """Main reports page - redirects to handover reports"""
    log_action('View Reports Tab', 'Accessed main reports page')
    # Redirect to handover reports as the main reports page
    from flask import redirect, url_for
    return redirect(url_for('reports.handover_reports'))


@reports_bp.route('/change-info-reports', methods=['GET'])
@login_required
def change_info_reports():
    """Change Info reports page"""
    log_action('View Change Info Reports', 'Accessed change info reports page')
    
    # Get filter parameters
    date_filter = request.args.get('date')
    account_id_filter = request.args.get('account_id')
    team_id_filter = request.args.get('team_id')
    app_filter = request.args.get('app_name')
    status_filter = request.args.get('status')
    
    # Initialize team context variables
    selected_team_id = None
    all_teams_selected = False
    team_filter_context = None
    accounts = []
    teams = []
    
    # Build query based on user permissions - select both tables
    query = db.session.query(ShiftChangeInfo, Shift.date.label('shift_date')).join(Shift)
    
    if current_user.role == 'super_admin':
        # Super admin can see all change info
        accounts = Account.query.filter_by(status='active').all()
        teams = Team.query.filter_by(status='active')
        if account_id_filter:
            teams = teams.filter_by(account_id=account_id_filter)
        teams = teams.all()
        
        # Handle team filtering for super admin
        if team_id_filter == '':
            all_teams_selected = True
        elif team_id_filter:
            try:
                selected_team_id = int(team_id_filter)
            except (TypeError, ValueError):
                selected_team_id = None
                
    elif current_user.role == 'account_admin':
        # Account admin can see their account's change info
        query = query.filter(ShiftChangeInfo.account_id == current_user.account_id)
        accounts = [Account.query.get(current_user.account_id)] if current_user.account_id else []
        teams = Team.query.filter_by(account_id=current_user.account_id, status='active').all()
        
        # Handle team filtering for account admin
        if team_id_filter == '':
            all_teams_selected = True
        elif team_id_filter:
            try:
                selected_team_id = int(team_id_filter)
            except (TypeError, ValueError):
                selected_team_id = None
                
    else:
        # Regular users: use team access service filtering
        team_filter_context = TeamAccessService.get_team_filter_context()
        teams = team_filter_context['user_teams']
        accounts = [Account.query.get(current_user.account_id)] if current_user.account_id else []
        
        # Handle team selection for regular users
        team_param = request.args.get('team_id')
        all_teams_selected = team_param == ''
        
        if team_param is None:
            # No filter provided -> default to previously selected/primary team
            selected_team_id = team_filter_context.get('selected_team_id')
        elif team_param == '':
            # Explicit "All Teams" selection
            selected_team_id = None
            all_teams_selected = True
        else:
            # Specific team selected
            try:
                selected_team_id = int(team_param)
            except (TypeError, ValueError):
                selected_team_id = team_filter_context.get('selected_team_id')
        
        # Apply team filtering for regular users
        if all_teams_selected:
            # Show all teams user has access to
            query = TeamAccessService.apply_team_filter(query, ShiftChangeInfo)
        elif selected_team_id:
            # Filter by specific team
            query = query.filter(ShiftChangeInfo.team_id == selected_team_id)
        else:
            # Fallback to team access service filtering
            query = TeamAccessService.apply_team_filter(query, ShiftChangeInfo)
    
    # Apply filters
    if date_filter:
        try:
            date_obj = datetime.strptime(date_filter, '%Y-%m-%d').date()
            query = query.filter(Shift.date == date_obj)
        except ValueError:
            pass
    
    if account_id_filter and current_user.role == 'super_admin':
        query = query.filter(ShiftChangeInfo.account_id == account_id_filter)
    
    if team_id_filter and current_user.role in ['super_admin', 'account_admin'] and not all_teams_selected:
        if selected_team_id:
            query = query.filter(ShiftChangeInfo.team_id == selected_team_id)
    
    if app_filter:
        query = query.filter(ShiftChangeInfo.app_name.ilike(f'%{app_filter}%'))
    
    if status_filter:
        query = query.filter(ShiftChangeInfo.status == status_filter)
    
    # Order by most recent first (MySQL doesn't support NULLS LAST)
    raw_change_infos = query.order_by(Shift.date.desc(), ShiftChangeInfo.change_datetime.desc()).all()
    
    # Deduplicate by change_number OR app_name+description - keep most recent version of each unique change
    change_map = {}
    for change_info, shift_date in raw_change_infos:
        # Use change_number if available, otherwise use app_name + description hash
        if change_info.change_number and change_info.change_number.strip():
            change_key = change_info.change_number.strip().lower()
        else:
            # Use a combination of app_name and description for deduplication if change_number is missing
            change_key = f"{change_info.app_name or ''}_{(change_info.description or '')[:50]}".strip().lower()
        
        if change_key and (change_key not in change_map or change_info.id > change_map[change_key][0].id):
            change_map[change_key] = (change_info, shift_date)
    
    change_infos = list(change_map.values())
    
    return render_template('change_info_reports.html',
                         change_infos=change_infos,
                         accounts=accounts,
                         teams=teams,
                         date_filter=date_filter,
                         account_id_filter=account_id_filter,
                         team_id_filter=team_id_filter,
                         selected_team_id=selected_team_id,
                         all_teams_selected=all_teams_selected,
                         app_filter=app_filter,
                         status_filter=status_filter)


@reports_bp.route('/kb-update-reports', methods=['GET'])
@login_required
def kb_update_reports():
    """KB Update reports page"""
    log_action('View KB Update Reports', 'Accessed KB update reports page')
    
    # Get filter parameters
    date_filter = request.args.get('date')
    account_id_filter = request.args.get('account_id')
    team_id_filter = request.args.get('team_id')
    app_filter = request.args.get('app_name')
    status_filter = request.args.get('status')
    
    # Initialize team context variables
    selected_team_id = None
    all_teams_selected = False
    team_filter_context = None
    accounts = []
    teams = []
    
    # Build query based on user permissions - select both tables
    query = db.session.query(ShiftKBUpdate, Shift.date.label('shift_date')).join(Shift)
    
    if current_user.role == 'super_admin':
        # Super admin can see all KB updates
        accounts = Account.query.filter_by(status='active').all()
        teams = Team.query.filter_by(status='active')
        if account_id_filter:
            teams = teams.filter_by(account_id=account_id_filter)
        teams = teams.all()
        
        # Handle team filtering for super admin
        if team_id_filter == '':
            all_teams_selected = True
        elif team_id_filter:
            try:
                selected_team_id = int(team_id_filter)
            except (TypeError, ValueError):
                selected_team_id = None
                
    elif current_user.role == 'account_admin':
        # Account admin can see their account's KB updates
        query = query.filter(ShiftKBUpdate.account_id == current_user.account_id)
        accounts = [Account.query.get(current_user.account_id)] if current_user.account_id else []
        teams = Team.query.filter_by(account_id=current_user.account_id, status='active').all()
        
        # Handle team filtering for account admin
        if team_id_filter == '':
            all_teams_selected = True
        elif team_id_filter:
            try:
                selected_team_id = int(team_id_filter)
            except (TypeError, ValueError):
                selected_team_id = None
                
    else:
        # Regular users: use team access service filtering
        team_filter_context = TeamAccessService.get_team_filter_context()
        teams = team_filter_context['user_teams']
        accounts = [Account.query.get(current_user.account_id)] if current_user.account_id else []
        
        # Handle team selection for regular users
        team_param = request.args.get('team_id')
        all_teams_selected = team_param == ''
        
        if team_param is None:
            # No filter provided -> default to previously selected/primary team
            selected_team_id = team_filter_context.get('selected_team_id')
        elif team_param == '':
            # Explicit "All Teams" selection
            selected_team_id = None
            all_teams_selected = True
        else:
            # Specific team selected
            try:
                selected_team_id = int(team_param)
            except (TypeError, ValueError):
                selected_team_id = team_filter_context.get('selected_team_id')
        
        # Apply team filtering for regular users
        if all_teams_selected:
            # Show all teams user has access to
            query = TeamAccessService.apply_team_filter(query, ShiftKBUpdate)
        elif selected_team_id:
            # Filter by specific team
            query = query.filter(ShiftKBUpdate.team_id == selected_team_id)
        else:
            # Fallback to team access service filtering
            query = TeamAccessService.apply_team_filter(query, ShiftKBUpdate)
    
    # Apply filters
    if date_filter:
        try:
            date_obj = datetime.strptime(date_filter, '%Y-%m-%d').date()
            query = query.filter(Shift.date == date_obj)
        except ValueError:
            pass
    
    if account_id_filter and current_user.role == 'super_admin':
        query = query.filter(ShiftKBUpdate.account_id == account_id_filter)
    
    if team_id_filter and current_user.role in ['super_admin', 'account_admin'] and not all_teams_selected:
        if selected_team_id:
            query = query.filter(ShiftKBUpdate.team_id == selected_team_id)
    
    if app_filter:
        query = query.filter(ShiftKBUpdate.app_name.ilike(f'%{app_filter}%'))
    
    if status_filter:
        query = query.filter(ShiftKBUpdate.status == status_filter)
    
    # Order by most recent first
    raw_kb_updates = query.order_by(Shift.date.desc(), ShiftKBUpdate.id.desc()).all()
    
    # 🔧 FIX: Improved deduplication - keep most recent version of each unique KB
    # Handle KBs with and without kb_number
    kb_map = {}
    for kb_update, shift_date in raw_kb_updates:
        # Use kb_number if available, otherwise use app_name + description hash (like carryforward)
        if kb_update.kb_number and kb_update.kb_number.strip():
            kb_key = kb_update.kb_number.strip().lower()
        else:
            kb_key = f"{kb_update.app_name or ''}_{(kb_update.description or '')[:50]}".strip().lower()
        
        # Keep the most recent version (highest ID) of each unique KB
        if kb_key and (kb_key not in kb_map or kb_update.id > kb_map[kb_key][0].id):
            kb_map[kb_key] = (kb_update, shift_date)
    
    kb_updates = list(kb_map.values())
    
    # Get unique statuses for filter dropdown
    status_options = ['New', 'Draft', 'In Review', 'Published']
    
    return render_template('kb_update_reports.html',
                         kb_updates=kb_updates,
                         accounts=accounts,
                         teams=teams,
                         date_filter=date_filter,
                         account_id_filter=account_id_filter,
                         team_id_filter=team_id_filter,
                         selected_team_id=selected_team_id,
                         all_teams_selected=all_teams_selected,
                         app_filter=app_filter,
                         status_filter=status_filter,
                         status_options=status_options)


# Bulk export filtered handover reports as CSV or PDF
@reports_bp.route('/handover-reports/export/bulk', methods=['GET'])
@login_required
def export_handover_bulk():
    log_action('Export Reports', f'Format: {request.args.get("format")}, Filters: account_id={request.args.get("account_id")}, team_id={request.args.get("team_id")}, date={request.args.get("date")}, shift_type={request.args.get("shift_type")}')
    date_filter = request.args.get('date')
    shift_type_filter = request.args.get('shift_type')
    account_id = request.args.get('account_id')
    team_id = request.args.get('team_id')
    format_type = request.args.get('format', 'csv')
    query = Shift.query
    if account_id:
        query = query.filter_by(account_id=account_id)
    if team_id:
        query = query.filter_by(team_id=team_id)
    if date_filter:
        try:
            date_obj = datetime.strptime(date_filter, '%Y-%m-%d').date()
            query = query.filter_by(date=date_obj)  # 🔧 FIXED: Use date column
        except Exception:
            pass
    if shift_type_filter:
        query = query.filter_by(current_shift_type=shift_type_filter)
    # Order by shift date only for now (newest first)
    # TODO: Re-add submitted_at ordering when MySQL compatibility issue is resolved
    shifts = query.order_by(
        Shift.date.desc()
    ).all()
    rows = []
    for shift in shifts:
        incidents = Incident.query.filter_by(shift_id=shift.id).all()
        key_points = ShiftKeyPoint.query.filter_by(shift_id=shift.id).all()
        
        # Get detailed incident information
        incident_details = []
        for i in incidents:
            details = f"[{i.type}] {i.title}"
            if i.status:
                details += f" (Status: {i.status})"
            if i.priority:
                details += f" (Priority: {i.priority})"
            if i.handover:
                details += f" - {i.handover}"
            incident_details.append(details)
        
        incident_titles = '; '.join(incident_details)
        
        keypoint_details = '; '.join([
            f"{kp.description} ({kp.status}) [Responsible: {TeamMember.query.get(kp.responsible_engineer_id).name if kp.responsible_engineer_id else 'N/A'}]" + 
            (f" [JIRA: {kp.jira_id}]" if kp.jira_id else "")
            for kp in key_points
        ])
        
        # Find who submitted this handover from audit log
        submitted_by = 'Unknown'
        audit_entry = AuditLog.query.filter(
            AuditLog.action.like('%Create Handover%'),
            AuditLog.details.like(f'%Shift: {shift.current_shift_type}%'),
            AuditLog.details.like(f'%Date: {shift.date}%')
        ).first()
        
        if audit_entry:
            # Try to get the actual user for better display name
            if audit_entry.user_id:
                user = User.query.get(audit_entry.user_id)
                if user:
                    submitted_by = user.display_name
                else:
                    submitted_by = audit_entry.username or 'Unknown User'
            else:
                submitted_by = audit_entry.username or 'Unknown User'
        
        rows.append({
            'Date': shift.date,
            'Current Shift': shift.current_shift_type,
            'Status': shift.status,
            'Submitted By': submitted_by,
            'Incidents': incident_titles,
            'Key Points': keypoint_details
        })
    if format_type == 'csv':
        import pandas as pd, io
        df = pd.DataFrame(rows)
        csv_io = io.StringIO()
        df.to_csv(csv_io, index=False)
        csv_io.seek(0)
        return send_file(io.BytesIO(csv_io.getvalue().encode()), mimetype='text/csv', as_attachment=True, download_name='handover_reports.csv')
    elif format_type == 'pdf':
        import io
        from reportlab.pdfgen import canvas
        pdf_io = io.BytesIO()
        c = canvas.Canvas(pdf_io)
        c.drawString(100, 800, "Shift Handover Reports")
        y = 780
        for row in rows:
            c.drawString(100, y, f"Date: {row['Date']} | Shift: {row['Current Shift']} | Status: {row['Status']} | Submitted By: {row['Submitted By']}")
            y -= 20
            c.drawString(120, y, f"Incidents: {row['Incidents']}")
            y -= 20
            c.drawString(120, y, f"Key Points: {row['Key Points']}")
            y -= 30
            if y < 100:
                c.showPage()
                y = 800
        c.save()
        pdf_io.seek(0)
        return send_file(pdf_io, mimetype='application/pdf', as_attachment=True, download_name='handover_reports.pdf')
    else:
        return "Invalid format", 400


# Export incidents as CSV for a single shift
@reports_bp.route('/handover-reports/export/csv/<int:shift_id>', methods=['GET'])
@login_required
def export_handover_csv(shift_id):
    log_action('Export Single Shift CSV', f'Shift ID: {shift_id}')
    shift = Shift.query.get_or_404(shift_id)
    return export_incidents_csv(shift.date, shift_id)

# Export key points as PDF for a single shift
@reports_bp.route('/handover-reports/export/pdf/<int:shift_id>', methods=['GET'])
@login_required
def export_handover_pdf(shift_id):
    log_action('Export Single Shift PDF', f'Shift ID: {shift_id}')
    shift = Shift.query.get_or_404(shift_id)
    return export_keypoints_pdf(shift.date, shift_id)


@reports_bp.route('/handover-reports/detailed/<int:shift_id>', methods=['GET'])
@login_required
def detailed_shift_report(shift_id):
    """Detailed view of a single shift report with enhanced UI sections"""
    log_action('View Detailed Shift Report', f'Shift ID: {shift_id}')
    
    try:
        # Get the shift
        shift = Shift.query.get_or_404(shift_id)
        
        # Check permissions
        if current_user.role == 'user':
            # Regular users can only see shifts from their teams
            user_team_ids = [team.id for team in current_user.get_teams()]
            if shift.team_id not in user_team_ids and shift.team_id != current_user.team_id:
                from flask import abort
                abort(403)
        elif current_user.role == 'account_admin':
            # Account admins can only see their account's shifts
            if shift.team.account_id != current_user.account_id:
                from flask import abort
                abort(403)
        # Super admins can see all shifts
        
        # Get all related data
        incidents = Incident.query.filter_by(shift_id=shift_id).all()
        
        # 🔍 ENHANCED KEY POINTS DEBUG: Check multiple possibilities
        key_points = ShiftKeyPoint.query.filter_by(shift_id=shift_id).all()
        
        # For draft shifts, also check active key points from reports logic
        if shift.status == 'draft':
            logger.debug(f"🔍 DRAFT SHIFT DETECTED - checking active key points as well")
            # Get active key points like in main reports
            all_active_kps = ShiftKeyPoint.query.filter(
                ShiftKeyPoint.account_id == shift.account_id,
                ShiftKeyPoint.team_id == shift.team_id,
                ShiftKeyPoint.status.in_(['Open', 'In Progress'])
            ).all()
            logger.debug(f"🔍 Found {len(all_active_kps)} active key points for account/team")
            
            # Apply COMPLETE dashboard-style filtering and deduplication
            all_key_points = key_points + all_active_kps
            
            # First: Apply submission filtering like dashboard
            filtered_kps = []
            for kp in all_key_points:
                shift = Shift.query.get(kp.shift_id)
                if shift and shift.status == 'sent':
                    # Check if there's a newer version that closed this key point (CASE-INSENSITIVE)
                    newer_closed = ShiftKeyPoint.query.filter(
                        func.lower(ShiftKeyPoint.description) == kp.description.lower(),
                        ShiftKeyPoint.jira_id == kp.jira_id,
                        ShiftKeyPoint.status == 'Closed',
                        ShiftKeyPoint.id > kp.id
                    ).first()
                    if newer_closed:
                        logger.debug(f"🔍 DETAILED: Excluding key point ID {kp.id} - found newer closed version ID {newer_closed.id}")
                        continue
                filtered_kps.append(kp)
            
            # Second: Apply exact dashboard deduplication
            kp_map = {}
            for kp in filtered_kps:
                if kp.status == 'Closed':
                    continue
                normalized_jira = kp.jira_id if kp.jira_id and kp.jira_id.lower() not in ['none', 'null', ''] else None
                key = (kp.description, normalized_jira)
                if key not in kp_map or kp.id > kp_map[key].id:
                    kp_map[key] = kp
            
            key_points = list(kp_map.values())
            logger.debug(f"🔍 After dashboard-style filtering and deduplication: {len(key_points)} unique key points")
        
        # 🔧 FIX: Filter out Completed/Cancelled/Implemented changes and Published KBs
        change_infos = ShiftChangeInfo.query.filter(
            ShiftChangeInfo.shift_id == shift_id,
            ~ShiftChangeInfo.status.in_(['Completed', 'Cancelled', 'Implemented'])
        ).all()
        kb_updates = ShiftKBUpdate.query.filter(
            ShiftKBUpdate.shift_id == shift_id,
            ShiftKBUpdate.status != 'Published'
        ).all()
        
        # 🔍 DEBUG: Check what data we're getting for the detailed report
        logger.debug(f"🔍 DETAILED REPORT DEBUG for shift {shift_id}:")
        logger.debug(f"  - Shift status: {shift.status}")
        logger.debug(f"  - Incidents found: {len(incidents)}")
        logger.debug(f"  - Key Points found (after processing): {len(key_points)}")
        logger.debug(f"  - Change Infos found (excluding Completed/Cancelled): {len(change_infos)}")
        logger.debug(f"  - KB Updates found (excluding Published): {len(kb_updates)}")
        
        # Debug first few key points
        for i, kp in enumerate(key_points[:3]):
            logger.debug(f"    KP {i+1}: '{kp.description[:50]}...' (Status: {kp.status}, Shift: {kp.shift_id})")
        
        for i, change in enumerate(change_infos):
            logger.debug(f"    Change {i+1}: {change.app_name} - {change.status}")
        
        for i, kb in enumerate(kb_updates):
            logger.debug(f"    KB Update {i+1}: {kb.app_name} - {kb.status}")
        
        # Get team member info - use same logic as main reports route
        from models.models import User
        from models.handover_enhanced import HandoverRequest
        
        submitted_by = 'Unknown'
        try:
            # First try to find from HandoverRequest table using shift attributes
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
                    logger.debug(f"🔍 DETAILED: Found accurate submitter: {submitted_by} (ID: {user.id}) for shift {shift.id}")
                else:
                    submitted_by = f'User ID: {handover_req.created_by_id}'
                    logger.debug(f"🔍 DETAILED: User not found, using ID: {submitted_by} for shift {shift.id}")
            else:
                # Fallback to audit logs
                logger.debug(f"🔍 DETAILED: No handover request found, checking audit logs for shift {shift.id}")
                audit_entry = AuditLog.query.filter(
                    AuditLog.action.contains('Handover Submitted'),
                    AuditLog.details.contains(f'Shift ID: {shift.id}')
                ).order_by(AuditLog.timestamp.desc()).first()
                
                if audit_entry:
                    if audit_entry.user_id:
                        user = User.query.get(audit_entry.user_id)
                        if user:
                            submitted_by = user.display_name or user.username
                            logger.debug(f"🔍 DETAILED: Fallback audit submitter: {submitted_by} for shift {shift.id}")
                        else:
                            submitted_by = audit_entry.username or 'Unknown User'
                            logger.debug(f"🔍 DETAILED: Using audit username: {submitted_by} for shift {shift.id}")
                else:
                    logger.debug(f"🔍 DETAILED: No audit entry found for shift {shift.id}")
                    submitted_by = 'Unknown'
        except Exception as e:
            logger.debug(f"🔍 DETAILED: Error finding submitter for shift {shift.id}: {e}")
            submitted_by = 'Unknown'
        
        # Organize incidents by type
        incidents_by_type = {
            'open': [],
            'closed': [],
            'priority': [],
            'handover': [],
            'escalated': []
        }
        
        for inc in incidents:
            incident_type = inc.type.lower() if inc.type else 'other'
            if incident_type in incidents_by_type:
                incidents_by_type[incident_type].append(inc)
            else:
                incidents_by_type.setdefault('other', []).append(inc)
        
        # Organize key points by status
        key_points_by_status = {
            'open': [],
            'in_progress': [],
            'closed': []
        }
        
        for kp in key_points:
            status = kp.status.lower().replace(' ', '_') if kp.status else 'open'
            if status in key_points_by_status:
                key_points_by_status[status].append(kp)
            else:
                key_points_by_status['open'].append(kp)
        
        return render_template(
            'detailed_shift_report.html',
            shift=shift,
            submitted_by=submitted_by,
            incidents=incidents,
            incidents_by_type=incidents_by_type,
            key_points=key_points,
            key_points_by_status=key_points_by_status,
            change_infos=change_infos,
            kb_updates=kb_updates
        )
        
    except Exception as e:
        logger.error(f"❌ Error in detailed_shift_report: {e}")
        from flask import abort
        abort(500)


@reports_bp.route('/handover-reports', methods=['GET'])
@login_required
def handover_reports():
    logger.debug(f"🚨 HANDOVER REPORTS ROUTE CALLED 🚨")
    
    # Check database integrity first
    total_shifts = Shift.query.count()
    total_incidents = Incident.query.count()
    total_key_points = ShiftKeyPoint.query.count()
    logger.debug(f"🔍 Database totals: {total_shifts} shifts, {total_incidents} incidents, {total_key_points} key points")
    
    # Show some sample records
    if total_incidents > 0:
        sample_incidents = Incident.query.limit(3).all()
        for inc in sample_incidents:
            logger.debug(f"🔍 Sample Incident: ID={inc.id}, shift_id={inc.shift_id}, title='{inc.title}'")
    
    if total_key_points > 0:
        sample_kps = ShiftKeyPoint.query.limit(3).all()
        for kp in sample_kps:
            logger.debug(f"🔍 Sample KeyPoint: ID={kp.id}, shift_id={kp.shift_id}, desc='{kp.description[:50]}'")
    
    try:
        # Default filters
        log_action('View Reports Tab', f'Filters: account_id={request.args.get("account_id")}, team_id={request.args.get("team_id")}, date={request.args.get("date")}, shift_type={request.args.get("shift_type")}')
        date_filter = request.args.get('date')
        shift_type_filter = request.args.get('shift_type')
        account_id = None
        team_id = None
        selected_team_id = None
        all_teams_selected = False
        team_filter_context = None
        accounts = []
        teams = []
        query = Shift.query
        if current_user.role == 'super_admin':
            accounts = Account.query.filter_by(is_active=True).all()
            # 🔧 FIX: For super_admin, only use filters if explicitly provided in request params
            # Don't use session values as defaults - this was causing empty results
            account_id = request.args.get('account_id')  # Don't use session defaults for super_admin
            logger.debug(f"🔍 SUPER_ADMIN: account_id from params only: {account_id}")
            
            # 🔧 FIX: Clear session defaults for super_admin to prevent stale selections
            if not account_id and 'selected_account_id' in session:
                session.pop('selected_account_id', None)
                logger.debug(f"🔍 SUPER_ADMIN: Cleared stale selected_account_id from session")
            teams = Team.query.filter_by(is_active=True)
            if account_id:
                teams = teams.filter_by(account_id=account_id)
                logger.debug(f"🔍 SUPER_ADMIN: Filtering teams by account_id: {account_id}")
            else:
                logger.debug(f"🔍 SUPER_ADMIN: No account_id in params - showing ALL accounts data")
            teams = teams.all()
            team_id = request.args.get('team_id')  # Don't use session defaults for super_admin
            if team_id == '':
                all_teams_selected = True
            elif team_id not in (None, 'None'):
                try:
                    selected_team_id = int(team_id)
                except (TypeError, ValueError):
                    selected_team_id = None
            logger.debug(f"🔍 SUPER_ADMIN: team_id from params only: {team_id}")
            
            # 🔧 FIX: Clear session defaults for super_admin to prevent stale selections  
            if not team_id and 'selected_team_id' in session:
                session.pop('selected_team_id', None)
                logger.debug(f"🔍 SUPER_ADMIN: Cleared stale selected_team_id from session")
        elif current_user.role == 'account_admin':
            account_id = current_user.account_id
            accounts = [Account.query.get(account_id)] if account_id else []
            teams = Team.query.filter_by(account_id=account_id, is_active=True).all()
            team_id = request.args.get('team_id') or session.get('selected_team_id')
            if team_id == '':
                all_teams_selected = True
            elif team_id:
                try:
                    selected_team_id = int(team_id)
                except (TypeError, ValueError):
                    selected_team_id = None
        else:
            # Regular users: use multi-team service with proper team access
            account_id = current_user.account_id
            accounts = [Account.query.get(account_id)] if account_id else []

            # Get team filter context using TeamAccessService
            team_filter_context = TeamAccessService.get_team_filter_context()
            teams = team_filter_context['user_teams']

            team_param = request.args.get('team_id')
            all_teams_selected = team_param == ''

            if team_param is None:
                # No filter provided -> default to previously selected/primary team
                selected_team_id = team_filter_context['selected_team_id']
            elif all_teams_selected:
                selected_team_id = None
            else:
                try:
                    selected_team_id = int(team_param)
                    TeamAccessService.set_selected_team(selected_team_id)
                except (TypeError, ValueError):
                    selected_team_id = team_filter_context['selected_team_id']

            team_id = selected_team_id  # maintain existing variable usage

            logger.debug(
                f"🔍 REGULAR_USER: team_param={team_param}, selected_team_id={selected_team_id}, "
                f"all_teams_selected={all_teams_selected}, user teams={len(teams)}"
            )
        # 🔧 FIX: Apply filtering logic based on user role and selections
        if current_user.role == 'super_admin':
            # For super_admin: only filter if explicitly selected
            if account_id:
                query = query.filter_by(account_id=account_id)
                logger.debug(f"🔍 SUPER_ADMIN: Filtering by account_id: {account_id}")
            else:
                logger.debug(f"🔍 SUPER_ADMIN: No account filter - showing ALL accounts")
            if team_id:
                query = query.filter_by(team_id=team_id)
                logger.debug(f"🔍 SUPER_ADMIN: Filtering by team_id: {team_id}")
            else:
                logger.debug(f"🔍 SUPER_ADMIN: No team filter - showing ALL teams")
        elif current_user.role == 'account_admin':
            # Account admin: filter by account and optional team
            if account_id:
                query = query.filter_by(account_id=account_id)
                logger.debug(f"🔍 ACCOUNT_ADMIN: Filtering by account_id: {account_id}")
            if team_id and not all_teams_selected:
                query = query.filter_by(team_id=team_id)
                logger.debug(f"🔍 ACCOUNT_ADMIN: Filtering by team_id: {team_id}")
        else:
            # Regular users: use multi-team filtering with proper account constraint
            if account_id:
                query = query.filter_by(account_id=account_id)
                logger.debug(f"🔍 REGULAR_USER: Filtering by account_id: {account_id}")
            
            # Apply team filtering using TeamAccessService
            effective_team_ids = TeamAccessService.get_effective_team_ids()
            if all_teams_selected:
                if effective_team_ids:
                    query = query.filter(Shift.team_id.in_(effective_team_ids))
                    logger.debug(f"🔍 REGULAR_USER: All Teams selected - filtering by team_ids: {effective_team_ids}")
                else:
                    query = query.filter(Shift.team_id == -1)
                    logger.debug(f"🔍 REGULAR_USER: No accessible teams")
            elif selected_team_id:
                if selected_team_id in effective_team_ids:
                    query = query.filter_by(team_id=selected_team_id)
                    logger.debug(f"🔍 REGULAR_USER: Filtering by selected team_id: {selected_team_id}")
                else:
                    query = query.filter(Shift.team_id == -1)
                    logger.debug(f"🔍 REGULAR_USER: Selected team {selected_team_id} invalid")
            else:
                # Default fallback: show primary team if available
                primary_team_id = (
                    team_filter_context['selected_team_id']
                    if team_filter_context and teams else None
                )
                if primary_team_id:
                    query = query.filter_by(team_id=primary_team_id)
                    selected_team_id = primary_team_id
                    logger.debug(f"🔍 REGULAR_USER: Fallback to primary team_id: {primary_team_id}")
                else:
                    query = query.filter(Shift.team_id == -1)
                    logger.debug(f"🔍 REGULAR_USER: No primary team available")
        if date_filter:
            try:
                date_obj = datetime.strptime(date_filter, '%Y-%m-%d').date()
                query = query.filter_by(date=date_obj)  # 🔧 FIXED: Use date column
                logger.debug(f"🔍 Filtering by date: {date_obj}")
            except Exception:
                logger.debug(f"🔍 Invalid date filter: {date_filter}")
                pass
        if shift_type_filter:
            query = query.filter_by(current_shift_type=shift_type_filter)
            logger.debug(f"🔍 Filtering by shift_type: {shift_type_filter}")
        
        logger.debug(f"🔍 Final query filters applied: account_id={account_id}, team_id={team_id}, date={date_filter}, shift_type={shift_type_filter}")
        
        # Show both sent and draft handovers in reports
        query = query.filter(Shift.status.in_(['sent', 'draft']))
        logger.debug(f"🔍 Added status filter: status in ['sent', 'draft']")
        
        # Order by shift date only for now (newest first)  
        # TODO: Re-add submitted_at ordering when MySQL compatibility issue is resolved
        shifts = query.order_by(
            Shift.date.desc()
        ).all()
        
        logger.debug(f"🔍 Found {len(shifts)} shifts total")
        for shift in shifts[:3]:  # Show first 3 shifts
            logger.debug(f"🔍 Shift ID: {shift.id}, Date: {shift.date}, Type: {shift.current_shift_type}, Submitted: {shift.submitted_at}")
        
        shift_data = []
        for shift in shifts:
            incidents = Incident.query.filter_by(shift_id=shift.id).all()
            # ✨ REPORTS FIX: Show comprehensive key points for handovers
            # For DRAFT handovers: Show all relevant key points (direct + active from team)
            # For SENT handovers: Show what was active at time of submission
            
            # First get key points directly associated with this shift
            direct_key_points = ShiftKeyPoint.query.filter_by(shift_id=shift.id).all()
            
            if shift.status == 'draft':
                # DRAFT: Show all relevant active key points from the same team
                logger.debug(f"🔍 REPORTS DRAFT: Shift {shift.id} is draft, showing all active key points")
                active_key_points = ShiftKeyPoint.query.filter(
                    ShiftKeyPoint.account_id == shift.account_id,
                    ShiftKeyPoint.team_id == shift.team_id,
                    ShiftKeyPoint.status.in_(['Open', 'In Progress']),
                    ShiftKeyPoint.shift_id != shift.id  # Exclude current shift's key points to avoid duplicates
                ).all()
                
                # Combine direct key points with active ones from other shifts
                all_key_points = direct_key_points + active_key_points
                
                # Apply SAME submission filtering as dashboard first
                filtered_kps = []
                for kp in all_key_points:
                    kp_shift = Shift.query.get(kp.shift_id)
                    if kp_shift and kp_shift.status == 'sent':
                        # Check if there's a newer version that closed this key point
                        newer_closed = ShiftKeyPoint.query.filter(
                            ShiftKeyPoint.description == kp.description,
                            ShiftKeyPoint.jira_id == kp.jira_id,
                            ShiftKeyPoint.status == 'Closed',
                            ShiftKeyPoint.id > kp.id
                        ).first()
                        if newer_closed:
                            continue
                    filtered_kps.append(kp)
                
                # Apply SAME deduplication logic as dashboard
                kp_map = {}
                for kp in filtered_kps:
                    if kp.status == 'Closed':
                        continue
                    normalized_jira = kp.jira_id if kp.jira_id and kp.jira_id.lower() not in ['none', 'null', ''] else None
                    key = (kp.description, normalized_jira)
                    if key not in kp_map or kp.id > kp_map[key].id:
                        kp_map[key] = kp
                
                key_points = list(kp_map.values())
                logger.debug(f"🔍 REPORTS DRAFT: Combined {len(direct_key_points)} direct + {len(active_key_points)} active = {len(key_points)} total key points")
                
            else:
                # SENT: Show direct key points, fallback to active ones if none exist
                key_points = direct_key_points
                if len(key_points) == 0:
                    # Fallback for sent handovers with no direct key points - apply same deduplication
                    active_key_points = ShiftKeyPoint.query.filter(
                        ShiftKeyPoint.account_id == shift.account_id,
                        ShiftKeyPoint.team_id == shift.team_id,
                        ShiftKeyPoint.status.in_(['Open', 'In Progress'])
                    ).order_by(ShiftKeyPoint.id.desc()).limit(10).all()
                    
                    # Apply SAME submission filtering as dashboard first
                    filtered_kps = []
                    for kp in active_key_points:
                        kp_shift = Shift.query.get(kp.shift_id)
                        if kp_shift and kp_shift.status == 'sent':
                            # Check if there's a newer version that closed this key point
                            newer_closed = ShiftKeyPoint.query.filter(
                                ShiftKeyPoint.description == kp.description,
                                ShiftKeyPoint.jira_id == kp.jira_id,
                                ShiftKeyPoint.status == 'Closed',
                                ShiftKeyPoint.id > kp.id
                            ).first()
                            if newer_closed:
                                continue
                        filtered_kps.append(kp)
                    
                    # Apply SAME deduplication logic as dashboard
                    kp_map = {}
                    for kp in filtered_kps:
                        if kp.status == 'Closed':
                            continue
                        normalized_jira = kp.jira_id if kp.jira_id and kp.jira_id.lower() not in ['none', 'null', ''] else None
                        key = (kp.description, normalized_jira)
                        if key not in kp_map or kp.id > kp_map[key].id:
                            kp_map[key] = kp
                    
                    key_points = list(kp_map.values())
                    logger.debug(f"🔍 REPORTS SENT: Using {len(active_key_points)} active key points (deduplicated to {len(key_points)}) as fallback")
            
            logger.debug(f"🔍 REPORTS SHIFT {shift.id}: Found {len(incidents)} incidents, {len(key_points)} key points")
            
            # Debug key points details with status breakdown
            status_counts = {'Open': 0, 'In Progress': 0, 'Closed': 0}
            for kp in key_points:
                status_counts[kp.status] = status_counts.get(kp.status, 0) + 1
                logger.debug(f"  📋 REPORTS KP {kp.id}: '{kp.description[:30]}...' - Status: {kp.status} - Responsible: {kp.responsible_engineer_id}")
            
            logger.debug(f"  📊 REPORTS Status breakdown for shift {shift.id}: {status_counts}")
            
            if len(key_points) == 0:
                logger.debug(f"  ⚠️  REPORTS WARNING: No key points found for shift {shift.id}")
            
            # Get detailed incident information
            incidents_data = []
            for inc in incidents:
                incident_details = {
                    'type': inc.type,
                    'title': inc.title,
                    'status': inc.status,
                    'priority': inc.priority,
                    'handover': inc.handover,
                    'assigned_to': inc.assigned_to,
                    'description': inc.description,
                    'escalated_to': inc.escalated_to
                }
                # Debug logging for incident assignment tracking
                if inc.assigned_to:
                    logger.debug(f"🔍 Incident {inc.id} has assignment: '{inc.assigned_to}'")
                incidents_data.append(incident_details)
            
            # Get detailed key points information - INCLUDING ALL STATUSES for reports
            key_points_data = []
            for kp in key_points:
                try:
                    engineer = None
                    if kp.responsible_engineer_id:
                        engineer = TeamMember.query.get(kp.responsible_engineer_id)
                    
                    kp_data = {
                        'description': kp.description,
                        'status': kp.status,
                        'responsible': engineer.name if engineer else 'N/A',
                        'jira_id': kp.jira_id,
                        'id': kp.id  # Add ID for debugging
                    }
                    key_points_data.append(kp_data)
                    logger.debug(f"  ✅ REPORTS Added KP {kp.id} to template data: Status={kp.status}")
                    
                except Exception as e:
                    logger.warning(f"🚨 Error processing key point {kp.id}: {e}")
                    # Add basic key point without responsible engineer
                    kp_data = {
                        'description': kp.description,
                        'status': kp.status,
                        'responsible': 'Error',
                        'jira_id': kp.jira_id,
                        'id': kp.id
                    }
                    key_points_data.append(kp_data)
                    logger.debug(f"  ⚠️  REPORTS Added KP {kp.id} with error to template data")
            
            # 🔧 FIX: Find who submitted this handover from HandoverRequest table (more accurate)
            submitted_by = 'Unknown'
            try:
                # Import here to avoid circular imports
                from models.handover_enhanced import HandoverRequest
                
                # Find the corresponding handover request with exact matching
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
                        logger.debug(f"🔍 REPORTS: Found accurate submitter: {submitted_by} (ID: {user.id}) for shift {shift.id}")
                    else:
                        submitted_by = f'User ID: {handover_req.created_by_id}'
                        logger.debug(f"🔍 REPORTS: User not found for ID: {handover_req.created_by_id}")
                else:
                    logger.debug(f"🔍 REPORTS: No HandoverRequest found for shift {shift.id}, trying audit log fallback...")
                    # Fallback to audit log with more specific matching
                    from models.audit_log import AuditLog
                    audit_entry = AuditLog.query.filter(
                        AuditLog.action.like('%Create Handover%'),
                        AuditLog.details.like(f'%Team: {shift.team_id}%'),
                        AuditLog.details.like(f'%Account: {shift.account_id}%'),
                        AuditLog.details.like(f'%Date: {shift.date}%')
                    ).first()
                    
                    if audit_entry and audit_entry.user_id:
                        user = User.query.get(audit_entry.user_id)
                        if user:
                            submitted_by = user.display_name or user.username
                            logger.debug(f"🔍 REPORTS: Fallback audit submitter: {submitted_by} for shift {shift.id}")
                        else:
                            submitted_by = audit_entry.username or 'Unknown User'
                    
            except Exception as e:
                logger.debug(f"🚨 Error finding submitter for shift {shift.id}: {e}")
                submitted_by = 'Unknown'
            
            # Get Change Info and KB Updates for this shift
            # 🔧 FIX: Filter out Completed/Cancelled/Implemented changes - they shouldn't appear in handover reports
            change_infos = ShiftChangeInfo.query.filter(
                ShiftChangeInfo.shift_id == shift.id,
                ~ShiftChangeInfo.status.in_(['Completed', 'Cancelled', 'Implemented'])
            ).all()
            change_infos_data = []
            for change_info in change_infos:
                engineer = None
                if change_info.responsible_engineer_id:
                    engineer = TeamMember.query.get(change_info.responsible_engineer_id)
                
                change_infos_data.append({
                    'app_name': change_info.app_name,
                    'change_number': change_info.change_number,
                    'description': change_info.description,
                    'change_datetime': change_info.change_datetime,
                    'responsible': engineer.name if engineer else 'N/A',
                    'status': change_info.status  # Include status for display in reports
                })
            
            # 🔧 FIX: Filter out Published KBs - they shouldn't appear in handover reports
            kb_updates = ShiftKBUpdate.query.filter(
                ShiftKBUpdate.shift_id == shift.id,
                ShiftKBUpdate.status != 'Published'
            ).all()
            kb_updates_data = []
            for kb_update in kb_updates:
                engineer = None
                if kb_update.responsible_engineer_id:
                    engineer = TeamMember.query.get(kb_update.responsible_engineer_id)
                
                kb_updates_data.append({
                    'app_name': kb_update.app_name,
                    'kb_number': kb_update.kb_number,
                    'description': kb_update.description,
                    'status': kb_update.status,
                    'responsible': engineer.name if engineer else 'N/A'
                })

            # Create serializable shift data instead of passing the model object
            shift_data.append({
                'shift': {
                    'id': shift.id,
                    'date': shift.date,
                    'current_shift_type': shift.current_shift_type,
                    'next_shift_type': shift.next_shift_type,
                    'status': shift.status,
                    'submitted_at': shift.submitted_at,
                    'additional_notes': shift.additional_notes,
                    'account_id': shift.account_id,
                    'team_id': shift.team_id
                },
                'incidents': incidents_data,
                'key_points': key_points_data,
                'change_infos': change_infos_data,
                'kb_updates': kb_updates_data,
                'submitted_by': submitted_by
            })
            
            # Debug what we're sending to template
            logger.debug(f"  📋 REPORTS Sending {len(key_points_data)} key points, {len(change_infos_data)} change_infos, {len(kb_updates_data)} kb_updates to template for shift {shift.id}")
            if len(change_infos_data) > 0 or len(kb_updates_data) > 0:
                logger.debug(f"  🔥 SHIFT {shift.id} HAS CHANGE/KB DATA - Should show extra sections!")
            for kp_data in key_points_data:
                logger.debug(f"    - KP {kp_data.get('id', 'Unknown')}: {kp_data['status']} - {kp_data['description'][:30]}...")
        
        # Calculate visualization data
        total_shifts = len(shift_data)
        total_incidents = sum(len(entry['incidents']) for entry in shift_data)
        total_keypoints = sum(len(entry['key_points']) for entry in shift_data)
        
        # Incident type distribution
        incident_types = {}
        incident_priorities = {'High': 0, 'Medium': 0, 'Low': 0}
        keypoint_statuses = {'Open': 0, 'In Progress': 0, 'Closed': 0}
        
        shift_type_distribution = {'Morning': 0, 'Evening': 0, 'Night': 0}
        
        for entry in shift_data:
            # Shift type distribution
            shift_type = entry['shift']['current_shift_type']
            if shift_type in shift_type_distribution:
                shift_type_distribution[shift_type] += 1
                
            # Incident analysis
            for inc in entry['incidents']:
                inc_type = inc['type']
                incident_types[inc_type] = incident_types.get(inc_type, 0) + 1
                
                priority = inc['priority']
                if priority in incident_priorities:
                    incident_priorities[priority] += 1
            
            # Key point analysis
            for kp in entry['key_points']:
                status = kp['status']
                if status in keypoint_statuses:
                    keypoint_statuses[status] += 1
        
        stats = {
            'total_shifts': total_shifts,
            'total_incidents': total_incidents,
            'total_keypoints': total_keypoints,
            'incident_types': incident_types,
            'incident_priorities': incident_priorities,
            'keypoint_statuses': keypoint_statuses,
            'shift_type_distribution': shift_type_distribution
        }
        
        # 🔍 DEBUG: Final data being sent to template
        logger.debug(f"🔍 REPORTS DEBUG: Sending {len(shift_data)} shifts to template")
        logger.debug(f"🔍 REPORTS DEBUG: Key Point Status Summary: {keypoint_statuses}")
        logger.debug(f"🔍 REPORTS DEBUG: Stats = {stats}")
        
        # Verify that closed key points are included in the data
        total_closed_in_data = 0
        for data in shift_data:
            closed_count = sum(1 for kp in data['key_points'] if kp['status'] == 'Closed')
            total_closed_in_data += closed_count
            if closed_count > 0:
                logger.debug(f"🔍 REPORTS: Shift {data['shift']['id']} has {closed_count} closed key points in template data")
        
        logger.debug(f"🔍 REPORTS FINAL: Total closed key points being sent to template: {total_closed_in_data}")
        
        # 🔧 FIX: Pre-sort and pre-group shift data by date for template
        if shift_data:
            shift_data.sort(key=lambda x: x['shift']['date'], reverse=True)
            logger.debug(f"🔍 REPORTS SORT: Sorted {len(shift_data)} shifts by date")
            for i, data in enumerate(shift_data[:5]):
                logger.debug(f"  {i+1}. {data['shift']['date']} ({data['shift']['current_shift_type']})")
            
            # Pre-group shifts by date in the correct order
            grouped_shift_data = OrderedDict()
            for entry in shift_data:
                date_str = entry['shift']['date'].strftime('%Y-%m-%d')
                if date_str not in grouped_shift_data:
                    grouped_shift_data[date_str] = []
                grouped_shift_data[date_str].append(entry)
            
            logger.debug(f"🔍 REPORTS GROUPS: Created {len(grouped_shift_data)} date groups")
            for date_str, entries in list(grouped_shift_data.items())[:3]:
                logger.debug(f"  {date_str}: {len(entries)} shifts")
        else:
            grouped_shift_data = OrderedDict()
        
        if shift_data:
            logger.debug(f"🔍 REPORTS DEBUG: First 3 shifts:")
            for i, data in enumerate(shift_data[:3]):
                shift = data['shift']
                closed_kps = [kp for kp in data['key_points'] if kp['status'] == 'Closed']
                logger.debug(f"🔍   Shift {i+1}: ID={shift['id']}, Date={shift['date']}, Type={shift['current_shift_type']}, Status={shift['status']}, Incidents={len(data['incidents'])}, KeyPoints={len(data['key_points'])}, Closed KPs={len(closed_kps)}")
        else:
            logger.debug(f"🔍 REPORTS DEBUG: No shift data to display!")
        
        # Extract ordered date keys to pass to template for explicit ordering
        ordered_date_keys = list(grouped_shift_data.keys()) if grouped_shift_data else []
        logger.debug(f"🔍 REPORTS ORDERED KEYS: {ordered_date_keys}")
        
        # Add cache busting to ensure fresh data
        import time
        cache_buster = int(time.time())
        
        # Get team filter context for multi-team users
        if current_user.role not in ['super_admin', 'account_admin']:
            team_filter_context = TeamAccessService.get_team_filter_context()
        else:
            team_filter_context = None
        
        return render_template(
            'handover_reports.html',
            shift_data=shift_data,
            grouped_shift_data=grouped_shift_data,
            ordered_date_keys=ordered_date_keys,
            stats=stats,
            date_filter=date_filter or '',
            shift_type_filter=shift_type_filter or '',
            accounts=accounts,
            teams=teams,
            selected_account_id=account_id,
            selected_team_id=selected_team_id,
            cache_buster=cache_buster,
            team_filter_context=team_filter_context
        )
    except Exception as e:
        logger.error(f"❌ Error in handover_reports: {e}")
        import traceback
        traceback.print_exc()
        return render_template(
            'handover_reports.html',
            shift_data=[],
            stats={},
            error=f"Error loading reports: {str(e)}",
            date_filter='',
            shift_type_filter='',
            accounts=[],
            teams=[],
            selected_account_id=None,
            selected_team_id=None,
            team_filter_context=None
        )


# API endpoints for inline editing
@reports_bp.route('/api/kb-updates/<int:kb_id>', methods=['PUT'])
@login_required
def update_kb_record(kb_id):
    """Update a KB update record"""
    try:
        kb_update = ShiftKBUpdate.query.get_or_404(kb_id)
        
        # Check permissions
        if current_user.role not in ['super_admin', 'account_admin']:
            if kb_update.account_id != current_user.account_id or kb_update.team_id != current_user.team_id:
                return jsonify({'error': 'Unauthorized'}), 403
        elif current_user.role == 'account_admin':
            if kb_update.account_id != current_user.account_id:
                return jsonify({'error': 'Unauthorized'}), 403
        
        data = request.get_json()
        
        # Update fields
        kb_update.app_name = data.get('app_name', kb_update.app_name)
        kb_update.kb_number = data.get('kb_number', kb_update.kb_number)
        kb_update.description = data.get('description', kb_update.description)
        kb_update.status = data.get('status', kb_update.status)
        
        # Handle responsible engineer
        responsible_engineer_id = data.get('responsible_engineer_id')
        if responsible_engineer_id:
            kb_update.responsible_engineer_id = responsible_engineer_id
        else:
            kb_update.responsible_engineer_id = None
        
        db.session.commit()
        
        # Get responsible engineer name for response
        responsible_engineer_name = None
        if kb_update.responsible_engineer:
            responsible_engineer_name = kb_update.responsible_engineer.name
        
        log_action('Update KB Record', f'Updated KB record {kb_id}')
        
        return jsonify({
            'success': True,
            'message': 'KB update saved successfully',
            'responsible_engineer_name': responsible_engineer_name
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@reports_bp.route('/api/kb-updates/<int:kb_id>', methods=['DELETE'])
@login_required
def delete_kb_record(kb_id):
    """Delete a KB update record"""
    try:
        kb_update = ShiftKBUpdate.query.get_or_404(kb_id)
        
        # Check permissions - only admins and team members can delete
        if current_user.role not in ['super_admin', 'account_admin', 'team_admin']:
            if kb_update.account_id != current_user.account_id or kb_update.team_id != current_user.team_id:
                return jsonify({'error': 'Unauthorized - insufficient permissions'}), 403
        elif current_user.role == 'account_admin':
            if kb_update.account_id != current_user.account_id:
                return jsonify({'error': 'Unauthorized - different account'}), 403
        elif current_user.role == 'team_admin':
            if kb_update.account_id != current_user.account_id or kb_update.team_id != current_user.team_id:
                return jsonify({'error': 'Unauthorized - different team'}), 403
        
        kb_number = kb_update.kb_number or 'N/A'
        app_name = kb_update.app_name or 'N/A'
        
        db.session.delete(kb_update)
        db.session.commit()
        
        log_action('Delete KB Record', f'Deleted KB record {kb_id}: {app_name} - {kb_number}')
        
        return jsonify({
            'success': True,
            'message': f'KB record deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting KB record {kb_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500


@reports_bp.route('/api/team-members', methods=['GET'])
@login_required
def get_team_members():
    """Get team members for dropdown"""
    try:
        logger.debug(f"[DEBUG] Getting team members for user {current_user.id} role {current_user.role}")
        query = TeamMember.query
        
        # Filter by user permissions
        if current_user.role == 'super_admin':
            logger.debug("[DEBUG] Super admin - getting all team members")
            pass  # Can see all team members
        elif current_user.role == 'account_admin':
            logger.debug(f"[DEBUG] Account admin - filtering by account {current_user.account_id}")
            query = query.filter_by(account_id=current_user.account_id)
        else:
            logger.debug(f"[DEBUG] Regular user - filtering by account {current_user.account_id} and team {current_user.team_id}")
            query = query.filter_by(account_id=current_user.account_id, team_id=current_user.team_id)
        
        members = query.all()
        logger.debug(f"[DEBUG] Found {len(members)} team members")
        
        result = [{
            'id': member.id,
            'name': member.name
        } for member in members]
        
        logger.debug(f"[DEBUG] Returning team members: {result}")
        return jsonify(result)
        
    except Exception as e:
        logger.debug(f"[DEBUG] Error getting team members: {str(e)}")
        return jsonify({'error': str(e)}), 500


@reports_bp.route('/api/change-info/<int:change_id>', methods=['PUT'])
@login_required
def update_change_info_record(change_id):
    """Update a change info record"""
    try:
        change_info = ShiftChangeInfo.query.get_or_404(change_id)
        
        # Check permissions
        if current_user.role not in ['super_admin', 'account_admin']:
            if change_info.account_id != current_user.account_id or change_info.team_id != current_user.team_id:
                return jsonify({'error': 'Unauthorized'}), 403
        elif current_user.role == 'account_admin':
            if change_info.account_id != current_user.account_id:
                return jsonify({'error': 'Unauthorized'}), 403
        
        data = request.get_json()
        
        # Update fields
        change_info.app_name = data.get('app_name', change_info.app_name)
        change_info.change_number = data.get('change_number', change_info.change_number)
        change_info.description = data.get('description', change_info.description)
        change_info.status = data.get('status', change_info.status)
        
        # Handle change datetime
        change_datetime_str = data.get('change_datetime')
        if change_datetime_str:
            try:
                change_info.change_datetime = datetime.fromisoformat(change_datetime_str.replace('Z', '+00:00'))
            except ValueError:
                change_info.change_datetime = None
        else:
            change_info.change_datetime = None
        
        # Handle responsible engineer
        responsible_engineer_id = data.get('responsible_engineer_id')
        if responsible_engineer_id:
            change_info.responsible_engineer_id = responsible_engineer_id
        else:
            change_info.responsible_engineer_id = None
        
        db.session.commit()
        
        # Get responsible engineer name for response
        responsible_engineer_name = None
        if change_info.responsible_engineer:
            responsible_engineer_name = change_info.responsible_engineer.name
        
        log_action('Update Change Info', f'Updated change info record {change_id}')
        
        return jsonify({
            'success': True,
            'message': 'Change info saved successfully',
            'responsible_engineer_name': responsible_engineer_name
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@reports_bp.route('/api/change-info/<int:change_id>', methods=['DELETE'])
@login_required
def delete_change_info_record(change_id):
    """Delete a change info record"""
    try:
        change_info = ShiftChangeInfo.query.get_or_404(change_id)
        
        # Check permissions - only admins and team members can delete
        if current_user.role not in ['super_admin', 'account_admin', 'team_admin']:
            if change_info.account_id != current_user.account_id or change_info.team_id != current_user.team_id:
                return jsonify({'error': 'Unauthorized - insufficient permissions'}), 403
        elif current_user.role == 'account_admin':
            if change_info.account_id != current_user.account_id:
                return jsonify({'error': 'Unauthorized - different account'}), 403
        elif current_user.role == 'team_admin':
            if change_info.account_id != current_user.account_id or change_info.team_id != current_user.team_id:
                return jsonify({'error': 'Unauthorized - different team'}), 403
        
        change_number = change_info.change_number or 'N/A'
        app_name = change_info.app_name or 'N/A'
        
        db.session.delete(change_info)
        db.session.commit()
        
        log_action('Delete Change Info', f'Deleted change info record {change_id}: {app_name} - {change_number}')
        
        return jsonify({
            'success': True,
            'message': f'Change info record deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting change info record {change_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500


@reports_bp.route('/api/change-info', methods=['POST'])
@login_required
def create_change_info_record():
    """Create a new change info record"""
    try:
        data = request.get_json()
        
        # Get current shift or create one for today
        from datetime import date
        today = date.today()
        current_shift = Shift.query.filter_by(
            date=today,
            account_id=current_user.account_id,
            team_id=current_user.team_id
        ).first()
        
        if not current_shift:
            # Create a new shift for today
            current_shift = Shift(
                date=today,
                current_shift_type='Morning',  # Default
                next_shift_type='Evening',     # Default
                account_id=current_user.account_id,
                team_id=current_user.team_id
            )
            db.session.add(current_shift)
            db.session.flush()  # Get the ID
        
        # Create new change info record
        change_info = ShiftChangeInfo(
            app_name=data.get('app_name'),
            change_number=data.get('change_number'),
            description=data.get('description'),
            status=data.get('status', 'New'),
            shift_id=current_shift.id,
            account_id=current_user.account_id,
            team_id=current_user.team_id
        )
        
        # Handle change datetime
        change_datetime_str = data.get('change_datetime')
        if change_datetime_str:
            try:
                change_info.change_datetime = datetime.fromisoformat(change_datetime_str.replace('Z', '+00:00'))
            except ValueError:
                change_info.change_datetime = None
        
        # Handle responsible engineer
        responsible_engineer_id = data.get('responsible_engineer_id')
        if responsible_engineer_id:
            change_info.responsible_engineer_id = responsible_engineer_id
        
        db.session.add(change_info)
        db.session.commit()
        
        log_action('Create Change Info', f'Created new change info record: {change_info.change_number}')
        
        return jsonify({
            'success': True,
            'message': 'Change info created successfully',
            'id': change_info.id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@reports_bp.route('/api/kb-updates', methods=['POST'])
@login_required
def create_kb_update_record():
    """Create a new KB update record"""
    try:
        data = request.get_json()
        
        # Get current shift or create one for today
        from datetime import date
        today = date.today()
        current_shift = Shift.query.filter_by(
            date=today,
            account_id=current_user.account_id,
            team_id=current_user.team_id
        ).first()
        
        if not current_shift:
            # Create a new shift for today
            current_shift = Shift(
                date=today,
                current_shift_type='Morning',  # Default
                next_shift_type='Evening',     # Default
                account_id=current_user.account_id,
                team_id=current_user.team_id
            )
            db.session.add(current_shift)
            db.session.flush()  # Get the ID
        
        # Create new KB update record
        kb_update = ShiftKBUpdate(
            app_name=data.get('app_name'),
            kb_number=data.get('kb_number'),
            description=data.get('description'),
            status=data.get('status', 'New'),
            shift_id=current_shift.id,
            account_id=current_user.account_id,
            team_id=current_user.team_id
        )
        
        # Handle responsible engineer
        responsible_engineer_id = data.get('responsible_engineer_id')
        if responsible_engineer_id:
            kb_update.responsible_engineer_id = responsible_engineer_id
        
        db.session.add(kb_update)
        db.session.commit()
        
        log_action('Create KB Update', f'Created new KB update record: {kb_update.kb_number}')
        
        return jsonify({
            'success': True,
            'message': 'KB update created successfully',
            'id': kb_update.id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

