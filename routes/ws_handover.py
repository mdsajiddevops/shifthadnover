"""
WebSocket handover-draft relay (CTCOAMSHM-7).

Implements a minimal y-websocket-compatible relay that:
  1. Sends the stored Yjs document state (HandoverDraft.ydoc_state) to every
     new client as a sync-step-2 message so they can catch up immediately.
  2. Requests the client's current full state via sync-step-1 on connect,
     then auto-saves the reply (sync-step-2) to the HandoverDraft row.
  3. Relays incremental update messages (0x00 0x02) and awareness messages
     (0x01) to all other clients in the same shift room.

Yjs binary protocol reference (lib0 encoding):
  [0x00 0x00 …]  messageSync + syncStep1  (client's state vector)
  [0x00 0x01 …]  messageSync + syncStep2  (full document state)
  [0x00 0x02 …]  messageSync + update     (incremental update)
  [0x01 …]       messageAwareness         (cursor / presence)

All multi-byte integers in the payload are lib0 variable-length encoded.

Route URL:  /ws/handover/<shift_id>
Auth:       Requires an authenticated Flask session (manual check — @login_required
            is incompatible with WebSocket upgrades).
Server:     Gunicorn gthread worker (gunicorn.conf.py worker_class='gthread').
"""
import threading
import logging

from flask_login import current_user

from models.models import db
from models.handover_draft import HandoverDraft
from services.sock_instance import sock

logger = logging.getLogger(__name__)

# ── Connection registry ──────────────────────────────────────────────────────
# Maps shift_id -> list of (ws, send_lock) tuples.
# Protected by _rooms_lock to avoid races between threads.

_rooms_lock = threading.RLock()
_rooms: dict = {}


def _add_conn(shift_id: int, ws, lock: threading.Lock) -> None:
    with _rooms_lock:
        _rooms.setdefault(shift_id, []).append((ws, lock))


def _remove_conn(shift_id: int, ws) -> None:
    with _rooms_lock:
        if shift_id in _rooms:
            _rooms[shift_id] = [(w, l) for w, l in _rooms[shift_id] if w is not ws]
            if not _rooms[shift_id]:
                del _rooms[shift_id]


def _broadcast(shift_id: int, data: bytes, exclude=None) -> None:
    """Send data to every connection in the room except the sender."""
    with _rooms_lock:
        conns = list(_rooms.get(shift_id, []))
    for ws, lock in conns:
        if ws is not exclude:
            try:
                with lock:
                    ws.send(data)
            except Exception:
                pass


# ── Yjs / lib0 protocol helpers ──────────────────────────────────────────────

def _encode_varint(n: int) -> bytes:
    if n == 0:
        return b'\x00'
    out = bytearray()
    while n > 0:
        bits = n & 0x7F
        n >>= 7
        if n:
            bits |= 0x80
        out.append(bits)
    return bytes(out)


def _decode_varint(buf: bytes, pos: int = 0):
    """Returns (value, next_pos). Reads a lib0 variable-length integer."""
    result, shift = 0, 0
    while pos < len(buf):
        b = buf[pos]
        pos += 1
        result |= (b & 0x7F) << shift
        if not (b & 0x80):
            break
        shift += 7
    return result, pos


def _build_sync_step1() -> bytes:
    """Empty-state-vector sync-step-1: requests the full document from the client."""
    # messageSync=0x00, syncStep1=0x00, stateVector length=0x00
    return b'\x00\x00\x00'


def _build_sync_step2(update: bytes) -> bytes:
    """Wrap raw update bytes in a sync-step-2 message."""
    return b'\x00\x01' + _encode_varint(len(update)) + update


def _build_update_msg(update: bytes) -> bytes:
    """Wrap raw update bytes in an incremental update message."""
    return b'\x00\x02' + _encode_varint(len(update)) + update


def _extract_payload(data: bytes) -> bytes:
    """
    Extract the raw update/state-vector bytes from a sync message.

    Sync message layout:  [msgType(1B)] [subType(1B)] [varint(len)] [payload]
    After subType (data[2:]) comes a varint-encoded length then the payload.
    """
    if len(data) < 3:
        return b''
    length, pos = _decode_varint(data, 2)
    return data[pos: pos + length]


# ── Database helpers ─────────────────────────────────────────────────────────

def _load_draft(shift_id: int) -> bytes | None:
    """Return the stored Yjs document bytes for this shift, or None."""
    draft = HandoverDraft.query.filter_by(shift_id=shift_id).first()
    return draft.ydoc_state if draft else None


def _save_draft(shift_id: int, state: bytes) -> None:
    """
    Upsert the Yjs document state for a shift (auto-save).

    Called on every sync-step-2 received, so the DB always holds the latest
    full document state known to the server.
    """
    try:
        draft = (
            HandoverDraft.query
            .filter_by(shift_id=shift_id)
            .with_for_update()
            .first()
        )
        if draft:
            draft.ydoc_state = state
        else:
            draft = HandoverDraft(shift_id=shift_id, ydoc_state=state)
            db.session.add(draft)
        db.session.commit()
        logger.debug("auto-save: shift=%s, bytes=%d", shift_id, len(state))
    except Exception as exc:
        db.session.rollback()
        logger.warning("auto-save failed: shift=%s error=%s", shift_id, exc)


# ── WebSocket endpoint ───────────────────────────────────────────────────────

@sock.route('/ws/handover/<int:shift_id>')
def ws_handover(ws, shift_id: int) -> None:
    """
    y-websocket-compatible relay for handover draft real-time collaboration.

    One WebSocket connection per browser tab, one Gunicorn thread per connection.
    """
    if not current_user.is_authenticated:
        ws.close(1008)
        return

    user_id = current_user.id
    send_lock = threading.Lock()
    _add_conn(shift_id, ws, send_lock)
    logger.info("ws_handover connect: user=%s shift=%s", user_id, shift_id)

    try:
        # ── Initial sync ─────────────────────────────────────────────────────
        # Send any persisted state so the new client catches up immediately.
        stored = _load_draft(shift_id)
        if stored:
            with send_lock:
                ws.send(_build_sync_step2(stored))

        # Request the client's current full state (triggers a sync-step-2 reply
        # which we'll save to DB, acting as the first auto-save).
        with send_lock:
            ws.send(_build_sync_step1())

        # ── Message loop ─────────────────────────────────────────────────────
        while True:
            data = ws.receive()
            if data is None:
                break

            if isinstance(data, str):
                data = data.encode('utf-8')
            if not data:
                continue

            msg_type = data[0]

            if msg_type == 0:  # messageSync
                sub = data[1] if len(data) > 1 else -1

                if sub == 0:  # sync-step-1 from client (state vector)
                    # Client is asking what the server knows; respond with stored state.
                    state = _load_draft(shift_id) or b''
                    with send_lock:
                        ws.send(_build_sync_step2(state))

                elif sub == 1:  # sync-step-2 from client (full document state) → auto-save
                    payload = _extract_payload(data)
                    if payload:
                        _save_draft(shift_id, payload)
                    # Relay to other clients as an update so they can merge.
                    _broadcast(shift_id, _build_update_msg(payload), exclude=ws)

                elif sub == 2:  # incremental update from client
                    _broadcast(shift_id, data, exclude=ws)

            elif msg_type == 1:  # messageAwareness (cursor / presence)
                _broadcast(shift_id, data, exclude=ws)

    except Exception as exc:
        logger.debug("ws_handover loop ended: user=%s shift=%s reason=%s", user_id, shift_id, exc)
    finally:
        _remove_conn(shift_id, ws)
        logger.info("ws_handover disconnect: user=%s shift=%s", user_id, shift_id)
