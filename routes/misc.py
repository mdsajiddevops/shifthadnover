from flask import Blueprint, render_template, request, jsonify, session, flash, redirect, url_for
from services.audit_service import log_action
from services.servicenow_service import servicenow_service
from models.models import User, TeamMember, db
from models.app_config import AppConfig
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from functools import wraps

# Force reload timestamp: 2025-10-11 11:47:00 - ULTRA MODERN TEMPLATE ACTIVATED
misc_bp = Blueprint('misc', __name__)

def feature_required(feature_name):
    """Decorator to check if a feature is enabled"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not AppConfig.is_enabled(feature_name):
                flash('This feature is currently disabled.', 'warning')
                return redirect(url_for('dashboard.dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def admin_required(f):
    """Decorator to check if user has admin privileges (super_admin, account_admin, or team_admin)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in ['super_admin', 'account_admin', 'team_admin']:
            flash('Access denied. Administrator privileges required.', 'error')
            return redirect(url_for('dashboard.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@misc_bp.route('/servicenow')
@login_required
@admin_required
@feature_required('feature_servicenow_integration')
def servicenow():
    """ServiceNow configuration and testing page"""
    log_action('View ServiceNow Tab', f'Path: {request.path}')
    
    # Check if ServiceNow is properly configured
    try:
        from models.servicenow_config import ServiceNowConfig
        servicenow_configured = ServiceNowConfig.is_configured()
        
        if not servicenow_configured:
            return render_template('servicenow/not_configured.html', 
                                 page_title='ServiceNow Integration',
                                 current_user=current_user,
                                 tab='servicenow')
    except Exception as e:
        servicenow_configured = False
    
    return render_template('servicenow/dashboard.html', 
                         page_title='ServiceNow Integration',
                         current_user=current_user,
                         tab='servicenow',
                         datetime=datetime,
                         servicenow_configured=servicenow_configured)

@misc_bp.route('/change-management')
@login_required
def change_management():
    log_action('View Change Management Tab', f'Path: {request.path}')
    
    # IMMEDIATE FIX: Return server-side rendered data instead of JavaScript version
    try:
        # Initialize ServiceNow service properly
        from flask import current_app
        servicenow_service.initialize(current_app)
        
        # Check if ServiceNow is enabled and configured
        if not servicenow_service.is_enabled_and_configured():
            return render_template('change_management_ultra_modern_clean.html',
                                 title='Change Management',
                                 current_user=current_user,
                                 tab='change_management',
                                 servicenow_available=False,
                                 error='ServiceNow integration is not enabled or configured. Please contact your administrator.',
                                 change_requests=[],
                                 change_tasks=[],
                                 current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
        # Get assignment groups
        assignment_groups = servicenow_service.get_configured_assignment_groups()
        print(f"DEBUG: Assignment groups configured: {assignment_groups}")
        
        if not assignment_groups:
            print("DEBUG: No assignment groups configured")
            return render_template('change_management_ultra_modern_clean.html', 
                                 title='Change Management',
                                 error='No assignment groups configured',
                                 change_requests=[],
                                 change_tasks=[],
                                 current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))        
        
        # Fetch change data directly
        print(f"DEBUG: About to fetch change data for assignment groups: {assignment_groups}")
        change_data = servicenow_service.get_change_requests_for_assignment_group(
            assignment_groups=assignment_groups
        )
        print(f"DEBUG: Change data returned: {change_data}")
        
        # Log success for debugging
        cr_count = len(change_data.get('change_requests', []))
        ct_count = len(change_data.get('change_tasks', []))
        print(f"DEBUG: Final counts - CRs: {cr_count}, CTs: {ct_count}")
        log_action('Change Management Data Loaded Successfully', 
                  f'CRs: {cr_count}, CTs: {ct_count}, Assignment Groups: {assignment_groups}')

        # Force template reload and cache busting
        from flask import make_response
        response = make_response(render_template('change_management_ultra_modern_clean.html',
                             title='Change Management',
                             change_requests=change_data.get('change_requests', []),
                             change_tasks=change_data.get('change_tasks', []),
                             current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                             error=None))
        
        # Add cache-busting headers
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
        
    except Exception as e:
        error_msg = f'Failed to fetch change data: {str(e)}'
        print(f"DEBUG: Exception in change_management: {error_msg}")
        import traceback
        traceback.print_exc()
        log_action('Error in change_management', f'Error: {error_msg}')
        return render_template('change_management_ultra_modern_clean.html',
                             title='Change Management',
                             error=error_msg,
                             change_requests=[],
                             change_tasks=[],
                             current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

@misc_bp.route('/change-management-modern')
@login_required
def change_management_modern():
    log_action('View Change Management Modern Tab', f'Path: {request.path}')
    
    # Use modern server-side rendered template with enhanced styling
    try:
        # Get assignment groups
        assignment_groups = servicenow_service.get_configured_assignment_groups()
        
        if not assignment_groups:
            return render_template('change_management_modern_v2.html', 
                                 title='Change Management',
                                 error='No assignment groups configured',
                                 change_requests=[],
                                 change_tasks=[],
                                 current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
        # Fetch change data directly
        print(f"DEBUG: About to fetch change data for assignment groups: {assignment_groups}")
        change_data = servicenow_service.get_change_requests_for_assignment_group(
            assignment_groups=assignment_groups
        )
        print(f"DEBUG: Change data returned: {change_data}")
        
        # Log success for debugging
        cr_count = len(change_data.get('change_requests', []))
        ct_count = len(change_data.get('change_tasks', []))
        print(f"DEBUG: Final counts - CRs: {cr_count}, CTs: {ct_count}")
        log_action('Change Management Modern Data Loaded Successfully', 
                  f'CRs: {cr_count}, CTs: {ct_count}, Assignment Groups: {assignment_groups}')

        # Force template reload and cache busting
        from flask import make_response
        response = make_response(render_template('change_management_modern_v2.html',
                             title='Change Management',
                             change_requests=change_data.get('change_requests', []),
                             change_tasks=change_data.get('change_tasks', []),
                             current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                             error=None))
        
        # Add cache-busting headers
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
        
    except Exception as e:
        error_msg = f'Failed to fetch change data: {str(e)}'
        log_action('Error in change_management_modern', f'Error: {error_msg}')
        return render_template('change_management_modern_v2.html',
                             title='Change Management',
                             error=error_msg,
                             change_requests=[],
                             change_tasks=[],
                             current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

@misc_bp.route('/change-management-fixed')
@login_required  
def change_management_fixed():
    log_action('View Change Management Fixed Tab', f'Path: {request.path}')
    return render_template('change_management_fixed.html', title='Change Management - Fixed')

@misc_bp.route('/test-js')
@login_required
def test_js():
    return render_template('test_js.html', title='JavaScript Test')

@misc_bp.route('/api/get_change_requests')
@login_required
def get_change_requests():
    """API endpoint to fetch change requests and tasks for assignment groups"""
    try:
        # Get the configured assignment groups from ServiceNow service
        assignment_groups = servicenow_service.get_configured_assignment_groups()
        
        if not assignment_groups:
            return jsonify({
                'error': 'No assignment groups configured in ServiceNow settings',
                'change_requests': [],
                'change_tasks': []
            })
        
        # Fetch change requests and tasks for assignment groups
        change_data = servicenow_service.get_change_requests_for_assignment_group(
            assignment_groups=assignment_groups
        )
        
        return jsonify(change_data)
        
    except Exception as e:
        log_action('Error in get_change_requests', f'Error: {str(e)}')
        return jsonify({
            'error': f'Failed to fetch change requests: {str(e)}',
            'change_requests': [],
            'change_tasks': []
        }), 500

@misc_bp.route('/problem-tickets')
def problem_tickets():
    log_action('View Problem Tickets Tab', f'Path: {request.path}')
    return render_template('coming_soon.html', title='Problem Tickets')

@misc_bp.route('/kb-details')
def kb_details():
    log_action('View KB Details Tab', f'Path: {request.path}')
    return render_template('coming_soon.html', title='KB Details')


@misc_bp.route('/postmortem-details')
def postmortem_details():
    log_action('View Postmortem Details Tab', f'Path: {request.path}')
    return render_template('coming_soon.html', title='Postmortem Details')

@misc_bp.route('/change-management-js')
@login_required
def change_management_js():
    """JavaScript version of Change Management (for testing)"""
    log_action('View Change Management JS Version', f'Path: {request.path}')
    from flask import make_response
    response = make_response(render_template('change_management_dashboard.html', title='Change Management - JS Version'))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@misc_bp.route('/change-management-server')
@login_required
def change_management_server():
    """Change Management Server-Side Rendered"""
    log_action('View Change Management Server Side', f'Path: {request.path}')
    
    try:
        # Get assignment groups
        assignment_groups = servicenow_service.get_configured_assignment_groups()
        
        if not assignment_groups:
            return render_template('change_management_server.html', 
                                 title='Change Management - Server Side',
                                 error='No assignment groups configured',
                                 change_requests=[],
                                 change_tasks=[],
                                 current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
        # Fetch change data
        change_data = servicenow_service.get_change_requests_for_assignment_group(
            assignment_groups=assignment_groups
        )
        
        return render_template('change_management_server.html',
                             title='Change Management - Server Side',
                             change_requests=change_data.get('change_requests', []),
                             change_tasks=change_data.get('change_tasks', []),
                             current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                             error=None)
        
    except Exception as e:
        log_action('Error in change_management_server', f'Error: {str(e)}')
        return render_template('change_management_server.html',
                             title='Change Management - Server Side',
                             error=f'Failed to fetch change data: {str(e)}',
                             change_requests=[],
                             change_tasks=[],
                             current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

@misc_bp.route('/change-management-minimal')
@login_required
def change_management_minimal():
    log_action('View Change Management Minimal Test', f'Path: {request.path}')
    from flask import make_response
    response = make_response(render_template('change_management_minimal.html', title='Change Management - Minimal'))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@misc_bp.route('/change-management-debug')
@login_required
def change_management_debug():
    """Debug route to show raw ServiceNow data"""
    log_action('View Change Management Debug', f'Path: {request.path}')
    
    try:
        # Get all change requests with no filtering
        cr_url = f"{servicenow_service.instance_url}/api/now/table/change_request"
        cr_params = {
            'sysparm_limit': '50',
            'sysparm_display_value': 'true',
            'sysparm_fields': 'sys_id,number,assignment_group,short_description,state'
        }
        
        cr_response = servicenow_service.session.get(cr_url, params=cr_params, timeout=servicenow_service.timeout)
        all_change_requests = cr_response.json().get('result', []) if cr_response.status_code == 200 else []
        
        # Get all change tasks with no filtering
        ct_url = f"{servicenow_service.instance_url}/api/now/table/change_task"
        ct_params = {
            'sysparm_limit': '50', 
            'sysparm_display_value': 'true',
            'sysparm_fields': 'sys_id,number,assignment_group,short_description,state'
        }
        
        ct_response = servicenow_service.session.get(ct_url, params=ct_params, timeout=servicenow_service.timeout)
        all_change_tasks = ct_response.json().get('result', []) if ct_response.status_code == 200 else []
        
        # Create debug info
        debug_info = {
            'total_change_requests': len(all_change_requests),
            'total_change_tasks': len(all_change_tasks),
            'sample_change_requests': all_change_requests[:10],
            'sample_change_tasks': all_change_tasks[:10],
            'assignment_groups_found': set(),
            'numbers_found': []
        }
        
        # Extract assignment groups and numbers
        for cr in all_change_requests:
            if cr.get('assignment_group'):
                debug_info['assignment_groups_found'].add(str(cr['assignment_group']))
            if cr.get('number'):
                debug_info['numbers_found'].append(cr['number'])
                
        for ct in all_change_tasks:
            if ct.get('assignment_group'):
                debug_info['assignment_groups_found'].add(str(ct['assignment_group']))
            if ct.get('number'):
                debug_info['numbers_found'].append(ct['number'])
        
        debug_info['assignment_groups_found'] = list(debug_info['assignment_groups_found'])
        
        return jsonify(debug_info)
        
    except Exception as e:
        return jsonify({'error': str(e)})

@misc_bp.route('/change-management-dashboard')
@login_required
def change_management_dashboard():
    log_action('View Change Management Dashboard', f'Path: {request.path}')
    return render_template('change_management_dashboard.html', title='Change Management Dashboard')

@misc_bp.route('/change-management-new')
@login_required
def change_management_new():
    """NEW Ultra Modern Change Management Dashboard - HORIZONTAL LAYOUT - ENHANCED TABLES - MODERNIZED VERSION"""
    log_action('View Change Management NEW', f'Path: {request.path}')
    
    try:
        # Get assignment groups
        assignment_groups = servicenow_service.get_configured_assignment_groups()
        
        if not assignment_groups:
            return render_template('change_management_ultra_modern_clean.html', 
                                 title='Change Management - Ultra Modern',
                                 error='No assignment groups configured',
                                 change_requests=[],
                                 change_tasks=[],
                                 current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
        # Handle pagination
        page = request.args.get('page', 1, type=int)
        per_page = 10  # Changed back to 10 records per page
        
        # Extract simplified filter parameters from request
        filters = {}
        
        # Only keep the 4 essential filters
        if request.args.get('state'):
            filters['state'] = request.args.get('state')
        
        if request.args.get('assignment_group_filter'):
            filters['assignment_group_filter'] = request.args.get('assignment_group_filter')
        
        if request.args.get('start_date'):
            filters['start_date'] = request.args.get('start_date')
        
        if request.args.get('end_date'):
            filters['end_date'] = request.args.get('end_date')
        
        # Fetch change data directly with filters and pagination
        change_data = servicenow_service.get_change_requests_for_assignment_group(
            assignment_groups=assignment_groups,
            filters=filters if filters else None,
            page=page,
            per_page=per_page
        )
        
        # Import time for cache busting
        import time
        timestamp = str(int(time.time()))
        
        # Process pagination data
        pagination = change_data.get('pagination', {})
        if pagination.get('total_pages', 0) > 1:
            # Create page range for pagination display
            current_page = pagination.get('current_page', 1)
            total_pages = pagination.get('total_pages', 1)
            
            # Show up to 5 page numbers around current page
            start_page = max(1, current_page - 2)
            end_page = min(total_pages, current_page + 2)
            
            page_range = []
            if start_page > 1:
                page_range.append(1)
                if start_page > 2:
                    page_range.append('...')
            
            for page_num in range(start_page, end_page + 1):
                page_range.append(page_num)
            
            if end_page < total_pages:
                if end_page < total_pages - 1:
                    page_range.append('...')
                page_range.append(total_pages)
            
            pagination['page_range'] = page_range
            pagination['start_record'] = (current_page - 1) * per_page + 1
            pagination['end_record'] = min(current_page * per_page, pagination.get('total', 0))
        
        # Force template reload and cache busting
        from flask import make_response
        response = make_response(render_template('change_management_ultra_modern_clean.html',
                             title='Change Management - Ultra Modern',
                             change_requests=change_data.get('change_requests', []),
                             change_tasks=change_data.get('change_tasks', []),
                             pagination=pagination,
                             current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                             timestamp=timestamp,
                             error=None))
        
        # Add strong cache-busting headers
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        response.headers['Last-Modified'] = datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT')
        return response
        
    except Exception as e:
        error_msg = f'Failed to fetch change data: {str(e)}'
        log_action('Error in change_management_new', f'Error: {error_msg}')
        return render_template('change_management_ultra_modern_clean.html',
                             title='Change Management - Ultra Modern',
                             error=error_msg,
                             change_requests=[],
                             change_tasks=[],
                             current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))


@misc_bp.route('/api/servicenow/test-connection', methods=['POST'])
@login_required
@admin_required
@feature_required('feature_servicenow_integration')
def test_servicenow_connection():
    """Test ServiceNow connection endpoint"""
    try:
        # Initialize ServiceNow service
        from flask import current_app
        servicenow_service.initialize(current_app)
        
        # Check if ServiceNow is enabled and configured
        if not servicenow_service.is_enabled_and_configured():
            return jsonify({
                'success': False,
                'message': 'ServiceNow integration is not enabled or properly configured'
            }), 400
        
        # Test the connection
        result = servicenow_service.test_connection()
        
        if result.get('success', False):
            log_action('ServiceNow Connection Test', 'Success')
            return jsonify({
                'success': True,
                'message': 'Connection successful',
                'details': result
            })
        else:
            log_action('ServiceNow Connection Test', f'Failed: {result.get("error", "Unknown error")}')
            return jsonify({
                'success': False,
                'message': result.get('error', 'Connection failed'),
                'details': result
            }), 400
            
    except Exception as e:
        error_msg = f'Error testing ServiceNow connection: {str(e)}'
        log_action('ServiceNow Connection Test Error', error_msg)
        return jsonify({
            'success': False,
            'message': error_msg,
            'details': None
        }), 500

@misc_bp.route('/servicenow/fetch-shift-incidents', methods=['GET'])
@login_required
@admin_required
@feature_required('feature_servicenow_integration')
def fetch_shift_incidents():
    """Fetch ServiceNow incidents for selected shift period"""
    try:
        # Get parameters from request
        shift_date = request.args.get('shift_date')
        shift_type = request.args.get('shift_type', 'day')
        refresh = request.args.get('refresh', 'false').lower() == 'true'
        
        if not shift_date:
            return jsonify({
                'success': False,
                'error': 'Shift date is required'
            }), 400
        
        # Initialize ServiceNow service
        from flask import current_app
        servicenow_service.initialize(current_app)
        
        # Parse shift date
        from datetime import datetime, time, timedelta
        try:
            parsed_date = datetime.strptime(shift_date, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Invalid date format. Use YYYY-MM-DD'
            }), 400
        
        # Convert shift type to datetime range
        shift_times = {
            'day': {'start': time(6, 0), 'end': time(14, 0)},      # 6 AM - 2 PM
            'evening': {'start': time(14, 0), 'end': time(22, 0)}, # 2 PM - 10 PM  
            'night': {'start': time(22, 0), 'end': time(6, 0)}     # 10 PM - 6 AM (next day)
        }
        
        if shift_type not in shift_times:
            shift_type = 'day'  # Default to day shift
            
        shift_time_config = shift_times[shift_type]
        
        # Create datetime objects for shift start and end
        shift_start = datetime.combine(parsed_date, shift_time_config['start'])
        
        if shift_type == 'night':
            # Night shift goes to next day
            shift_end = datetime.combine(parsed_date + timedelta(days=1), shift_time_config['end'])
        else:
            shift_end = datetime.combine(parsed_date, shift_time_config['end'])
        
        # Get assignment groups
        assignment_groups = servicenow_service.get_configured_assignment_groups()
        if not assignment_groups:
            return jsonify({
                'success': False,
                'error': 'No assignment groups configured'
            }), 400
        
        # Fetch incidents for the shift
        result = servicenow_service.get_shift_incidents(
            assignment_groups=assignment_groups,
            shift_start=shift_start,
            shift_end=shift_end
        )
        
        if result.get('success', False):
            # Get incidents from result
            open_incidents = result.get('open_incidents', [])
            closed_incidents = result.get('closed_incidents', [])
            total_incidents = result.get('total_incidents', [])
            
            summary = {
                'total_count': len(total_incidents),
                'open_count': len(open_incidents),
                'closed_count': len(closed_incidents),
                'shift_date': shift_date,
                'shift_type': shift_type,
                'shift_period': f"{shift_start.strftime('%Y-%m-%d %H:%M')} - {shift_end.strftime('%Y-%m-%d %H:%M')}"
            }
            
            log_action('Fetch ServiceNow Incidents', f'Success: {len(total_incidents)} incidents for {shift_date} {shift_type}')
            
            return jsonify({
                'success': True,
                'open_incidents': open_incidents,
                'closed_incidents': closed_incidents,
                'summary': summary
            })
        else:
            error_msg = result.get('error', 'Failed to fetch incidents')
            log_action('Fetch ServiceNow Incidents Error', error_msg)
            return jsonify({
                'success': False,
                'error': error_msg
            }), 500
            
    except Exception as e:
        error_msg = f'Error fetching ServiceNow incidents: {str(e)}'
        log_action('Fetch ServiceNow Incidents Error', error_msg)
        return jsonify({
            'success': False,
            'error': error_msg
        }), 500

