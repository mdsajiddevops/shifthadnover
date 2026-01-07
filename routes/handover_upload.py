"""
Handover Upload Route

This module handles the upload and processing of Excel files containing handover data.
"""

import os
import tempfile
from datetime import datetime
from flask import Blueprint, request, jsonify, send_file, current_app
from flask_login import login_required, current_user
from openpyxl import load_workbook
from models.models import db, User, Team, TeamMember

handover_upload_bp = Blueprint('handover_upload', __name__)


def get_cell_value(ws, row, col):
    """Safely get cell value, returning empty string for None."""
    value = ws.cell(row=row, column=col).value
    return str(value).strip() if value is not None else ""


def parse_uploaded_handover(file_path):
    """
    Parse the uploaded Excel file and extract handover data.
    
    Args:
        file_path: Path to the uploaded Excel file
        
    Returns:
        Dictionary containing parsed handover data
    """
    try:
        wb = load_workbook(file_path, data_only=True)
    except Exception as e:
        return {'error': f'Failed to read Excel file: {str(e)}'}
    
    result = {
        'basic_info': {},
        'open_incidents': [],
        'closed_incidents': [],
        'priority_incidents': [],
        'handover_incidents': [],
        'escalated_incidents': [],
        'change_info': [],
        'kb_updates': [],
        'key_points': [],
        'errors': [],
        'warnings': []
    }
    
    # Parse Basic Info sheet
    if 'Basic Info' in wb.sheetnames:
        ws = wb['Basic Info']
        basic_fields = {
            2: 'handover_date',
            3: 'current_shift',
            4: 'next_shift',
            5: 'current_engineers',
            6: 'next_engineers',
            7: 'additional_notes'
        }
        
        for row, field in basic_fields.items():
            value = get_cell_value(ws, row, 2)  # Column B
            result['basic_info'][field] = value
        
        # Validate required fields
        if not result['basic_info'].get('handover_date'):
            result['errors'].append('Handover Date is required in Basic Info sheet')
        if not result['basic_info'].get('current_shift'):
            result['errors'].append('Current Shift is required in Basic Info sheet')
        if not result['basic_info'].get('next_shift'):
            result['errors'].append('Next Shift is required in Basic Info sheet')
    else:
        result['errors'].append('Basic Info sheet not found in the uploaded file')
    
    # Parse Open Incidents sheet
    if 'Open Incidents' in wb.sheetnames:
        ws = wb['Open Incidents']
        for row in range(3, ws.max_row + 1):  # Start from row 3 (after header and example)
            app_name = get_cell_value(ws, row, 1)
            incident_id = get_cell_value(ws, row, 2)
            
            if app_name or incident_id:  # Only process if at least one field has data
                result['open_incidents'].append({
                    'app_name': app_name,
                    'incident_id': incident_id,
                    'priority': get_cell_value(ws, row, 3) or 'Medium',
                    'assigned_to': get_cell_value(ws, row, 4),
                    'description': get_cell_value(ws, row, 5)
                })
    
    # Parse Closed Incidents sheet
    if 'Closed Incidents' in wb.sheetnames:
        ws = wb['Closed Incidents']
        for row in range(3, ws.max_row + 1):
            app_name = get_cell_value(ws, row, 1)
            incident_id = get_cell_value(ws, row, 2)
            
            if app_name or incident_id:
                result['closed_incidents'].append({
                    'app_name': app_name,
                    'incident_id': incident_id,
                    'resolution': get_cell_value(ws, row, 3)
                })
    
    # Parse Priority Incidents sheet
    if 'Priority Incidents' in wb.sheetnames:
        ws = wb['Priority Incidents']
        for row in range(3, ws.max_row + 1):
            app_name = get_cell_value(ws, row, 1)
            incident_id = get_cell_value(ws, row, 2)
            
            if app_name or incident_id:
                result['priority_incidents'].append({
                    'app_name': app_name,
                    'incident_id': incident_id,
                    'priority_level': get_cell_value(ws, row, 3) or 'High',
                    'escalated_to': get_cell_value(ws, row, 4),
                    'impact_actions': get_cell_value(ws, row, 5)
                })
    
    # Parse Handover Incidents sheet
    if 'Handover Incidents' in wb.sheetnames:
        ws = wb['Handover Incidents']
        for row in range(3, ws.max_row + 1):
            app_name = get_cell_value(ws, row, 1)
            incident_id = get_cell_value(ws, row, 2)
            
            if app_name or incident_id:
                result['handover_incidents'].append({
                    'app_name': app_name,
                    'incident_id': incident_id,
                    'status': get_cell_value(ws, row, 3) or 'Monitoring',
                    'next_action_by': get_cell_value(ws, row, 4),
                    'notes': get_cell_value(ws, row, 5)
                })
    
    # Parse Escalated Incidents sheet
    if 'Escalated Incidents' in wb.sheetnames:
        ws = wb['Escalated Incidents']
        for row in range(3, ws.max_row + 1):
            app_name = get_cell_value(ws, row, 1)
            incident_id = get_cell_value(ws, row, 2)
            
            if app_name or incident_id:
                result['escalated_incidents'].append({
                    'app_name': app_name,
                    'incident_id': incident_id,
                    'escalated_to': get_cell_value(ws, row, 3),
                    'reason': get_cell_value(ws, row, 4),
                    'status_next_steps': get_cell_value(ws, row, 5)
                })
    
    # Parse Change Info sheet
    if 'Change Info' in wb.sheetnames:
        ws = wb['Change Info']
        for row in range(3, ws.max_row + 1):
            app_name = get_cell_value(ws, row, 1)
            change_number = get_cell_value(ws, row, 2)
            
            if app_name or change_number:
                datetime_value = get_cell_value(ws, row, 4)
                result['change_info'].append({
                    'app_name': app_name,
                    'change_number': change_number,
                    'description': get_cell_value(ws, row, 3),
                    'datetime': datetime_value,
                    'responsible_engineer': get_cell_value(ws, row, 5),
                    'status': get_cell_value(ws, row, 6) or 'New'
                })
    
    # Parse KB Updates sheet
    if 'KB Updates' in wb.sheetnames:
        ws = wb['KB Updates']
        for row in range(3, ws.max_row + 1):
            app_name = get_cell_value(ws, row, 1)
            kb_number = get_cell_value(ws, row, 2)
            
            if app_name or kb_number:
                result['kb_updates'].append({
                    'app_name': app_name,
                    'kb_number': kb_number,
                    'description': get_cell_value(ws, row, 3),
                    'responsible_person': get_cell_value(ws, row, 4),
                    'status': get_cell_value(ws, row, 5) or 'New'
                })
    
    # Parse Key Points sheet
    if 'Key Points' in wb.sheetnames:
        ws = wb['Key Points']
        for row in range(3, ws.max_row + 1):
            details = get_cell_value(ws, row, 1)
            
            if details:
                result['key_points'].append({
                    'description': details,
                    'assigned_to': get_cell_value(ws, row, 2),
                    'status': get_cell_value(ws, row, 3) or 'Open'
                })
    
    # Add summary
    result['summary'] = {
        'open_incidents_count': len(result['open_incidents']),
        'closed_incidents_count': len(result['closed_incidents']),
        'priority_incidents_count': len(result['priority_incidents']),
        'handover_incidents_count': len(result['handover_incidents']),
        'escalated_incidents_count': len(result['escalated_incidents']),
        'change_info_count': len(result['change_info']),
        'kb_updates_count': len(result['kb_updates']),
        'key_points_count': len(result['key_points']),
        'total_entries': sum([
            len(result['open_incidents']),
            len(result['closed_incidents']),
            len(result['priority_incidents']),
            len(result['handover_incidents']),
            len(result['escalated_incidents']),
            len(result['change_info']),
            len(result['kb_updates']),
            len(result['key_points'])
        ])
    }
    
    return result


@handover_upload_bp.route('/api/handover/download-template')
@login_required
def download_template():
    """Download the handover upload template."""
    from utils.handover_template_generator import generate_handover_template
    import io
    
    # Generate the template in memory
    wb = generate_handover_template()
    
    # Save to bytes buffer
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    
    return send_file(
        buffer,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'handover_template_{datetime.now().strftime("%Y%m%d")}.xlsx'
    )


@handover_upload_bp.route('/api/handover/upload', methods=['POST'])
@login_required
def upload_handover():
    """
    Upload and parse a handover Excel file.
    Returns the parsed data for preview before submission.
    """
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'}), 400
    
    if not file.filename.endswith(('.xlsx', '.xls')):
        return jsonify({'success': False, 'error': 'Invalid file format. Please upload an Excel file (.xlsx or .xls)'}), 400
    
    # Save to temporary file
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, f'handover_upload_{current_user.id}_{datetime.now().timestamp()}.xlsx')
    
    try:
        file.save(temp_path)
        
        # Parse the file
        parsed_data = parse_uploaded_handover(temp_path)
        
        # Check for errors
        if parsed_data.get('errors'):
            return jsonify({
                'success': False,
                'error': 'Validation errors found',
                'errors': parsed_data['errors'],
                'warnings': parsed_data.get('warnings', [])
            }), 400
        
        # Return parsed data for preview
        return jsonify({
            'success': True,
            'data': parsed_data,
            'message': f"Successfully parsed {parsed_data['summary']['total_entries']} entries from the uploaded file"
        })
        
    except Exception as e:
        current_app.logger.error(f"Error processing handover upload: {str(e)}")
        return jsonify({'success': False, 'error': f'Error processing file: {str(e)}'}), 500
    finally:
        # Clean up temp file
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass


@handover_upload_bp.route('/api/handover/validate-upload', methods=['POST'])
@login_required
def validate_upload():
    """
    Validate uploaded handover data against current team configuration.
    Checks if engineer names match existing team members, etc.
    """
    data = request.get_json()
    
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400
    
    team_id = data.get('team_id')
    if not team_id:
        return jsonify({'success': False, 'error': 'Team ID is required'}), 400
    
    # Get team members
    team_members = TeamMember.query.filter_by(team_id=team_id, is_active=True).all()
    member_names = {m.name.lower(): m.id for m in team_members}
    
    validation_result = {
        'valid': True,
        'warnings': [],
        'member_mappings': {}
    }
    
    # Validate engineer names in uploaded data
    uploaded_data = data.get('uploaded_data', {})
    
    # Check assigned engineers in incidents
    for inc_type in ['open_incidents', 'handover_incidents']:
        for i, inc in enumerate(uploaded_data.get(inc_type, [])):
            assigned = inc.get('assigned_to') or inc.get('next_action_by', '')
            if assigned and assigned.lower() not in member_names:
                validation_result['warnings'].append(
                    f"{inc_type.replace('_', ' ').title()} row {i+1}: '{assigned}' not found in team members"
                )
    
    # Check responsible engineers in change info and KB updates
    for change in uploaded_data.get('change_info', []):
        engineer = change.get('responsible_engineer', '')
        if engineer and engineer.lower() not in member_names:
            validation_result['warnings'].append(
                f"Change Info: '{engineer}' not found in team members"
            )
    
    for kb in uploaded_data.get('kb_updates', []):
        person = kb.get('responsible_person', '')
        if person and person.lower() not in member_names:
            validation_result['warnings'].append(
                f"KB Update: '{person}' not found in team members"
            )
    
    for kp in uploaded_data.get('key_points', []):
        assigned = kp.get('assigned_to', '')
        if assigned and assigned.lower() not in member_names:
            validation_result['warnings'].append(
                f"Key Point: '{assigned}' not found in team members"
            )
    
    return jsonify({
        'success': True,
        'validation': validation_result,
        'team_members': [{'id': m.id, 'name': m.name} for m in team_members]
    })

