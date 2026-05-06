"""
Roster Scheduler Blueprint — Phase 2 Flask integration.

Pages:
  GET  /roster-scheduler            — main grid view (all roles)
  GET  /admin/roster-scheduler      — admin settings (coverage reqs, holidays, member roles)

API endpoints:
  GET  /api/roster/schedule         — fetch current month grid
  POST /api/roster/generate         — generate + persist schedule
  POST /api/roster/preview          — dry-run preview
  POST /api/roster/leave            — apply leave + auto-fix
  GET  /api/roster/coverage-requirements          — list coverage reqs for team
  POST /api/roster/coverage-requirements          — create/update req
  DELETE /api/roster/coverage-requirements/<id>   — delete req
  GET  /api/roster/holidays         — list holidays for account+year
  POST /api/roster/holidays         — create holiday
  DELETE /api/roster/holidays/<id>  — delete holiday
  GET  /api/roster/members          — list team members with scheduling_role
  PUT  /api/roster/members/<id>/role — update scheduling_role
"""
from datetime import date, datetime

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user

from models.models import db, TeamMember
from models.roster_scheduler_models import (
    ScheduledShift,
    ShiftCoverageRequirement,
    PublicHoliday,
)

roster_scheduler_bp = Blueprint('roster_scheduler', __name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _admin_required():
    return current_user.role in ('super_admin', 'account_admin', 'team_admin')


def _current_account_team():
    """Return (account_id, team_id) from session or current_user."""
    from flask import session
    account_id = session.get('selected_account_id') or getattr(current_user, 'account_id', None)
    team_id = session.get('selected_team_id') or getattr(current_user, 'team_id', None)
    return account_id, team_id


def _parse_year_month(req):
    today = date.today()
    try:
        year = int(req.args.get('year', today.year))
        month = int(req.args.get('month', today.month))
    except (ValueError, TypeError):
        year, month = today.year, today.month
    return year, month


# ---------------------------------------------------------------------------
# Page views
# ---------------------------------------------------------------------------

@roster_scheduler_bp.route('/roster-scheduler')
@login_required
def roster_scheduler():
    """Main roster scheduler view — available to all authenticated users."""
    account_id, team_id = _current_account_team()
    today = date.today()
    year = int(request.args.get('year', today.year))
    month = int(request.args.get('month', today.month))

    # Clamp
    if month < 1:
        month, year = 12, year - 1
    elif month > 12:
        month, year = 1, year + 1

    # Month navigation labels
    import calendar
    month_name = calendar.month_name[month]

    # Fetch teams for selector (super_admin sees all, others see own)
    from models.models import Team
    if current_user.role == 'super_admin':
        teams = Team.query.filter_by(account_id=account_id).all() if account_id else []
    else:
        teams = Team.query.filter_by(account_id=account_id).all() if account_id else []

    return render_template(
        'roster_scheduler/index.html',
        year=year,
        month=month,
        month_name=month_name,
        teams=teams,
        team_id=team_id,
        account_id=account_id,
    )


@roster_scheduler_bp.route('/admin/roster-scheduler')
@login_required
def roster_scheduler_admin():
    """Admin settings page — coverage requirements, holidays, member roles."""
    if not _admin_required():
        flash('Admin access required.', 'danger')
        return redirect(url_for('roster_scheduler.roster_scheduler'))

    account_id, team_id = _current_account_team()

    from models.models import Team
    if current_user.role == 'super_admin':
        teams = Team.query.filter_by(account_id=account_id).all() if account_id else []
    else:
        teams = Team.query.filter_by(account_id=account_id).all() if account_id else []

    today = date.today()
    return render_template(
        'roster_scheduler/admin.html',
        teams=teams,
        team_id=team_id,
        account_id=account_id,
        current_year=today.year,
    )


# ---------------------------------------------------------------------------
# API — schedule
# ---------------------------------------------------------------------------

@roster_scheduler_bp.route('/api/roster/schedule')
@login_required
def api_get_schedule():
    account_id, team_id = _current_account_team()
    year, month = _parse_year_month(request)

    req_team_id = request.args.get('team_id', team_id)
    try:
        req_team_id = int(req_team_id)
    except (ValueError, TypeError):
        return jsonify({'success': False, 'error': 'Invalid team_id'}), 400

    from services.roster_scheduler_service import get_shift_view
    try:
        data = get_shift_view(req_team_id, account_id, year, month)
        return jsonify({'success': True, 'data': data, 'year': year, 'month': month})
    except Exception as exc:
        return jsonify({'success': False, 'error': str(exc)}), 500


@roster_scheduler_bp.route('/api/roster/generate', methods=['POST'])
@login_required
def api_generate_schedule():
    if not _admin_required():
        return jsonify({'success': False, 'error': 'Admin required'}), 403

    account_id, team_id = _current_account_team()
    body = request.get_json(force=True) or {}

    try:
        req_team_id = int(body.get('team_id', team_id))
        year = int(body.get('year', date.today().year))
        month = int(body.get('month', date.today().month))
        overwrite = bool(body.get('overwrite', False))
    except (ValueError, TypeError) as exc:
        return jsonify({'success': False, 'error': f'Invalid parameters: {exc}'}), 400

    from services.roster_scheduler_service import generate_month_schedule
    try:
        result = generate_month_schedule(req_team_id, account_id, year, month,
                                         overwrite=overwrite)
        return jsonify({'success': True, **result})
    except Exception as exc:
        return jsonify({'success': False, 'error': str(exc)}), 500


@roster_scheduler_bp.route('/api/roster/preview', methods=['POST'])
@login_required
def api_preview_schedule():
    if not _admin_required():
        return jsonify({'success': False, 'error': 'Admin required'}), 403

    account_id, team_id = _current_account_team()
    body = request.get_json(force=True) or {}

    try:
        req_team_id = int(body.get('team_id', team_id))
        year = int(body.get('year', date.today().year))
        month = int(body.get('month', date.today().month))
    except (ValueError, TypeError) as exc:
        return jsonify({'success': False, 'error': f'Invalid parameters: {exc}'}), 400

    from services.roster_scheduler_service import preview_month_schedule
    try:
        result = preview_month_schedule(req_team_id, account_id, year, month)
        return jsonify({'success': True, **result})
    except Exception as exc:
        return jsonify({'success': False, 'error': str(exc)}), 500


@roster_scheduler_bp.route('/api/roster/leave', methods=['POST'])
@login_required
def api_apply_leave():
    if not _admin_required():
        return jsonify({'success': False, 'error': 'Admin required'}), 403

    account_id, team_id = _current_account_team()
    body = request.get_json(force=True) or {}

    try:
        member_id = int(body['member_id'])
        leave_code = str(body['leave_code'])
        raw_dates = body['dates']  # list of "YYYY-MM-DD"
        dates = [date.fromisoformat(d) for d in raw_dates]
        auto_fix = bool(body.get('auto_fix', True))
    except (KeyError, ValueError, TypeError) as exc:
        return jsonify({'success': False, 'error': f'Invalid parameters: {exc}'}), 400

    from services.roster_scheduler_service import apply_leave
    try:
        result = apply_leave(member_id, dates, leave_code, account_id, team_id, auto_fix)
        return jsonify({'success': True, **result})
    except ValueError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400
    except Exception as exc:
        return jsonify({'success': False, 'error': str(exc)}), 500


# ---------------------------------------------------------------------------
# API — coverage requirements
# ---------------------------------------------------------------------------

@roster_scheduler_bp.route('/api/roster/coverage-requirements', methods=['GET'])
@login_required
def api_get_coverage_reqs():
    account_id, team_id = _current_account_team()
    req_team_id = request.args.get('team_id', team_id)
    try:
        req_team_id = int(req_team_id)
    except (ValueError, TypeError):
        return jsonify({'success': False, 'error': 'Invalid team_id'}), 400

    rows = ShiftCoverageRequirement.query.filter_by(
        team_id=req_team_id, is_active=True
    ).order_by(ShiftCoverageRequirement.shift_code).all()

    return jsonify({'success': True, 'data': [
        {'id': r.id, 'shift_code': r.shift_code, 'required_count': r.required_count}
        for r in rows
    ]})


@roster_scheduler_bp.route('/api/roster/coverage-requirements', methods=['POST'])
@login_required
def api_upsert_coverage_req():
    if not _admin_required():
        return jsonify({'success': False, 'error': 'Admin required'}), 403

    account_id, team_id = _current_account_team()
    body = request.get_json(force=True) or {}

    try:
        req_team_id = int(body.get('team_id', team_id))
        shift_code = str(body['shift_code']).strip().upper()
        required_count = str(body['required_count']).strip()
    except (KeyError, ValueError, TypeError) as exc:
        return jsonify({'success': False, 'error': f'Invalid parameters: {exc}'}), 400

    # Validate required_count
    if required_count != '*' and not required_count.isdigit():
        return jsonify({'success': False, 'error': 'required_count must be a number or *'}), 400

    existing = ShiftCoverageRequirement.query.filter_by(
        team_id=req_team_id, shift_code=shift_code
    ).first()
    if existing:
        existing.required_count = required_count
        existing.is_active = True
    else:
        existing = ShiftCoverageRequirement(
            team_id=req_team_id,
            account_id=account_id,
            shift_code=shift_code,
            required_count=required_count,
        )
        db.session.add(existing)
    db.session.commit()
    return jsonify({'success': True, 'id': existing.id})


@roster_scheduler_bp.route('/api/roster/coverage-requirements/<int:req_id>', methods=['DELETE'])
@login_required
def api_delete_coverage_req(req_id):
    if not _admin_required():
        return jsonify({'success': False, 'error': 'Admin required'}), 403

    row = ShiftCoverageRequirement.query.get_or_404(req_id)
    row.is_active = False
    db.session.commit()
    return jsonify({'success': True})


# ---------------------------------------------------------------------------
# API — public holidays
# ---------------------------------------------------------------------------

@roster_scheduler_bp.route('/api/roster/holidays', methods=['GET'])
@login_required
def api_get_holidays():
    account_id, _ = _current_account_team()
    try:
        year = int(request.args.get('year', date.today().year))
    except (ValueError, TypeError):
        year = date.today().year

    import calendar
    start = date(year, 1, 1)
    end = date(year, 12, 31)
    rows = PublicHoliday.query.filter(
        PublicHoliday.account_id == account_id,
        PublicHoliday.date >= start,
        PublicHoliday.date <= end,
        PublicHoliday.is_active == True,
    ).order_by(PublicHoliday.date).all()

    return jsonify({'success': True, 'data': [
        {'id': r.id, 'date': r.date.isoformat(), 'name': r.name}
        for r in rows
    ]})


@roster_scheduler_bp.route('/api/roster/holidays', methods=['POST'])
@login_required
def api_create_holiday():
    if not _admin_required():
        return jsonify({'success': False, 'error': 'Admin required'}), 403

    account_id, _ = _current_account_team()
    body = request.get_json(force=True) or {}

    try:
        holiday_date = date.fromisoformat(str(body['date']))
        name = str(body['name']).strip()
    except (KeyError, ValueError, TypeError) as exc:
        return jsonify({'success': False, 'error': f'Invalid parameters: {exc}'}), 400

    if not name:
        return jsonify({'success': False, 'error': 'Holiday name is required'}), 400

    existing = PublicHoliday.query.filter_by(
        account_id=account_id, date=holiday_date
    ).first()
    if existing:
        existing.name = name
        existing.is_active = True
    else:
        existing = PublicHoliday(account_id=account_id, date=holiday_date, name=name)
        db.session.add(existing)
    db.session.commit()
    return jsonify({'success': True, 'id': existing.id})


@roster_scheduler_bp.route('/api/roster/holidays/<int:holiday_id>', methods=['DELETE'])
@login_required
def api_delete_holiday(holiday_id):
    if not _admin_required():
        return jsonify({'success': False, 'error': 'Admin required'}), 403

    row = PublicHoliday.query.get_or_404(holiday_id)
    row.is_active = False
    db.session.commit()
    return jsonify({'success': True})


# ---------------------------------------------------------------------------
# API — team members (scheduling_role)
# ---------------------------------------------------------------------------

@roster_scheduler_bp.route('/api/roster/members')
@login_required
def api_get_members():
    account_id, team_id = _current_account_team()
    req_team_id = request.args.get('team_id', team_id)
    try:
        req_team_id = int(req_team_id)
    except (ValueError, TypeError):
        return jsonify({'success': False, 'error': 'Invalid team_id'}), 400

    members = TeamMember.query.filter_by(
        team_id=req_team_id, account_id=account_id, is_active=True
    ).order_by(TeamMember.name).all()

    return jsonify({'success': True, 'data': [
        {
            'id': m.id,
            'name': m.name,
            'role': m.role,
            'scheduling_role': getattr(m, 'scheduling_role', 'support') or 'support',
        }
        for m in members
    ]})


@roster_scheduler_bp.route('/api/roster/members/<int:member_id>/role', methods=['PUT'])
@login_required
def api_update_member_role(member_id):
    if not _admin_required():
        return jsonify({'success': False, 'error': 'Admin required'}), 403

    body = request.get_json(force=True) or {}
    scheduling_role = str(body.get('scheduling_role', 'support')).lower()
    if scheduling_role not in ('lead', 'support'):
        return jsonify({'success': False, 'error': "scheduling_role must be 'lead' or 'support'"}), 400

    member = TeamMember.query.get_or_404(member_id)
    member.scheduling_role = scheduling_role
    db.session.commit()
    return jsonify({'success': True})
