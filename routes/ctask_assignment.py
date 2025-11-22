"""
CTask Assignment Routes
Routes for automatic assignment of change tasks to engineers
"""
from flask import Blueprint, request, jsonify, render_template, flash, redirect, url_for, abort
from flask_login import login_required, current_user
from services.ctask_assignment_service import CTaskAssignmentService
from services.audit_service import log_action
from services.console_service import get_console_output, clear_console
from models.app_config import AppConfig
from datetime import datetime, date, timedelta
import logging
from functools import wraps

ctask_assignment_bp = Blueprint('ctask_assignment', __name__)
logger = logging.getLogger(__name__)

# Global instance to maintain state across requests
ctask_assignment_service = CTaskAssignmentService()

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

@ctask_assignment_bp.route('/ctask-assignment')
@login_required
@admin_required
@feature_required('feature_ctask_assignment')
def ctask_assignment_dashboard():
    """CTask Assignment Dashboard"""
    try:
        log_action('View CTask Assignment Dashboard', f'User: {current_user.username}')
        
        # Get shift schedule for next 7 days
        today = date.today()
        end_date = today + timedelta(days=7)
        shift_schedule = ctask_assignment_service.get_shift_schedule(today, end_date)
        
        return render_template('ctask_assignment_dashboard.html',
                             title='CTask Assignment',
                             shift_schedule=shift_schedule,
                             today=today)
        
    except Exception as e:
        logger.error(f"Error loading CTask assignment dashboard: {str(e)}")
        flash(f'Error loading dashboard: {str(e)}', 'error')
        return redirect(url_for('dashboard.dashboard'))

@ctask_assignment_bp.route('/assign-ctask', methods=['POST'])
@login_required
@admin_required
def assign_ctask():
    """Assign a specific CTask to engineer based on planned time"""
    try:
        data = request.get_json()
        
        ctask_number = data.get('ctask_number')
        planned_date = data.get('planned_date')  # YYYY-MM-DD
        planned_time = data.get('planned_time')  # HH:MM:SS
        
        if not all([ctask_number, planned_date, planned_time]):
            return jsonify({
                'success': False,
                'message': 'Missing required fields: ctask_number, planned_date, planned_time'
            }), 400
        
        log_action('Manual CTask Assignment Request', 
                  f'CTask: {ctask_number}, Date: {planned_date}, Time: {planned_time}')
        
        assignment_service = CTaskAssignmentService()
        result = assignment_service.auto_assign_ctask(ctask_number, planned_date, planned_time)
        
        if result['success']:
            log_action('CTask Assignment Success', 
                      f'CTask: {ctask_number} assigned to {result["assigned_to"]}')
        else:
            log_action('CTask Assignment Failed', 
                      f'CTask: {ctask_number}, Reason: {result["message"]}')
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error assigning CTask: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error assigning CTask: {str(e)}'
        }), 500

@ctask_assignment_bp.route('/find-engineer', methods=['POST'])
@login_required
@admin_required
def find_engineer():
    """Find engineer on duty for specific date and time"""
    try:
        data = request.get_json()
        
        planned_date_str = data.get('planned_date')  # YYYY-MM-DD
        planned_time_str = data.get('planned_time')  # HH:MM:SS
        
        if not all([planned_date_str, planned_time_str]):
            return jsonify({
                'success': False,
                'message': 'Missing required fields: planned_date, planned_time'
            }), 400
        
        # Parse date and time
        planned_date = datetime.strptime(planned_date_str, '%Y-%m-%d').date()
        planned_time = datetime.strptime(planned_time_str, '%H:%M:%S').time()
        
        engineer = ctask_assignment_service.get_engineer_on_duty(planned_date, planned_time)
        
        if engineer:
            return jsonify({
                'success': True,
                'engineer': engineer,
                'message': f'Engineer {engineer["name"]} is on duty during this time'
            })
        else:
            return jsonify({
                'success': False,
                'message': f'No engineer found on duty for {planned_date_str} at {planned_time_str}'
            })
        
    except Exception as e:
        logger.error(f"Error finding engineer: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error finding engineer: {str(e)}'
        }), 500

@ctask_assignment_bp.route('/process-pending-ctasks', methods=['POST'])
@login_required
@admin_required
def process_pending_ctasks():
    """Process all pending CTasks for auto-assignment"""
    try:
        log_action('Process Pending CTasks', f'User: {current_user.username}')
        
        results = ctask_assignment_service.process_pending_ctasks()
        
        successful_assignments = [r for r in results if r['success']]
        failed_assignments = [r for r in results if not r['success']]
        
        log_action('Pending CTasks Processing Complete', 
                  f'Successful: {len(successful_assignments)}, Failed: {len(failed_assignments)}')
        
        return jsonify({
            'success': True,
            'message': f'Processed {len(results)} CTasks',
            'successful_assignments': len(successful_assignments),
            'failed_assignments': len(failed_assignments),
            'results': results
        })
        
    except Exception as e:
        logger.error(f"Error processing pending CTasks: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error processing pending CTasks: {str(e)}'
        }), 500

@ctask_assignment_bp.route('/shift-schedule')
@login_required
def get_shift_schedule():
    """Get shift schedule for date range"""
    try:
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        
        if start_date_str and end_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        else:
            # Default to next 7 days
            start_date = date.today()
            end_date = start_date + timedelta(days=7)
        
        shift_schedule = ctask_assignment_service.get_shift_schedule(start_date, end_date)
        
        return jsonify({
            'success': True,
            'shift_schedule': shift_schedule,
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d')
        })
        
    except Exception as e:
        logger.error(f"Error getting shift schedule: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error getting shift schedule: {str(e)}'
        }), 500

@ctask_assignment_bp.route('/scheduler-status')
@login_required
def scheduler_status():
    """Get CTask scheduler status"""
    try:
        # Get status from the real background scheduler
        from services.ctask_scheduler import get_scheduler_status
        real_status = get_scheduler_status()
        
        # Get status from assignment service (for UI state consistency)
        service_status = ctask_assignment_service.get_scheduler_status()
        
        # Combine both statuses - use real scheduler's running state
        combined_status = service_status.copy()
        combined_status['status'] = 'Running' if real_status.get('running', False) else 'Stopped'
        
        # Update last check time from real scheduler if available
        if real_status.get('last_check'):
            combined_status['last_check'] = real_status['last_check']
        if real_status.get('next_check'):
            combined_status['next_check'] = real_status['next_check']
            
        return jsonify({
            'success': True,
            'status': combined_status
        })
    except Exception as e:
        logger.error(f"Error getting scheduler status: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error getting status: {str(e)}'
        }), 500

@ctask_assignment_bp.route('/force-scheduler-check', methods=['POST'])
@login_required
def force_scheduler_check():
    """Force immediate scheduler check"""
    try:
        log_action('Force CTask Check', f'User: {current_user.username}')
        
        from services.ctask_scheduler import force_scheduler_check
        results = force_scheduler_check()
        
        return jsonify({
            'success': True,
            'message': 'Forced check completed',
            'results': results
        })
        
    except Exception as e:
        logger.error(f"Error forcing scheduler check: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error forcing check: {str(e)}'
        }), 500

@ctask_assignment_bp.route('/test-ctask/<ctask_number>')
@login_required
def test_ctask_assignment(ctask_number):
    """Test assignment for a specific CTask with detailed output"""
    try:
        log_action('Test CTask Assignment', f'Testing {ctask_number} by {current_user.username}')
        
        # Example: assume today at current time
        from datetime import datetime, date
        planned_date = date.today().strftime('%Y-%m-%d')
        planned_time = datetime.now().strftime('%H:%M:%S')
        
        assignment_service = CTaskAssignmentService()
        
        # Clear console for this test
        from services.console_service import clear_console
        clear_console()
        
        # Run assignment with detailed logging
        result = assignment_service.auto_assign_ctask(ctask_number, planned_date, planned_time)
        
        # Get console output for chat display
        from services.console_service import get_console_output
        console_log = get_console_output(20)
        
        return jsonify({
            'success': True,
            'ctask_number': ctask_number,
            'planned_date': planned_date,
            'planned_time': planned_time,
            'assignment_result': result,
            'detailed_log': console_log,
            'chat_summary': f"""
🎯 CTASK ASSIGNMENT TEST RESULTS:

📋 Task: {ctask_number}
📅 Date: {planned_date}
🕒 Time: {planned_time}

{console_log}

📊 Final Result: {'✅ SUCCESS' if result.get('success') else '❌ FAILED'}
💬 Message: {result.get('message', 'No message')}
"""
        })
        
    except Exception as e:
        logger.error(f"Error testing CTask assignment: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error testing assignment: {str(e)}',
            'chat_summary': f"""
❌ ERROR TESTING {ctask_number}:

🚨 Error: {str(e)}

Please check the application logs for more details.
"""
        }), 500

@ctask_assignment_bp.route('/demo-assignment/<ctask_number>')
@login_required
def demo_ctask_assignment(ctask_number):
    """Demo assignment showing complete flow with detailed chat output"""
    try:
        log_action('Demo CTask Assignment', f'Demo for {ctask_number} by {current_user.username}')
        
        # Use your specific example
        planned_date_str = '2025-10-13'
        planned_time_str = '06:30:00'
        
        assignment_service = CTaskAssignmentService()
        
        # Clear console for clean demo
        from services.console_service import clear_console, console
        clear_console()
        
        # Parse date and time
        from datetime import datetime
        planned_date = datetime.strptime(planned_date_str, '%Y-%m-%d').date()
        planned_time = datetime.strptime(planned_time_str, '%H:%M:%S').time()
        
        console.info(f"🎯 DEMO: Starting assignment for {ctask_number}", {
            'scenario': 'CHG0040003 example',
            'planned_date': planned_date_str,
            'planned_time': planned_time_str
        })
        
        # Find engineer on duty
        engineer = assignment_service.get_engineer_on_duty(planned_date, planned_time)
        
        if engineer:
            console.success(f"✅ DEMO: Would assign to {engineer['name']}")
            # Simulate successful assignment
            demo_result = {
                'success': True,
                'message': f'Successfully assigned {ctask_number} to {engineer["name"]}',
                'ctask_number': ctask_number,
                'assigned_to': engineer['name'],
                'assigned_email': engineer['email'],
                'shift_code': engineer['shift_code'],
                'planned_date': planned_date_str,
                'planned_time': planned_time_str,
                'shift_detection': f"Time {planned_time_str} → {engineer['shift_code']} Shift",
                'assignment_logic': 'Selected first engineer alphabetically from available engineers on shift'
            }
        else:
            console.error(f"❌ DEMO: No engineer found on duty")
            demo_result = {
                'success': False,
                'message': f'No engineer found on duty for {planned_date_str} at {planned_time_str}',
                'ctask_number': ctask_number
            }
        
        # Get console output
        from services.console_service import get_console_output
        console_log = get_console_output(20)
        
        return jsonify({
            'success': True,
            'demo_mode': True,
            'ctask_number': ctask_number,
            'scenario': 'CHG0040003 example - 2025-10-13 at 06:30:00',
            'assignment_result': demo_result,
            'detailed_log': console_log,
            'chat_summary': f"""
🎯 DEMO: CTask Assignment for CHG0040003

📋 Scenario: Your example - CHG0040003 on 2025-10-13 at 06:30:00
📅 This demonstrates the exact logic for your requirement

{console_log}

📊 Result: {'✅ SUCCESS' if demo_result.get('success') else '❌ FAILED'}
👤 Engineer: {demo_result.get('assigned_to', 'None found')}
🔄 Logic: {demo_result.get('assignment_logic', 'N/A')}

This shows exactly how CTASK0010003 and future CTasks will be automatically assigned!
"""
        })
        
    except Exception as e:
        logger.error(f"Error in demo assignment: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error in demo: {str(e)}',
            'chat_summary': f"""
❌ DEMO ERROR for {ctask_number}:

🚨 Error: {str(e)}

Please check the system configuration and try again.
"""
        }), 500

@ctask_assignment_bp.route('/console-output')
@login_required 
def get_console():
    """Get console output for display"""
    try:
        count = request.args.get('count', 50, type=int)
        output = get_console_output(count)
        
        return jsonify({
            'success': True,
            'console_output': output,
            'message_count': count
        })
        
    except Exception as e:
        logger.error(f"Error getting console output: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error getting console: {str(e)}'
        }), 500

@ctask_assignment_bp.route('/assign-ctask-now/<ctask_number>', methods=['POST'])
@login_required
def assign_ctask_immediately(ctask_number):
    """
    Immediately assign a CTask by fetching its details from ServiceNow
    This is useful for manual assignment of CTasks
    """
    try:
        log_action('Manual CTask Assignment Request', 
                  f'CTask: {ctask_number} by {current_user.username}')
        
        # Fetch CTask details from ServiceNow
        assignment_service = CTaskAssignmentService()
        servicenow = assignment_service.servicenow
        
        if not servicenow.is_configured():
            return jsonify({
                'success': False,
                'message': 'ServiceNow not configured - cannot fetch CTask details'
            }), 500
        
        # Get CTask details
        from urllib.parse import urljoin
        
        # Fetch the specific CTask
        ctask_url = urljoin(servicenow.instance_url, '/api/now/table/change_task')
        ctask_params = {
            'sysparm_query': f'number={ctask_number}',
            'sysparm_fields': 'sys_id,number,short_description,planned_start_date,planned_end_date,work_start,work_end,assignment_group',
            'sysparm_display_value': 'true'
        }
        
        ctask_response = servicenow.session.get(ctask_url, params=ctask_params, timeout=servicenow.timeout)
        ctask_response.raise_for_status()
        ctask_data = ctask_response.json()
        
        if not ctask_data.get('result'):
            return jsonify({
                'success': False,
                'message': f'CTask {ctask_number} not found in ServiceNow'
            }), 404
        
        ctask = ctask_data['result'][0]
        
        # Extract planned date and time
        planned_date_str, planned_time_str = assignment_service._extract_planned_datetime(ctask)
        
        if not planned_date_str or not planned_time_str:
            return jsonify({
                'success': False,
                'message': f'No planned date/time found for {ctask_number}',
                'ctask_details': ctask
            }), 400
        
        # Perform assignment
        result = assignment_service.auto_assign_ctask(ctask_number, planned_date_str, planned_time_str)
        
        if result['success']:
            log_action('Manual CTask Assignment Success', 
                      f'CTask: {ctask_number} assigned to {result["assigned_to"]}')
        else:
            log_action('Manual CTask Assignment Failed', 
                      f'CTask: {ctask_number}, Reason: {result["message"]}')
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error assigning CTask {ctask_number}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error assigning CTask: {str(e)}',
            'ctask_number': ctask_number
        }), 500

@ctask_assignment_bp.route('/webhook/ctask-created', methods=['POST'])
def ctask_webhook():
    """
    Webhook endpoint for ServiceNow to notify about new CTasks
    This endpoint should be configured in ServiceNow Business Rules
    """
    try:
        data = request.get_json()
        
        # Extract CTask information from webhook payload
        ctask_number = data.get('number') or data.get('ctask_number')
        planned_start_date = data.get('planned_start_date') or data.get('work_start')
        assignment_group = data.get('assignment_group')
        
        if not ctask_number:
            return jsonify({
                'success': False,
                'message': 'Missing ctask_number in webhook payload'
            }), 400
        
        log_action('CTask Webhook Received', 
                  f'CTask: {ctask_number}, Assignment Group: {assignment_group}')
        
        # Extract date and time from planned_start_date
        if planned_start_date:
            try:
                # Parse ServiceNow datetime format (YYYY-MM-DD HH:MM:SS)
                if ' ' in planned_start_date:
                    planned_date_str, planned_time_str = planned_start_date.split(' ', 1)
                else:
                    planned_date_str = planned_start_date
                    planned_time_str = '09:00:00'  # Default time if not provided
                    
                # Automatically assign the CTask
                assignment_service = CTaskAssignmentService()
                result = assignment_service.auto_assign_ctask(ctask_number, planned_date_str, planned_time_str)
                
                if result['success']:
                    log_action('Webhook CTask Assignment Success', 
                              f'CTask: {ctask_number} assigned to {result["assigned_to"]}')
                    
                    return jsonify({
                        'success': True,
                        'message': f'CTask {ctask_number} automatically assigned to {result["assigned_to"]}',
                        'assignment_result': result
                    })
                else:
                    log_action('Webhook CTask Assignment Failed', 
                              f'CTask: {ctask_number}, Reason: {result["message"]}')
                    
                    return jsonify({
                        'success': False,
                        'message': result['message'],
                        'ctask_number': ctask_number
                    })
                    
            except Exception as e:
                return jsonify({
                    'success': False,
                    'message': f'Error parsing planned date/time: {str(e)}',
                    'ctask_number': ctask_number
                }), 400
        else:
            return jsonify({
                'success': False,
                'message': 'No planned_start_date provided in webhook',
                'ctask_number': ctask_number
            }), 400
        
    except Exception as e:
        logger.error(f"Error processing CTask webhook: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error processing webhook: {str(e)}'
        }), 500

@ctask_assignment_bp.route('/clear-console', methods=['POST'])
@login_required
def clear_console_output():
    """Clear console output"""
    try:
        clear_console()
        log_action('Clear Console', f'User: {current_user.username}')
        
        return jsonify({
            'success': True,
            'message': 'Console cleared'
        })
        
    except Exception as e:
        logger.error(f"Error clearing console: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error clearing console: {str(e)}'
        }), 500

@ctask_assignment_bp.route('/start-automatic-assignment', methods=['POST'])
@login_required
def start_automatic_assignment():
    """Start automatic CTask assignment scheduler"""
    try:
        # Start the real background scheduler
        from services.ctask_scheduler import start_ctask_scheduler
        start_ctask_scheduler()
        
        # Also update the assignment service state for UI consistency
        ctask_assignment_service.start_scheduler()
        
        log_action('Start Automatic Assignment', f'User: {current_user.username}')
        
        return jsonify({
            'success': True,
            'message': 'Automatic assignment started successfully'
        })
        
    except Exception as e:
        logger.error(f"Error starting automatic assignment: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error starting automatic assignment: {str(e)}'
        }), 500

@ctask_assignment_bp.route('/stop-automatic-assignment', methods=['POST'])
@login_required
def stop_automatic_assignment():
    """Stop automatic CTask assignment scheduler"""
    try:
        # Stop the real background scheduler
        from services.ctask_scheduler import stop_ctask_scheduler
        stop_ctask_scheduler()
        
        # Also update the assignment service state for UI consistency
        ctask_assignment_service.stop_scheduler()
        
        log_action('Stop Automatic Assignment', f'User: {current_user.username}')
        
        return jsonify({
            'success': True,
            'message': 'Automatic assignment stopped successfully'
        })
        
    except Exception as e:
        logger.error(f"Error stopping automatic assignment: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error stopping automatic assignment: {str(e)}'
        }), 500

@ctask_assignment_bp.route('/scheduler-status', methods=['GET'])
@login_required
def get_scheduler_status():
    """Get current scheduler status"""
    try:
        assignment_service = ctask_assignment_service
        
        # Get scheduler status
        status = assignment_service.get_scheduler_status()
        
        return jsonify({
            'success': True,
            'status': status.get('status', 'Stopped'),
            'last_check': status.get('last_check', 'Never'),
            'next_check': status.get('next_check', 'Unknown'),
            'check_interval': status.get('check_interval', '2 minutes')
        })
        
    except Exception as e:
        logger.error(f"Error getting scheduler status: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error getting scheduler status: {str(e)}'
        }), 500