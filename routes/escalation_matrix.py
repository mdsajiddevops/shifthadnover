from flask import Blueprint, render_template, request, redirect, url_for, flash, session, send_file, jsonify
from flask_login import login_required, current_user
import os
import pandas as pd
from functools import wraps
from io import BytesIO

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

@escalation_bp.route('/download-sample-escalation-matrix')
@login_required
def download_sample_escalation_matrix():
    """Generate and download a sample escalation matrix template"""
    try:
        # Create sample data matching the exact format from image-2
        sample_data = {
            'Team Email ID': ['billing_systems_app_support@example.co', 'billing_systems_app_support@example.co', 'billing_systems_app_support@example.co', 'billing_systems_app_support@example.co', 'billing_systems_app_support@example.co'],
            'Contact Details': ['+1-555-707-8085', '+1-555-707-8085', '+1-555-707-8085', '+1-555-707-8085', '+1-555-707-8085'],
            'Support Coverage': ['Mon-Fri 8AM-5PM PST', 'Mon-Fri 8AM-5PM PST', 'Mon-Fri 8AM-5PM PST', 'Mon-Fri 8AM-5PM PST', 'Mon-Fri 8AM-5PM PST'],
            'SLA': ['P1 - 25 min, P2 - 45 min', 'P1 - 25 min, P2 - 45 min', 'P1 - 25 min, P2 - 45 min', 'P1 - 25 min, P2 - 45 min', 'P1 - 25 min, P2 - 45 min'],
            'ServiceNow Assignment Group': ['BILLING_SYSTEM_APP', 'BILLING_SYSTEM_APP', 'BILLING_SYSTEM_APP', 'BILLING_SYSTEM_APP', 'BILLING_SYSTEM_APP'],
            'Escalation Level 1': ['Isabella Moore (+1-555-000-1111, isabella.moore@example.co)', 'Isabella Moore (+1-555-000-1111, isabella.moore@example.co)', 'Isabella Moore (+1-555-000-1111, isabella.moore@example.co)', 'Isabella Moore (+1-555-000-1111, isabella.moore@example.co)', 'Isabella Moore (+1-555-000-1111, isabella.moore@example.co)'],
            'Escalation Level 2': ['William Harris (+1-555-111-2223, william.harris@example.co)', 'William Harris (+1-555-111-2223, william.harris@example.co)', 'William Harris (+1-555-111-2223, william.harris@example.co)', 'William Harris (+1-555-111-2223, william.harris@example.co)', 'William Harris (+1-555-111-2223, william.harris@example.co)'],
            'Escalation Level 3': ['Charlotte Miller (+1-555-222-3334, charlotte.miller@example.com)', 'Charlotte Miller (+1-555-222-3334, charlotte.miller@example.com)', 'Charlotte Miller (+1-555-222-3334, charlotte.miller@example.com)', 'Charlotte Miller (+1-555-222-3334, charlotte.miller@example.com)', 'Charlotte Miller (+1-555-222-3334, charlotte.miller@example.com)']
        }
        
        # Create DataFrame
        df = pd.DataFrame(sample_data)
        
        # Create BytesIO object to store the Excel file in memory
        output = BytesIO()
        
        # Write to Excel with multiple sheets matching the image-2 format
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Create multiple sample sheets as shown in image-2
            sheet_names = ['acme_corp_team_a', 'acme_corp_team_b']
            
            for sheet_name in sheet_names:
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                
                # Get the worksheet for formatting
                worksheet = writer.sheets[sheet_name]
                
                # Auto-adjust column widths
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

@escalation_bp.route('/api/teams-by-account')
@login_required
def get_teams_by_account():
    """API endpoint to get teams for a specific account (for escalation matrix upload)"""
    account_id = request.args.get('account_id')
    
    if not account_id:
        return jsonify({'teams': []})
    
    try:
        account_id = int(account_id)
        
        # Security check: ensure user has permission to access this account
        if current_user.role == 'super_admin':
            # Super admin can access any account
            pass
        elif current_user.role == 'account_admin' and current_user.account_id == account_id:
            # Account admin can only access their own account
            pass
        else:
            # Other roles cannot access this endpoint
            return jsonify({'teams': []})
        
        from models.models import Team
        teams = Team.query.filter_by(account_id=account_id, is_active=True).order_by(Team.name).all()
        teams_data = [{'id': team.id, 'name': team.name} for team in teams]
        
        return jsonify({'teams': teams_data})
        
    except (TypeError, ValueError):
        return jsonify({'teams': []})

@escalation_bp.route('/escalation-matrix', methods=['GET', 'POST'])
@login_required
@admin_required_for_upload
def escalation_matrix():
    app_names = []
    matrix_data = None
    selected_app = request.args.get('application')
    if request.method == 'POST':
        if current_user.role not in ['super_admin', 'account_admin', 'team_admin']:
            flash('Access denied. Administrator privileges required for uploading.', 'error')
            return redirect(url_for('escalation_matrix.escalation_matrix'))
        
        file = request.files.get('file')
        
        # For admins, get account_id and team_id from form submission
        if current_user.role == 'super_admin':
            # Super admin can select any account and team
            account_id = request.form.get('upload_account_id')
            team_id = request.form.get('upload_team_id')
        elif current_user.role == 'account_admin':
            # Account admin can only upload to their account, but can select team
            account_id = current_user.account_id
            team_id = request.form.get('upload_team_id')
        else:
            # Team admin uses their current account/team
            account_id = getattr(current_user, 'account_id', None)
            team_id = getattr(current_user, 'team_id', None)
        
        # Validate and convert to integers
        try:
            account_id = int(account_id) if account_id else None
        except (TypeError, ValueError):
            account_id = None
        try:
            team_id = int(team_id) if team_id else None
        except (TypeError, ValueError):
            team_id = None
        
        # Validation
        if not account_id:
            flash('Please select a valid account.', 'error')
            return redirect(url_for('escalation_matrix.escalation_matrix'))
        
        if not team_id:
            flash('Please select a valid team.', 'error')
            return redirect(url_for('escalation_matrix.escalation_matrix'))
        
        # Additional security check for account_admin
        if current_user.role == 'account_admin' and account_id != current_user.account_id:
            flash('Access denied. You can only upload to your own account.', 'error')
            return redirect(url_for('escalation_matrix.escalation_matrix'))
        if file and file.filename.endswith('.xlsx'):
            filepath = os.path.join(UPLOAD_FOLDER, file.filename)
            # If file exists, remove it before saving new one
            if os.path.exists(filepath):
                os.remove(filepath)
            file.save(filepath)
            # Save or update file info in EscalationMatrixFile table
            from models.models import EscalationMatrixFile, db
            import datetime
            # Find by filename only to avoid duplicate constraint issues
            existing_file = EscalationMatrixFile.query.filter_by(filename=file.filename).first()
            if existing_file:
                # Update existing record with new account/team info and timestamp
                existing_file.account_id = account_id
                existing_file.team_id = team_id
                existing_file.upload_time = datetime.datetime.now()
            else:
                matrix_file = EscalationMatrixFile(filename=file.filename, upload_time=datetime.datetime.now(), account_id=account_id, team_id=team_id)
                db.session.add(matrix_file)
            # Parse and save each sheet/row if you have a model for escalation matrix rows
            xls = pd.ExcelFile(filepath)
            for sheet_name in xls.sheet_names:
                df = xls.parse(sheet_name)
                table_data = df.where(pd.notnull(df), '').to_dict(orient='records')
                # If you have a model like EscalationMatrixRow, save each row
                # from models.models import EscalationMatrixRow
                # for row in table_data:
                #     escalation_row = EscalationMatrixRow(...)
                #     db.session.add(escalation_row)
            db.session.commit()
            flash('Escalation matrix uploaded and replaced successfully!')
            return redirect(url_for('escalation_matrix.escalation_matrix'))
        else:
            flash('Please upload a valid .xlsx file.')
    # Find the latest uploaded file
    files = [f for f in os.listdir(UPLOAD_FOLDER) if f.endswith('.xlsx')]
    app_names = []
    xls = None
    account_name = None
    team_name = None
    account_id = request.args.get('account_id') or (session.get('selected_account_id') if hasattr(session, 'get') else None)
    team_id = request.args.get('team_id') or (session.get('selected_team_id') if hasattr(session, 'get') else None)
    # Ensure IDs are integers for filtering
    try:
        account_id = int(account_id) if account_id else None
    except Exception:
        account_id = None
    try:
        team_id = int(team_id) if team_id else None
    except Exception:
        team_id = None
    if files:
        from models.models import EscalationMatrixFile, Account, Team
        # Find the latest file for the selected account/team
        file_query = EscalationMatrixFile.query
        # Super Admin: use filter, fallback to latest file if no filter
        if current_user.role == 'super_admin':
            if account_id is not None:
                file_query = file_query.filter_by(account_id=account_id)
            if team_id is not None:
                file_query = file_query.filter_by(team_id=team_id)
            latest_db_file = file_query.order_by(EscalationMatrixFile.upload_time.desc()).first()
            if not latest_db_file:
                latest_db_file = EscalationMatrixFile.query.order_by(EscalationMatrixFile.upload_time.desc()).first()
            if latest_db_file:
                latest_file = latest_db_file.filename
                xls = pd.ExcelFile(os.path.join(UPLOAD_FOLDER, latest_file))
                # Always use account_id/team_id from the file record for name lookup
                file_account_id = latest_db_file.account_id
                file_team_id = latest_db_file.team_id
                account_obj = Account.query.get(file_account_id) if file_account_id else None
                team_obj = Team.query.get(file_team_id) if file_team_id else None
                account_name = account_obj.name if account_obj else None
                team_name = team_obj.name if team_obj else None
                all_sheets = xls.sheet_names
                # If both account and team names are present, filter by both
                if account_name and team_name:
                    filtered = [s for s in all_sheets if account_name in s and team_name in s]
                    app_names = filtered if filtered else all_sheets
                elif account_name:
                    filtered = [s for s in all_sheets if account_name in s]
                    app_names = filtered if filtered else all_sheets
                elif team_name:
                    filtered = [s for s in all_sheets if team_name in s]
                    app_names = filtered if filtered else all_sheets
                else:
                    app_names = all_sheets
            else:
                app_names = []
        # Account Admin: use user's account, filter by team if selected
        elif current_user.role == 'account_admin':
            file_query = file_query.filter_by(account_id=current_user.account_id)
            if team_id is not None:
                file_query = file_query.filter_by(team_id=team_id)
            latest_db_file = file_query.order_by(EscalationMatrixFile.upload_time.desc()).first()
            if not latest_db_file:
                latest_db_file = EscalationMatrixFile.query.filter_by(account_id=current_user.account_id).order_by(EscalationMatrixFile.upload_time.desc()).first()
            if latest_db_file:
                latest_file = latest_db_file.filename
                xls = pd.ExcelFile(os.path.join(UPLOAD_FOLDER, latest_file))
                file_team_id = latest_db_file.team_id
                team_obj = Team.query.get(file_team_id) if file_team_id else None
                team_name = team_obj.name if team_obj else None
                all_sheets = xls.sheet_names
                if team_name:
                    filtered = [s for s in all_sheets if team_name in s]
                    app_names = filtered if filtered else all_sheets
                else:
                    app_names = all_sheets
            else:
                app_names = []
        # Team Admin and Regular Users: use user's account/team
        else:
            # First try to find files for exact account/team match
            file_query = file_query.filter_by(account_id=current_user.account_id, team_id=current_user.team_id)
            latest_db_file = file_query.order_by(EscalationMatrixFile.upload_time.desc()).first()
            
            # If no exact match, try to find files for the user's account
            if not latest_db_file:
                latest_db_file = EscalationMatrixFile.query.filter_by(account_id=current_user.account_id).order_by(EscalationMatrixFile.upload_time.desc()).first()
            
            # If still no files found, try to find any files that might be accessible
            if not latest_db_file:
                latest_db_file = EscalationMatrixFile.query.order_by(EscalationMatrixFile.upload_time.desc()).first()
            
            if latest_db_file:
                latest_file = latest_db_file.filename
                xls = pd.ExcelFile(os.path.join(UPLOAD_FOLDER, latest_file))
                file_account_id = latest_db_file.account_id
                file_team_id = latest_db_file.team_id
                
                # Get account and team names for filtering
                account_obj = Account.query.get(current_user.account_id) if current_user.account_id else None
                team_obj = Team.query.get(current_user.team_id) if current_user.team_id else None
                account_name = account_obj.name if account_obj else None
                team_name = team_obj.name if team_obj else None
                
                all_sheets = xls.sheet_names
                
                # Filter sheets based on user's account/team
                if account_name and team_name:
                    # Try to find sheets with both account and team names
                    filtered = [s for s in all_sheets if account_name.lower() in s.lower() and team_name.lower() in s.lower()]
                    if not filtered:
                        # If no exact match, try account name only
                        filtered = [s for s in all_sheets if account_name.lower() in s.lower()]
                    if not filtered:
                        # If still no match, try team name only
                        filtered = [s for s in all_sheets if team_name.lower() in s.lower()]
                    app_names = filtered if filtered else all_sheets
                elif account_name:
                    filtered = [s for s in all_sheets if account_name.lower() in s.lower()]
                    app_names = filtered if filtered else all_sheets
                elif team_name:
                    filtered = [s for s in all_sheets if team_name.lower() in s.lower()]
                    app_names = filtered if filtered else all_sheets
                else:
                    app_names = all_sheets
            else:
                app_names = []
    if selected_app and selected_app in app_names:
        df = xls.parse(selected_app)
        matrix_data = df.where(pd.notnull(df), '').to_dict(orient='records')
    from models.models import Account, Team
    accounts = []
    teams = []
    account_id = None
    team_id = None
    selected_team_id = None
    if current_user.role == 'super_admin':
        accounts = Account.query.filter_by(is_active=True).all()
        account_id = request.args.get('account_id') or (session.get('selected_account_id') if hasattr(session, 'get') else None)
        teams = Team.query.filter_by(is_active=True)
        if account_id:
            teams = teams.filter_by(account_id=account_id)
        teams = teams.all()
        team_id = request.args.get('team_id')
        if not team_id:
            selected_team_id = None
        else:
            selected_team_id = team_id
    elif current_user.role == 'account_admin':
        account_id = current_user.account_id
        accounts = [Account.query.get(account_id)] if account_id else []
        teams = Team.query.filter_by(account_id=account_id, is_active=True).all()
        team_id = request.args.get('team_id') or (session.get('selected_team_id') if hasattr(session, 'get') else None)
        selected_team_id = team_id
    elif current_user.role == 'team_admin':
        account_id = current_user.account_id
        team_id = current_user.team_id
        accounts = [Account.query.get(account_id)] if account_id else []
        teams = [Team.query.get(team_id)] if team_id else []
        selected_team_id = team_id
    else:
        # Regular users: show their account/team info but no filtering controls
        account_id = current_user.account_id
        team_id = current_user.team_id
        accounts = [Account.query.get(account_id)] if account_id else []
        teams = [Team.query.get(team_id)] if team_id else []
        selected_team_id = team_id
    # Always show Application dropdown if app_names is available
    return render_template('escalation_matrix.html', app_names=app_names, matrix_data=matrix_data, selected_app=selected_app, accounts=accounts, teams=teams, selected_account_id=account_id, selected_team_id=selected_team_id)

