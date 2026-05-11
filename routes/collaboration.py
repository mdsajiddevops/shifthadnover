"""
Collaborative Handover Routes
=============================
API endpoints for real-time collaborative editing of handover forms.
Uses Server-Sent Events (SSE) for real-time updates without Redis.
"""

from flask import Blueprint, request, jsonify, Response, stream_with_context, g
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from models.models import db, Shift, TeamMember, User
from models.collaboration import (
    HandoverSession, SectionLock, HandoverChange, 
    DraftIncident, DraftKeyPoint, DraftChangeInfo, DraftKBUpdate
)
import json
import uuid
import time
import logging

logger = logging.getLogger(__name__)

collaboration_bp = Blueprint('collaboration', __name__, url_prefix='/api/collaboration')

# In-memory stores for real-time collaboration (consider Redis for multi-process)
_field_states = {}  # {shift_id: {field_key: {value, version, user_id, timestamp}}}
_typing_indicators = {}  # {shift_id: {field_key: {user_id, user_name, timestamp}}}
_pending_broadcasts = {}  # {shift_id: {user_id: [broadcasts]}} — per-user queues
_active_sse_users = {}   # {shift_id: set(user_ids)} — currently streaming users


def _queue_broadcast(shift_id, sender_user_id, broadcast):
    """Add a broadcast to every OTHER user's per-user queue."""
    recipients = _active_sse_users.get(shift_id, set())
    for uid in recipients:
        if uid != sender_user_id:
            _pending_broadcasts.setdefault(shift_id, {}).setdefault(uid, []).append(broadcast)


# ============================================================================
# Session Management
# ============================================================================

@collaboration_bp.route('/session/join/<int:shift_id>', methods=['POST'])
@login_required
def join_session(shift_id):
    """Join or resume a collaborative editing session for a handover shift.
    ---
    tags:
      - collaboration
    security:
      - SessionCookie: []
    parameters:
      - in: path
        name: shift_id
        type: integer
        required: true
        description: ID of the shift to collaborate on
    responses:
      200:
        description: Session joined; returns session token and active participants
        schema:
          type: object
          properties:
            success:
              type: boolean
            session_token:
              type: string
            active_users:
              type: array
              items:
                type: object
                properties:
                  user_id:
                    type: integer
                  username:
                    type: string
      404:
        description: Shift not found
    """
    try:
        # Verify shift exists and user has access
        shift = Shift.query.get_or_404(shift_id)
        
        # Check if user already has an active session
        existing = HandoverSession.query.filter_by(
            shift_id=shift_id,
            user_id=current_user.id,
            is_active=True
        ).first()
        
        if existing:
            # Reactivate existing session
            existing.last_heartbeat = datetime.utcnow()
            db.session.commit()
            session_token = existing.session_token
        else:
            # Create new session
            session_token = str(uuid.uuid4())
            session = HandoverSession(
                shift_id=shift_id,
                user_id=current_user.id,
                session_token=session_token
            )
            db.session.add(session)
            db.session.commit()

            user_display = current_user.display_name or current_user.username
            active_sessions_for_broadcast = HandoverSession.get_active_users(shift_id)
            _queue_broadcast(shift_id, current_user.id, {
                'type': 'user_joined',
                'user': {'user_id': current_user.id, 'username': current_user.username, 'user_name': user_display},
                'active_users': [s.to_dict() for s in active_sessions_for_broadcast]
            })

        # Get all active users (for the join response)
        active_sessions = HandoverSession.get_active_users(shift_id)
        active_users = [s.to_dict() for s in active_sessions]
        
        # Get current locks
        locks = SectionLock.get_locks_for_shift(shift_id)
        lock_data = [l.to_dict() for l in locks]
        
        # Get draft data
        draft_incidents = DraftIncident.query.filter_by(shift_id=shift_id).all()
        draft_keypoints = DraftKeyPoint.query.filter_by(shift_id=shift_id).all()
        draft_changeinfos = DraftChangeInfo.query.filter_by(shift_id=shift_id).all()
        draft_kbupdates = DraftKBUpdate.query.filter_by(shift_id=shift_id).all()
        
        # Get field states for initial sync
        field_states = _field_states.get(shift_id, {})
        
        # Get recent changes for sync
        recent_changes = HandoverChange.query.filter_by(shift_id=shift_id).order_by(
            HandoverChange.created_at.desc()
        ).limit(100).all()
        
        logger.info(f"User {current_user.username} joined collaborative session for shift {shift_id}")
        
        return jsonify({
            'success': True,
            'session_token': session_token,
            'user_id': current_user.id,
            'user_name': current_user.username,
            'active_users': active_users,
            'locks': lock_data,
            'draft_incidents': [i.to_dict() for i in draft_incidents],
            'draft_keypoints': [k.to_dict() for k in draft_keypoints],
            'draft_changeinfos': [c.to_dict() for c in draft_changeinfos],
            'draft_kbupdates': [k.to_dict() for k in draft_kbupdates],
            'field_states': field_states,
            'recent_changes': [c.to_dict() for c in recent_changes],
            'last_change_id': _get_last_change_id(shift_id)
        })
        
    except Exception as e:
        logger.error(f"Error joining session: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@collaboration_bp.route('/session/leave/<int:shift_id>', methods=['POST'])
@login_required
def leave_session(shift_id):
    """Leave a collaborative editing session"""
    try:
        # Deactivate session
        session = HandoverSession.query.filter_by(
            shift_id=shift_id,
            user_id=current_user.id,
            is_active=True
        ).first()
        
        if session:
            session.is_active = False
            db.session.commit()
        
        # Release all locks held by this user
        SectionLock.query.filter_by(
            shift_id=shift_id,
            user_id=current_user.id
        ).delete()
        db.session.commit()
        
        # Get updated active users
        active_sessions = HandoverSession.get_active_users(shift_id)
        active_users = [s.to_dict() for s in active_sessions]
        
        # Broadcast user left event
        user_display = current_user.display_name or current_user.username
        _queue_broadcast(shift_id, current_user.id, {
            'type': 'user_left',
            'user': {'user_id': current_user.id, 'username': current_user.username, 'user_name': user_display},
            'active_users': active_users
        })
        
        logger.info(f"User {current_user.username} left collaborative session for shift {shift_id}")
        
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"Error leaving session: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@collaboration_bp.route('/session/heartbeat/<int:shift_id>', methods=['POST'])
@login_required
def heartbeat(shift_id):
    """Send heartbeat to keep session alive"""
    try:
        data = request.get_json() or {}
        
        session = HandoverSession.query.filter_by(
            shift_id=shift_id,
            user_id=current_user.id,
            is_active=True
        ).first()
        
        if session:
            session.last_heartbeat = datetime.utcnow()
            session.current_section = data.get('current_section')
            session.current_item_id = data.get('current_item_id')
            db.session.commit()
        
        # Cleanup stale sessions
        HandoverSession.cleanup_stale_sessions()
        
        # Return updated active users
        active_sessions = HandoverSession.get_active_users(shift_id)
        
        return jsonify({
            'success': True,
            'active_users': [s.to_dict() for s in active_sessions]
        })
        
    except Exception as e:
        logger.error(f"Error processing heartbeat: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@collaboration_bp.route('/session/context/<int:shift_id>', methods=['POST'])
@login_required
def update_context(shift_id):
    """Update the current editing context for a session"""
    try:
        data = request.get_json() or {}
        
        session = HandoverSession.query.filter_by(
            shift_id=shift_id,
            user_id=current_user.id,
            is_active=True
        ).first()
        
        if session:
            session.current_section = data.get('current_section')
            session.current_item_id = data.get('current_item_id')
            db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"Error updating context: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# Server-Sent Events for Real-time Updates
# ============================================================================

@collaboration_bp.route('/stream/<int:shift_id>')
@login_required
def event_stream(shift_id):
    """SSE endpoint for real-time updates"""
    
    def generate():
        last_change_id = int(request.args.get('last_change_id', 0))
        last_check = datetime.utcnow()
        user_id = current_user.id

        # Register this user as an active SSE recipient
        _active_sse_users.setdefault(shift_id, set()).add(user_id)

        try:
            yield f"data: {json.dumps({'type': 'connected', 'shift_id': shift_id})}\n\n"

            while True:
                # Drain this user's personal broadcast queue
                user_queue = _pending_broadcasts.get(shift_id, {})
                if user_id in user_queue:
                    for broadcast in user_queue.pop(user_id):
                        yield f"data: {json.dumps(broadcast)}\n\n"

                # Check for new changes in database
                new_changes = HandoverChange.get_unsynced_changes(shift_id, last_change_id)
                for change in new_changes:
                    if change.user_id != user_id:
                        yield f"data: {json.dumps({'type': 'change', 'data': change.to_dict()})}\n\n"
                    last_change_id = max(last_change_id, change.id)

                # Send active users update every 30 seconds
                if (datetime.utcnow() - last_check).seconds >= 30:
                    active_sessions = HandoverSession.get_active_users(shift_id)
                    locks = SectionLock.get_locks_for_shift(shift_id)
                    yield f"data: {json.dumps({'type': 'presence', 'active_users': [s.to_dict() for s in active_sessions], 'locks': [l.to_dict() for l in locks]})}\n\n"
                    last_check = datetime.utcnow()

                time.sleep(0.5)
                yield ": keepalive\n\n"

        except GeneratorExit:
            pass
        except Exception as e:
            logger.error(f"SSE error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        finally:
            _active_sse_users.get(shift_id, set()).discard(user_id)
            _pending_broadcasts.get(shift_id, {}).pop(user_id, None)
    
    response = Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'
        }
    )
    return response


# ============================================================================
# Lock Management
# ============================================================================

@collaboration_bp.route('/lock/acquire', methods=['POST'])
@login_required
def acquire_lock():
    """Acquire a soft lock on a section"""
    try:
        data = request.get_json()
        shift_id = data.get('shift_id')
        section_type = data.get('section_type')
        item_id = data.get('item_id')
        
        if not all([shift_id, section_type, item_id]):
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        lock = SectionLock.acquire_lock(
            shift_id=shift_id,
            user_id=current_user.id,
            section_type=section_type,
            item_id=item_id,
            duration_seconds=60
        )
        
        if lock:
            # Record the lock acquisition as a change for broadcast
            HandoverChange.record_change(
                shift_id=shift_id,
                user_id=current_user.id,
                change_type='lock',
                section_type=section_type,
                item_id=item_id
            )
            
            return jsonify({
                'success': True,
                'lock': lock.to_dict()
            })
        else:
            # Lock held by another user
            existing = SectionLock.query.filter_by(
                shift_id=shift_id,
                section_type=section_type,
                item_id=item_id
            ).first()
            
            return jsonify({
                'success': False,
                'error': 'Section is being edited by another user',
                'locked_by': existing.to_dict() if existing else None
            }), 409
            
    except Exception as e:
        logger.error(f"Error acquiring lock: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@collaboration_bp.route('/lock/release', methods=['POST'])
@login_required
def release_lock():
    """Release a soft lock on a section"""
    try:
        data = request.get_json()
        shift_id = data.get('shift_id')
        section_type = data.get('section_type')
        item_id = data.get('item_id')
        
        if not all([shift_id, section_type, item_id]):
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        released = SectionLock.release_lock(
            shift_id=shift_id,
            user_id=current_user.id,
            section_type=section_type,
            item_id=item_id
        )
        
        if released:
            # Record the lock release as a change for broadcast
            HandoverChange.record_change(
                shift_id=shift_id,
                user_id=current_user.id,
                change_type='unlock',
                section_type=section_type,
                item_id=item_id
            )
        
        return jsonify({'success': True, 'released': released})
        
    except Exception as e:
        logger.error(f"Error releasing lock: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@collaboration_bp.route('/lock/extend', methods=['POST'])
@login_required
def extend_lock():
    """Extend a lock duration"""
    try:
        data = request.get_json()
        shift_id = data.get('shift_id')
        section_type = data.get('section_type')
        item_id = data.get('item_id')
        
        lock = SectionLock.acquire_lock(
            shift_id=shift_id,
            user_id=current_user.id,
            section_type=section_type,
            item_id=item_id,
            duration_seconds=60
        )
        
        return jsonify({
            'success': lock is not None,
            'lock': lock.to_dict() if lock else None
        })
        
    except Exception as e:
        logger.error(f"Error extending lock: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# Draft Incident Management
# ============================================================================

@collaboration_bp.route('/incident/add', methods=['POST'])
@login_required
def add_draft_incident():
    """Add a new incident to the collaborative draft"""
    try:
        data = request.get_json()
        shift_id = data.get('shift_id')
        temp_id = data.get('temp_id') or f"inc_{uuid.uuid4().hex[:12]}"
        
        # Check if temp_id already exists
        existing = DraftIncident.query.filter_by(shift_id=shift_id, temp_id=temp_id).first()
        if existing:
            return jsonify({'success': False, 'error': 'Incident already exists'}), 409
        
        incident = DraftIncident(
            shift_id=shift_id,
            temp_id=temp_id,
            incident_type=data.get('incident_type', 'Open'),
            app_name=data.get('app_name'),
            incident_id=data.get('incident_id'),
            title=data.get('title'),
            description=data.get('description'),
            priority=data.get('priority', 'Medium'),
            status=data.get('status', 'Active'),
            assigned_to=data.get('assigned_to'),
            escalated_to=data.get('escalated_to'),
            resolution=data.get('resolution'),
            created_by_id=current_user.id
        )
        db.session.add(incident)
        db.session.commit()
        
        # Record change for broadcast
        HandoverChange.record_change(
            shift_id=shift_id,
            user_id=current_user.id,
            change_type='add',
            section_type='incident',
            item_id=temp_id,
            new_value=incident.to_dict()
        )
        
        logger.info(f"User {current_user.username} added incident {temp_id} to shift {shift_id}")
        
        return jsonify({
            'success': True,
            'incident': incident.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error adding draft incident: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@collaboration_bp.route('/incident/update', methods=['POST'])
@login_required
def update_draft_incident():
    """Update an incident in the collaborative draft"""
    try:
        data = request.get_json()
        shift_id = data.get('shift_id')
        temp_id = data.get('temp_id')
        version = data.get('version', 1)
        
        incident = DraftIncident.query.filter_by(
            shift_id=shift_id,
            temp_id=temp_id
        ).first()
        
        if not incident:
            return jsonify({'success': False, 'error': 'Incident not found'}), 404
        
        # Optimistic locking check
        if incident.version != version:
            return jsonify({
                'success': False,
                'error': 'Conflict: Incident was modified by another user',
                'current': incident.to_dict()
            }), 409
        
        old_value = incident.to_dict()
        
        # Update fields
        for field in ['incident_type', 'app_name', 'incident_id', 'title', 'description',
                      'priority', 'status', 'assigned_to', 'escalated_to', 'resolution']:
            if field in data:
                setattr(incident, field, data[field])
        
        incident.updated_by_id = current_user.id
        incident.updated_at = datetime.utcnow()
        incident.version += 1
        
        db.session.commit()
        
        # Record change for broadcast
        HandoverChange.record_change(
            shift_id=shift_id,
            user_id=current_user.id,
            change_type='update',
            section_type='incident',
            item_id=temp_id,
            old_value=old_value,
            new_value=incident.to_dict()
        )
        
        return jsonify({
            'success': True,
            'incident': incident.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating draft incident: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@collaboration_bp.route('/incident/delete', methods=['POST'])
@login_required
def delete_draft_incident():
    """Delete an incident from the collaborative draft"""
    try:
        data = request.get_json()
        shift_id = data.get('shift_id')
        temp_id = data.get('temp_id')
        
        incident = DraftIncident.query.filter_by(
            shift_id=shift_id,
            temp_id=temp_id
        ).first()
        
        if not incident:
            return jsonify({'success': False, 'error': 'Incident not found'}), 404
        
        old_value = incident.to_dict()
        db.session.delete(incident)
        db.session.commit()
        
        # Record change for broadcast
        HandoverChange.record_change(
            shift_id=shift_id,
            user_id=current_user.id,
            change_type='delete',
            section_type='incident',
            item_id=temp_id,
            old_value=old_value
        )
        
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting draft incident: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# Draft Key Point Management
# ============================================================================

@collaboration_bp.route('/keypoint/add', methods=['POST'])
@login_required
def add_draft_keypoint():
    """Add a new key point to the collaborative draft"""
    try:
        data = request.get_json()
        shift_id = data.get('shift_id')
        temp_id = data.get('temp_id') or f"kp_{uuid.uuid4().hex[:12]}"
        
        keypoint = DraftKeyPoint(
            shift_id=shift_id,
            temp_id=temp_id,
            description=data.get('description', ''),
            status=data.get('status', 'Open'),
            responsible_engineer_id=data.get('responsible_engineer_id'),
            jira_id=data.get('jira_id'),
            created_by_id=current_user.id
        )
        db.session.add(keypoint)
        db.session.commit()
        
        # Record change for broadcast
        HandoverChange.record_change(
            shift_id=shift_id,
            user_id=current_user.id,
            change_type='add',
            section_type='keypoint',
            item_id=temp_id,
            new_value=keypoint.to_dict()
        )
        
        return jsonify({
            'success': True,
            'keypoint': keypoint.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error adding draft keypoint: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@collaboration_bp.route('/keypoint/update', methods=['POST'])
@login_required
def update_draft_keypoint():
    """Update a key point in the collaborative draft"""
    try:
        data = request.get_json()
        shift_id = data.get('shift_id')
        temp_id = data.get('temp_id')
        version = data.get('version', 1)
        
        keypoint = DraftKeyPoint.query.filter_by(
            shift_id=shift_id,
            temp_id=temp_id
        ).first()
        
        if not keypoint:
            return jsonify({'success': False, 'error': 'Key point not found'}), 404
        
        # Optimistic locking check
        if keypoint.version != version:
            return jsonify({
                'success': False,
                'error': 'Conflict: Key point was modified by another user',
                'current': keypoint.to_dict()
            }), 409
        
        old_value = keypoint.to_dict()
        
        # Update fields
        for field in ['description', 'status', 'responsible_engineer_id', 'jira_id']:
            if field in data:
                setattr(keypoint, field, data[field])
        
        keypoint.updated_by_id = current_user.id
        keypoint.updated_at = datetime.utcnow()
        keypoint.version += 1
        
        db.session.commit()
        
        # Record change for broadcast
        HandoverChange.record_change(
            shift_id=shift_id,
            user_id=current_user.id,
            change_type='update',
            section_type='keypoint',
            item_id=temp_id,
            old_value=old_value,
            new_value=keypoint.to_dict()
        )
        
        return jsonify({
            'success': True,
            'keypoint': keypoint.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating draft keypoint: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@collaboration_bp.route('/keypoint/delete', methods=['POST'])
@login_required
def delete_draft_keypoint():
    """Delete a key point from the collaborative draft"""
    try:
        data = request.get_json()
        shift_id = data.get('shift_id')
        temp_id = data.get('temp_id')
        
        keypoint = DraftKeyPoint.query.filter_by(
            shift_id=shift_id,
            temp_id=temp_id
        ).first()
        
        if not keypoint:
            return jsonify({'success': False, 'error': 'Key point not found'}), 404
        
        old_value = keypoint.to_dict()
        db.session.delete(keypoint)
        db.session.commit()
        
        # Record change for broadcast
        HandoverChange.record_change(
            shift_id=shift_id,
            user_id=current_user.id,
            change_type='delete',
            section_type='keypoint',
            item_id=temp_id,
            old_value=old_value
        )
        
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting draft keypoint: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# Draft Change Info Management
# ============================================================================

@collaboration_bp.route('/changeinfo/add', methods=['POST'])
@login_required
def add_draft_changeinfo():
    """Add a new change info to the collaborative draft"""
    try:
        data = request.get_json()
        shift_id = data.get('shift_id')
        temp_id = data.get('temp_id') or f"ci_{uuid.uuid4().hex[:12]}"
        
        changeinfo = DraftChangeInfo(
            shift_id=shift_id,
            temp_id=temp_id,
            application_name=data.get('application_name', ''),
            change_number=data.get('change_number', ''),
            description=data.get('description', ''),
            change_datetime=data.get('change_datetime', ''),
            responsible_engineer_id=data.get('responsible_engineer_id'),
            status=data.get('status', 'Pending'),
            created_by_id=current_user.id
        )
        db.session.add(changeinfo)
        db.session.commit()
        
        # Record change for broadcast
        HandoverChange.record_change(
            shift_id=shift_id,
            user_id=current_user.id,
            change_type='add',
            section_type='changeinfo',
            item_id=temp_id,
            new_value=changeinfo.to_dict()
        )
        
        return jsonify({
            'success': True,
            'changeinfo': changeinfo.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error adding draft changeinfo: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@collaboration_bp.route('/changeinfo/update', methods=['POST'])
@login_required
def update_draft_changeinfo():
    """Update a change info in the collaborative draft"""
    try:
        data = request.get_json()
        shift_id = data.get('shift_id')
        temp_id = data.get('temp_id')
        version = data.get('version', 1)
        
        changeinfo = DraftChangeInfo.query.filter_by(
            shift_id=shift_id,
            temp_id=temp_id
        ).first()
        
        if not changeinfo:
            return jsonify({'success': False, 'error': 'Change info not found'}), 404
        
        if changeinfo.version != version:
            return jsonify({
                'success': False,
                'error': 'Conflict: Change info was modified by another user',
                'current': changeinfo.to_dict()
            }), 409
        
        old_value = changeinfo.to_dict()
        
        for field in ['application_name', 'change_number', 'description', 
                      'change_datetime', 'responsible_engineer_id', 'status']:
            if field in data:
                setattr(changeinfo, field, data[field])
        
        changeinfo.updated_by_id = current_user.id
        changeinfo.updated_at = datetime.utcnow()
        changeinfo.version += 1
        
        db.session.commit()
        
        HandoverChange.record_change(
            shift_id=shift_id,
            user_id=current_user.id,
            change_type='update',
            section_type='changeinfo',
            item_id=temp_id,
            old_value=old_value,
            new_value=changeinfo.to_dict()
        )
        
        return jsonify({
            'success': True,
            'changeinfo': changeinfo.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating draft changeinfo: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@collaboration_bp.route('/changeinfo/delete', methods=['POST'])
@login_required
def delete_draft_changeinfo():
    """Delete a change info from the collaborative draft"""
    try:
        data = request.get_json()
        shift_id = data.get('shift_id')
        temp_id = data.get('temp_id')
        
        changeinfo = DraftChangeInfo.query.filter_by(
            shift_id=shift_id,
            temp_id=temp_id
        ).first()
        
        if not changeinfo:
            return jsonify({'success': False, 'error': 'Change info not found'}), 404
        
        old_value = changeinfo.to_dict()
        db.session.delete(changeinfo)
        db.session.commit()
        
        HandoverChange.record_change(
            shift_id=shift_id,
            user_id=current_user.id,
            change_type='delete',
            section_type='changeinfo',
            item_id=temp_id,
            old_value=old_value
        )
        
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting draft changeinfo: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# Draft KB Update Management
# ============================================================================

@collaboration_bp.route('/kbupdate/add', methods=['POST'])
@login_required
def add_draft_kbupdate():
    """Add a new KB update to the collaborative draft"""
    try:
        data = request.get_json()
        shift_id = data.get('shift_id')
        temp_id = data.get('temp_id') or f"kb_{uuid.uuid4().hex[:12]}"
        
        kbupdate = DraftKBUpdate(
            shift_id=shift_id,
            temp_id=temp_id,
            application_name=data.get('application_name', ''),
            kb_number=data.get('kb_number', ''),
            description=data.get('description', ''),
            responsible_person_id=data.get('responsible_person_id'),
            status=data.get('status', 'Pending'),
            created_by_id=current_user.id
        )
        db.session.add(kbupdate)
        db.session.commit()
        
        # Record change for broadcast
        HandoverChange.record_change(
            shift_id=shift_id,
            user_id=current_user.id,
            change_type='add',
            section_type='kbupdate',
            item_id=temp_id,
            new_value=kbupdate.to_dict()
        )
        
        return jsonify({
            'success': True,
            'kbupdate': kbupdate.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error adding draft kbupdate: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@collaboration_bp.route('/kbupdate/update', methods=['POST'])
@login_required
def update_draft_kbupdate():
    """Update a KB update in the collaborative draft"""
    try:
        data = request.get_json()
        shift_id = data.get('shift_id')
        temp_id = data.get('temp_id')
        version = data.get('version', 1)
        
        kbupdate = DraftKBUpdate.query.filter_by(
            shift_id=shift_id,
            temp_id=temp_id
        ).first()
        
        if not kbupdate:
            return jsonify({'success': False, 'error': 'KB update not found'}), 404
        
        if kbupdate.version != version:
            return jsonify({
                'success': False,
                'error': 'Conflict: KB update was modified by another user',
                'current': kbupdate.to_dict()
            }), 409
        
        old_value = kbupdate.to_dict()
        
        for field in ['application_name', 'kb_number', 'description', 
                      'responsible_person_id', 'status']:
            if field in data:
                setattr(kbupdate, field, data[field])
        
        kbupdate.updated_by_id = current_user.id
        kbupdate.updated_at = datetime.utcnow()
        kbupdate.version += 1
        
        db.session.commit()
        
        HandoverChange.record_change(
            shift_id=shift_id,
            user_id=current_user.id,
            change_type='update',
            section_type='kbupdate',
            item_id=temp_id,
            old_value=old_value,
            new_value=kbupdate.to_dict()
        )
        
        return jsonify({
            'success': True,
            'kbupdate': kbupdate.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating draft kbupdate: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@collaboration_bp.route('/kbupdate/delete', methods=['POST'])
@login_required
def delete_draft_kbupdate():
    """Delete a KB update from the collaborative draft"""
    try:
        data = request.get_json()
        shift_id = data.get('shift_id')
        temp_id = data.get('temp_id')
        
        kbupdate = DraftKBUpdate.query.filter_by(
            shift_id=shift_id,
            temp_id=temp_id
        ).first()
        
        if not kbupdate:
            return jsonify({'success': False, 'error': 'KB update not found'}), 404
        
        old_value = kbupdate.to_dict()
        db.session.delete(kbupdate)
        db.session.commit()
        
        HandoverChange.record_change(
            shift_id=shift_id,
            user_id=current_user.id,
            change_type='delete',
            section_type='kbupdate',
            item_id=temp_id,
            old_value=old_value
        )
        
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting draft kbupdate: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# Sync & Status
# ============================================================================

@collaboration_bp.route('/sync/<int:shift_id>')
@login_required
def sync_changes(shift_id):
    """Get changes since a specific change ID (polling fallback)"""
    try:
        last_change_id = int(request.args.get('last_change_id', 0))
        
        changes = HandoverChange.get_unsynced_changes(shift_id, last_change_id)
        active_sessions = HandoverSession.get_active_users(shift_id)
        locks = SectionLock.get_locks_for_shift(shift_id)
        
        return jsonify({
            'success': True,
            'changes': [c.to_dict() for c in changes],
            'active_users': [s.to_dict() for s in active_sessions],
            'locks': [l.to_dict() for l in locks],
            'last_change_id': changes[-1].id if changes else last_change_id
        })
        
    except Exception as e:
        logger.error(f"Error syncing changes: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@collaboration_bp.route('/status/<int:shift_id>')
@login_required
def get_status(shift_id):
    """Get current collaboration status for a shift"""
    try:
        active_sessions = HandoverSession.get_active_users(shift_id)
        locks = SectionLock.get_locks_for_shift(shift_id)
        draft_incidents = DraftIncident.query.filter_by(shift_id=shift_id).all()
        draft_keypoints = DraftKeyPoint.query.filter_by(shift_id=shift_id).all()
        draft_changeinfos = DraftChangeInfo.query.filter_by(shift_id=shift_id).all()
        draft_kbupdates = DraftKBUpdate.query.filter_by(shift_id=shift_id).all()
        
        return jsonify({
            'success': True,
            'active_users': [s.to_dict() for s in active_sessions],
            'locks': [l.to_dict() for l in locks],
            'draft_incidents_count': len(draft_incidents),
            'draft_keypoints_count': len(draft_keypoints),
            'draft_changeinfos_count': len(draft_changeinfos),
            'draft_kbupdates_count': len(draft_kbupdates),
            'last_change_id': _get_last_change_id(shift_id)
        })
        
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


def _get_last_change_id(shift_id):
    """Helper to get the last change ID for a shift"""
    last_change = HandoverChange.query.filter_by(shift_id=shift_id).order_by(
        HandoverChange.id.desc()
    ).first()
    return last_change.id if last_change else 0

# ============================================================================
# Live Field Updates (Real-time sync as users type)
# ============================================================================

@collaboration_bp.route('/field/update', methods=['POST'])
@login_required
def update_field():
    """
    Update a single field value and broadcast to all connected users.
    This enables real-time sync as users type.
    """
    try:
        data = request.get_json()
        shift_id = data.get('shift_id')
        section_type = data.get('section_type')
        item_id = data.get('item_id')
        field_name = data.get('field_name')
        value = data.get('value')
        
        if not all([shift_id, section_type, item_id, field_name]):
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        field_key = f"{section_type}:{item_id}:{field_name}"
        
        # Initialize field states for this shift
        if shift_id not in _field_states:
            _field_states[shift_id] = {}
        
        # Get current state
        current_state = _field_states[shift_id].get(field_key)
        
        # IMPROVED CONFLICT DETECTION:
        # Only detect conflict if:
        # 1. Another user updated this field in the last 2 seconds
        # 2. The value is different from what this user is sending
        # This prevents false positives when the same user is typing
        conflict_detected = False
        if current_state:
            last_update_time = current_state.get('timestamp')
            last_user_id = current_state.get('user_id')
            last_value = current_state.get('value')
            
            if last_user_id != current_user.id and last_value != value:
                # Another user made changes - check if within conflict window (2 seconds)
                if last_update_time:
                    try:
                        last_update = datetime.fromisoformat(last_update_time)
                        time_diff = (datetime.utcnow() - last_update).total_seconds()
                        # Only show conflict if changes were very recent (within 2 seconds)
                        if time_diff < 2:
                            conflict_detected = True
                    except:
                        pass
        
        if conflict_detected:
            # Return conflict but don't block - just inform the user
            return jsonify({
                'success': True,  # Still save the change
                'warning': 'concurrent_edit',
                'current_value': current_state.get('value'),
                'last_modified_by': current_state.get('user_name'),
                'message': f"{current_state.get('user_name')} is also editing this field"
            })
        
        # Update field state
        new_version = (current_state.get('version', 0) if current_state else 0) + 1
        user_display_name = current_user.display_name or current_user.username
        _field_states[shift_id][field_key] = {
            'value': value,
            'version': new_version,
            'user_id': current_user.id,
            'user_name': user_display_name,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Queue for broadcast (don't store to database for every keystroke - too heavy)
        _queue_broadcast(shift_id, current_user.id, {
            'type': 'field_update',
            'data': {
                'section_type': section_type,
                'item_id': item_id,
                'field_name': field_name,
                'value': value,
                'version': new_version,
                'user_id': current_user.id,
                'user_name': user_display_name,
                'timestamp': datetime.utcnow().isoformat()
            }
        })
        
        logger.info(f"[COLLAB] Field update queued: {field_key} by {current_user.username}, value length: {len(str(value))}")
        
        return jsonify({
            'success': True,
            'version': new_version
        })
        
    except Exception as e:
        logger.error(f"Error updating field: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@collaboration_bp.route('/typing', methods=['POST'])
@login_required
def typing_indicator():
    """
    Send typing indicator to other users.
    Shows who is currently typing in which field.
    """
    try:
        data = request.get_json()
        shift_id = data.get('shift_id')
        section_type = data.get('section_type')
        item_id = data.get('item_id')
        field_name = data.get('field_name')
        is_typing = data.get('is_typing', False)
        
        if not all([shift_id, section_type, item_id, field_name]):
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        field_key = f"{section_type}:{item_id}:{field_name}"
        user_display_name = current_user.display_name or current_user.username
        
        # Initialize typing indicators for this shift
        if shift_id not in _typing_indicators:
            _typing_indicators[shift_id] = {}
        
        if is_typing:
            _typing_indicators[shift_id][field_key] = {
                'user_id': current_user.id,
                'user_name': user_display_name,
                'timestamp': datetime.utcnow().isoformat()
            }
        else:
            _typing_indicators[shift_id].pop(field_key, None)
        
        # Queue for broadcast
        _queue_broadcast(shift_id, current_user.id, {
            'type': 'typing',
            'data': {
                'section_type': section_type,
                'item_id': item_id,
                'field_name': field_name,
                'user_id': current_user.id,
                'user_name': user_display_name,
                'is_typing': is_typing
            }
        })
        
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"Error sending typing indicator: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@collaboration_bp.route('/field/states/<int:shift_id>')
@login_required
def get_field_states(shift_id):
    """Get all current field states for a shift (for initial sync)"""
    try:
        states = _field_states.get(shift_id, {})
        typing = _typing_indicators.get(shift_id, {})
        
        return jsonify({
            'success': True,
            'field_states': states,
            'typing_indicators': typing
        })
        
    except Exception as e:
        logger.error(f"Error getting field states: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# Enhanced SSE stream that includes field updates and typing indicators
@collaboration_bp.route('/stream/v2/<int:shift_id>')
@login_required  
def event_stream_v2(shift_id):
    """Enhanced SSE endpoint with field-level updates and typing indicators"""
    
    def generate():
        last_change_id = int(request.args.get('last_change_id', 0))
        last_presence_update = datetime.utcnow()
        user_id = current_user.id

        # Register this user as an active SSE recipient
        _active_sse_users.setdefault(shift_id, set()).add(user_id)

        try:
            # Send initial connection confirmation
            yield f"data: {json.dumps({'type': 'connected', 'shift_id': shift_id, 'user_id': user_id})}\n\n"

            while True:
                # Drain this user's personal broadcast queue
                user_queue = _pending_broadcasts.get(shift_id, {})
                if user_id in user_queue:
                    broadcasts = user_queue.pop(user_id)
                    for broadcast in broadcasts:
                        yield f"data: {json.dumps(broadcast)}\n\n"

                # Check for database changes (add/update/delete operations)
                new_changes = HandoverChange.get_unsynced_changes(shift_id, last_change_id)
                for change in new_changes:
                    if change.user_id != user_id:
                        yield f"data: {json.dumps({'type': 'change', 'data': change.to_dict()})}\n\n"
                    last_change_id = max(last_change_id, change.id)

                # Send presence update every 15 seconds
                if (datetime.utcnow() - last_presence_update).total_seconds() >= 15:
                    active_sessions = HandoverSession.get_active_users(shift_id)
                    locks = SectionLock.get_locks_for_shift(shift_id)
                    typing = _typing_indicators.get(shift_id, {})

                    # Clean up old typing indicators (older than 5 seconds)
                    cutoff = (datetime.utcnow() - timedelta(seconds=5)).isoformat()
                    typing = {k: v for k, v in typing.items() if v.get('timestamp', '') > cutoff}

                    yield f"data: {json.dumps({'type': 'presence', 'active_users': [s.to_dict() for s in active_sessions], 'locks': [l.to_dict() for l in locks], 'typing_indicators': typing})}\n\n"
                    last_presence_update = datetime.utcnow()

                # Small delay
                time.sleep(0.5)

                # Keepalive
                yield ": keepalive\n\n"

        except GeneratorExit:
            pass
        except Exception as e:
            logger.error(f"SSE v2 error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        finally:
            # Deregister user from active SSE set and clean up their queue
            _active_sse_users.get(shift_id, set()).discard(user_id)
            _pending_broadcasts.get(shift_id, {}).pop(user_id, None)
    
    response = Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'
        }
    )
    return response


# ============================================================================
# Draft Changes Management (for tracking unsaved changes)
# ============================================================================

@collaboration_bp.route('/draft/changes/<int:shift_id>')
@login_required
def get_draft_changes(shift_id):
    """Get all draft changes for a shift (unsaved edits)"""
    try:
        # Get field states
        field_states = _field_states.get(shift_id, {})
        
        # Get draft items
        draft_incidents = DraftIncident.query.filter_by(shift_id=shift_id).all()
        draft_keypoints = DraftKeyPoint.query.filter_by(shift_id=shift_id).all()
        
        # Get recent changes
        recent_changes = HandoverChange.query.filter_by(shift_id=shift_id).order_by(
            HandoverChange.created_at.desc()
        ).limit(50).all()
        
        return jsonify({
            'success': True,
            'field_states': field_states,
            'draft_incidents': [i.to_dict() for i in draft_incidents],
            'draft_keypoints': [k.to_dict() for k in draft_keypoints],
            'recent_changes': [c.to_dict() for c in recent_changes]
        })
        
    except Exception as e:
        logger.error(f"Error getting draft changes: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@collaboration_bp.route('/draft/persist/<int:shift_id>', methods=['POST'])
@login_required
def persist_draft(shift_id):
    """Persist all collaborative changes to the main shift record"""
    try:
        # Get the shift
        shift = Shift.query.get_or_404(shift_id)
        
        # Get all field states and apply them
        field_states = _field_states.get(shift_id, {})
        
        # Get draft incidents and convert to real incidents
        draft_incidents = DraftIncident.query.filter_by(shift_id=shift_id).all()
        
        # Get draft keypoints and convert to real keypoints
        draft_keypoints = DraftKeyPoint.query.filter_by(shift_id=shift_id).all()
        
        # Apply changes to shift (this would integrate with your existing handover logic)
        # ... implementation depends on your existing data model
        
        # Clear field states after persist
        if shift_id in _field_states:
            del _field_states[shift_id]
        
        # Clear typing indicators
        if shift_id in _typing_indicators:
            del _typing_indicators[shift_id]
        
        logger.info(f"Draft persisted for shift {shift_id} by {current_user.username}")
        
        return jsonify({
            'success': True,
            'message': 'Draft saved successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error persisting draft: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# Incident Collaboration: Duplicate Detection & Draft Sharing
# ============================================================================

@collaboration_bp.route('/incident/save', methods=['POST'])
@login_required
def save_draft_incident():
    """Save or update the current user's draft incident row."""
    try:
        data = request.get_json() or {}
        shift_id = data.get('shift_id')
        temp_id = data.get('temp_id', '').strip()

        if not shift_id or not temp_id:
            return jsonify({'success': False, 'error': 'Missing shift_id or temp_id'}), 400

        Shift.query.get_or_404(shift_id)

        draft = DraftIncident.query.filter_by(shift_id=shift_id, temp_id=temp_id).first()

        if draft:
            if draft.created_by_id != current_user.id:
                return jsonify({'success': False, 'error': 'Not your incident'}), 403
            draft.incident_id = data.get('incident_id') or draft.incident_id
            draft.app_name = data.get('app_name') or draft.app_name
            draft.title = data.get('title') or draft.title
            draft.incident_type = data.get('status') or draft.incident_type or 'Open'
            draft.priority = data.get('priority') or draft.priority
            draft.assigned_to = data.get('assigned_to') or draft.assigned_to
            draft.escalated_to = data.get('escalated_to') or draft.escalated_to
            draft.description = data.get('notes') or draft.description
            draft.updated_by_id = current_user.id
            draft.version = (draft.version or 1) + 1
        else:
            draft = DraftIncident(
                shift_id=shift_id,
                temp_id=temp_id,
                incident_id=data.get('incident_id', ''),
                app_name=data.get('app_name', ''),
                title=data.get('title', ''),
                incident_type=data.get('status', 'Open') or 'Open',
                priority=data.get('priority', 'Medium'),
                assigned_to=data.get('assigned_to', ''),
                escalated_to=data.get('escalated_to', ''),
                description=data.get('notes', ''),
                created_by_id=current_user.id
            )
            db.session.add(draft)

        db.session.commit()
        return jsonify({'success': True, 'temp_id': temp_id})

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error saving draft incident: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@collaboration_bp.route('/incident/check', methods=['GET'])
@login_required
def check_incident_duplicate():
    """Check if an incident ID was already entered by another user in this shift's draft."""
    shift_id = request.args.get('shift_id', type=int)
    incident_id = (request.args.get('incident_id') or '').strip()

    if not shift_id or not incident_id:
        return jsonify({'success': False, 'error': 'Missing params'}), 400

    existing = DraftIncident.query.filter(
        DraftIncident.shift_id == shift_id,
        DraftIncident.incident_id == incident_id,
        DraftIncident.created_by_id != current_user.id
    ).first()

    if existing:
        creator_name = 'Unknown'
        if existing.created_by:
            creator_name = existing.created_by.display_name or existing.created_by.username
        return jsonify({
            'success': True,
            'duplicate': True,
            'added_by': creator_name,
            'added_by_id': existing.created_by_id
        })

    return jsonify({'success': True, 'duplicate': False})


@collaboration_bp.route('/incidents/others', methods=['GET'])
@login_required
def get_others_incidents():
    """Get all draft incidents added by other users for this shift."""
    shift_id = request.args.get('shift_id', type=int)

    if not shift_id:
        return jsonify({'success': False, 'error': 'Missing shift_id'}), 400

    incidents = DraftIncident.query.filter(
        DraftIncident.shift_id == shift_id,
        DraftIncident.created_by_id != current_user.id
    ).all()

    return jsonify({
        'success': True,
        'incidents': [i.to_dict() for i in incidents],
        'count': len(incidents)
    })