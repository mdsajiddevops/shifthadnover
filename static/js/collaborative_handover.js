/**
 * Collaborative Handover Client
 * =============================
 * Real-time collaborative editing for handover forms.
 * Uses Server-Sent Events (SSE) for live updates.
 */

class CollaborativeHandover {
    constructor(shiftId, options = {}) {
        this.shiftId = shiftId;
        this.sessionToken = null;
        this.eventSource = null;
        this.lastChangeId = 0;
        this.activeUsers = [];
        this.locks = [];
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.heartbeatInterval = null;
        this.lockRefreshInterval = null;
        this.currentLocks = new Map(); // Our own locks
        
        // Callbacks
        this.onUserJoin = options.onUserJoin || (() => {});
        this.onUserLeave = options.onUserLeave || (() => {});
        this.onPresenceUpdate = options.onPresenceUpdate || (() => {});
        this.onIncidentAdded = options.onIncidentAdded || (() => {});
        this.onIncidentUpdated = options.onIncidentUpdated || (() => {});
        this.onIncidentDeleted = options.onIncidentDeleted || (() => {});
        this.onKeyPointAdded = options.onKeyPointAdded || (() => {});
        this.onKeyPointUpdated = options.onKeyPointUpdated || (() => {});
        this.onKeyPointDeleted = options.onKeyPointDeleted || (() => {});
        this.onLockAcquired = options.onLockAcquired || (() => {});
        this.onLockReleased = options.onLockReleased || (() => {});
        this.onConflict = options.onConflict || (() => {});
        this.onError = options.onError || ((err) => console.error('Collaboration error:', err));
        this.onConnectionChange = options.onConnectionChange || (() => {});
        
        // UI Elements (to be set by consumer)
        this.activeUsersContainer = null;
    }
    
    /**
     * Join the collaborative session
     */
    async join() {
        try {
            const response = await fetch(`/api/collaboration/session/join/${this.shiftId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            
            const data = await response.json();
            
            if (!data.success) {
                throw new Error(data.error || 'Failed to join session');
            }
            
            this.sessionToken = data.session_token;
            this.activeUsers = data.active_users;
            this.locks = data.locks;
            this.lastChangeId = data.last_change_id;
            
            // Start SSE connection
            this.connectSSE();
            
            // Start heartbeat
            this.startHeartbeat();
            
            // Start lock refresh
            this.startLockRefresh();
            
            // Notify presence update
            this.onPresenceUpdate(this.activeUsers, this.locks);
            
            console.log(`Joined collaborative session for shift ${this.shiftId}`);
            
            return {
                activeUsers: this.activeUsers,
                draftIncidents: data.draft_incidents,
                draftKeypoints: data.draft_keypoints
            };
            
        } catch (error) {
            this.onError(error);
            throw error;
        }
    }
    
    /**
     * Leave the collaborative session
     */
    async leave() {
        try {
            // Stop intervals
            if (this.heartbeatInterval) {
                clearInterval(this.heartbeatInterval);
            }
            if (this.lockRefreshInterval) {
                clearInterval(this.lockRefreshInterval);
            }
            
            // Close SSE
            if (this.eventSource) {
                this.eventSource.close();
            }
            
            // Release all our locks
            for (const [key, lock] of this.currentLocks) {
                await this.releaseLock(lock.section_type, lock.item_id);
            }
            
            // Leave session
            await fetch(`/api/collaboration/session/leave/${this.shiftId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            
            console.log(`Left collaborative session for shift ${this.shiftId}`);
            
        } catch (error) {
            console.error('Error leaving session:', error);
        }
    }
    
    /**
     * Connect to Server-Sent Events stream
     */
    connectSSE() {
        if (this.eventSource) {
            this.eventSource.close();
        }
        
        const url = `/api/collaboration/stream/${this.shiftId}?last_change_id=${this.lastChangeId}`;
        this.eventSource = new EventSource(url);
        
        this.eventSource.onopen = () => {
            console.log('SSE connected');
            this.reconnectAttempts = 0;
            this.onConnectionChange(true);
        };
        
        this.eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.handleSSEMessage(data);
            } catch (e) {
                console.error('Error parsing SSE message:', e);
            }
        };
        
        this.eventSource.onerror = (error) => {
            console.error('SSE error:', error);
            this.onConnectionChange(false);
            
            // Attempt reconnect
            if (this.reconnectAttempts < this.maxReconnectAttempts) {
                this.reconnectAttempts++;
                setTimeout(() => this.connectSSE(), 2000 * this.reconnectAttempts);
            } else {
                this.onError(new Error('Lost connection to collaboration server'));
            }
        };
    }
    
    /**
     * Handle incoming SSE message
     */
    handleSSEMessage(data) {
        switch (data.type) {
            case 'connected':
                console.log('SSE stream connected');
                break;
                
            case 'presence':
                this.activeUsers = data.active_users;
                this.locks = data.locks;
                this.onPresenceUpdate(this.activeUsers, this.locks);
                break;
                
            case 'change':
                this.handleChange(data.data);
                break;
                
            case 'error':
                this.onError(new Error(data.message));
                break;
        }
    }
    
    /**
     * Handle a change event
     */
    handleChange(change) {
        this.lastChangeId = Math.max(this.lastChangeId, change.id);
        
        switch (change.change_type) {
            case 'add':
                if (change.section_type === 'incident') {
                    this.onIncidentAdded(change.new_value, change.user_name);
                } else if (change.section_type === 'keypoint') {
                    this.onKeyPointAdded(change.new_value, change.user_name);
                }
                break;
                
            case 'update':
                if (change.section_type === 'incident') {
                    this.onIncidentUpdated(change.new_value, change.old_value, change.user_name);
                } else if (change.section_type === 'keypoint') {
                    this.onKeyPointUpdated(change.new_value, change.old_value, change.user_name);
                }
                break;
                
            case 'delete':
                if (change.section_type === 'incident') {
                    this.onIncidentDeleted(change.item_id, change.user_name);
                } else if (change.section_type === 'keypoint') {
                    this.onKeyPointDeleted(change.item_id, change.user_name);
                }
                break;
                
            case 'lock':
                this.onLockAcquired(change.section_type, change.item_id, change.user_name);
                break;
                
            case 'unlock':
                this.onLockReleased(change.section_type, change.item_id, change.user_name);
                break;
        }
    }
    
    /**
     * Start heartbeat to keep session alive
     */
    startHeartbeat() {
        this.heartbeatInterval = setInterval(async () => {
            try {
                const response = await fetch(`/api/collaboration/session/heartbeat/${this.shiftId}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        current_section: this.currentSection,
                        current_item_id: this.currentItemId
                    })
                });
                
                const data = await response.json();
                if (data.success) {
                    this.activeUsers = data.active_users;
                    this.onPresenceUpdate(this.activeUsers, this.locks);
                }
            } catch (error) {
                console.error('Heartbeat error:', error);
            }
        }, 30000); // Every 30 seconds
    }
    
    /**
     * Start lock refresh to keep locks active
     */
    startLockRefresh() {
        this.lockRefreshInterval = setInterval(async () => {
            for (const [key, lock] of this.currentLocks) {
                try {
                    await fetch('/api/collaboration/lock/extend', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            shift_id: this.shiftId,
                            section_type: lock.section_type,
                            item_id: lock.item_id
                        })
                    });
                } catch (error) {
                    console.error('Lock refresh error:', error);
                }
            }
        }, 45000); // Every 45 seconds (locks expire at 60s)
    }
    
    /**
     * Set current editing context (for showing to other users)
     */
    setEditingContext(section, itemId) {
        this.currentSection = section;
        this.currentItemId = itemId;
    }
    
    /**
     * Acquire a lock on a section
     */
    async acquireLock(sectionType, itemId) {
        try {
            const response = await fetch('/api/collaboration/lock/acquire', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    shift_id: this.shiftId,
                    section_type: sectionType,
                    item_id: itemId
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                const key = `${sectionType}:${itemId}`;
                this.currentLocks.set(key, { section_type: sectionType, item_id: itemId });
                return true;
            } else {
                // Show who has the lock
                if (data.locked_by) {
                    this.onConflict({
                        type: 'lock_conflict',
                        section_type: sectionType,
                        item_id: itemId,
                        locked_by: data.locked_by
                    });
                }
                return false;
            }
        } catch (error) {
            this.onError(error);
            return false;
        }
    }
    
    /**
     * Release a lock on a section
     */
    async releaseLock(sectionType, itemId) {
        try {
            await fetch('/api/collaboration/lock/release', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    shift_id: this.shiftId,
                    section_type: sectionType,
                    item_id: itemId
                })
            });
            
            const key = `${sectionType}:${itemId}`;
            this.currentLocks.delete(key);
        } catch (error) {
            console.error('Error releasing lock:', error);
        }
    }
    
    /**
     * Check if a section is locked by another user
     */
    isLockedByOther(sectionType, itemId) {
        const lock = this.locks.find(l => 
            l.section_type === sectionType && 
            l.item_id === itemId
        );
        return lock && !lock.is_expired;
    }
    
    /**
     * Get lock info for a section
     */
    getLockInfo(sectionType, itemId) {
        return this.locks.find(l => 
            l.section_type === sectionType && 
            l.item_id === itemId
        );
    }
    
    // ========================================================================
    // Incident Operations
    // ========================================================================
    
    async addIncident(incidentData) {
        try {
            const response = await fetch('/api/collaboration/incident/add', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    shift_id: this.shiftId,
                    ...incidentData
                })
            });
            
            const data = await response.json();
            
            if (!data.success) {
                throw new Error(data.error);
            }
            
            return data.incident;
            
        } catch (error) {
            this.onError(error);
            throw error;
        }
    }
    
    async updateIncident(tempId, updates, version) {
        try {
            const response = await fetch('/api/collaboration/incident/update', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    shift_id: this.shiftId,
                    temp_id: tempId,
                    version: version,
                    ...updates
                })
            });
            
            const data = await response.json();
            
            if (!data.success) {
                if (response.status === 409) {
                    this.onConflict({
                        type: 'version_conflict',
                        section_type: 'incident',
                        item_id: tempId,
                        current: data.current,
                        attempted: updates
                    });
                }
                throw new Error(data.error);
            }
            
            return data.incident;
            
        } catch (error) {
            this.onError(error);
            throw error;
        }
    }
    
    async deleteIncident(tempId) {
        try {
            const response = await fetch('/api/collaboration/incident/delete', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    shift_id: this.shiftId,
                    temp_id: tempId
                })
            });
            
            const data = await response.json();
            
            if (!data.success) {
                throw new Error(data.error);
            }
            
            return true;
            
        } catch (error) {
            this.onError(error);
            throw error;
        }
    }
    
    // ========================================================================
    // Key Point Operations
    // ========================================================================
    
    async addKeyPoint(keyPointData) {
        try {
            const response = await fetch('/api/collaboration/keypoint/add', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    shift_id: this.shiftId,
                    ...keyPointData
                })
            });
            
            const data = await response.json();
            
            if (!data.success) {
                throw new Error(data.error);
            }
            
            return data.keypoint;
            
        } catch (error) {
            this.onError(error);
            throw error;
        }
    }
    
    async updateKeyPoint(tempId, updates, version) {
        try {
            const response = await fetch('/api/collaboration/keypoint/update', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    shift_id: this.shiftId,
                    temp_id: tempId,
                    version: version,
                    ...updates
                })
            });
            
            const data = await response.json();
            
            if (!data.success) {
                if (response.status === 409) {
                    this.onConflict({
                        type: 'version_conflict',
                        section_type: 'keypoint',
                        item_id: tempId,
                        current: data.current,
                        attempted: updates
                    });
                }
                throw new Error(data.error);
            }
            
            return data.keypoint;
            
        } catch (error) {
            this.onError(error);
            throw error;
        }
    }
    
    async deleteKeyPoint(tempId) {
        try {
            const response = await fetch('/api/collaboration/keypoint/delete', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    shift_id: this.shiftId,
                    temp_id: tempId
                })
            });
            
            const data = await response.json();
            
            if (!data.success) {
                throw new Error(data.error);
            }
            
            return true;
            
        } catch (error) {
            this.onError(error);
            throw error;
        }
    }
    
    // ========================================================================
    // UI Helpers
    // ========================================================================
    
    /**
     * Render active users badges
     */
    renderActiveUsers(container) {
        if (!container) return;
        
        container.innerHTML = '';
        
        this.activeUsers.forEach((user, index) => {
            const badge = document.createElement('div');
            badge.className = 'collab-user-badge';
            badge.style.cssText = `
                display: inline-flex;
                align-items: center;
                justify-content: center;
                width: 32px;
                height: 32px;
                border-radius: 50%;
                background: ${this.getUserColor(index)};
                color: white;
                font-weight: bold;
                font-size: 14px;
                margin-left: ${index > 0 ? '-8px' : '0'};
                border: 2px solid white;
                cursor: pointer;
                z-index: ${10 - index};
                position: relative;
            `;
            badge.textContent = user.user_avatar;
            badge.title = `${user.user_name}${user.current_section ? ` - Editing ${user.current_section}` : ''}`;
            
            // Pulse animation for users currently editing
            if (user.current_section) {
                badge.style.animation = 'collab-pulse 2s infinite';
            }
            
            container.appendChild(badge);
        });
        
        // Add count if more than 5 users
        if (this.activeUsers.length > 5) {
            const more = document.createElement('div');
            more.className = 'collab-user-more';
            more.style.cssText = `
                display: inline-flex;
                align-items: center;
                justify-content: center;
                width: 32px;
                height: 32px;
                border-radius: 50%;
                background: #6c757d;
                color: white;
                font-weight: bold;
                font-size: 12px;
                margin-left: -8px;
                border: 2px solid white;
            `;
            more.textContent = `+${this.activeUsers.length - 5}`;
            container.appendChild(more);
        }
    }
    
    /**
     * Get a consistent color for user index
     */
    getUserColor(index) {
        const colors = [
            '#4CAF50', '#2196F3', '#FF9800', '#9C27B0', '#E91E63',
            '#00BCD4', '#FF5722', '#3F51B5', '#8BC34A', '#FFC107'
        ];
        return colors[index % colors.length];
    }
    
    /**
     * Show a lock indicator on an element
     */
    showLockIndicator(element, lockedBy) {
        element.classList.add('collab-locked');
        
        let indicator = element.querySelector('.collab-lock-indicator');
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.className = 'collab-lock-indicator';
            indicator.style.cssText = `
                position: absolute;
                top: 0;
                right: 0;
                background: rgba(255, 152, 0, 0.9);
                color: white;
                padding: 2px 8px;
                font-size: 11px;
                border-radius: 0 0 0 4px;
                z-index: 100;
            `;
            element.style.position = 'relative';
            element.appendChild(indicator);
        }
        
        indicator.innerHTML = `<i class="bi bi-lock-fill"></i> ${lockedBy}`;
    }
    
    /**
     * Remove lock indicator from an element
     */
    hideLockIndicator(element) {
        element.classList.remove('collab-locked');
        const indicator = element.querySelector('.collab-lock-indicator');
        if (indicator) {
            indicator.remove();
        }
    }
    
    /**
     * Show attribution on an item
     */
    showAttribution(element, userName, timestamp) {
        let attr = element.querySelector('.collab-attribution');
        if (!attr) {
            attr = document.createElement('div');
            attr.className = 'collab-attribution';
            attr.style.cssText = `
                font-size: 11px;
                color: #6c757d;
                margin-top: 4px;
            `;
            element.appendChild(attr);
        }
        
        const timeStr = timestamp ? new Date(timestamp).toLocaleTimeString() : '';
        attr.innerHTML = `<i class="bi bi-person"></i> ${userName} ${timeStr ? `at ${timeStr}` : ''}`;
    }
    
    /**
     * Show toast notification
     */
    showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `collab-toast collab-toast-${type}`;
        toast.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            padding: 12px 20px;
            background: ${type === 'error' ? '#dc3545' : type === 'warning' ? '#ffc107' : '#17a2b8'};
            color: ${type === 'warning' ? '#212529' : 'white'};
            border-radius: 4px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            z-index: 9999;
            animation: slideIn 0.3s ease;
        `;
        toast.textContent = message;
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }
}

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes collab-pulse {
        0%, 100% { box-shadow: 0 0 0 0 rgba(76, 175, 80, 0.4); }
        50% { box-shadow: 0 0 0 8px rgba(76, 175, 80, 0); }
    }
    
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
    
    .collab-locked {
        opacity: 0.7;
        pointer-events: none;
    }
    
    .collab-locked input,
    .collab-locked textarea,
    .collab-locked select {
        background-color: #f8f9fa !important;
    }
    
    .collab-highlight {
        animation: collab-highlight 1s ease;
    }
    
    @keyframes collab-highlight {
        0% { background-color: rgba(76, 175, 80, 0.3); }
        100% { background-color: transparent; }
    }
`;
document.head.appendChild(style);

// Export for use
window.CollaborativeHandover = CollaborativeHandover;
