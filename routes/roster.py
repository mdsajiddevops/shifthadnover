from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from flask import session
from models.models import TeamMember, ShiftRoster, Team, Account, db
from services.multi_team_service import MultiTeamService, apply_team_filtering
from services.team_access_service import TeamAccessService
from datetime import datetime, date
import logging

logger = logging.getLogger(__name__)

roster_bp = Blueprint('roster', __name__)



# Shift Roster View with Month/Year filters
@roster_bp.route('/roster', methods=['GET', 'POST'])
@login_required
def roster():
    if request.method == 'POST' and current_user.role == 'viewer':
        flash('You do not have permission to edit shift roster.')
        return redirect(url_for('roster.roster'))
    # Get filter values from query params
    import calendar
    month_str = request.args.get('month')
    year = request.args.get('year', default=None, type=int)
    now = datetime.now()
    month = None
    if month_str:
        try:
            month = list(calendar.month_name).index(month_str)
        except ValueError:
            month = None
    if not month:
        month = now.month
    if not year:
        year = now.year
    filter_date = request.args.get('filter_date')
    # Default to today's date if no filter is provided
    if not filter_date:
        filter_date = now.strftime('%Y-%m-%d')
    filter_shift = request.args.get('filter_shift')

    query = db.session.query(ShiftRoster)
    account_id = None
    team_id = None
    accounts = []
    teams = []
    if current_user.role == 'super_admin':
        accounts = Account.query.filter_by(is_active=True).all()
        account_id = request.args.get('account_id')
        team_id = request.args.get('team_id')
        # Update session with selected values for consistent filtering
        if account_id:
            session['selected_account_id'] = account_id
        else:
            account_id = session.get('selected_account_id')
        if team_id:
            try:
                team_id = int(team_id)
                session['selected_team_id'] = team_id
            except (TypeError, ValueError):
                team_id = None
        else:
            team_id = session.get('selected_team_id')
        teams = Team.query.filter_by(is_active=True)
        if account_id:
            teams = teams.filter_by(account_id=account_id)
        teams = teams.all()
        if account_id:
            query = query.filter(ShiftRoster.account_id==account_id)
        if team_id:
            query = query.filter(ShiftRoster.team_id==team_id)
        # Ensure team_id is int for team_members query as well
        tm_query = TeamMember.query
        if account_id:
            tm_query = tm_query.filter_by(account_id=account_id)
        if team_id:
            tm_query = tm_query.filter_by(team_id=team_id)
    elif current_user.role == 'account_admin':
        account_id = current_user.account_id
        if not account_id:
            flash('Access denied: No account assigned.', 'error')
            return redirect(url_for('main.dashboard'))
            
        accounts = [Account.query.get(account_id)] if account_id else []
        teams = Team.query.filter_by(account_id=account_id, is_active=True).all()
        team_id = request.args.get('team_id')
        
        # SECURITY FIX: Validate team belongs to admin's account
        if team_id:
            try:
                team_id = int(team_id)
                # Verify the team belongs to the admin's account
                team_exists = Team.query.filter_by(id=team_id, account_id=account_id).first()
                if not team_exists:
                    flash('Access denied: Team not found in your account.', 'error')
                    team_id = None
            except (TypeError, ValueError):
                team_id = None
        
        query = query.filter(ShiftRoster.account_id==account_id)
        if team_id:
            query = query.filter(ShiftRoster.team_id==team_id)
        else:
            # If no team selected, show all teams for account
            team_ids = [t.id for t in teams]
            if team_ids:
                query = query.filter(ShiftRoster.team_id.in_(team_ids))
            else:
                query = query.filter(ShiftRoster.team_id.in_([-1]))  # No teams = no results
    else:
        # Regular users: Show ONLY their own team's roster (not all teams in account)
        account_id = current_user.account_id
        team_id = current_user.team_id  # Use user's assigned team
        
        accounts = [Account.query.get(account_id)] if account_id else []
        
        # Only show user's own team
        if team_id:
            user_team = Team.query.filter_by(id=team_id, account_id=account_id, is_active=True).first()
            teams = [user_team] if user_team else []
        else:
            teams = []
        
        # Check if user has a team assigned
        if not teams:
            flash('No team assigned to your account. Please contact your administrator.', 'info')
            return redirect(url_for('main.dashboard'))
        
        # Filter by account AND user's specific team only
        query = query.filter(ShiftRoster.account_id == account_id)
        query = query.filter(ShiftRoster.team_id == team_id)
        
        # Log access for security monitoring
        from flask import current_app
        current_app.logger.info(f"User {current_user.username} (role: {current_user.role}) accessed roster - account: {account_id}, team: {team_id}")
    # Removed debug flash
    if month:
        query = query.filter(db.extract('month', ShiftRoster.date) == month)
    if year:
        query = query.filter(db.extract('year', ShiftRoster.date) == year)
    roster_entries = query.order_by(ShiftRoster.date).all()
    if not roster_entries:
        pass
    tm_query = TeamMember.query
    if current_user.role == 'super_admin':
        account_id = session.get('selected_account_id')
        team_id = session.get('selected_team_id')
        if account_id:
            tm_query = tm_query.filter_by(account_id=account_id)
        if team_id:
            tm_query = tm_query.filter_by(team_id=team_id)
    elif current_user.role == 'account_admin':
        account_id = current_user.account_id
        team_id = request.args.get('team_id')
        
        # SECURITY FIX: Validate team belongs to admin's account (same as above)
        if team_id:
            try:
                team_id = int(team_id)
                # Verify the team belongs to the admin's account
                team_exists = Team.query.filter_by(id=team_id, account_id=account_id).first()
                if not team_exists:
                    team_id = None
            except (TypeError, ValueError):
                team_id = None
        
        tm_query = tm_query.filter_by(account_id=account_id)
        if team_id:
            tm_query = tm_query.filter_by(team_id=team_id)
        else:
            # If no team selected, show all team members for account
            team_ids = [t.id for t in teams]
            if team_ids:
                tm_query = tm_query.filter(TeamMember.team_id.in_(team_ids))
            else:
                tm_query = tm_query.filter(TeamMember.team_id.in_([-1]))  # No teams = no results
    else:
        # Regular users: show ONLY their own team members
        account_id = current_user.account_id
        team_id = current_user.team_id  # Use user's assigned team
        
        tm_query = tm_query.filter_by(account_id=account_id)
        if team_id:
            tm_query = tm_query.filter_by(team_id=team_id)
        else:
            # No team assigned = no results
            tm_query = tm_query.filter(TeamMember.team_id.in_([-1]))
    all_members_all = tm_query.all()
    # Only include members with at least one shift entry
    member_ids_with_shifts = {entry.team_member_id for entry in roster_entries}
    all_members = [m for m in all_members_all if m.id in member_ids_with_shifts]
    # Debug: Show roster_entries and all_members
    # Removed debug flash
    # Build a set of all dates in the filtered result
    all_dates = sorted({entry.date for entry in roster_entries})
    # Build roster data: {member_name: {date: shift_code}}
    roster_data = {member.name: {date: '' for date in all_dates} for member in all_members}
    for entry in roster_entries:
        member = next((m for m in all_members if m.id == entry.team_member_id), None)
        if member:
            roster_data[member.name][entry.date] = entry.shift_code
    # For dropdowns
    months = [calendar.month_name[i] for i in range(1, 13)]
    # Show current year and next 10 years
    current_year = now.year
    years = [current_year + i for i in range(11)]

    # SECURITY FIX: Team Availability Filter with role-based access control
    present_members = []
    present_members_by_shift = {}
    if filter_date:
        date_obj = datetime.strptime(filter_date, '%Y-%m-%d').date()
        
        # Build base query with role-based security restrictions
        if current_user.role == 'super_admin':
            # Super admin can filter by any account/team
            base_roster_query = ShiftRoster.query.filter(ShiftRoster.date == date_obj)
            if account_id:
                base_roster_query = base_roster_query.filter(ShiftRoster.account_id == account_id)
            if team_id:
                base_roster_query = base_roster_query.filter(ShiftRoster.team_id == team_id)
                
        elif current_user.role == 'account_admin':
            # Account admin restricted to their account only
            base_roster_query = ShiftRoster.query.filter(
                ShiftRoster.date == date_obj,
                ShiftRoster.account_id == current_user.account_id
            )
            if team_id and team_id in [t.id for t in teams]:  # Validate team belongs to account
                base_roster_query = base_roster_query.filter(ShiftRoster.team_id == team_id)
                
        else:
            # Regular users - show ONLY their own team
            user_account_id = current_user.account_id
            user_team_id = current_user.team_id
            
            if not user_account_id or not user_team_id:
                # No account/team assigned = no results
                base_roster_query = ShiftRoster.query.filter(ShiftRoster.id == -1)
            else:
                base_roster_query = ShiftRoster.query.filter(
                    ShiftRoster.date == date_obj,
                    ShiftRoster.account_id == user_account_id,
                    ShiftRoster.team_id == user_team_id  # Only user's team
                )
        
        if filter_shift is not None and filter_shift != '':
            # Single shift filter with security
            present_entries = base_roster_query.filter(ShiftRoster.shift_code == filter_shift).all()
            present_member_ids = [e.team_member_id for e in present_entries]
            
            if present_member_ids:
                # Additional security: ensure team members belong to allowed teams
                allowed_team_ids = []
                if current_user.role == 'super_admin':
                    allowed_team_ids = [t.id for t in Team.query.all()] if not team_id else [team_id]
                elif current_user.role == 'account_admin':
                    allowed_team_ids = [t.id for t in teams]
                else:
                    # Regular users: ONLY their own team
                    allowed_team_ids = [current_user.team_id] if current_user.team_id else []
                
                present_members = TeamMember.query.filter(
                    TeamMember.id.in_(present_member_ids),
                    TeamMember.team_id.in_(allowed_team_ids)
                ).all() if allowed_team_ids else []
            else:
                present_members = []
        else:
            # Group by shift_code with security restrictions
            shift_codes = ['D', 'E', 'N', 'LE', 'G']
            for code in shift_codes:
                entries = base_roster_query.filter(ShiftRoster.shift_code == code).all()
                member_ids = [e.team_member_id for e in entries]
                
                if member_ids:
                    # Apply same team security as above
                    allowed_team_ids = []
                    if current_user.role == 'super_admin':
                        allowed_team_ids = [t.id for t in Team.query.all()] if not team_id else [team_id]
                    elif current_user.role == 'account_admin':
                        allowed_team_ids = [t.id for t in teams]
                    else:
                        # Regular users: ONLY their own team
                        allowed_team_ids = [current_user.team_id] if current_user.team_id else []
                    
                    members = TeamMember.query.filter(
                        TeamMember.id.in_(member_ids),
                        TeamMember.team_id.in_(allowed_team_ids)
                    ).all() if allowed_team_ids else []
                else:
                    members = []
                    
                present_members_by_shift[code] = members
            
            # Ensure all shift codes are present in the dict, even if empty
            for code in shift_codes:
                if code not in present_members_by_shift:
                    present_members_by_shift[code] = []
        
        # Security logging for team availability filter access
        from flask import current_app
        if filter_shift:
            current_app.logger.info(f"User {current_user.username} (role: {current_user.role}) filtered team availability - Date: {filter_date}, Shift: {filter_shift}, Results: {len(present_members)} members")
        else:
            total_members = sum(len(members) for members in present_members_by_shift.values())
            current_app.logger.info(f"User {current_user.username} (role: {current_user.role}) viewed team availability - Date: {filter_date}, All shifts, Results: {total_members} members")

    # Set team filter context for template
    if current_user.role not in ['super_admin', 'account_admin']:
        team_filter_context = TeamAccessService.get_team_filter_context()
    else:
        team_filter_context = None
    
    return render_template(
        'shift_roster.html',
        all_dates=all_dates,
        all_members=all_members,
        roster_data=roster_data,
        months=months,
        years=years,
        selected_month=month,
        selected_year=year,
        filter_date=filter_date,
        filter_shift=filter_shift,
        present_members=present_members,
        present_members_by_shift=present_members_by_shift if 'present_members_by_shift' in locals() else {},
        accounts=accounts,
        teams=teams,
        selected_account_id=account_id,
        selected_team_id=team_id,
        team_filter_context=team_filter_context
    )


# ========================================
# ROSTER API ENDPOINTS (CRUD Operations)
# ========================================

# Valid shift codes for validation
VALID_SHIFT_CODES = ['D', 'E', 'N', 'LE', 'G', 'VL', 'HL', 'CO', 'SL', 'OS', 'OF', 'O', '']


def is_admin():
    """Check if current user has admin privileges"""
    return current_user.is_authenticated and current_user.role in ['super_admin', 'account_admin', 'team_admin']


def can_access_roster(account_id, team_id):
    """
    Check if current user can access/modify roster for given account/team.
    Returns True if authorized, False otherwise.
    """
    if not current_user.is_authenticated:
        return False
    
    if current_user.role == 'super_admin':
        return True
    
    if current_user.role == 'account_admin':
        return current_user.account_id == account_id
    
    if current_user.role == 'team_admin':
        return current_user.account_id == account_id and current_user.team_id == team_id
    
    return False


@roster_bp.route('/api/roster/update', methods=['POST'])
@login_required
def update_roster_entry():
    """
    Update a single roster entry (shift code).
    
    Request JSON:
    {
        "roster_id": int (optional - if updating existing entry),
        "member_id": int,
        "date": "YYYY-MM-DD",
        "shift_code": "D" | "E" | "N" | "LE" | "G" | "VL" | "HL" | "CO" | "" (empty for off)
    }
    """
    if not is_admin():
        return jsonify({'success': False, 'error': 'Admin access required'}), 403
    
    try:
        data = request.get_json()
        
        roster_id = data.get('roster_id')
        member_id = data.get('member_id')
        date_str = data.get('date')
        shift_code = data.get('shift_code', '').strip().upper()
        
        # Validate shift code
        if shift_code and shift_code not in VALID_SHIFT_CODES:
            return jsonify({'success': False, 'error': f'Invalid shift code: {shift_code}'}), 400
        
        # Parse date
        try:
            entry_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            return jsonify({'success': False, 'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        
        # Get member to verify account/team access
        member = TeamMember.query.get(member_id)
        if not member:
            return jsonify({'success': False, 'error': 'Team member not found'}), 404
        
        # Authorization check
        if not can_access_roster(member.account_id, member.team_id):
            return jsonify({'success': False, 'error': 'Unauthorized to modify this roster'}), 403
        
        if roster_id:
            # Update existing entry
            roster_entry = ShiftRoster.query.get(roster_id)
            if not roster_entry:
                return jsonify({'success': False, 'error': 'Roster entry not found'}), 404
            
            if shift_code:
                roster_entry.shift_code = shift_code
                db.session.commit()
                logger.info(f"[ROSTER EDIT] User {current_user.username} updated roster ID {roster_id}: {shift_code}")
            else:
                # Empty shift code = delete the entry
                db.session.delete(roster_entry)
                db.session.commit()
                logger.info(f"[ROSTER EDIT] User {current_user.username} deleted roster ID {roster_id}")
                return jsonify({'success': True, 'message': 'Shift entry removed', 'action': 'deleted'})
        else:
            # Check if entry exists for this member/date
            existing = ShiftRoster.query.filter_by(
                team_member_id=member_id,
                date=entry_date,
                account_id=member.account_id,
                team_id=member.team_id
            ).first()
            
            if existing:
                if shift_code:
                    existing.shift_code = shift_code
                    db.session.commit()
                    logger.info(f"[ROSTER EDIT] User {current_user.username} updated existing entry for {member.name} on {entry_date}: {shift_code}")
                else:
                    db.session.delete(existing)
                    db.session.commit()
                    logger.info(f"[ROSTER EDIT] User {current_user.username} deleted entry for {member.name} on {entry_date}")
                    return jsonify({'success': True, 'message': 'Shift entry removed', 'action': 'deleted'})
            else:
                if not shift_code:
                    return jsonify({'success': True, 'message': 'No entry to remove', 'action': 'none'})
                
                # Create new entry
                new_entry = ShiftRoster(
                    date=entry_date,
                    shift_code=shift_code,
                    team_member_id=member_id,
                    account_id=member.account_id,
                    team_id=member.team_id
                )
                db.session.add(new_entry)
                db.session.commit()
                logger.info(f"[ROSTER EDIT] User {current_user.username} created new entry for {member.name} on {entry_date}: {shift_code}")
        
        return jsonify({
            'success': True,
            'message': 'Roster updated successfully',
            'shift_code': shift_code,
            'action': 'updated'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"[ROSTER EDIT] Error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@roster_bp.route('/api/roster/bulk-update', methods=['POST'])
@login_required
def bulk_update_roster():
    """
    Bulk update roster entries for a member across multiple dates.
    
    Request JSON:
    {
        "member_id": int,
        "updates": [
            {"date": "YYYY-MM-DD", "shift_code": "D"},
            {"date": "YYYY-MM-DD", "shift_code": "N"},
            ...
        ]
    }
    """
    if not is_admin():
        return jsonify({'success': False, 'error': 'Admin access required'}), 403
    
    try:
        data = request.get_json()
        member_id = data.get('member_id')
        updates = data.get('updates', [])
        
        member = TeamMember.query.get(member_id)
        if not member:
            return jsonify({'success': False, 'error': 'Team member not found'}), 404
        
        if not can_access_roster(member.account_id, member.team_id):
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
        updated_count = 0
        created_count = 0
        deleted_count = 0
        
        for update in updates:
            date_str = update.get('date')
            shift_code = update.get('shift_code', '').strip().upper()
            
            try:
                entry_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except (ValueError, TypeError):
                continue
            
            existing = ShiftRoster.query.filter_by(
                team_member_id=member_id,
                date=entry_date,
                account_id=member.account_id,
                team_id=member.team_id
            ).first()
            
            if existing:
                if shift_code:
                    existing.shift_code = shift_code
                    updated_count += 1
                else:
                    db.session.delete(existing)
                    deleted_count += 1
            elif shift_code:
                new_entry = ShiftRoster(
                    date=entry_date,
                    shift_code=shift_code,
                    team_member_id=member_id,
                    account_id=member.account_id,
                    team_id=member.team_id
                )
                db.session.add(new_entry)
                created_count += 1
        
        db.session.commit()
        logger.info(f"[ROSTER BULK] User {current_user.username} bulk updated {member.name}: {updated_count} updated, {created_count} created, {deleted_count} deleted")
        
        return jsonify({
            'success': True,
            'message': f'Updated {updated_count}, created {created_count}, deleted {deleted_count} entries',
            'updated': updated_count,
            'created': created_count,
            'deleted': deleted_count
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"[ROSTER BULK] Error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@roster_bp.route('/api/roster/delete/<int:roster_id>', methods=['DELETE'])
@login_required
def delete_roster_entry(roster_id):
    """Delete a single roster entry."""
    if not is_admin():
        return jsonify({'success': False, 'error': 'Admin access required'}), 403
    
    try:
        roster_entry = ShiftRoster.query.get(roster_id)
        if not roster_entry:
            return jsonify({'success': False, 'error': 'Roster entry not found'}), 404
        
        if not can_access_roster(roster_entry.account_id, roster_entry.team_id):
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
        member = TeamMember.query.get(roster_entry.team_member_id)
        member_name = member.name if member else 'Unknown'
        
        db.session.delete(roster_entry)
        db.session.commit()
        
        logger.info(f"[ROSTER DELETE] User {current_user.username} deleted roster entry {roster_id} for {member_name}")
        
        return jsonify({'success': True, 'message': 'Roster entry deleted'})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"[ROSTER DELETE] Error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@roster_bp.route('/api/roster/member/<int:member_id>/month', methods=['GET'])
@login_required
def get_member_roster(member_id):
    """
    Get roster data for a specific member for a month.
    
    Query params:
        - month: int (1-12)
        - year: int
    """
    try:
        member = TeamMember.query.get(member_id)
        if not member:
            return jsonify({'success': False, 'error': 'Member not found'}), 404
        
        month = request.args.get('month', type=int)
        year = request.args.get('year', type=int)
        
        if not month or not year:
            now = datetime.now()
            month = month or now.month
            year = year or now.year
        
        entries = ShiftRoster.query.filter(
            ShiftRoster.team_member_id == member_id,
            db.extract('month', ShiftRoster.date) == month,
            db.extract('year', ShiftRoster.date) == year
        ).all()
        
        roster_data = {
            entry.date.strftime('%Y-%m-%d'): {
                'id': entry.id,
                'shift_code': entry.shift_code
            }
            for entry in entries
        }
        
        return jsonify({
            'success': True,
            'member_id': member_id,
            'member_name': member.name,
            'month': month,
            'year': year,
            'roster': roster_data
        })
        
    except Exception as e:
        logger.error(f"[ROSTER GET] Error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@roster_bp.route('/api/roster/add-member-shift', methods=['POST'])
@login_required
def add_member_shift():
    """
    Add a new shift entry for a member on a specific date.
    Creates entry if doesn't exist, updates if exists.
    
    Request JSON:
    {
        "member_id": int,
        "date": "YYYY-MM-DD",
        "shift_code": "D" | "E" | "N" | etc.
    }
    """
    if not is_admin():
        return jsonify({'success': False, 'error': 'Admin access required'}), 403
    
    try:
        data = request.get_json()
        member_id = data.get('member_id')
        date_str = data.get('date')
        shift_code = data.get('shift_code', '').strip().upper()
        
        if not member_id or not date_str or not shift_code:
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        if shift_code not in VALID_SHIFT_CODES:
            return jsonify({'success': False, 'error': f'Invalid shift code: {shift_code}'}), 400
        
        try:
            entry_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'success': False, 'error': 'Invalid date format'}), 400
        
        member = TeamMember.query.get(member_id)
        if not member:
            return jsonify({'success': False, 'error': 'Member not found'}), 404
        
        if not can_access_roster(member.account_id, member.team_id):
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
        # Check if entry exists
        existing = ShiftRoster.query.filter_by(
            team_member_id=member_id,
            date=entry_date,
            account_id=member.account_id,
            team_id=member.team_id
        ).first()
        
        if existing:
            existing.shift_code = shift_code
            action = 'updated'
        else:
            new_entry = ShiftRoster(
                date=entry_date,
                shift_code=shift_code,
                team_member_id=member_id,
                account_id=member.account_id,
                team_id=member.team_id
            )
            db.session.add(new_entry)
            action = 'created'
        
        db.session.commit()
        logger.info(f"[ROSTER ADD] User {current_user.username} {action} shift for {member.name} on {entry_date}: {shift_code}")
        
        return jsonify({
            'success': True,
            'message': f'Shift {action} successfully',
            'action': action,
            'shift_code': shift_code
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"[ROSTER ADD] Error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@roster_bp.route('/api/roster/team-members', methods=['GET'])
@login_required
def get_team_members_for_roster():
    """
    Get team members for roster editing dropdown.
    
    Query params:
        - account_id: int (required for super_admin)
        - team_id: int (required)
    """
    try:
        account_id = request.args.get('account_id', type=int)
        team_id = request.args.get('team_id', type=int)
        
        if current_user.role == 'super_admin':
            if not account_id or not team_id:
                return jsonify({'success': False, 'error': 'Account and team required'}), 400
        elif current_user.role == 'account_admin':
            account_id = current_user.account_id
            if not team_id:
                return jsonify({'success': False, 'error': 'Team required'}), 400
        else:
            account_id = current_user.account_id
            team_id = current_user.team_id
        
        members = TeamMember.query.filter_by(
            account_id=account_id,
            team_id=team_id,
            is_active=True
        ).order_by(TeamMember.name).all()
        
        return jsonify({
            'success': True,
            'members': [
                {'id': m.id, 'name': m.name, 'employee_id': m.employee_id}
                for m in members
            ]
        })
        
    except Exception as e:
        logger.error(f"[ROSTER MEMBERS] Error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

