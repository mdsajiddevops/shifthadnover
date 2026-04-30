from flask import Blueprint, render_template, request, redirect, url_for, flash, session, send_file, jsonify
from flask_login import login_required, current_user
import os
import pandas as pd
from functools import wraps
from io import BytesIO
from services.team_access_service import TeamAccessService
from models.models import db, Account, Team
from models.escalation_matrix import EscalationMatrixEntry

UPLOAD_FOLDER = 'uploads/escalation_matrix'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

escalation_bp = Blueprint('escalation_matrix', __name__)

def admin_required_for_upload(f):
    """Decorator to check upload permissions for escalation matrix"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # For POST requests (uploads), require admin privileges
        if request.method == 'POST':
            if not current_user.is_authenticated or current_user.role not in ['super_admin', 'account_admin', 'team_admin']:
                flash('Access denied. Administrator privileges required for uploading.', 'error')
                return redirect(url_for('escalation_matrix.escalation_matrix'))
        return f(*args, **kwargs)
    return decorated_function


def is_admin():
    """Check if current user is an admin"""
    return current_user.role in ['super_admin', 'account_admin', 'team_admin']


@escalation_bp.route('/download-sample-escalation-matrix')
@login_required
def download_sample_escalation_matrix():
    """Generate and download a sample escalation matrix template"""
    try:
        # Create sample data matching the exact format
        sample_data = {
            'Team Email ID': ['billing_systems_app_support@example.co', 'payment_systems_app_support@example.co'],
            'Contact Details': ['+1-555-707-8085', '+1-555-808-9096'],
            'Support Coverage': ['Mon-Fri 8AM-5PM PST', '24x7'],
            'SLA': ['P1 - 25 min, P2 - 45 min', 'P1 - 15 min, P2 - 30 min'],
            'ServiceNow Assignment Group': ['BILLING_SYSTEM_APP', 'PAYMENT_SYSTEM_APP'],
            'Escalation Level 1': ['Isabella Moore (+1-555-000-1111, isabella.moore@example.co)', 'John Smith (+1-555-111-2222, john.smith@example.co)'],
            'Escalation Level 2': ['William Harris (+1-555-111-2223, william.harris@example.co)', 'Jane Doe (+1-555-222-3333, jane.doe@example.co)'],
            'Escalation Level 3': ['Charlotte Miller (+1-555-222-3334, charlotte.miller@example.com)', 'Bob Wilson (+1-555-333-4444, bob.wilson@example.com)'],
            'Notes': ['Primary billing support', 'Payment gateway support']
        }
        
        df = pd.DataFrame(sample_data)
        output = BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            sheet_names = ['Application_Team_A', 'Application_Team_B']
            
            for sheet_name in sheet_names:
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                worksheet = writer.sheets[sheet_name]
                
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
        
        output.seek(0)
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='Sample_Escalation_Matrix_Template.xlsx'
        )
        
    except Exception as e:
        flash(f'Error generating sample template: {str(e)}', 'error')
        return redirect(url_for('escalation_matrix.escalation_matrix'))


@escalation_bp.route('/api/escalation-matrix/teams-by-account')
@login_required
def get_teams_by_account():
    """API endpoint to get teams for a specific account"""
    account_id = request.args.get('account_id')
    
    if not account_id:
        return jsonify({'teams': []})
    
    try:
        account_id = int(account_id)
        
        # Security check
        if current_user.role == 'super_admin':
            pass
        elif current_user.role == 'account_admin' and current_user.account_id == account_id:
            pass
        else:
            return jsonify({'teams': []})
        
        teams = Team.query.filter_by(account_id=account_id, is_active=True).order_by(Team.name).all()
        teams_data = [{'id': team.id, 'name': team.name} for team in teams]
        
        return jsonify({'teams': teams_data})
        
    except (TypeError, ValueError):
        return jsonify({'teams': []})


@escalation_bp.route('/api/escalation-matrix/entries')
@login_required
def get_entries_api():
    """API endpoint to get escalation matrix entries"""
    account_id = request.args.get('account_id', type=int)
    team_id = request.args.get('team_id', type=int)
    application = request.args.get('application')
    
    query = EscalationMatrixEntry.query.filter_by(is_active=True)
    
    # Apply role-based filtering
    if current_user.role == 'super_admin':
        if account_id:
            query = query.filter_by(account_id=account_id)
        if team_id:
            query = query.filter_by(team_id=team_id)
    elif current_user.role == 'account_admin':
        query = query.filter_by(account_id=current_user.account_id)
        if team_id:
            query = query.filter_by(team_id=team_id)
    else:
        # Team admin or user - filter by their teams
        user_team_ids = TeamAccessService.get_user_team_ids()
        if team_id and team_id in user_team_ids:
            # User selected a specific team they have access to
            query = query.filter(EscalationMatrixEntry.team_id == team_id)
        elif user_team_ids:
            # Show all their teams if no specific team selected
            query = query.filter(EscalationMatrixEntry.team_id.in_(user_team_ids))
    
    if application:
        query = query.filter_by(application_name=application)
    
    entries = query.order_by(EscalationMatrixEntry.application_name, EscalationMatrixEntry.id).all()
    
    return jsonify({
        'entries': [entry.to_dict() for entry in entries],
        'count': len(entries)
    })


@escalation_bp.route('/api/escalation-matrix/entry/<int:entry_id>', methods=['GET'])
@login_required
def get_entry_api(entry_id):
    """Get a single escalation matrix entry"""
    entry = EscalationMatrixEntry.query.get_or_404(entry_id)
    return jsonify(entry.to_dict())


@escalation_bp.route('/api/escalation-matrix/entry', methods=['POST'])
@login_required
def add_entry_api():
    """Add a new escalation matrix entry"""
    if not is_admin():
        return jsonify({'success': False, 'error': 'Admin access required'}), 403
    
    data = request.get_json()
    
    try:
        entry = EscalationMatrixEntry(
            application_name=data.get('application_name', 'Default'),
            team_email_id=data.get('team_email_id'),
            contact_details=data.get('contact_details'),
            support_coverage=data.get('support_coverage'),
            sla=data.get('sla'),
            servicenow_assignment_group=data.get('servicenow_assignment_group'),
            escalation_level_1=data.get('escalation_level_1'),
            escalation_level_2=data.get('escalation_level_2'),
            escalation_level_3=data.get('escalation_level_3'),
            escalation_level_4=data.get('escalation_level_4'),
            escalation_level_5=data.get('escalation_level_5'),
            notes=data.get('notes'),
            additional_info=data.get('additional_info'),
            account_id=data.get('account_id') or current_user.account_id,
            team_id=data.get('team_id') or current_user.team_id,
            created_by=current_user.id
        )
        
        db.session.add(entry)
        db.session.commit()
        
        return jsonify({'success': True, 'entry': entry.to_dict()})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@escalation_bp.route('/api/escalation-matrix/entry/<int:entry_id>', methods=['PUT'])
@login_required
def edit_entry_api(entry_id):
    """Edit an escalation matrix entry"""
    if not is_admin():
        return jsonify({'success': False, 'error': 'Admin access required'}), 403
    
    entry = EscalationMatrixEntry.query.get_or_404(entry_id)
    data = request.get_json()
    
    try:
        entry.application_name = data.get('application_name', entry.application_name)
        entry.team_email_id = data.get('team_email_id')
        entry.contact_details = data.get('contact_details')
        entry.support_coverage = data.get('support_coverage')
        entry.sla = data.get('sla')
        entry.servicenow_assignment_group = data.get('servicenow_assignment_group')
        entry.escalation_level_1 = data.get('escalation_level_1')
        entry.escalation_level_2 = data.get('escalation_level_2')
        entry.escalation_level_3 = data.get('escalation_level_3')
        entry.escalation_level_4 = data.get('escalation_level_4')
        entry.escalation_level_5 = data.get('escalation_level_5')
        entry.notes = data.get('notes')
        entry.additional_info = data.get('additional_info')
        
        if data.get('account_id'):
            entry.account_id = data.get('account_id')
        if data.get('team_id'):
            entry.team_id = data.get('team_id')
        
        db.session.commit()
        
        return jsonify({'success': True, 'entry': entry.to_dict()})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@escalation_bp.route('/api/escalation-matrix/entry/<int:entry_id>', methods=['DELETE'])
@login_required
def delete_entry_api(entry_id):
    """Delete an escalation matrix entry"""
    if not is_admin():
        return jsonify({'success': False, 'error': 'Admin access required'}), 403
    
    entry = EscalationMatrixEntry.query.get_or_404(entry_id)
    
    try:
        # Soft delete
        entry.is_active = False
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Entry deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@escalation_bp.route('/api/escalation-matrix/import', methods=['POST'])
@login_required
def import_entries():
    """Import escalation matrix entries from Excel file"""
    if not is_admin():
        return jsonify({'success': False, 'error': 'Admin access required'}), 403
    
    file = request.files.get('file')
    account_id = request.form.get('account_id', type=int) or current_user.account_id
    team_id = request.form.get('team_id', type=int) or current_user.team_id
    replace_existing = request.form.get('replace_existing', 'false').lower() == 'true'
    
    if not file or not file.filename.endswith('.xlsx'):
        return jsonify({'success': False, 'error': 'Please upload a valid .xlsx file'}), 400
    
    try:
        xls = pd.ExcelFile(file)
        imported_count = 0
        
        # If replacing, delete existing entries for this account/team
        if replace_existing:
            EscalationMatrixEntry.query.filter_by(
                account_id=account_id,
                team_id=team_id,
                is_active=True
            ).update({'is_active': False})
        
        for sheet_name in xls.sheet_names:
            df = xls.parse(sheet_name)
            df = df.where(pd.notnull(df), None)
            
            for _, row in df.iterrows():
                row_dict = row.to_dict()
                
                # Skip empty rows
                if all(v is None or str(v).strip() == '' for v in row_dict.values()):
                    continue
                
                entry = EscalationMatrixEntry.from_excel_row(
                    row_dict,
                    application_name=sheet_name,
                    account_id=account_id,
                    team_id=team_id,
                    created_by=current_user.id
                )
                db.session.add(entry)
                imported_count += 1
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Successfully imported {imported_count} entries from {len(xls.sheet_names)} sheets',
            'count': imported_count
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@escalation_bp.route('/api/escalation-matrix/applications')
@login_required
def get_applications():
    """Get list of unique application names for filtering"""
    query = EscalationMatrixEntry.query.filter_by(is_active=True)
    
    # Apply role-based filtering
    if current_user.role == 'super_admin':
        account_id = request.args.get('account_id', type=int)
        team_id = request.args.get('team_id', type=int)
        if account_id:
            query = query.filter_by(account_id=account_id)
        if team_id:
            query = query.filter_by(team_id=team_id)
    elif current_user.role == 'account_admin':
        query = query.filter_by(account_id=current_user.account_id)
        team_id = request.args.get('team_id', type=int)
        if team_id:
            query = query.filter_by(team_id=team_id)
    else:
        # Team admin or user - filter by their teams
        user_team_ids = TeamAccessService.get_user_team_ids()
        team_id = request.args.get('team_id', type=int)
        if team_id and team_id in user_team_ids:
            query = query.filter(EscalationMatrixEntry.team_id == team_id)
        elif user_team_ids:
            query = query.filter(EscalationMatrixEntry.team_id.in_(user_team_ids))
    
    applications = query.with_entities(EscalationMatrixEntry.application_name).distinct().all()
    app_names = [app[0] for app in applications if app[0]]
    
    return jsonify({'applications': sorted(app_names)})


@escalation_bp.route('/escalation-matrix', methods=['GET', 'POST'])
@login_required
@admin_required_for_upload
def escalation_matrix():
    """Main escalation matrix page"""
    # Get filter parameters
    account_id = request.args.get('account_id', type=int)
    team_id = request.args.get('team_id', type=int)
    selected_app = request.args.get('application')
    
    # Get accounts and teams for dropdowns
    accounts = []
    teams = []
    
    if current_user.role == 'super_admin':
        accounts = Account.query.filter_by(is_active=True).order_by(Account.name).all()
        if account_id:
            teams = Team.query.filter_by(account_id=account_id, is_active=True).order_by(Team.name).all()
        else:
            teams = Team.query.filter_by(is_active=True).order_by(Team.name).all()
    elif current_user.role == 'account_admin':
        account_id = current_user.account_id
        accounts = [Account.query.get(account_id)] if account_id else []
        teams = Team.query.filter_by(account_id=account_id, is_active=True).order_by(Team.name).all()
    else:
        # Team admin or user - support multi-team filtering
        url_team_id = request.args.get('team_id', type=int)
        team_filter_context = TeamAccessService.get_team_filter_context(url_team_id=url_team_id)
        account_id = team_filter_context.get('selected_account_id')
        accounts = [Account.query.get(account_id)] if account_id else []
        teams = team_filter_context.get('user_teams', [])
        
        # Use URL param team_id if provided, otherwise use selected from context
        if team_id:
            # Validate user has access to this team
            user_team_ids = [t.id for t in teams]
            if team_id not in user_team_ids:
                team_id = team_filter_context.get('selected_team_id')
        else:
            team_id = team_filter_context.get('selected_team_id')
    
    # Build query for entries
    query = EscalationMatrixEntry.query.filter_by(is_active=True)
    
    if current_user.role == 'super_admin':
        if account_id:
            query = query.filter_by(account_id=account_id)
        if team_id:
            query = query.filter_by(team_id=team_id)
    elif current_user.role == 'account_admin':
        query = query.filter_by(account_id=current_user.account_id)
        if team_id:
            query = query.filter_by(team_id=team_id)
    else:
        # Regular users - filter by selected team or all their teams
        user_team_ids = TeamAccessService.get_user_team_ids()
        if team_id and team_id in user_team_ids:
            # Specific team selected from filter
            query = query.filter(EscalationMatrixEntry.team_id == team_id)
        elif user_team_ids:
            query = query.filter(EscalationMatrixEntry.team_id.in_(user_team_ids))
    
    # Get unique application names for filter
    app_query = query.with_entities(EscalationMatrixEntry.application_name).distinct()
    app_names = [app[0] for app in app_query.all() if app[0]]
    app_names = sorted(set(app_names))
    
    # Filter by selected application
    matrix_data = []
    if selected_app:
        entries = query.filter_by(application_name=selected_app).order_by(EscalationMatrixEntry.id).all()
        matrix_data = [entry.to_dict() for entry in entries]
    
    # Get total count
    total_count = query.count()
    
    return render_template('escalation_matrix.html',
                         app_names=app_names,
                         matrix_data=matrix_data,
                         selected_app=selected_app,
                         accounts=accounts,
                         teams=teams,
                         selected_account_id=account_id,
                         selected_team_id=team_id,
                         total_count=total_count,
                         is_admin=is_admin())
