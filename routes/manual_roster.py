"""
Manual Roster Entry
Allows adding individual shifts via calendar UI
"""

from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from models.models import db, Team, TeamMember, Account
from models.team_roster_models import RosterAssignment, TeamShiftConfig
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

manual_roster_bp = Blueprint('manual_roster', __name__)


@manual_roster_bp.route('/admin/manual-roster')
@login_required
def manual_roster():
    """Manual roster entry page with calendar UI."""
    if current_user.role != 'super_admin':
        return "Access denied - Super Admin only", 403
    
    # Super admin can see all teams and accounts
    teams = Team.query.filter_by(is_active=True).order_by(Team.name).all()
    accounts = Account.query.filter_by(is_active=True).order_by(Account.name).all()
    
    return render_template('admin/manual_roster.html', teams=teams, accounts=accounts)


@manual_roster_bp.route('/api/manual-roster/members/<int:team_id>')
@login_required
def get_team_members(team_id):
    """Get team members for a team."""
    try:
        members = TeamMember.query.filter_by(team_id=team_id, is_active=True).order_by(TeamMember.name).all()
        return jsonify({
            'success': True,
            'members': [{'id': m.id, 'name': m.name, 'email': m.email} for m in members]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@manual_roster_bp.route('/api/manual-roster/entries')
@login_required
def get_roster_entries():
    """Get roster entries for calendar display."""
    try:
        team_id = request.args.get('team_id', type=int)
        start_date = request.args.get('start')
        end_date = request.args.get('end')
        
        if not team_id:
            return jsonify({'success': True, 'entries': []})
        
        query = RosterAssignment.query.filter_by(team_id=team_id, is_active=True)
        
        if start_date:
            query = query.filter(RosterAssignment.assignment_date >= datetime.strptime(start_date, '%Y-%m-%d').date())
        if end_date:
            query = query.filter(RosterAssignment.assignment_date <= datetime.strptime(end_date, '%Y-%m-%d').date())
        
        entries = query.all()
        
        # Format for FullCalendar
        events = []
        shift_colors = {
            'Day': '#28a745',
            'Morning': '#28a745',
            'Evening': '#fd7e14',
            'Night': '#6f42c1',
            'Onshore': '#17a2b8',
            'OnShore': '#17a2b8',
            'Offshore': '#20c997',
            'OffShore': '#20c997',
            'General': '#6c757d',
            'Late Evening': '#e83e8c',
        }
        
        for entry in entries:
            # Get user info
            user = entry.user
            user_name = user.username if user else 'Unknown'
            if user and (user.first_name or user.last_name):
                user_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
            
            # Get shift info
            shift_config = entry.shift_config
            shift_name = shift_config.shift_name if shift_config else 'Unknown'
            
            events.append({
                'id': entry.id,
                'title': f"{user_name} - {shift_name}",
                'start': entry.assignment_date.isoformat(),
                'backgroundColor': shift_colors.get(shift_name, '#6c757d'),
                'borderColor': shift_colors.get(shift_name, '#6c757d'),
                'extendedProps': {
                    'user_id': entry.user_id,
                    'user_name': user_name,
                    'shift_name': shift_name,
                    'shift_config_id': entry.shift_config_id
                }
            })
        
        return jsonify({'success': True, 'entries': events})
    except Exception as e:
        logger.error(f"Error getting roster entries: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@manual_roster_bp.route('/api/manual-roster/add', methods=['POST'])
@login_required
def add_roster_entry():
    """Add a new roster entry."""
    if current_user.role != 'super_admin':
        return jsonify({'error': 'Access denied - Super Admin only'}), 403
    
    try:
        data = request.get_json()
        
        team_id = data.get('team_id')
        user_id = data.get('member_id')  # Using member_id from frontend but it's user_id
        date_str = data.get('date')
        shift_config_id = data.get('shift_config_id')
        
        if not all([team_id, user_id, date_str, shift_config_id]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        assignment_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        # Get team's account_id
        team = Team.query.get(team_id)
        if not team:
            return jsonify({'error': 'Team not found'}), 404
        
        account_id = team.account_id
        
        # Check if entry already exists
        existing = RosterAssignment.query.filter_by(
            team_id=team_id,
            user_id=user_id,
            shift_config_id=shift_config_id,
            assignment_date=assignment_date
        ).first()
        
        if existing:
            # Reactivate if inactive
            existing.is_active = True
            db.session.commit()
            return jsonify({
                'success': True,
                'message': 'Shift assignment updated successfully',
                'id': existing.id
            })
        
        # Create new entry
        entry = RosterAssignment(
            team_id=team_id,
            account_id=account_id,
            user_id=user_id,
            shift_config_id=shift_config_id,
            assignment_date=assignment_date,
            created_by_id=current_user.id
        )
        db.session.add(entry)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Shift assignment added successfully',
            'id': entry.id
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error adding roster entry: {e}")
        return jsonify({'error': str(e)}), 500


@manual_roster_bp.route('/api/manual-roster/delete/<int:entry_id>', methods=['DELETE'])
@login_required
def delete_roster_entry(entry_id):
    """Delete a roster entry."""
    if current_user.role != 'super_admin':
        return jsonify({'error': 'Access denied - Super Admin only'}), 403
    
    try:
        entry = RosterAssignment.query.get_or_404(entry_id)
        entry.is_active = False  # Soft delete
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Entry deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@manual_roster_bp.route('/api/manual-roster/shifts/<int:team_id>')
@login_required
def get_team_shifts(team_id):
    """Get available shift configurations for a team."""
    try:
        shifts = TeamShiftConfig.get_team_shifts(team_id)
        return jsonify({
            'success': True,
            'shifts': [{'id': s.id, 'name': s.shift_name, 'start': s.start_time.strftime('%H:%M'), 'end': s.end_time.strftime('%H:%M')} for s in shifts]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@manual_roster_bp.route('/api/manual-roster/bulk-add', methods=['POST'])
@login_required
def bulk_add_roster():
    """Add multiple roster entries at once (for date range)."""
    if current_user.role != 'super_admin':
        return jsonify({'error': 'Access denied - Super Admin only'}), 403
    
    try:
        data = request.get_json()
        
        team_id = data.get('team_id')
        user_id = data.get('member_id')
        start_date = datetime.strptime(data.get('start_date'), '%Y-%m-%d').date()
        end_date = datetime.strptime(data.get('end_date'), '%Y-%m-%d').date()
        shift_config_id = data.get('shift_config_id')
        
        if not all([team_id, user_id, start_date, end_date, shift_config_id]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Get team's account_id
        team = Team.query.get(team_id)
        if not team:
            return jsonify({'error': 'Team not found'}), 404
        
        account_id = team.account_id
        
        added_count = 0
        current_date = start_date
        
        while current_date <= end_date:
            # Check if entry exists
            existing = RosterAssignment.query.filter_by(
                team_id=team_id,
                user_id=user_id,
                shift_config_id=shift_config_id,
                assignment_date=current_date
            ).first()
            
            if existing:
                existing.is_active = True
            else:
                entry = RosterAssignment(
                    team_id=team_id,
                    account_id=account_id,
                    user_id=user_id,
                    shift_config_id=shift_config_id,
                    assignment_date=current_date,
                    created_by_id=current_user.id
                )
                db.session.add(entry)
            
            added_count += 1
            current_date += timedelta(days=1)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Successfully added/updated {added_count} shift entries',
            'count': added_count
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error bulk adding roster: {e}")
        return jsonify({'error': str(e)}), 500

