"""
Shift Swap & Leave Management Routes
API endpoints for managing shift swaps and leave requests
"""

from flask import Blueprint, request, jsonify, render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime, date
from services.shift_swap_leave_service import shift_swap_leave_service
from models.models import User, ShiftRoster, TeamMember, UserTeamMembership, db
from models.shift_swap_leave import ShiftSwapRequest, LeaveRequest
import logging

logger = logging.getLogger(__name__)

# Create blueprint
shift_swap_leave_bp = Blueprint('shift_swap_leave', __name__, url_prefix='/shift-management')

@shift_swap_leave_bp.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard for shift management"""
    try:
        # Get user's requests
        user_requests = shift_swap_leave_service.get_user_requests(current_user.id)
        
        # Get pending requests for approval (if user is admin)
        pending_requests = {'success': True, 'swap_requests': [], 'leave_requests': []}
        if current_user.role in ['super_admin', 'account_admin', 'team_admin']:
            pending_requests = shift_swap_leave_service.get_pending_requests_for_approval(current_user.id)
        
        return render_template('shift_management/dashboard.html',
                             user_requests=user_requests,
                             pending_requests=pending_requests,
                             current_user=current_user)
    except Exception as e:
        logger.error(f"Error loading shift management dashboard: {str(e)}")
        flash('Error loading dashboard', 'error')
        return redirect('/')

@shift_swap_leave_bp.route('/swap/request', methods=['GET', 'POST'])
@login_required
def request_swap():
    """Request a shift swap"""
    if request.method == 'GET':
        # Show swap request form
        return render_template('shift_management/request_swap.html', current_user=current_user)
    
    try:
        data = request.get_json() if request.is_json else request.form.to_dict()
        
        # Validate required fields
        required_fields = ['swap_with_id', 'original_date', 'original_shift_code', 
                          'swap_date', 'swap_shift_code', 'reason']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
        
        # Parse dates
        try:
            original_date = datetime.strptime(data['original_date'], '%Y-%m-%d').date()
            swap_date = datetime.strptime(data['swap_date'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'success': False, 'error': 'Invalid date format'}), 400
        
        # Create the swap request
        result = shift_swap_leave_service.create_shift_swap_request(
            requester_id=current_user.id,
            swap_with_id=int(data['swap_with_id']),
            original_date=original_date,
            original_shift_code=data['original_shift_code'],
            swap_date=swap_date,
            swap_shift_code=data['swap_shift_code'],
            reason=data['reason']
        )
        
        if result['success']:
            if request.is_json:
                return jsonify(result)
            else:
                flash('Shift swap request submitted successfully!', 'success')
                return redirect(url_for('shift_swap_leave.dashboard'))
        else:
            if request.is_json:
                return jsonify(result), 400
            else:
                flash(f'Error: {result["error"]}', 'error')
                return render_template('shift_management/request_swap.html', current_user=current_user)
    
    except Exception as e:
        logger.error(f"Error creating swap request: {str(e)}")
        error_msg = 'An error occurred while processing your request'
        if request.is_json:
            return jsonify({'success': False, 'error': error_msg}), 500
        else:
            flash(error_msg, 'error')
            return render_template('shift_management/request_swap.html', current_user=current_user)

@shift_swap_leave_bp.route('/leave/request', methods=['GET', 'POST'])
@login_required
def request_leave():
    """Request leave"""
    if request.method == 'GET':
        # Show leave request form
        return render_template('shift_management/request_leave.html', current_user=current_user)
    
    try:
        data = request.get_json() if request.is_json else request.form.to_dict()
        
        # Validate required fields
        required_fields = ['leave_type', 'leave_date', 'shift_code']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
        
        # Parse date
        try:
            leave_date = datetime.strptime(data['leave_date'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'success': False, 'error': 'Invalid date format'}), 400
        
        # Create the leave request
        result = shift_swap_leave_service.create_leave_request(
            requester_id=current_user.id,
            leave_type=data['leave_type'],
            leave_date=leave_date,
            shift_code=data['shift_code'],
            reason=data.get('reason', '')
        )
        
        if result['success']:
            if request.is_json:
                return jsonify(result)
            else:
                flash('Leave request submitted successfully!', 'success')
                return redirect(url_for('shift_swap_leave.dashboard'))
        else:
            if request.is_json:
                return jsonify(result), 400
            else:
                flash(f'Error: {result["error"]}', 'error')
                return render_template('shift_management/request_leave.html', current_user=current_user)
    
    except Exception as e:
        logger.error(f"Error creating leave request: {str(e)}")
        error_msg = 'An error occurred while processing your request'
        if request.is_json:
            return jsonify({'success': False, 'error': error_msg}), 500
        else:
            flash(error_msg, 'error')
            return render_template('shift_management/request_leave.html', current_user=current_user)

@shift_swap_leave_bp.route('/api/eligible-partners')
@login_required
def get_eligible_partners():
    """Get eligible team members for shift swapping - STRICT team and account isolation"""
    try:
        # STRICT REQUIREMENT: Current user must have teams and account_id
        user_team_memberships = current_user.get_teams()
        if not user_team_memberships or not current_user.account_id:
            return jsonify({
                'success': False, 
                'error': 'User must be assigned to teams and account to find eligible partners'
            }), 403
        
        request_date_str = request.args.get('date')
        shift_code = request.args.get('shift_code')
        
        if not request_date_str or not shift_code:
            return jsonify({'success': False, 'error': 'Missing date or shift_code parameter'}), 400
        
        try:
            request_date = datetime.strptime(request_date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'success': False, 'error': 'Invalid date format'}), 400
        
        user_team_ids = [membership.team_id for membership in user_team_memberships]
        logger.info(f"Finding eligible partners for user {current_user.username} (team_ids={user_team_ids}, account_id={current_user.account_id})")
        
        partners = shift_swap_leave_service.get_eligible_swap_partners(
            current_user.id, request_date, shift_code
        )
        
        return jsonify({'success': True, 'partners': partners})
    
    except Exception as e:
        logger.error(f"Error getting eligible partners: {str(e)}")
        return jsonify({'success': False, 'error': 'An error occurred'}), 500

@shift_swap_leave_bp.route('/api/user-schedule')
@login_required
def get_user_schedule():
    """Get user's upcoming schedule - STRICT team and account isolation"""
    try:
        user_id = request.args.get('user_id', current_user.id, type=int)
        
        # STRICT REQUIREMENT: Current user must have teams and account_id
        user_team_memberships = current_user.get_teams()
        if not user_team_memberships or not current_user.account_id:
            return jsonify({'success': False, 'error': 'User must be assigned to teams and account'}), 403
        
        # Get the requested user
        user = User.query.get(user_id)
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        # STRICT ISOLATION: Can only view schedules of users in same teams and account
        user_team_ids = [membership.team_id for membership in user_team_memberships]
        user_in_same_teams = user.is_member_of_team_ids(user_team_ids, account_id=current_user.account_id)
        
        # Fallback: check if user has old team_id that matches any of current user's teams
        if not user_in_same_teams and hasattr(user, 'team_id') and user.team_id:
            user_in_same_teams = user.team_id in user_team_ids
            
        if not user_in_same_teams or user.account_id != current_user.account_id:
            logger.warning(f"User {current_user.username} attempted to access schedule of user {user.username} from different team/account")
            return jsonify({'success': False, 'error': 'Access denied - can only view schedules within your teams'}), 403
        
        # Find team member in any of the shared teams
        team_member = TeamMember.query.filter(
            TeamMember.name == user.username,
            TeamMember.account_id == current_user.account_id,
            TeamMember.team_id.in_(user_team_ids)
        ).first()
        
        if not team_member:
            return jsonify({'success': True, 'schedule': []})
        
        # Get upcoming shifts (next 30 days) - STRICT filtering
        from datetime import timedelta
        start_date = date.today()
        end_date = start_date + timedelta(days=30)
        
        shifts = ShiftRoster.query.filter(
            ShiftRoster.team_member_id == team_member.id,
            ShiftRoster.date >= start_date,
            ShiftRoster.date <= end_date,
            ShiftRoster.account_id == current_user.account_id,  # STRICT: Same account as current user
            ShiftRoster.team_id.in_(user_team_ids)              # STRICT: Teams that current user belongs to
        ).order_by(ShiftRoster.date).all()
        
        schedule = [{
            'date': shift.date.isoformat(),
            'shift_code': shift.shift_code,
            'day_of_week': shift.date.strftime('%A')
        } for shift in shifts]
        
        return jsonify({'success': True, 'schedule': schedule})
    
    except Exception as e:
        logger.error(f"Error getting user schedule: {str(e)}")
        return jsonify({'success': False, 'error': 'An error occurred'}), 500

@shift_swap_leave_bp.route('/admin/approve-swap/<int:request_id>', methods=['POST'])
@login_required
def approve_swap_request(request_id):
    """Approve a shift swap request"""
    if current_user.role not in ['super_admin', 'account_admin', 'team_admin']:
        return jsonify({'success': False, 'error': 'Insufficient permissions'}), 403
    
    try:
        data = request.get_json() if request.is_json else request.form.to_dict()
        comments = data.get('comments', '')
        
        result = shift_swap_leave_service.approve_swap_request(
            request_id=request_id,
            approver_id=current_user.id,
            comments=comments
        )
        
        if request.is_json:
            return jsonify(result)
        else:
            if result['success']:
                flash(result['message'], 'success')
            else:
                flash(f'Error: {result["error"]}', 'error')
            return redirect(url_for('shift_swap_leave.dashboard'))
    
    except Exception as e:
        logger.error(f"Error approving swap request: {str(e)}")
        error_msg = 'An error occurred while processing the approval'
        if request.is_json:
            return jsonify({'success': False, 'error': error_msg}), 500
        else:
            flash(error_msg, 'error')
            return redirect(url_for('shift_swap_leave.dashboard'))

@shift_swap_leave_bp.route('/admin/approve-leave/<int:request_id>', methods=['POST'])
@login_required
def approve_leave_request(request_id):
    """Approve a leave request"""
    if current_user.role not in ['super_admin', 'account_admin', 'team_admin']:
        return jsonify({'success': False, 'error': 'Insufficient permissions'}), 403
    
    try:
        data = request.get_json() if request.is_json else request.form.to_dict()
        comments = data.get('comments', '')
        covered_by_id = data.get('covered_by_id')
        if covered_by_id:
            covered_by_id = int(covered_by_id)
        
        result = shift_swap_leave_service.approve_leave_request(
            request_id=request_id,
            approver_id=current_user.id,
            comments=comments,
            covered_by_id=covered_by_id
        )
        
        if request.is_json:
            return jsonify(result)
        else:
            if result['success']:
                flash(result['message'], 'success')
            else:
                flash(f'Error: {result["error"]}', 'error')
            return redirect(url_for('shift_swap_leave.dashboard'))
    
    except Exception as e:
        logger.error(f"Error approving leave request: {str(e)}")
        error_msg = 'An error occurred while processing the approval'
        if request.is_json:
            return jsonify({'success': False, 'error': error_msg}), 500
        else:
            flash(error_msg, 'error')
            return redirect(url_for('shift_swap_leave.dashboard'))

@shift_swap_leave_bp.route('/admin/reject-swap/<int:request_id>', methods=['POST'])
@login_required
def reject_swap_request(request_id):
    """Reject a shift swap request"""
    if current_user.role not in ['super_admin', 'account_admin', 'team_admin']:
        return jsonify({'success': False, 'error': 'Insufficient permissions'}), 403
    
    try:
        data = request.get_json() if request.is_json else request.form.to_dict()
        comments = data.get('comments', '')
        
        if not comments:
            error_msg = 'Rejection reason is required'
            if request.is_json:
                return jsonify({'success': False, 'error': error_msg}), 400
            else:
                flash(error_msg, 'error')
                return redirect(url_for('shift_swap_leave.dashboard'))
        
        result = shift_swap_leave_service.reject_request(
            request_type='swap',
            request_id=request_id,
            approver_id=current_user.id,
            comments=comments
        )
        
        if request.is_json:
            return jsonify(result)
        else:
            if result['success']:
                flash(result['message'], 'success')
            else:
                flash(f'Error: {result["error"]}', 'error')
            return redirect(url_for('shift_swap_leave.dashboard'))
    
    except Exception as e:
        logger.error(f"Error rejecting swap request: {str(e)}")
        error_msg = 'An error occurred while processing the rejection'
        if request.is_json:
            return jsonify({'success': False, 'error': error_msg}), 500
        else:
            flash(error_msg, 'error')
            return redirect(url_for('shift_swap_leave.dashboard'))

@shift_swap_leave_bp.route('/admin/reject-leave/<int:request_id>', methods=['POST'])
@login_required
def reject_leave_request(request_id):
    """Reject a leave request"""
    if current_user.role not in ['super_admin', 'account_admin', 'team_admin']:
        return jsonify({'success': False, 'error': 'Insufficient permissions'}), 403
    
    try:
        data = request.get_json() if request.is_json else request.form.to_dict()
        comments = data.get('comments', '')
        
        if not comments:
            error_msg = 'Rejection reason is required'
            if request.is_json:
                return jsonify({'success': False, 'error': error_msg}), 400
            else:
                flash(error_msg, 'error')
                return redirect(url_for('shift_swap_leave.dashboard'))
        
        result = shift_swap_leave_service.reject_request(
            request_type='leave',
            request_id=request_id,
            approver_id=current_user.id,
            comments=comments
        )
        
        if request.is_json:
            return jsonify(result)
        else:
            if result['success']:
                flash(result['message'], 'success')
            else:
                flash(f'Error: {result["error"]}', 'error')
            return redirect(url_for('shift_swap_leave.dashboard'))
    
    except Exception as e:
        logger.error(f"Error rejecting leave request: {str(e)}")
        error_msg = 'An error occurred while processing the rejection'
        if request.is_json:
            return jsonify({'success': False, 'error': error_msg}), 500
        else:
            flash(error_msg, 'error')
            return redirect(url_for('shift_swap_leave.dashboard'))

@shift_swap_leave_bp.route('/api/my-requests')
@login_required
def get_my_requests():
    """Get current user's requests"""
    try:
        result = shift_swap_leave_service.get_user_requests(current_user.id)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error getting user requests: {str(e)}")
        return jsonify({'success': False, 'error': 'An error occurred'}), 500

@shift_swap_leave_bp.route('/api/pending-approvals')
@login_required
def get_pending_approvals():
    """Get requests pending approval"""
    if current_user.role not in ['super_admin', 'account_admin', 'team_admin']:
        return jsonify({'success': False, 'error': 'Insufficient permissions'}), 403
    
    try:
        result = shift_swap_leave_service.get_pending_requests_for_approval(current_user.id)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error getting pending approvals: {str(e)}")
        return jsonify({'success': False, 'error': 'An error occurred'}), 500

@shift_swap_leave_bp.route('/api/team-members')
@login_required
def get_team_members():
    """Get team members for dropdowns - STRICT team and account isolation"""
    try:
        user_team_memberships = current_user.get_teams()
        user_team_ids = [membership.team_id for membership in user_team_memberships] if user_team_memberships else []
        logger.info(f"API team-members called by user: {current_user.username} (Team IDs: {user_team_ids}, Account ID: {current_user.account_id})")
        
        # STRICT REQUIREMENT: User must have teams and account_id assigned
        if not user_team_memberships or not current_user.account_id:
            logger.warning(f"User {current_user.username} missing team memberships or account_id ({current_user.account_id})")
            return jsonify({
                'success': False, 
                'error': 'User must be assigned to teams and account to view team members',
                'team_members': []
            })
        
        # Get team members from user's teams and account, excluding current user
        team_members_query = User.query.join(UserTeamMembership).filter(
            User.id != current_user.id,
            User.is_active == True,
            User.status == 'active',
            UserTeamMembership.team_id.in_(user_team_ids),  # Teams that current user belongs to
            User.account_id == current_user.account_id,     # STRICT: Same account only
            UserTeamMembership.is_active == True
        ).distinct()
        
        # Also get from TeamMember table for additional members (STRICT filtering)
        team_members_from_table = TeamMember.query.filter(
            TeamMember.team_id.in_(user_team_ids),
            TeamMember.account_id == current_user.account_id
        ).all()
        
        # Get users from User table
        users = team_members_query.limit(50).all()
        
        members_data = []
        
        # Add users from User table
        for user in users:
            members_data.append({
                'id': user.id,
                'username': user.username,
                'full_name': user.display_name,  # Use the property method
                'email': user.email if user.email else '',
                'source': 'user'
            })
        
        # Add team members from TeamMember table (if they don't have corresponding User records)
        existing_user_ids = {member['id'] for member in members_data}
        for tm in team_members_from_table:
            if tm.user_id and tm.user_id not in existing_user_ids:
                # Get the corresponding user record
                user = User.query.get(tm.user_id)
                if user and user.id != current_user.id:
                    members_data.append({
                        'id': user.id,
                        'username': user.username,
                        'full_name': user.display_name,
                        'email': user.email if user.email else tm.email,
                        'source': 'team_member'
                    })
            elif not tm.user_id:
                # TeamMember without corresponding User (legacy data)
                members_data.append({
                    'id': f"tm_{tm.id}",  # Use a special ID format
                    'username': tm.name,
                    'full_name': tm.name,
                    'email': tm.email,
                    'source': 'team_member_only'
                })
        
        # NO FALLBACK TO ACCOUNT LEVEL - Strict team isolation only
        # Users can only see their exact team members, no exceptions
        if not members_data:
            logger.info(f"No team members found for team_ids={user_team_ids}, account_id={current_user.account_id}")
            logger.info("STRICT ISOLATION: Not falling back to account level - team members only")
        
        logger.info(f"Returning {len(members_data)} team members from team_ids={user_team_ids}, account_id={current_user.account_id}")
        return jsonify({'success': True, 'team_members': members_data})
    
    except Exception as e:
        logger.error(f"Error getting team members: {str(e)}")
        return jsonify({'success': False, 'error': 'An error occurred'}), 500

@shift_swap_leave_bp.route('/api/shift-codes')
@login_required
def get_shift_codes():
    """Get available shift codes - STRICT team and account isolation"""
    try:
        user_team_memberships = current_user.get_teams()
        user_team_ids = [membership.team_id for membership in user_team_memberships] if user_team_memberships else []
        logger.info(f"API shift-codes called by user: {current_user.username} (Team IDs: {user_team_ids}, Account ID: {current_user.account_id})")
        
        # STRICT REQUIREMENT: User must have teams and account_id assigned
        if not user_team_memberships or not current_user.account_id:
            logger.warning(f"User {current_user.username} missing team memberships or account_id ({current_user.account_id})")
            return jsonify({
                'success': False, 
                'error': 'User must be assigned to teams and account to view shift codes',
                'shift_codes': []
            })
        
        # Get shift codes ONLY from the user's teams and account
        from sqlalchemy import text
        team_ids_str = ','.join(map(str, user_team_ids))
        result = db.session.execute(
            text(f"SELECT DISTINCT shift_code FROM shift_roster WHERE shift_code IS NOT NULL AND team_id IN ({team_ids_str}) AND account_id = :account_id"),
            {'account_id': current_user.account_id}
        )
        codes = [row[0] for row in result.fetchall() if row[0] not in ['LE', 'OFF', 'VL', 'HL']]  # Exclude leave codes
        
        logger.info(f"Returning {len(codes)} shift codes for team_ids={user_team_ids}, account_id={current_user.account_id}: {codes}")
        return jsonify({'success': True, 'shift_codes': codes})
    
    except Exception as e:
        logger.error(f"Error getting shift codes: {str(e)}")
        return jsonify({'success': False, 'error': 'An error occurred'}), 500

@shift_swap_leave_bp.route('/api/user-teams')
@login_required
def get_user_teams():
    """Get list of teams the current user belongs to"""
    try:
        from models.models import Team
        
        user_team_memberships = current_user.get_teams()
        
        if not user_team_memberships:
            return jsonify({
                'success': True,
                'teams': [],
                'message': 'User is not assigned to any teams'
            })
        
        teams_data = []
        for membership in user_team_memberships:
            team = Team.query.get(membership.team_id)
            if team:
                teams_data.append({
                    'id': team.id,
                    'name': team.name,
                    'is_primary': membership.is_primary,
                    'role': membership.role
                })
        
        # Sort with primary team first
        teams_data.sort(key=lambda x: (not x['is_primary'], x['name']))
        
        logger.info(f"Returning {len(teams_data)} teams for user {current_user.username}")
        return jsonify({
            'success': True,
            'teams': teams_data
        })
    
    except Exception as e:
        logger.error(f"Error getting user teams: {str(e)}")
        return jsonify({'success': False, 'error': 'An error occurred'}), 500

# Temporary test endpoints without login requirement
@shift_swap_leave_bp.route('/api/test-shift-codes')
def test_get_shift_codes():
    """Test endpoint for shift codes without authentication"""
    try:
        from sqlalchemy import text
        result = db.session.execute(
            text("SELECT DISTINCT shift_code FROM shift_roster WHERE shift_code IS NOT NULL")
        )
        codes = [row[0] for row in result.fetchall() if row[0] not in ['LE', 'OFF', 'VL', 'HL']]
        return jsonify({'success': True, 'shift_codes': codes, 'count': len(codes)})
    except Exception as e:
        logger.error(f"Error in test shift codes: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@shift_swap_leave_bp.route('/api/test-team-members')
def test_get_team_members():
    """Test endpoint for team members without authentication"""
    try:
        team_members = User.query.filter(
            User.first_name.isnot(None),
            User.last_name.isnot(None)
        ).limit(10).all()
        
        members_data = [{
            'id': member.id,
            'username': member.username,
            'full_name': f"{member.first_name} {member.last_name}",
            'email': member.email if member.email else ''
        } for member in team_members]
        
        return jsonify({'success': True, 'team_members': members_data, 'count': len(members_data)})
    except Exception as e:
        logger.error(f"Error in test team members: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@shift_swap_leave_bp.route('/api/user-shift-details')
@login_required
def get_user_shift_details():
    """Get specific shift details for a user on a specific date"""
    try:
        # STRICT REQUIREMENT: Current user must have teams and account_id
        user_team_memberships = current_user.get_teams()
        if not user_team_memberships or not current_user.account_id:
            return jsonify({
                'success': False, 
                'error': 'User must be assigned to teams and account'
            }), 403
        
        user_id = request.args.get('user_id')
        shift_date_str = request.args.get('date')
        
        if not user_id or not shift_date_str:
            return jsonify({'success': False, 'error': 'Missing user_id or date parameter'}), 400
        
        try:
            user_id = int(user_id)
            shift_date = datetime.strptime(shift_date_str, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            return jsonify({'success': False, 'error': 'Invalid user_id or date format'}), 400
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        # STRICT ISOLATION: Can only view shifts of users in same teams and account
        user_team_ids = [membership.team_id for membership in user_team_memberships]
        user_in_same_teams = user.is_member_of_team_ids(user_team_ids, account_id=current_user.account_id)
        
        # Fallback: check if user has old team_id that matches any of current user's teams
        if not user_in_same_teams and hasattr(user, 'team_id') and user.team_id:
            user_in_same_teams = user.team_id in user_team_ids
            
        if not user_in_same_teams or user.account_id != current_user.account_id:
            logger.warning(f"User {current_user.username} attempted to access shift details of user {user.username} from different team/account")
            return jsonify({'success': False, 'error': 'Access denied - can only view shifts within your teams'}), 403
        
        # First try to find TeamMember by user_id (most reliable)
        team_member = TeamMember.query.filter(
            TeamMember.user_id == user.id,
            TeamMember.account_id == current_user.account_id,
            TeamMember.team_id.in_(user_team_ids)
        ).first()
        
        # Fallback: try matching by name variations
        if not team_member:
            # Try exact username match
            team_member = TeamMember.query.filter(
                TeamMember.name == user.username,
                TeamMember.account_id == current_user.account_id,
                TeamMember.team_id.in_(user_team_ids)
            ).first()
        
        if not team_member:
            # Try display name match (First Last)
            display_name = f"{user.first_name} {user.last_name}" if user.first_name and user.last_name else None
            if display_name:
                team_member = TeamMember.query.filter(
                    TeamMember.name == display_name,
                    TeamMember.account_id == current_user.account_id,
                    TeamMember.team_id.in_(user_team_ids)
                ).first()
        
        if not team_member:
            # Try case-insensitive partial match
            team_member = TeamMember.query.filter(
                TeamMember.name.ilike(f"%{user.username.replace('.', '%').replace('_', '%')}%"),
                TeamMember.account_id == current_user.account_id,
                TeamMember.team_id.in_(user_team_ids)
            ).first()
        
        if not team_member:
            logger.warning(f"No TeamMember found for user {user.username} (id={user.id}) in teams {user_team_ids}")
            return jsonify({
                'success': True, 
                'shift': None,
                'message': 'User not found in team roster'
            })
        
        logger.info(f"Found TeamMember: {team_member.name} (id={team_member.id}) for user {user.username}")
        
        # Get shift for the specific date - check all user's teams
        shift_roster = ShiftRoster.query.filter(
            ShiftRoster.team_member_id == team_member.id,
            ShiftRoster.date == shift_date,
            ShiftRoster.account_id == current_user.account_id
        ).first()
        
        if shift_roster:
            # Get shift timing from shift codes configuration
            shift_timings = {
                'DAY': '06:00 - 14:00',
                'EVENING': '14:00 - 22:00', 
                'NIGHT': '22:00 - 06:00',
                'MORNING': '06:00 - 14:00',
                'OFF': 'No shift',
                'N': '22:00 - 06:00'  # Handle 'N' shift code
            }
            
            return jsonify({
                'success': True,
                'shift': {
                    'shift_code': shift_roster.shift_code,
                    'timing': shift_timings.get(shift_roster.shift_code, f'{shift_roster.shift_code} shift'),
                    'date': shift_date.isoformat()
                }
            })
        else:
            return jsonify({
                'success': True,
                'shift': None,
                'message': 'No shift scheduled for this date'
            })
    
    except Exception as e:
        logger.error(f"Error getting user shift details: {str(e)}")
        return jsonify({'success': False, 'error': 'An error occurred'}), 500

@shift_swap_leave_bp.route('/api/available-engineers')
@login_required
def get_available_engineers():
    """Get available engineers for swap on a specific date - filtered by team"""
    try:
        # STRICT REQUIREMENT: Current user must have team memberships and account_id
        user_team_memberships = current_user.get_teams()
        if not user_team_memberships or not current_user.account_id:
            return jsonify({
                'success': False, 
                'error': 'User must be assigned to teams and account'
            }), 403
        
        user_team_ids = [membership.team_id for membership in user_team_memberships]
        
        shift_date_str = request.args.get('date')
        exclude_user_id = request.args.get('exclude_user_id')
        team_id_param = request.args.get('team_id')  # Optional team filter
        
        if not shift_date_str:
            return jsonify({'success': False, 'error': 'Missing date parameter'}), 400
        
        try:
            shift_date = datetime.strptime(shift_date_str, '%Y-%m-%d').date()
            exclude_user_id = int(exclude_user_id) if exclude_user_id else None
            team_id_filter = int(team_id_param) if team_id_param else None
        except (ValueError, TypeError):
            return jsonify({'success': False, 'error': 'Invalid date format or user_id'}), 400
        
        # If team_id is specified, validate user belongs to that team and filter by it
        if team_id_filter:
            if team_id_filter not in user_team_ids:
                return jsonify({
                    'success': False, 
                    'error': 'Access denied - you do not belong to this team'
                }), 403
            # Filter to only the specified team
            filter_team_ids = [team_id_filter]
        else:
            # No filter specified, use all user's teams
            filter_team_ids = user_team_ids
        
        # Get team members from the filtered team(s)
        team_members = TeamMember.query.filter(
            TeamMember.account_id == current_user.account_id,
            TeamMember.team_id.in_(filter_team_ids)
        ).all()
        
        logger.info(f"Found {len(team_members)} team members for team_ids={filter_team_ids}")
        
        # Also find current user's TeamMember record to exclude
        current_user_team_member = TeamMember.query.filter(
            TeamMember.user_id == current_user.id,
            TeamMember.account_id == current_user.account_id
        ).first()
        
        # If not found by user_id, try by name variations
        if not current_user_team_member:
            current_user_team_member = TeamMember.query.filter(
                TeamMember.account_id == current_user.account_id,
                TeamMember.team_id.in_(user_team_ids),
                db.or_(
                    TeamMember.name == current_user.username,
                    TeamMember.name.ilike(f"%{current_user.username.replace('.', '%')}%"),
                    TeamMember.name == f"{current_user.first_name} {current_user.last_name}" if current_user.first_name else False
                )
            ).first()
        
        current_user_tm_id = current_user_team_member.id if current_user_team_member else None
        logger.info(f"Current user TeamMember ID: {current_user_tm_id}")
        
        available_engineers = []
        seen_tm_ids = set()  # Avoid duplicates
        
        for team_member in team_members:
            # Skip if this is the current user's team member record or already added
            if team_member.id == current_user_tm_id or team_member.id in seen_tm_ids:
                continue
            
            # Skip if exclude_user_id matches the team_member's user_id
            if exclude_user_id and team_member.user_id == exclude_user_id:
                continue
            
            seen_tm_ids.add(team_member.id)
            
            # Get their shift for the selected date
            current_shift = 'Off'
            shift_roster = ShiftRoster.query.filter(
                ShiftRoster.team_member_id == team_member.id,
                ShiftRoster.date == shift_date,
                ShiftRoster.account_id == current_user.account_id
            ).first()
            
            if shift_roster:
                current_shift = shift_roster.shift_code
            
            # Try to find corresponding User for the ID (needed for swap submission)
            # We need a valid user_id to create a swap request
            user = None
            user_id = None
            
            if team_member.user_id:
                user = User.query.get(team_member.user_id)
                if user:
                    user_id = user.id
            
            # If no user_id from team_member, try to find User by name matching
            if not user:
                # Try various name formats
                possible_names = [
                    team_member.name,
                    team_member.name.lower().replace('-', '.'),  # Infrauser-3 -> infrauser.3
                    team_member.name.lower().replace('-', ''),   # Infrauser-3 -> infrauser3
                ]
                for name in possible_names:
                    user = User.query.filter(
                        User.account_id == current_user.account_id,
                        db.or_(
                            User.username == name,
                            User.username.ilike(name)
                        )
                    ).first()
                    if user:
                        user_id = user.id
                        break
            
            # Skip team members without a linked user account (can't do swap request)
            if not user_id:
                logger.debug(f"Skipping team member {team_member.name} - no linked user account found")
                continue
            
            # Use team member's name for display (from roster)
            display_name = team_member.name
            username = team_member.name
            
            if user:
                username = user.username
                # If team member name looks like ID, use user's proper name
                if ' ' not in team_member.name and (user.first_name or user.last_name):
                    display_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
            
            available_engineers.append({
                'id': user_id,
                'username': username,
                'full_name': display_name,
                'current_shift': current_shift
            })
        
        logger.info(f"Returning {len(available_engineers)} available engineers for shift swap")
        return jsonify({
            'success': True,
            'engineers': available_engineers
        })
    
    except Exception as e:
        logger.error(f"Error getting available engineers: {str(e)}")
        return jsonify({'success': False, 'error': 'An error occurred'}), 500

@shift_swap_leave_bp.route('/simple-swap-request', methods=['GET', 'POST'])
@login_required
def simple_swap_request():
    """Simplified shift swap request form"""
    if request.method == 'POST':
        try:
            # Get form data
            swap_date_str = request.form.get('swap_date')
            from_engineer_id = request.form.get('from_engineer_id')
            original_shift_code = request.form.get('original_shift_code')
            swap_with_engineer_id = request.form.get('swap_with_engineer_id')
            
            # Log form data for debugging
            logger.info(f"Form data received - date: {swap_date_str}, from: {from_engineer_id}, shift: {original_shift_code}, swap_with: {swap_with_engineer_id}")
            
            # Validate required fields
            missing_fields = []
            if not swap_date_str:
                missing_fields.append('date')
            if not from_engineer_id:
                missing_fields.append('from_engineer')
            if not swap_with_engineer_id:
                missing_fields.append('swap_with_engineer')
            
            if missing_fields:
                flash(f'Missing required fields: {", ".join(missing_fields)}. Please ensure all fields are filled.', 'error')
                return redirect(url_for('shift_swap_leave.simple_swap_request'))
            
            # Parse date
            try:
                swap_date = datetime.strptime(swap_date_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid date format.', 'error')
                return redirect(url_for('shift_swap_leave.simple_swap_request'))
            
            # Validate that user can only create requests for themselves unless admin
            if current_user.role not in ['super_admin', 'account_admin', 'team_admin']:
                if int(from_engineer_id) != current_user.id:
                    flash('You can only create swap requests for yourself.', 'error')
                    return redirect(url_for('shift_swap_leave.simple_swap_request'))
            
            # Get the target engineer's shift for the same date
            swap_with_user = User.query.get(int(swap_with_engineer_id))
            if not swap_with_user:
                flash('Selected engineer not found.', 'error')
                return redirect(url_for('shift_swap_leave.simple_swap_request'))
            
            # Get user's team memberships
            user_team_memberships = current_user.get_teams()
            user_team_ids = [m.team_id for m in user_team_memberships] if user_team_memberships else []
            
            # Get swap partner's shift for the same date
            # First try by user_id (most reliable)
            swap_with_team_member = None
            if user_team_ids:
                swap_with_team_member = TeamMember.query.filter(
                    TeamMember.user_id == swap_with_user.id,
                    TeamMember.account_id == current_user.account_id,
                    TeamMember.team_id.in_(user_team_ids)
                ).first()
            
            # If not found by user_id, try name matching as fallback
            if not swap_with_team_member and user_team_ids:
                # Try various name formats
                possible_names = [
                    swap_with_user.username,
                    swap_with_user.username.replace('.', '-'),
                    swap_with_user.username.replace('.', '-').title(),
                    f"{swap_with_user.first_name}-{swap_with_user.last_name}" if swap_with_user.first_name and swap_with_user.last_name else None,
                    f"{swap_with_user.first_name} {swap_with_user.last_name}" if swap_with_user.first_name and swap_with_user.last_name else None
                ]
                possible_names = [n for n in possible_names if n]
                
                swap_with_team_member = TeamMember.query.filter(
                    TeamMember.name.in_(possible_names),
                    TeamMember.account_id == current_user.account_id,
                    TeamMember.team_id.in_(user_team_ids)
                ).first()
            
            swap_partner_shift = 'OFF'
            if swap_with_team_member:
                partner_roster = ShiftRoster.query.filter(
                    ShiftRoster.team_member_id == swap_with_team_member.id,
                    ShiftRoster.date == swap_date,
                    ShiftRoster.account_id == current_user.account_id
                ).first()
                
                if partner_roster:
                    swap_partner_shift = partner_roster.shift_code
            
            # Create swap request with automatic reason
            reason = f"Shift swap request for {swap_date.strftime('%Y-%m-%d')} - System generated request"
            
            result = shift_swap_leave_service.create_shift_swap_request(
                requester_id=int(from_engineer_id),
                swap_with_id=int(swap_with_engineer_id),
                original_date=swap_date,
                original_shift_code=original_shift_code or 'OFF',
                swap_date=swap_date,  # Same date swap
                swap_shift_code=swap_partner_shift,
                reason=reason
            )
            
            if result['success']:
                flash('Shift swap request submitted successfully!', 'success')
                return redirect(url_for('shift_swap_leave.dashboard'))
            else:
                flash(f'Error: {result["error"]}', 'error')
                
        except Exception as e:
            logger.error(f"Error processing simple swap request: {str(e)}")
            flash('An error occurred while processing your request. Please try again.', 'error')
    
    # GET request - render form
    from datetime import timedelta
    today = date.today()
    min_date = today.isoformat()
    max_date = (today + timedelta(days=90)).isoformat()
    
    # Get team members for admin dropdown
    team_members = []
    if current_user.role in ['super_admin', 'account_admin', 'team_admin']:
        # Get users from user's teams
        user_team_memberships = current_user.get_teams()
        user_team_ids = [m.team_id for m in user_team_memberships] if user_team_memberships else []
        
        if user_team_ids:
            team_members_query = User.query.join(UserTeamMembership).filter(
                User.account_id == current_user.account_id,
                User.is_active == True,
                User.role.in_(['user', 'engineer', 'team_admin']),
                UserTeamMembership.team_id.in_(user_team_ids),
                UserTeamMembership.is_active == True
            ).distinct().all()
        else:
            # Fallback to legacy team_id
            team_members_query = User.query.filter(
                User.account_id == current_user.account_id,
                User.team_id == current_user.team_id,
                User.is_active == True,
                User.role.in_(['user', 'engineer', 'team_admin'])
            ).all()
        
        team_members = [{
            'id': user.id,
            'full_name': f"{user.first_name} {user.last_name}"
        } for user in team_members_query]
    
    return render_template('shift_management/simple_swap_request.html', 
                         current_user=current_user,
                         min_date=min_date,
                         max_date=max_date,
                         team_members=team_members)

# Error handlers
@shift_swap_leave_bp.errorhandler(404)
def not_found(error):
    return jsonify({'success': False, 'error': 'Resource not found'}), 404

@shift_swap_leave_bp.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {str(error)}")
    return jsonify({'success': False, 'error': 'Internal server error'}), 500
@shift_swap_leave_bp.route("/api/user-shift/<date>", methods=["GET"])
@login_required
def get_user_shift_for_date(date):
    """Get user's scheduled shift for a specific date"""
    try:
        from datetime import datetime
        from models.models import ShiftRoster, TeamMember
        
        # Parse the date
        try:
            leave_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"success": False, "error": "Invalid date format"}), 400
        
        # Get user's team memberships to find their teams
        user_team_memberships = current_user.get_teams()
        user_team_ids = [m.team_id for m in user_team_memberships] if user_team_memberships else []
        
        # Try to find TeamMember by user_id first (most reliable)
        team_member = TeamMember.query.filter_by(user_id=current_user.id).first()
        
        # Fallback: try matching by name variations
        if not team_member and current_user.account_id:
            # Try exact username match
            team_member = TeamMember.query.filter(
                TeamMember.name == current_user.username,
                TeamMember.account_id == current_user.account_id
            ).first()
        
        if not team_member and current_user.account_id:
            # Try display name match (First Last)
            display_name = f"{current_user.first_name} {current_user.last_name}" if current_user.first_name and current_user.last_name else None
            if display_name:
                team_member = TeamMember.query.filter(
                    TeamMember.name == display_name,
                    TeamMember.account_id == current_user.account_id
                ).first()
        
        if not team_member and current_user.account_id:
            # Try case-insensitive partial match (e.g., "infrauser3" matches "Infrauser-3")
            search_pattern = current_user.username.replace('.', '%').replace('_', '%').replace('-', '%')
            team_member = TeamMember.query.filter(
                TeamMember.name.ilike(f"%{search_pattern}%"),
                TeamMember.account_id == current_user.account_id
            ).first()
        
        if not team_member:
            logger.warning(f"No TeamMember found for user {current_user.username} (id={current_user.id})")
            return jsonify({"success": False, "error": "Team member record not found"}), 404
        
        logger.info(f"Found TeamMember: {team_member.name} (id={team_member.id}) for user {current_user.username}")
        
        # Get scheduled shift for the date
        roster_entry = ShiftRoster.query.filter_by(
            date=leave_date,
            team_member_id=team_member.id
        ).first()

        # If not found and user has account_id, try with account_id filter
        if not roster_entry and current_user.account_id:
            roster_entry = ShiftRoster.query.filter_by(
                date=leave_date,
                team_member_id=team_member.id,
                account_id=current_user.account_id
            ).first()
        
        if roster_entry:
            shift_names = {
                "D": "Day Shift",
                "E": "Evening Shift", 
                "N": "Night Shift",
                "OS": "On-Site",
                "OF": "Off Duty",
                "O": "Week Off"
            }
            
            return jsonify({
                "success": True,
                "shift": {
                    "code": roster_entry.shift_code,
                    "name": shift_names.get(roster_entry.shift_code, roster_entry.shift_code)
                },
                "date": date
            })
        else:
            # Debug info to help troubleshoot
            logger.debug(f"DEBUG: No roster entry found for user {current_user.id}, team_member {team_member.id}, date {leave_date}")
            
            return jsonify({
                "success": True,
                "shift": None,
                "message": "No shift scheduled for this date"
            })
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
