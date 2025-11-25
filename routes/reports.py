
from flask import Blueprint, render_template, request, send_file, session
from flask_login import login_required, current_user
from datetime import datetime
from sqlalchemy import func
from models.models import Shift, Incident, ShiftKeyPoint, TeamMember, Account, Team, User
from models.audit_log import AuditLog
from services.export_service import export_incidents_csv, export_keypoints_pdf

from services.audit_service import log_action


reports_bp = Blueprint('reports', __name__)


@reports_bp.route('/reports', methods=['GET'])
@login_required
def reports():
    """Main reports page - redirects to handover reports"""
    log_action('View Reports Tab', 'Accessed main reports page')
    # Redirect to handover reports as the main reports page
    from flask import redirect, url_for
    return redirect(url_for('reports.handover_reports'))


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


@reports_bp.route('/handover-reports', methods=['GET'])
@login_required
def handover_reports():
    print(f"🚨 HANDOVER REPORTS ROUTE CALLED 🚨", flush=True)
    
    # Check database integrity first
    total_shifts = Shift.query.count()
    total_incidents = Incident.query.count()
    total_key_points = ShiftKeyPoint.query.count()
    print(f"🔍 Database totals: {total_shifts} shifts, {total_incidents} incidents, {total_key_points} key points", flush=True)
    
    # Show some sample records
    if total_incidents > 0:
        sample_incidents = Incident.query.limit(3).all()
        for inc in sample_incidents:
            print(f"🔍 Sample Incident: ID={inc.id}, shift_id={inc.shift_id}, title='{inc.title}'", flush=True)
    
    if total_key_points > 0:
        sample_kps = ShiftKeyPoint.query.limit(3).all()
        for kp in sample_kps:
            print(f"🔍 Sample KeyPoint: ID={kp.id}, shift_id={kp.shift_id}, desc='{kp.description[:50]}'", flush=True)
    
    try:
        # Default filters
        log_action('View Reports Tab', f'Filters: account_id={request.args.get("account_id")}, team_id={request.args.get("team_id")}, date={request.args.get("date")}, shift_type={request.args.get("shift_type")}')
        date_filter = request.args.get('date')
        shift_type_filter = request.args.get('shift_type')
        account_id = None
        team_id = None
        accounts = []
        teams = []
        query = Shift.query
        if current_user.role == 'super_admin':
            accounts = Account.query.filter_by(is_active=True).all()
            account_id = request.args.get('account_id') or session.get('selected_account_id')
            print(f"🔍 SUPER_ADMIN: account_id from params/session: {account_id}", flush=True)
            teams = Team.query.filter_by(is_active=True)
            if account_id:
                teams = teams.filter_by(account_id=account_id)
                print(f"🔍 SUPER_ADMIN: Filtering teams by account_id: {account_id}", flush=True)
            else:
                print(f"🔍 SUPER_ADMIN: No account_id selected - showing ALL accounts data", flush=True)
                # 🔧 FIX: For super_admin with no account selected, don't filter by account
                # This allows super_admin to see ALL data from ALL accounts by default
            teams = teams.all()
            team_id = request.args.get('team_id') or session.get('selected_team_id')
            print(f"🔍 SUPER_ADMIN: team_id from params/session: {team_id}", flush=True)
            # 🔧 FIX: For super_admin, if no team is selected, show all teams
            if not account_id and team_id:
                # If specific team selected but no account, still filter by team
                print(f"🔍 SUPER_ADMIN: Filtering by team_id only: {team_id}", flush=True)
        elif current_user.role == 'account_admin':
            account_id = current_user.account_id
            accounts = [Account.query.get(account_id)] if account_id else []
            teams = Team.query.filter_by(account_id=account_id, is_active=True).all()
            team_id = request.args.get('team_id') or session.get('selected_team_id')
        else:
            account_id = current_user.account_id
            team_id = current_user.team_id
            accounts = [Account.query.get(account_id)] if account_id else []
            teams = [Team.query.get(team_id)] if team_id else []
        # 🔧 FIX: Apply filtering logic based on user role and selections
        if current_user.role == 'super_admin':
            # For super_admin: only filter if explicitly selected
            if account_id:
                query = query.filter_by(account_id=account_id)
                print(f"🔍 SUPER_ADMIN: Filtering by account_id: {account_id}", flush=True)
            else:
                print(f"🔍 SUPER_ADMIN: No account filter - showing ALL accounts", flush=True)
            if team_id:
                query = query.filter_by(team_id=team_id)
                print(f"🔍 SUPER_ADMIN: Filtering by team_id: {team_id}", flush=True)
            else:
                print(f"🔍 SUPER_ADMIN: No team filter - showing ALL teams", flush=True)
        else:
            # For account_admin and regular users: always filter by their assigned account/team
            if account_id:
                query = query.filter_by(account_id=account_id)
                print(f"🔍 NON-SUPER: Filtering by account_id: {account_id}", flush=True)
            if team_id:
                query = query.filter_by(team_id=team_id)
                print(f"🔍 NON-SUPER: Filtering by team_id: {team_id}", flush=True)
        if date_filter:
            try:
                date_obj = datetime.strptime(date_filter, '%Y-%m-%d').date()
                query = query.filter_by(date=date_obj)  # 🔧 FIXED: Use date column
                print(f"🔍 Filtering by date: {date_obj}", flush=True)
            except Exception:
                print(f"🔍 Invalid date filter: {date_filter}", flush=True)
                pass
        if shift_type_filter:
            query = query.filter_by(current_shift_type=shift_type_filter)
            print(f"🔍 Filtering by shift_type: {shift_type_filter}", flush=True)
        
        print(f"🔍 Final query filters applied: account_id={account_id}, team_id={team_id}, date={date_filter}, shift_type={shift_type_filter}", flush=True)
        # Order by shift date only for now (newest first)  
        # TODO: Re-add submitted_at ordering when MySQL compatibility issue is resolved
        shifts = query.order_by(
            Shift.date.desc()
        ).all()
        
        print(f"🔍 Found {len(shifts)} shifts total", flush=True)
        for shift in shifts[:3]:  # Show first 3 shifts
            print(f"🔍 Shift ID: {shift.id}, Date: {shift.date}, Type: {shift.current_shift_type}, Submitted: {shift.submitted_at}", flush=True)
        
        shift_data = []
        for shift in shifts:
            incidents = Incident.query.filter_by(shift_id=shift.id).all()
            # ✨ REPORTS FIX: Get ALL key points without any filtering for historical tracking
            key_points = ShiftKeyPoint.query.filter_by(shift_id=shift.id).all()
            
            print(f"🔍 REPORTS SHIFT {shift.id}: Found {len(incidents)} incidents, {len(key_points)} key points", flush=True)
            
            # Debug key points details with status breakdown
            status_counts = {'Open': 0, 'In Progress': 0, 'Closed': 0}
            for kp in key_points:
                status_counts[kp.status] = status_counts.get(kp.status, 0) + 1
                print(f"  📋 REPORTS KP {kp.id}: '{kp.description[:30]}...' - Status: {kp.status} - Responsible: {kp.responsible_engineer_id}")
            
            print(f"  📊 REPORTS Status breakdown for shift {shift.id}: {status_counts}")
            
            if len(key_points) == 0:
                print(f"  ⚠️  REPORTS WARNING: No key points found for shift {shift.id}")
            
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
                    print(f"🔍 Incident {inc.id} has assignment: '{inc.assigned_to}'")
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
                    print(f"  ✅ REPORTS Added KP {kp.id} to template data: Status={kp.status}")
                    
                except Exception as e:
                    print(f"🚨 Error processing key point {kp.id}: {e}")
                    # Add basic key point without responsible engineer
                    kp_data = {
                        'description': kp.description,
                        'status': kp.status,
                        'responsible': 'Error',
                        'jira_id': kp.jira_id,
                        'id': kp.id
                    }
                    key_points_data.append(kp_data)
                    print(f"  ⚠️  REPORTS Added KP {kp.id} with error to template data")
            
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
            
            shift_data.append({
                'shift': shift,
                'incidents': incidents_data,
                'key_points': key_points_data,
                'submitted_by': submitted_by
            })
            
            # Debug what we're sending to template
            print(f"  📋 REPORTS Sending {len(key_points_data)} key points to template for shift {shift.id}")
            for kp_data in key_points_data:
                print(f"    - KP {kp_data.get('id', 'Unknown')}: {kp_data['status']} - {kp_data['description'][:30]}...")
        
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
            shift_type = entry['shift'].current_shift_type
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
        print(f"🔍 REPORTS DEBUG: Sending {len(shift_data)} shifts to template")
        print(f"🔍 REPORTS DEBUG: Key Point Status Summary: {keypoint_statuses}")
        print(f"🔍 REPORTS DEBUG: Stats = {stats}")
        
        # Verify that closed key points are included in the data
        total_closed_in_data = 0
        for data in shift_data:
            closed_count = sum(1 for kp in data['key_points'] if kp['status'] == 'Closed')
            total_closed_in_data += closed_count
            if closed_count > 0:
                print(f"🔍 REPORTS: Shift {data['shift'].id} has {closed_count} closed key points in template data")
        
        print(f"🔍 REPORTS FINAL: Total closed key points being sent to template: {total_closed_in_data}")
        
        if shift_data:
            print(f"🔍 REPORTS DEBUG: First 3 shifts:")
            for i, data in enumerate(shift_data[:3]):
                shift = data['shift']
                closed_kps = [kp for kp in data['key_points'] if kp['status'] == 'Closed']
                print(f"🔍   Shift {i+1}: ID={shift.id}, Date={shift.date}, Type={shift.current_shift_type}, Status={shift.status}, Incidents={len(data['incidents'])}, KeyPoints={len(data['key_points'])}, Closed KPs={len(closed_kps)}")
        else:
            print(f"🔍 REPORTS DEBUG: No shift data to display!")
        
        return render_template(
            'handover_reports.html',
            shift_data=shift_data,
            stats=stats,
            date_filter=date_filter or '',
            shift_type_filter=shift_type_filter or '',
            accounts=accounts,
            teams=teams,
            selected_account_id=account_id,
            selected_team_id=team_id
        )
    except Exception as e:
        print(f"❌ Error in handover_reports: {e}", flush=True)
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
            selected_team_id=None
        )

