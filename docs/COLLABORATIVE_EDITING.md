# Real-Time Collaborative Editing for Handover Forms

## Overview

This document describes the implementation of real-time collaborative editing for the Shift Handover application, similar to Google Sheets / Excel Online.

## Architecture

### Technology Stack
- **Backend**: Flask with Server-Sent Events (SSE) for real-time communication
- **Frontend**: Vanilla JavaScript with CollaborativeHandoverV2 class
- **Database**: MySQL 8.0 for persistence
- **In-Memory State**: Python dictionaries for field states and typing indicators

### Key Components

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Client Browsers                               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐          │
│  │   User A     │    │   User B     │    │   User C     │          │
│  │ (Editing)    │    │ (Viewing)    │    │ (Editing)    │          │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘          │
│         │                   │                    │                   │
│         └───────────────────┼────────────────────┘                   │
│                             │                                        │
│                      ┌──────▼───────┐                               │
│                      │  EventSource │                               │
│                      │  (SSE Stream)│                               │
│                      └──────┬───────┘                               │
└─────────────────────────────┼───────────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────────┐
│                         Flask Server                                 │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                   Collaboration Routes                         │ │
│  │  /api/collaboration/session/join/<shift_id>  - Join session    │ │
│  │  /api/collaboration/session/leave/<shift_id> - Leave session   │ │
│  │  /api/collaboration/stream/<shift_id>        - SSE stream      │ │
│  │  /api/collaboration/field/update             - Field changes   │ │
│  │  /api/collaboration/typing                   - Typing indicator│ │
│  │  /api/collaboration/lock/*                   - Lock management │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ┌─────────────────────┐    ┌─────────────────────────────────────┐│
│  │   In-Memory State   │    │          MySQL Database             ││
│  │  ┌───────────────┐  │    │  ┌─────────────────────────────────┐││
│  │  │ _field_states │  │    │  │ handover_session                │││
│  │  │ _typing_ind.  │  │    │  │ section_lock                    │││
│  │  │ _pending_     │  │    │  │ handover_change                 │││
│  │  │  broadcasts   │  │    │  │ draft_incident                  │││
│  │  └───────────────┘  │    │  │ draft_key_point                 │││
│  └─────────────────────┘    │  └─────────────────────────────────┘││
│                             └─────────────────────────────────────┘│
└────────────────────────────────────────────────────────────────────┘
```

## Features

### 1. Live Presence
- Show all users currently working on the same draft
- User avatars with initials displayed at the top
- Connection status indicator (green dot = connected)

### 2. Field-Level Editing Visibility
- When a user edits a field, other users see an indicator: "User-1 is editing"
- Visual highlight on the entry being edited
- Typing indicators show who is actively typing

### 3. Real-Time Sync
- Changes are broadcast immediately via SSE
- 300ms debounce to prevent excessive network calls
- Field updates appear live for all connected users

### 4. User Attribution
- Each change tracks who made it and when
- Attribution shown in "Last updated by X at Y" format
- Full audit trail in handover_change table

### 5. No Blocking Popups
- Conflict detection only warns about concurrent edits within 2 seconds
- Changes are always saved (last write wins)
- Toast notifications instead of blocking modals

## Event/Message Schema

### SSE Message Types

```javascript
// User joined session
{
    "type": "user_joined",
    "user": {"user_id": 1, "username": "john.doe"},
    "active_users": [...]
}

// User left session
{
    "type": "user_left",
    "user": {"user_id": 1, "username": "john.doe"},
    "active_users": [...]
}

// Field update (real-time typing)
{
    "type": "field_update",
    "data": {
        "section_type": "incident_open",
        "item_id": "open_0",
        "field_name": "description",
        "value": "Server issue...",
        "version": 5,
        "user_id": 1,
        "user_name": "John Doe",
        "timestamp": "2026-02-06T10:30:00Z"
    }
}

// Typing indicator
{
    "type": "typing",
    "data": {
        "section_type": "incident_open",
        "item_id": "open_0",
        "field_name": "description",
        "user_id": 1,
        "user_name": "John Doe",
        "is_typing": true
    }
}

// Presence update (periodic)
{
    "type": "presence",
    "active_users": [...],
    "locks": [...]
}
```

### Field Update Request

```javascript
POST /api/collaboration/field/update
{
    "shift_id": 123,
    "session_token": "uuid",
    "section_type": "incident_open",
    "item_id": "open_0",
    "field_name": "description",
    "value": "New description text"
}
```

### Field Update Response

```javascript
// Success
{
    "success": true,
    "version": 6
}

// Concurrent edit warning (non-blocking)
{
    "success": true,
    "warning": "concurrent_edit",
    "current_value": "...",
    "last_modified_by": "Jane Doe",
    "message": "Jane Doe is also editing this field"
}
```

## UI Behavior

### Active Users Panel
- Located at top of handover form
- Shows user avatars with initials
- Tooltip on hover shows full name
- Pulsing animation when user is actively editing

### Field-Level Indicators
- `.collab-field-updated` - Brief yellow highlight when field changes
- `.collab-typing-indicator` - "User is typing..." with animated dots
- `.collab-editing-entry` - Purple left border on entry being edited
- `.collab-editing-indicator` - Badge showing "User is editing"

### Lock Indicators
- `.collab-locked` - Dashed orange border around locked section
- `.collab-lock-badge` - Lock icon with user name
- Inputs are disabled when another user has the lock

### Connection Status
- Green dot: Connected
- Red blinking dot: Disconnected (auto-reconnect in progress)

## Database Schema

### handover_session
```sql
CREATE TABLE handover_session (
    id INT AUTO_INCREMENT PRIMARY KEY,
    shift_id INT NOT NULL,
    user_id INT NOT NULL,
    session_token VARCHAR(64) UNIQUE NOT NULL,
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_heartbeat DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    current_section VARCHAR(64),
    current_item_id VARCHAR(64)
);
```

### section_lock
```sql
CREATE TABLE section_lock (
    id INT AUTO_INCREMENT PRIMARY KEY,
    shift_id INT NOT NULL,
    user_id INT NOT NULL,
    section_type VARCHAR(32) NOT NULL,
    item_id VARCHAR(64) NOT NULL,
    locked_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME NOT NULL
);
```

### handover_change
```sql
CREATE TABLE handover_change (
    id INT AUTO_INCREMENT PRIMARY KEY,
    shift_id INT NOT NULL,
    user_id INT NOT NULL,
    change_type VARCHAR(32) NOT NULL,
    section_type VARCHAR(32) NOT NULL,
    item_id VARCHAR(64),
    field_name VARCHAR(64),
    old_value TEXT,
    new_value TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    version INT DEFAULT 1,
    synced BOOLEAN DEFAULT FALSE
);
```

## Conflict Handling

### Strategy: Last Write Wins with Notification

1. **User A and User B** both edit the same field
2. **User A** finishes first - change is saved
3. **User B** finishes - receives toast notification:
   - "User A is also editing this field"
   - User B's change is still saved (last write wins)
4. Both users see the final value via SSE broadcast

### Soft Locking (Optional)

When enabled:
1. User focuses on a field → acquires soft lock (60 seconds)
2. Other users see lock indicator but can still type
3. Lock auto-releases on blur or after 60 seconds
4. Lock can be extended while user is actively editing

## Test Cases

### 1. Basic Collaboration
- [ ] User A joins session - sees own avatar
- [ ] User B joins session - both see each other's avatars
- [ ] User A leaves - User B no longer sees User A

### 2. Real-Time Sync
- [ ] User A types in a field - User B sees changes live
- [ ] User A adds a new incident - appears in User B's view
- [ ] User A deletes an incident - disappears from User B's view

### 3. Concurrent Edits
- [ ] Both users edit same field simultaneously - no blocking popup
- [ ] Second user to finish sees toast warning
- [ ] Both see final value after sync

### 4. Disconnect/Reconnect
- [ ] Simulate network disconnect - connection status shows red
- [ ] Wait for auto-reconnect - status returns to green
- [ ] Verify no data loss during reconnection

### 5. Multiple Sections
- [ ] User A edits incidents, User B edits keypoints - no conflicts
- [ ] User A edits Open Incidents, User B edits Closed Incidents - no conflicts

## Files

### Backend
- `routes/collaboration.py` — All collaboration API endpoints (join/leave/field-update/lock/typing)
- `routes/collab_sse.py` — SSE stream endpoint (`/api/collaboration/stream/<shift_id>`)
- `models/collaboration.py` — DB models: `HandoverSession`, `SectionLock`, `HandoverChange`, `DraftIncident`, `DraftKeyPoint`, `DraftChangeInfo`, `DraftKBUpdate`

### Frontend
- `static/js/yjs.bundle.js` — Self-hosted YJS CRDT bundle (~91 KB, no CDN dependency)
- `static/js/yjs-sse-provider.js` — Custom YJS SSE provider
- `static/js/collaborative_handover_v2.js` — Main client-side collaboration logic
- `static/js/collaboration.js` — Collab UI wiring
- `static/css/collaborative_handover.css` — Visual indicators and animations
- `templates/partials/collaborative_handover.html` — UI partial for collaboration panel

### App Registration
- `app.py` — Registers `collaboration_bp` and `collab_sse_bp` blueprints

## Deployment

```bash
# Local (Docker or Podman)
docker-compose up --build
# or
podman-compose up --build

# Production — see docs/PROD_DEPLOYMENT_GUIDE.md
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d --build
docker-compose -f docker-compose.prod.yml logs -f web
```

**Important:** `static/js/yjs.bundle.js` must be present after `git pull`. Verify with:
```bash
ls -lh static/js/yjs.bundle.js   # expected: ~91 KB
```

Access the application at: http://localhost:5000

## Future Improvements

1. **Redis for Multi-Process Support**: Current implementation uses in-memory dictionaries which don't work across multiple Flask processes. Redis would enable horizontal scaling.

2. **WebSocket Support**: SSE is unidirectional. WebSockets would enable bidirectional communication for lower latency.

3. **Operational Transform (OT)**: For character-by-character sync like Google Docs, implement OT algorithm.

4. **Presence Cursors**: Show other users' cursor positions in text fields.

5. **Offline Support**: Queue changes when offline, sync when reconnected.
