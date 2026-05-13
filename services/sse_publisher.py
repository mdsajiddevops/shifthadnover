"""
CoreAction SSE Publisher — COMP-014 (CTCOAMSHM-115, REQ-007, REQ-009)

Writes a HandoverChange-compatible event record so the existing SSE poll/delivery
mechanism can pick it up and broadcast a core_action_change event to subscribed clients.

The caller's db_session owns the commit; this service never calls commit/rollback.
Exceptions propagate upward — the service layer (COMP-008) handles degradation routing.
"""
import json
from datetime import datetime

from models.collaboration import HandoverChange


def publish_core_action_event(
    core_action_id: str,
    event_type: str,
    resource_id,
    actor,
    db_session,
) -> None:
    """Write a HandoverChange row so the SSE stream delivers a core_action_change event.

    Stores actor_user_id and resource_id as a JSON blob in new_value so the stream
    generator can include both in the broadcast payload without schema changes.
    """
    metadata = json.dumps({
        "actor": str(actor),
        "resource_id": str(resource_id) if resource_id is not None else None,
    })
    change = HandoverChange(
        # HandoverChange.shift_id is a non-nullable int FK; 0 is the CoreAction sentinel.
        shift_id=0,
        user_id=0,
        change_type="core_action_change",
        section_type=event_type,
        item_id=str(core_action_id),
        field_name="core_action_metadata",
        new_value=metadata,
        created_at=datetime.utcnow(),
    )
    db_session.add(change)
