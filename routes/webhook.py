"""
Webhook endpoint — receives incidents from Power Automate and routes them
to the correct team via assignment-group mapping.

Routing priority:
  1. Explicit team_id in payload
  2. team_name lookup
  3. assignment_group → TeamAssignmentGroup table lookup
  4. Unrouted (stored with routing_status='unrouted', team_id=NULL)

Incidents are upserted by incident_id so status updates don't create duplicates.
"""

import json
import secrets
import logging
from datetime import datetime, timedelta, date as date_type, time as time_type

from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
from functools import wraps

from models.models import (
    db, WebhookIncident, WebhookToken, TeamAssignmentGroup, Team, Account
)

webhook_bp = Blueprint('webhook', __name__)
logger = logging.getLogger(__name__)

_RESOLVED_STATUSES = {'resolved', 'closed', 'complete', 'completed'}


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def _get_active_token():
    token_row = WebhookToken.query.filter_by(is_active=True).first()
    if not token_row:
        token_row = WebhookToken(
            token=secrets.token_urlsafe(32),
            label='power_automate',
            is_active=True,
        )
        db.session.add(token_row)
        db.session.commit()
        logger.info("Generated new webhook token.")
    return token_row


def _require_webhook_token(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        incoming = request.headers.get('X-Webhook-Token', '').strip()
        if not incoming:
            return jsonify({'success': False, 'error': 'Missing X-Webhook-Token header'}), 401
        token_row = WebhookToken.query.filter_by(is_active=True).first()
        if not token_row or not secrets.compare_digest(token_row.token, incoming):
            logger.warning("Webhook: invalid token from %s", request.remote_addr)
            return jsonify({'success': False, 'error': 'Invalid token'}), 403
        return f(*args, **kwargs)
    return decorated


def _require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_user.role not in ('super_admin', 'account_admin', 'team_admin'):
            return jsonify({'success': False, 'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated


# ---------------------------------------------------------------------------
# Internal: resolve team from payload
# ---------------------------------------------------------------------------

def _resolve_team(payload):
    """Return (team_id, account_id, routing_status) from the payload fields."""
    team_id    = payload.get('team_id')
    account_id = payload.get('account_id')

    # Priority 1: explicit team_id
    if team_id:
        team = Team.query.get(int(team_id))
        return (int(team_id), int(account_id) if account_id else (team.account_id if team else None), 'routed')

    # Priority 2: team_name
    team_name = (payload.get('team_name') or '').strip()
    if team_name:
        team = Team.query.filter(Team.name == team_name, Team.is_active == True).first()
        if team:
            return (team.id, int(account_id) if account_id else team.account_id, 'routed')

    # Priority 3: assignment_group mapping
    assignment_group = (payload.get('assignment_group') or '').strip()
    if assignment_group:
        mapping = TeamAssignmentGroup.query.filter(
            TeamAssignmentGroup.is_active == True,
            db.func.lower(TeamAssignmentGroup.assignment_group) == assignment_group.lower(),
        ).first()
        if mapping:
            return (mapping.team_id, int(account_id) if account_id else mapping.account_id, 'routed')
        logger.warning("Webhook: no mapping for assignment_group='%s'", assignment_group)
        return (None, int(account_id) if account_id else None, 'unrouted')

    return (None, int(account_id) if account_id else None, 'unrouted')


def _parse_occurred_at(payload):
    """Parse occurred_at from payload; fall back to now."""
    raw = payload.get('occurred_at') or payload.get('opened_at') or ''
    for fmt in ('%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M'):
        try:
            return datetime.strptime(raw.replace('+00:00', '').rstrip('Z'), fmt.rstrip('Z'))
        except (ValueError, AttributeError):
            continue
    return datetime.utcnow()


# ---------------------------------------------------------------------------
# POST /api/webhook/incidents  — called by Power Automate
# ---------------------------------------------------------------------------

@webhook_bp.route('/api/webhook/incidents', methods=['POST'])
@_require_webhook_token
def receive_incident():
    """
    Upserts an incident by incident_id. Accepts:
    {
        "incident_id":       "INC0001234",          // required
        "title":             "App not responding",
        "application":       "MyApp",
        "priority":          "High",
        "status":            "Active",              // Active|Resolved|Closed
        "assignment_group":  "NOC-APAC-L1",        // used for team routing
        "assigned_to":       "John Doe",
        "escalated_to":      "L2-Bridge",
        "category":          "Infrastructure",
        "description":       "Health check failing",
        "resolution_notes":  "Restarted the service",
        "occurred_at":       "2026-05-10T09:00:00Z",
        "team_id":           7,                     // optional override
        "account_id":        3                      // optional override
    }
    """
    try:
        payload = request.get_json(force=True, silent=True) or {}
        incident_id = (payload.get('incident_id') or '').strip()
        if not incident_id:
            return jsonify({'success': False, 'error': 'incident_id is required'}), 400

        status           = (payload.get('status') or 'Active').strip()
        assignment_group = (payload.get('assignment_group') or '').strip() or None
        is_resolved      = status.lower() in _RESOLVED_STATUSES
        team_id, account_id, routing_status = _resolve_team(payload)
        occurred_at      = _parse_occurred_at(payload)

        # Upsert: look up by incident_id (+ account_id when available to avoid cross-account collisions)
        query = WebhookIncident.query.filter_by(incident_id=incident_id)
        if account_id:
            query = query.filter_by(account_id=account_id)
        existing = query.first()

        def _str(key):
            return (payload.get(key) or '').strip() or None

        if existing:
            existing.status           = status
            existing.assignment_group = assignment_group or existing.assignment_group
            existing.assigned_to      = _str('assigned_to')      or existing.assigned_to
            existing.escalated_to     = _str('escalated_to')     or existing.escalated_to
            existing.description      = _str('description')      or existing.description
            existing.resolution_notes = _str('resolution_notes') or existing.resolution_notes
            existing.category         = _str('category')         or existing.category
            existing.last_updated_at  = datetime.utcnow()
            existing.raw_payload      = json.dumps(payload)
            if is_resolved and not existing.resolved_at:
                existing.resolved_at = datetime.utcnow()
            elif not is_resolved:
                existing.resolved_at = None
            # Re-route if team now resolved
            if team_id:
                existing.team_id        = team_id
                existing.account_id     = account_id
                existing.routing_status = 'routed'
            db.session.commit()
            logger.info("Webhook: updated incident %s (db id=%d, routing=%s)", incident_id, existing.id, existing.routing_status)
            return jsonify({'success': True, 'message': f'Incident {incident_id} updated.', 'id': existing.id, 'action': 'updated'}), 200

        incident = WebhookIncident(
            incident_id      = incident_id,
            application      = _str('application'),
            title            = _str('title'),
            priority         = _str('priority'),
            status           = status,
            description      = _str('description'),
            assigned_to      = _str('assigned_to'),
            escalated_to     = _str('escalated_to'),
            assignment_group = assignment_group,
            category         = _str('category'),
            resolution_notes = _str('resolution_notes'),
            team_id          = team_id,
            account_id       = account_id,
            source           = 'power_automate',
            routing_status   = routing_status,
            is_active        = True,
            occurred_at      = occurred_at,
            resolved_at      = datetime.utcnow() if is_resolved else None,
            last_updated_at  = datetime.utcnow(),
            raw_payload      = json.dumps(payload),
            received_at      = datetime.utcnow(),
        )
        db.session.add(incident)
        db.session.commit()
        logger.info("Webhook: created incident %s (db id=%d, routing=%s)", incident_id, incident.id, routing_status)
        return jsonify({'success': True, 'message': f'Incident {incident_id} received.', 'id': incident.id, 'action': 'created', 'routing_status': routing_status}), 201

    except Exception:
        db.session.rollback()
        logger.exception("Webhook: failed to store incident")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500


# ---------------------------------------------------------------------------
# GET /api/webhook/incidents  — called by the handover form (AJAX)
# ---------------------------------------------------------------------------

@webhook_bp.route('/api/webhook/incidents', methods=['GET'])
@login_required
def get_webhook_incidents():
    """
    Returns webhook incidents for a team filtered by shift time window.

    Query params:
        team_id      (int)    — defaults to current user's team
        account_id   (int)    — defaults to current user's account
        date         (str)    — YYYY-MM-DD  shift date
        shift_start  (str)    — HH:MM  start of shift window
        shift_end    (str)    — HH:MM  end of shift window (handles overnight)
        include_resolved (1)  — include resolved incidents (default: yes)
    """
    try:
        team_id    = request.args.get('team_id',    type=int) or current_user.team_id
        account_id = request.args.get('account_id', type=int) or current_user.account_id
        shift_date = request.args.get('date')
        shift_start_str = request.args.get('shift_start')
        shift_end_str   = request.args.get('shift_end')

        # No is_active filter here — incidents stay queryable regardless of dismiss state.
        # is_active=False only hides incidents from the admin unrouted panel.
        query = WebhookIncident.query
        if team_id:
            query = query.filter_by(team_id=team_id)
        if account_id:
            query = query.filter_by(account_id=account_id)

        # Apply shift window filter on occurred_at
        if shift_date and shift_start_str:
            try:
                d = date_type.fromisoformat(shift_date)
                sh, sm = map(int, shift_start_str.split(':'))
                window_start = datetime.combine(d, time_type(sh, sm))

                if shift_end_str:
                    eh, em = map(int, shift_end_str.split(':'))
                    window_end = datetime.combine(d, time_type(eh, em))
                    if window_end <= window_start:
                        window_end += timedelta(days=1)
                else:
                    window_end = window_start + timedelta(hours=9)

                query = query.filter(
                    WebhookIncident.occurred_at >= window_start,
                    WebhookIncident.occurred_at <= window_end,
                )
            except (ValueError, AttributeError):
                pass

        incidents = query.order_by(WebhookIncident.occurred_at.desc()).all()

        def _fmt_dt(dt):
            return dt.strftime('%Y-%m-%d %H:%M') if dt else ''

        return jsonify({
            'success':   True,
            'incidents': [
                {
                    'id':               i.id,
                    'incident_id':      i.incident_id,
                    'application':      i.application      or '',
                    'title':            i.title            or i.incident_id,
                    'priority':         i.priority         or 'Medium',
                    'status':           i.status           or 'Active',
                    'description':      i.description      or '',
                    'assigned_to':      i.assigned_to      or '',
                    'escalated_to':     i.escalated_to     or '',
                    'assignment_group': i.assignment_group or '',
                    'category':         i.category         or '',
                    'resolution_notes': i.resolution_notes or '',
                    'occurred_at':      _fmt_dt(i.occurred_at),
                    'resolved_at':      _fmt_dt(i.resolved_at),
                    'is_resolved':      i.resolved_at is not None,
                    'routing_status':   i.routing_status   or 'routed',
                }
                for i in incidents
            ],
            'count': len(incidents),
        })

    except Exception:
        logger.exception("Webhook: failed to fetch incidents")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500


# ---------------------------------------------------------------------------
# POST /api/webhook/incidents/<id>/dismiss
# ---------------------------------------------------------------------------

@webhook_bp.route('/api/webhook/incidents/<int:incident_id>/dismiss', methods=['POST'])
@login_required
def dismiss_webhook_incident(incident_id):
    incident = WebhookIncident.query.get_or_404(incident_id)
    incident.is_active = False
    db.session.commit()
    return jsonify({'success': True})


# ---------------------------------------------------------------------------
# GET /api/webhook/incidents/unrouted  — admin: list unrouted incidents
# ---------------------------------------------------------------------------

@webhook_bp.route('/api/webhook/incidents/unrouted', methods=['GET'])
@login_required
@_require_admin
def list_unrouted_incidents():
    try:
        q = WebhookIncident.query.filter_by(routing_status='unrouted')
        if current_user.role != 'super_admin' and current_user.account_id:
            q = q.filter(
                (WebhookIncident.account_id == current_user.account_id) |
                (WebhookIncident.account_id == None)
            )
        rows = q.order_by(WebhookIncident.received_at.desc()).limit(100).all()
        return jsonify({
            'success': True,
            'count':   len(rows),
            'incidents': [
                {
                    'id':               r.id,
                    'incident_id':      r.incident_id,
                    'assignment_group': r.assignment_group or '(none)',
                    'title':            r.title or '',
                    'status':           r.status or '',
                    'received_at':      r.received_at.strftime('%Y-%m-%d %H:%M') if r.received_at else '',
                }
                for r in rows
            ],
        })
    except Exception:
        logger.exception("Webhook: failed to list unrouted")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500


# ---------------------------------------------------------------------------
# POST /api/webhook/incidents/<id>/reroute  — re-run routing for one incident
# ---------------------------------------------------------------------------

@webhook_bp.route('/api/webhook/incidents/<int:incident_id>/reroute', methods=['POST'])
@login_required
@_require_admin
def reroute_incident(incident_id):
    try:
        inc = WebhookIncident.query.get_or_404(incident_id)
        if not inc.assignment_group:
            return jsonify({'success': False, 'error': 'Incident has no assignment_group to route by'}), 400
        mapping = TeamAssignmentGroup.query.filter(
            TeamAssignmentGroup.is_active == True,
            db.func.lower(TeamAssignmentGroup.assignment_group) == inc.assignment_group.lower(),
        ).first()
        if not mapping:
            return jsonify({'success': False, 'error': f'Still no mapping for "{inc.assignment_group}"'}), 404
        inc.team_id        = mapping.team_id
        inc.account_id     = mapping.account_id
        inc.routing_status = 'routed'
        db.session.commit()
        return jsonify({'success': True, 'team_id': mapping.team_id})
    except Exception:
        db.session.rollback()
        logger.exception("Webhook: reroute failed")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500


# ---------------------------------------------------------------------------
# Assignment group CRUD
# ---------------------------------------------------------------------------

@webhook_bp.route('/api/webhook/assignment-groups', methods=['GET'])
@login_required
def list_assignment_groups():
    """List assignment groups for the current user's team(s)."""
    try:
        q = TeamAssignmentGroup.query.filter_by(is_active=True)
        if current_user.role == 'super_admin':
            pass
        elif current_user.role in ('account_admin',):
            q = q.filter_by(account_id=current_user.account_id)
        else:
            q = q.filter_by(team_id=current_user.team_id)

        rows = q.order_by(TeamAssignmentGroup.assignment_group).all()
        return jsonify({
            'success': True,
            'groups': [
                {
                    'id':               r.id,
                    'team_id':          r.team_id,
                    'team_name':        r.team.name if r.team else '',
                    'account_id':       r.account_id,
                    'assignment_group': r.assignment_group,
                    'description':      r.description or '',
                    'created_at':       r.created_at.strftime('%Y-%m-%d') if r.created_at else '',
                }
                for r in rows
            ],
        })
    except Exception:
        logger.exception("Webhook: failed to list assignment groups")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500


@webhook_bp.route('/api/webhook/assignment-groups', methods=['POST'])
@login_required
@_require_admin
def add_assignment_group():
    """Add a new assignment group → team mapping."""
    try:
        data             = request.get_json(force=True, silent=True) or {}
        assignment_group = (data.get('assignment_group') or '').strip()
        team_id          = data.get('team_id')
        account_id       = data.get('account_id')
        description      = (data.get('description') or '').strip() or None

        if not assignment_group:
            return jsonify({'success': False, 'error': 'assignment_group is required'}), 400
        if not team_id:
            return jsonify({'success': False, 'error': 'team_id is required'}), 400

        team = Team.query.get(int(team_id))
        if not team:
            return jsonify({'success': False, 'error': 'Team not found'}), 404

        # Account admins can only add for their own account
        if current_user.role == 'account_admin' and team.account_id != current_user.account_id:
            return jsonify({'success': False, 'error': 'Access denied'}), 403

        resolved_account_id = int(account_id) if account_id else team.account_id

        # Reactivate if soft-deleted
        existing = TeamAssignmentGroup.query.filter(
            TeamAssignmentGroup.account_id == resolved_account_id,
            db.func.lower(TeamAssignmentGroup.assignment_group) == assignment_group.lower(),
        ).first()
        if existing:
            existing.is_active        = True
            existing.team_id          = int(team_id)
            existing.description      = description or existing.description
            existing.created_by_id    = current_user.id
            db.session.commit()
            return jsonify({'success': True, 'id': existing.id, 'action': 'reactivated'})

        row = TeamAssignmentGroup(
            team_id          = int(team_id),
            account_id       = resolved_account_id,
            assignment_group = assignment_group,
            description      = description,
            created_by_id    = current_user.id,
        )
        db.session.add(row)
        db.session.commit()
        return jsonify({'success': True, 'id': row.id, 'action': 'created'}), 201

    except Exception:
        db.session.rollback()
        logger.exception("Webhook: failed to add assignment group")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500


@webhook_bp.route('/api/webhook/assignment-groups/<int:group_id>', methods=['DELETE'])
@login_required
@_require_admin
def delete_assignment_group(group_id):
    """Soft-delete an assignment group mapping."""
    try:
        row = TeamAssignmentGroup.query.get_or_404(group_id)
        if current_user.role == 'account_admin' and row.account_id != current_user.account_id:
            return jsonify({'success': False, 'error': 'Access denied'}), 403
        row.is_active = False
        db.session.commit()
        return jsonify({'success': True})
    except Exception:
        db.session.rollback()
        logger.exception("Webhook: failed to delete assignment group")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500


# ---------------------------------------------------------------------------
# Admin page  GET /webhook/admin
# ---------------------------------------------------------------------------

@webhook_bp.route('/webhook/admin', methods=['GET'])
@login_required
@_require_admin
def webhook_admin_page():
    # Teams available to this admin for the dropdown
    if current_user.role == 'super_admin':
        teams = Team.query.filter_by(is_active=True).order_by(Team.name).all()
    elif current_user.role == 'account_admin':
        teams = Team.query.filter_by(account_id=current_user.account_id, is_active=True).order_by(Team.name).all()
    else:
        teams = Team.query.filter_by(id=current_user.team_id, is_active=True).all()

    token_row     = _get_active_token()
    unrouted_count = WebhookIncident.query.filter_by(routing_status='unrouted').count()
    return render_template('webhook_admin.html',
        teams=teams,
        token=token_row.token,
        unrouted_count=unrouted_count,
    )


# ---------------------------------------------------------------------------
# Token management
# ---------------------------------------------------------------------------

@webhook_bp.route('/api/webhook/token', methods=['GET'])
@login_required
def view_webhook_token():
    if current_user.role not in ('super_admin', 'account_admin'):
        return jsonify({'success': False, 'error': 'Admin access required'}), 403
    token_row = _get_active_token()
    return jsonify({
        'success':    True,
        'token':      token_row.token,
        'label':      token_row.label,
        'created_at': token_row.created_at.strftime('%Y-%m-%d %H:%M') if token_row.created_at else '',
    })


@webhook_bp.route('/api/webhook/token/regenerate', methods=['POST'])
@login_required
def regenerate_webhook_token():
    if current_user.role not in ('super_admin', 'account_admin'):
        return jsonify({'success': False, 'error': 'Admin access required'}), 403
    WebhookToken.query.update({'is_active': False})
    new_token = WebhookToken(token=secrets.token_urlsafe(32), label='power_automate', is_active=True)
    db.session.add(new_token)
    db.session.commit()
    logger.info("Webhook token regenerated by %s", current_user.username)
    return jsonify({'success': True, 'token': new_token.token, 'message': 'New token generated. Update Power Automate.'})
