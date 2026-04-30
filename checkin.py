"""
Check-in/Check-out functionality for team members
"""
from flask import Blueprint, request, jsonify, session
from flask_login import login_required, current_user
from datetime import datetime
from models.models import db, TeamMember, CheckInLog, User
from sqlalchemy import and_

checkin_bp = Blueprint('checkin', __name__)

@checkin_bp.route('/api/checkin', methods=['POST'])
@login_required
def checkin():
    """Handle team member check-in"""
    try:
        data = request.get_json()
        status = data.get('status')  # 'online', 'oncall', 'offline'
        location = data.get('location', '')
        notes = data.get('notes', '')
        
        if status not in ['online', 'oncall', 'offline']:
            return jsonify({'error': 'Invalid status'}), 400
        
        # Find the team member associated with the current user
        # NEW LOGIC: Prioritize TeamMember records that are actually used in shift rosters
        from models.models import ShiftRoster
        from datetime import date
        
        # Get all TeamMember records for this user
        all_team_members = TeamMember.query.filter_by(user_id=current_user.id).all()
        
        # Find which one is being used in today's shift roster
        team_member = None
        today_date = date.today()
        
        for tm in all_team_members:
            # Check if this TeamMember is in today's shift roster
            shift_entry = ShiftRoster.query.filter_by(
                date=today_date,
                team_member_id=tm.id,
                account_id=current_user.account_id
            ).first()
            
            if shift_entry:
                team_member = tm
                print(f"🎯 Found TeamMember ID {tm.id} in shift roster for {today_date}")
                break
        
        # Fallback to account_id matching if no shift roster entry found
        if not team_member:
            team_member = TeamMember.query.filter_by(
                user_id=current_user.id, 
                account_id=current_user.account_id
            ).first()
        
        # Final fallback to any team member record
        if not team_member:
            team_member = TeamMember.query.filter_by(user_id=current_user.id).first()
        
        if not team_member:
            return jsonify({'error': 'Team member not found'}), 404
        
        # Debug log which team member is being updated
        from models.models import Team
        team = Team.query.get(team_member.team_id)
        print(f"🔧 Updating status for TeamMember ID: {team_member.id}, Team: {team.name if team else 'Unknown'}, Status: {status}")
        
        # Check if there's an active check-in session
        active_checkin = CheckInLog.query.filter(
            and_(
                CheckInLog.team_member_id == team_member.id,
                CheckInLog.checkout_time.is_(None)
            )
        ).first()
        
        # Close previous session if exists
        if active_checkin:
            active_checkin.checkout_time = datetime.utcnow()
            db.session.add(active_checkin)
        
        # Update team member status
        team_member.availability_status = status
        team_member.last_checkin = datetime.utcnow()
        team_member.checkin_location = location if location else None
        db.session.add(team_member)
        
        # Create new check-in log entry (if not checking out)
        if status != 'offline':
            new_checkin = CheckInLog(
                team_member_id=team_member.id,
                user_id=current_user.id,
                status=status,
                checkin_time=datetime.utcnow(),
                location=location,
                notes=notes,
                ip_address=request.environ.get('REMOTE_ADDR'),
                user_agent=request.environ.get('HTTP_USER_AGENT', '')[:256]
            )
            db.session.add(new_checkin)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Successfully checked in as {team_member.status_display}',
            'status': status,
            'display_status': team_member.status_display,
            'timestamp': team_member.last_checkin.strftime('%Y-%m-%d %H:%M:%S') if team_member.last_checkin else None
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Check-in failed: {str(e)}'}), 500

@checkin_bp.route('/api/checkin/status', methods=['GET'])
@login_required
def get_checkin_status():
    """Get current user's check-in status"""
    try:
        team_member = TeamMember.query.filter_by(user_id=current_user.id).first()
        
        if not team_member:
            return jsonify({'error': 'Team member not found'}), 404
        
        return jsonify({
            'success': True,
            'status': team_member.availability_status or 'offline',
            'display_status': team_member.status_display,
            'last_checkin': team_member.last_checkin.strftime('%Y-%m-%d %H:%M:%S') if team_member.last_checkin else None,
            'location': team_member.checkin_location
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to get status: {str(e)}'}), 500

@checkin_bp.route('/api/team-status/<int:team_id>', methods=['GET'])
@login_required
def get_team_status(team_id):
    """Get check-in status for all team members"""
    try:
        # Check if user has access to this team
        user_teams = [tm.team_id for tm in current_user.team_memberships]
        
        # Allow access if user is admin or member of the team
        if current_user.role not in ['super_admin', 'account_admin'] and team_id not in user_teams:
            return jsonify({'error': 'Access denied'}), 403
        
        team_members = TeamMember.query.filter_by(team_id=team_id).all()
        
        status_data = []
        for member in team_members:
            status_data.append({
                'id': member.id,
                'name': member.name,
                'status': member.availability_status or 'offline',
                'display_status': member.status_display,
                'last_checkin': member.last_checkin.strftime('%Y-%m-%d %H:%M:%S') if member.last_checkin else None,
                'location': member.checkin_location,
                'badge_class': member.status_badge_class
            })
        
        return jsonify({
            'success': True,
            'team_members': status_data
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to get team status: {str(e)}'}), 500

@checkin_bp.route('/api/checkin/history', methods=['GET'])
@login_required
def get_checkin_history():
    """Get check-in history for current user"""
    try:
        team_member = TeamMember.query.filter_by(user_id=current_user.id).first()
        
        if not team_member:
            return jsonify({'error': 'Team member not found'}), 404
        
        # Get recent check-in history (last 10 entries)
        history = CheckInLog.query.filter_by(team_member_id=team_member.id)\
            .order_by(CheckInLog.checkin_time.desc())\
            .limit(10).all()
        
        history_data = []
        for entry in history:
            duration = None
            if entry.checkout_time:
                duration_delta = entry.checkout_time - entry.checkin_time
                hours, remainder = divmod(duration_delta.total_seconds(), 3600)
                minutes = remainder // 60
                duration = f"{int(hours)}h {int(minutes)}m"
            
            history_data.append({
                'id': entry.id,
                'status': entry.status,
                'checkin_time': entry.checkin_time.strftime('%Y-%m-%d %H:%M:%S'),
                'checkout_time': entry.checkout_time.strftime('%Y-%m-%d %H:%M:%S') if entry.checkout_time else 'Active',
                'duration': duration,
                'location': entry.location,
                'notes': entry.notes
            })
        
        return jsonify({
            'success': True,
            'history': history_data
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to get history: {str(e)}'}), 500