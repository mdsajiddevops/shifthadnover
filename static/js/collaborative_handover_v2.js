/**
 * Collaborative Handover Client v2
 * =================================
 * Enhanced real-time collaborative editing for handover forms.
 * Features:
 * - Live field synchronization as users type (no save required)
 * - Automatic change broadcasting via SSE
 * - Field-level locking with visual indicators
 * - User attribution for all changes
 * - Conflict detection and resolution
 */

class CollaborativeHandoverV2 {
    constructor(shiftId, options = {}) {
        this.shiftId = shiftId;
        this.sessionToken = null;
        this.eventSource = null;
        this.lastChangeId = 0;
        this.activeUsers = [];
        this.locks = {};
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.heartbeatInterval = null;
        this.lockRefreshInterval = null;
        this.currentLocks = new Map();
        this.pendingChanges = new Map(); // Track pending changes for debouncing
        this.fieldVersions = new Map(); // Track field versions for conflict detection
        this.isConnected = false;
        this.userId = null;
        this.userName = null;
        
        // Debounce timers
        this.debounceTimers = new Map();
        this.DEBOUNCE_DELAY = 300; // ms - send changes after 300ms of inactivity
        this.TYPING_INDICATOR_DELAY = 100; // ms - show typing indicator faster
        
        // Callbacks
        this.callbacks = {
            onUserJoin: options.onUserJoin || (() => {}),
            onUserLeave: options.onUserLeave || (() => {}),
            onPresenceUpdate: options.onPresenceUpdate || (() => {}),
            onFieldChange: options.onFieldChange || (() => {}),
            onItemAdded: options.onItemAdded || (() => {}),
            onItemUpdated: options.onItemUpdated || (() => {}),
            onItemDeleted: options.onItemDeleted || (() => {}),
            onLockAcquired: options.onLockAcquired || (() => {}),
            onLockReleased: options.onLockReleased || (() => {}),
            onTypingStart: options.onTypingStart || (() => {}),
            onTypingStop: options.onTypingStop || (() => {}),
            onConflict: options.onConflict || (() => {}),
            onError: options.onError || ((err) => console.error('Collaboration error:', err)),
            onConnectionChange: options.onConnectionChange || (() => {}),
            onSyncComplete: options.onSyncComplete || (() => {})
        };
        
        // Color palette for user indicators
        this.userColors = [
            '#4CAF50', '#2196F3', '#9C27B0', '#FF9800', '#E91E63',
            '#00BCD4', '#8BC34A', '#FF5722', '#673AB7', '#3F51B5'
        ];
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
            this.locks = this._processLocks(data.locks || []);
            this.lastChangeId = data.last_change_id || 0;
            this.userId = data.user_id;
            this.userName = data.user_name;
            
            // Connect to SSE stream
            this.connectSSE();
            
            // Start heartbeat
            this.startHeartbeat();
            
            // Start lock refresh
            this.startLockRefresh();
            
            // Update UI with active users
            this.updateActiveUsersUI();
            
            console.log(`Joined collaborative session for shift ${this.shiftId}`);
            
            // Return initial data for syncing
            return {
                activeUsers: this.activeUsers,
                draftIncidents: data.draft_incidents || [],
                draftKeypoints: data.draft_keypoints || [],
                draftChanges: data.draft_changes || [],
                fieldStates: data.field_states || {}
            };
            
        } catch (error) {
            this.callbacks.onError(error);
            throw error;
        }
    }
    
    /**
     * Leave the collaborative session
     */
    async leave() {
        try {
            this.isConnected = false;
            
            // Clear all intervals
            if (this.heartbeatInterval) clearInterval(this.heartbeatInterval);
            if (this.lockRefreshInterval) clearInterval(this.lockRefreshInterval);
            
            // Clear all debounce timers
            for (const timer of this.debounceTimers.values()) {
                clearTimeout(timer);
            }
            this.debounceTimers.clear();
            
            // Close SSE connection
            if (this.eventSource) {
                this.eventSource.close();
                this.eventSource = null;
            }
            
            // Release all locks
            for (const [key, lock] of this.currentLocks) {
                await this.releaseLock(lock.section_type, lock.item_id);
            }
            
            // Notify server
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
     * Connect to SSE stream for real-time updates
     */
    connectSSE() {
        if (this.eventSource) {
            this.eventSource.close();
        }
        
        // Use v2 endpoint for enhanced field-level updates and typing indicators
        const url = `/api/collaboration/stream/v2/${this.shiftId}?last_change_id=${this.lastChangeId}&session=${this.sessionToken}`;
        this.eventSource = new EventSource(url);
        
        this.eventSource.onopen = () => {
            console.log('SSE connected');
            this.isConnected = true;
            this.reconnectAttempts = 0;
            this.callbacks.onConnectionChange(true);
            this.updateConnectionStatusUI(true);
        };
        
        this.eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.handleSSEMessage(data);
            } catch (e) {
                console.error('Error parsing SSE message:', e);
            }
        };
        
        this.eventSource.onerror = () => {
            console.error('SSE connection error');
            this.isConnected = false;
            this.callbacks.onConnectionChange(false);
            this.updateConnectionStatusUI(false);
            
            // Attempt reconnect with exponential backoff
            if (this.reconnectAttempts < this.maxReconnectAttempts) {
                this.reconnectAttempts++;
                const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
                console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
                setTimeout(() => this.connectSSE(), delay);
            } else {
                this.callbacks.onError(new Error('Lost connection to collaboration server'));
            }
        };
    }
    
    /**
     * Handle incoming SSE message
     */
    handleSSEMessage(data) {
        switch (data.type) {
            case 'connected':
                console.log('SSE stream initialized');
                break;
                
            case 'presence':
                this.activeUsers = data.active_users || [];
                this.locks = this._processLocks(data.locks || []);
                this.callbacks.onPresenceUpdate(this.activeUsers, this.locks);
                this.updateActiveUsersUI();
                this.updateLockIndicatorsUI();
                break;
                
            case 'change':
                this.handleRemoteChange(data.data);
                break;
                
            case 'field_update':
                console.log('[COLLAB] Received field_update event:', data);
                this.handleFieldUpdate(data.data);
                break;
                
            case 'typing':
                this.handleTypingIndicator(data.data);
                break;
                
            case 'user_joined':
                this.activeUsers = data.active_users || this.activeUsers;
                this.callbacks.onUserJoin(data.user);
                this.updateActiveUsersUI();
                this.showNotification(`${data.user?.user_name || data.user?.username || 'Someone'} joined the session`, 'info');
                break;
                
            case 'user_left':
                this.activeUsers = data.active_users || this.activeUsers;
                this.callbacks.onUserLeave(data.user);
                this.updateActiveUsersUI();
                this.showNotification(`${data.user?.user_name || data.user?.username || 'Someone'} left the session`, 'info');
                break;
                
            case 'error':
                this.callbacks.onError(new Error(data.message));
                break;
        }
    }
    
    /**
     * Handle a remote change (add/update/delete)
     */
    handleRemoteChange(change) {
        if (!change) return;
        
        this.lastChangeId = Math.max(this.lastChangeId, change.id || 0);
        
        console.log('Remote change received:', change);
        
        switch (change.change_type) {
            case 'add':
                this.handleRemoteAdd(change);
                break;
            case 'update':
                this.handleRemoteUpdate(change);
                break;
            case 'delete':
                this.handleRemoteDelete(change);
                break;
            case 'lock':
                this.handleRemoteLock(change);
                break;
            case 'unlock':
                this.handleRemoteUnlock(change);
                break;
        }
    }
    
    /**
     * Handle field-level updates (for live typing sync)
     */
    handleFieldUpdate(data) {
        console.log('[COLLAB] handleFieldUpdate called with:', data);
        
        if (!data || data.user_id === this.userId) {
            console.log('[COLLAB] Skipping own change or no data');
            return; // Skip our own changes
        }
        
        const { section_type, item_id, field_name, value, user_name } = data;
        console.log('[COLLAB] Processing field update:', { section_type, item_id, field_name, value, user_name });
        
        // Show editing indicator on the entry (brief)
        this.showEditingIndicator(section_type, item_id, user_name);
        
        // Clear editing indicator after a short delay
        const editKey = `${section_type}:${item_id}`;
        if (this._editingTimers && this._editingTimers[editKey]) {
            clearTimeout(this._editingTimers[editKey]);
        }
        if (!this._editingTimers) this._editingTimers = {};
        this._editingTimers[editKey] = setTimeout(() => {
            this.hideEditingIndicator(section_type, item_id);
        }, 1500); // Reduced to 1.5s for faster clearing
        
        // Hide typing indicator since we received the actual value
        this.hideTypingIndicator(section_type, item_id, field_name);
        
        // Find the field in the DOM and update it
        const field = this.findFieldElement(section_type, item_id, field_name);
        console.log('[COLLAB DEBUG] Finding field:', { section_type, item_id, field_name, found: !!field });
        
        if (field) {
            // Store current cursor position if this field is focused
            const wasFocused = document.activeElement === field;
            const cursorPos = wasFocused ? field.selectionStart : null;
            
            // Update value
            console.log('[COLLAB DEBUG] Updating field value:', { 
                currentValue: field.value, 
                newValue: value, 
                fieldName: field.name,
                fieldId: field.id 
            });
            
            if (field.value !== value) {
                // CRITICAL: Mark field as remotely updated to prevent re-broadcasting
                field.dataset.collabRemoteUpdate = 'true';
                
                field.value = value;
                
                // Trigger input event so any form listeners are notified
                // But our listener will skip re-broadcasting due to the flag
                field.dispatchEvent(new Event('input', { bubbles: true }));
                
                // Clear the flag after event dispatch
                setTimeout(() => {
                    delete field.dataset.collabRemoteUpdate;
                }, 50);
                
                // Add visual indicator for remote change
                this.showFieldUpdateIndicator(field, user_name);
                
                // Add/update attribution badge on the entry
                const entry = field.closest('.incident-entry, .keypoint-entry, .changeinfo-entry, .kbupdate-entry, .kb-update-entry');
                if (entry) {
                    this.updateEntryAttribution(entry, user_name, 'Updated');
                }
            }
            
            // Restore cursor if was focused (for minimal disruption)
            if (wasFocused && cursorPos !== null) {
                field.setSelectionRange(cursorPos, cursorPos);
            }
        } else {
            console.warn('[COLLAB] Could not find field element:', { section_type, item_id, field_name });
        }
        
        this.callbacks.onFieldChange({
            section_type, item_id, field_name, value, user_name
        });
    }
    
    /**
     * Handle typing indicator from other users
     */
    handleTypingIndicator(data) {
        if (!data || data.user_id === this.userId) return;
        
        const { section_type, item_id, field_name, user_name, is_typing } = data;
        const key = `${section_type}:${item_id}:${field_name}`;
        
        // Initialize typing timeout map
        if (!this._typingTimeouts) this._typingTimeouts = {};
        
        // Clear any existing auto-clear timeout for this field
        if (this._typingTimeouts[key]) {
            clearTimeout(this._typingTimeouts[key]);
            delete this._typingTimeouts[key];
        }
        
        if (is_typing) {
            this.callbacks.onTypingStart({ section_type, item_id, field_name, user_name });
            this.showTypingIndicator(section_type, item_id, field_name, user_name);
            
            // Auto-clear typing indicator after 3 seconds of no updates (safety net)
            this._typingTimeouts[key] = setTimeout(() => {
                this.hideTypingIndicator(section_type, item_id, field_name);
                this.hideEditingIndicator(section_type, item_id);
            }, 3000);
        } else {
            this.callbacks.onTypingStop({ section_type, item_id, field_name, user_name });
            this.hideTypingIndicator(section_type, item_id, field_name);
        }
    }
    
    /**
     * Handle remote item addition
     */
    handleRemoteAdd(change) {
        const { section_type, item_id, new_value, user_name } = change;
        
        this.callbacks.onItemAdded({ section_type, item_id, data: new_value, user_name });
        
        // Add item to the DOM
        this.addItemToDOM(section_type, item_id, new_value, user_name);
        
        this.showNotification(`${user_name} added a new ${this.getSectionLabel(section_type)}`, 'success');
    }
    
    /**
     * Handle remote item update
     */
    handleRemoteUpdate(change) {
        const { section_type, item_id, new_value, old_value, user_name, field_name } = change;
        
        this.callbacks.onItemUpdated({ section_type, item_id, data: new_value, oldData: old_value, user_name });
        
        // Update item in the DOM
        this.updateItemInDOM(section_type, item_id, new_value, user_name, field_name);
    }
    
    /**
     * Handle remote item deletion
     */
    handleRemoteDelete(change) {
        const { section_type, item_id, user_name } = change;
        
        this.callbacks.onItemDeleted({ section_type, item_id, user_name });
        
        // Remove item from the DOM with animation
        this.removeItemFromDOM(section_type, item_id);
        
        this.showNotification(`${user_name} removed a ${this.getSectionLabel(section_type)}`, 'warning');
    }
    
    /**
     * Handle remote lock acquisition
     */
    handleRemoteLock(change) {
        const { section_type, item_id, user_id, user_name } = change;
        
        if (user_id !== this.userId) {
            this.locks[`${section_type}:${item_id}`] = {
                section_type, item_id, user_id, user_name,
                locked_at: new Date().toISOString()
            };
            
            this.callbacks.onLockAcquired({ section_type, item_id, user_name });
            this.showLockIndicator(section_type, item_id, user_name);
        }
    }
    
    /**
     * Handle remote lock release
     */
    handleRemoteUnlock(change) {
        const { section_type, item_id } = change;
        
        console.log('[COLLAB] Lock released:', section_type, item_id);
        
        delete this.locks[`${section_type}:${item_id}`];
        
        this.callbacks.onLockReleased({ section_type, item_id });
        this.hideLockIndicator(section_type, item_id);
        
        // Also hide editing indicator when lock is released
        this.hideEditingIndicator(section_type, item_id);
    }
    
    // ========================================================================
    // Field Change Broadcasting (Live Sync)
    // ========================================================================
    
    /**
     * Broadcast a field change to other users (called when user types)
     */
    async broadcastFieldChange(sectionType, itemId, fieldName, value) {
        console.log('[COLLAB SEND] Broadcasting field change:', { sectionType, itemId, fieldName, value: value?.substring?.(0, 50) || value });
        const key = `${sectionType}:${itemId}:${fieldName}`;
        
        // Store the latest value for this field
        if (!this._pendingValues) this._pendingValues = {};
        this._pendingValues[key] = { sectionType, itemId, fieldName, value };
        
        // Clear existing debounce timer
        if (this.debounceTimers.has(key)) {
            clearTimeout(this.debounceTimers.get(key));
        }
        
        // Send typing indicator immediately
        this.sendTypingIndicator(sectionType, itemId, fieldName, true);
        
        // Debounce the actual field update (reduced to 150ms for faster sync)
        const timer = setTimeout(async () => {
            try {
                await this.sendFieldUpdate(sectionType, itemId, fieldName, value);
                // Don't stop typing here - wait for blur or explicit stop
            } catch (error) {
                console.error('Error broadcasting field change:', error);
            }
        }, 150); // Reduced from 300ms
        
        this.debounceTimers.set(key, timer);
    }
    
    /**
     * Flush pending field update immediately (called on blur)
     * This ensures the final value is sent without waiting for debounce
     */
    async flushFieldUpdate(sectionType, itemId, fieldName, value) {
        const key = `${sectionType}:${itemId}:${fieldName}`;
        
        // Cancel any pending debounced update
        if (this.debounceTimers.has(key)) {
            clearTimeout(this.debounceTimers.get(key));
            this.debounceTimers.delete(key);
        }
        
        // Send the final value immediately
        try {
            await this.sendFieldUpdate(sectionType, itemId, fieldName, value);
        } catch (error) {
            console.error('Error flushing field update:', error);
        }
        
        // Stop typing indicator
        this.sendTypingIndicator(sectionType, itemId, fieldName, false);
        
        // Clean up pending value
        if (this._pendingValues) {
            delete this._pendingValues[key];
        }
    }
    
    /**
     * Send field update to server
     */
    async sendFieldUpdate(sectionType, itemId, fieldName, value) {
        try {
            const response = await fetch('/api/collaboration/field/update', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    shift_id: this.shiftId,
                    session_token: this.sessionToken,
                    section_type: sectionType,
                    item_id: itemId,
                    field_name: fieldName,
                    value: value
                })
            });
            
            const data = await response.json();
            
            // Handle concurrent edit warning (non-blocking)
            if (data.warning === 'concurrent_edit') {
                // Show a subtle notification instead of blocking modal
                this.showNotification(`${data.last_modified_by} is also editing this field`, 'warning');
            }
            
            // Only show conflict modal for actual conflicts (rare case)
            if (!data.success && data.conflict) {
                this.callbacks.onConflict({
                    type: 'field_conflict',
                    section_type: sectionType,
                    item_id: itemId,
                    field_name: fieldName,
                    our_value: value,
                    their_value: data.current_value,
                    their_user: data.last_modified_by
                });
            }
            
            return data;
            
        } catch (error) {
            this.callbacks.onError(error);
            throw error;
        }
    }
    
    /**
     * Send typing indicator
     */
    async sendTypingIndicator(sectionType, itemId, fieldName, isTyping) {
        try {
            await fetch('/api/collaboration/typing', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    shift_id: this.shiftId,
                    session_token: this.sessionToken,
                    section_type: sectionType,
                    item_id: itemId,
                    field_name: fieldName,
                    is_typing: isTyping
                })
            });
        } catch (error) {
            console.error('Error sending typing indicator:', error);
        }
    }
    
    // ========================================================================
    // Lock Management
    // ========================================================================
    
    /**
     * Acquire a lock on a section/field
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
                if (data.locked_by) {
                    this.showLockConflictWarning(sectionType, itemId, data.locked_by.user_name);
                }
                return false;
            }
        } catch (error) {
            this.callbacks.onError(error);
            return false;
        }
    }
    
    /**
     * Release a lock
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
     * Check if a section is locked by someone else
     */
    isLockedByOther(sectionType, itemId) {
        const key = `${sectionType}:${itemId}`;
        const lock = this.locks[key];
        return lock && lock.user_id !== this.userId;
    }
    
    // ========================================================================
    // Item CRUD Operations
    // ========================================================================
    
    /**
     * Add a new item (incident, keypoint, etc.)
     */
    async addItem(sectionType, itemData) {
        try {
            const response = await fetch(`/api/collaboration/${sectionType}/add`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    shift_id: this.shiftId,
                    ...itemData
                })
            });
            
            const data = await response.json();
            
            if (!data.success) {
                throw new Error(data.error);
            }
            
            return data.item || data.incident || data.keypoint;
            
        } catch (error) {
            this.callbacks.onError(error);
            throw error;
        }
    }
    
    /**
     * Update an item
     */
    async updateItem(sectionType, itemId, updates) {
        try {
            const response = await fetch(`/api/collaboration/${sectionType}/update`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    shift_id: this.shiftId,
                    temp_id: itemId,
                    ...updates
                })
            });
            
            const data = await response.json();
            
            if (!data.success) {
                if (data.error?.includes('Conflict')) {
                    this.callbacks.onConflict({
                        type: 'item_conflict',
                        section_type: sectionType,
                        item_id: itemId,
                        current: data.current
                    });
                }
                throw new Error(data.error);
            }
            
            return data.item || data.incident || data.keypoint;
            
        } catch (error) {
            this.callbacks.onError(error);
            throw error;
        }
    }
    
    /**
     * Delete an item
     */
    async deleteItem(sectionType, itemId) {
        try {
            const response = await fetch(`/api/collaboration/${sectionType}/delete`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    shift_id: this.shiftId,
                    temp_id: itemId
                })
            });
            
            const data = await response.json();
            
            if (!data.success) {
                throw new Error(data.error);
            }
            
            return true;
            
        } catch (error) {
            this.callbacks.onError(error);
            throw error;
        }
    }
    
    // ========================================================================
    // Heartbeat & Session Management
    // ========================================================================
    
    startHeartbeat() {
        this.heartbeatInterval = setInterval(async () => {
            try {
                const response = await fetch(`/api/collaboration/session/heartbeat/${this.shiftId}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        session_token: this.sessionToken,
                        current_section: this.currentSection,
                        current_item_id: this.currentItemId
                    })
                });
                
                const data = await response.json();
                if (data.success && data.active_users) {
                    this.activeUsers = data.active_users;
                    this.updateActiveUsersUI();
                }
            } catch (error) {
                console.error('Heartbeat error:', error);
            }
        }, 15000); // Every 15 seconds
    }
    
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
        }, 30000); // Every 30 seconds
    }
    
    // ========================================================================
    // UI Helper Methods
    // ========================================================================
    
    /**
     * Find a field element in the DOM
     */
    findFieldElement(sectionType, itemId, fieldName) {
        // Build selector based on section type and field name
        const containerMap = {
            'incident_open': '#open-incidents-container',
            'incident_closed': '#closed-incidents-container',
            'incident_priority': '#priority-incidents-container',
            'incident_handover': '#handover-incidents-container',
            'keypoint': '#keypoints-container',
            'change': '#changes-container',
            'changeinfo': '#changes-container',
            'kbupdate': '#kbupdates-container'
        };
        
        // Map section types to field name prefixes used in the form
        const fieldPrefixMap = {
            'incident_open': 'open_incident',
            'incident_closed': 'closed_incident',
            'incident_priority': 'priority_incident',
            'incident_handover': 'handover_incident',
            'keypoint': 'keypoint',
            'change': 'change',
            'changeinfo': 'change',
            'kbupdate': 'kb'
        };
        
        const container = document.querySelector(containerMap[sectionType]);
        if (!container) {
            console.log(`[Collab] Container not found for section: ${sectionType}`);
            return null;
        }
        
        // Find all entries in the container
        const items = container.querySelectorAll('.incident-entry, .keypoint-entry, .changeinfo-entry, .kbupdate-entry, .kb-update-entry');
        
        // Extract index from itemId (e.g., "incident_open_0" -> 0)
        let targetIndex = 0;
        const indexMatch = itemId.match(/_([0-9]+)$/);
        if (indexMatch) {
            targetIndex = parseInt(indexMatch[1], 10);
        }
        
        console.log(`[Collab] Looking for field: section=${sectionType}, itemId=${itemId}, field=${fieldName}, targetIndex=${targetIndex}, items found=${items.length}`);
        
        // Get the item at the target index
        const item = items[targetIndex];
        if (!item) {
            console.log(`[Collab] Item at index ${targetIndex} not found`);
            return null;
        }
        
        // DEBUG: Log all fields in this item
        const allFields = item.querySelectorAll('input, textarea, select');
        console.log(`[Collab DEBUG] All fields in item ${targetIndex}:`, Array.from(allFields).map(f => f.name || f.id || 'no-name'));
        
        // Build the expected field name based on form naming convention
        const prefix = fieldPrefixMap[sectionType] || sectionType;
        
        // Actual field name mappings based on form HTML
        // Form uses: open_incident_app[], closed_incident_id[], etc.
        const fieldNameMap = {
            'app': ['_app[]'],
            'app_name': ['_app[]'],
            'incident_id': ['_id[]'],
            'id': ['_id[]'],
            'priority': ['_priority[]'],
            'level': ['_level[]'],
            'assigned': ['_assigned[]'],
            'assigned_to': ['_assigned[]'],
            'description': ['_description[]'],
            'resolution': ['_resolution[]'],
            'status': ['_status[]'],
            'next_by': ['_next_by[]'],
            'notes': ['_notes[]'],
            'escalated': ['_escalated[]'],
            'impact': ['_impact[]'],
            'to': ['_to[]']
        };
        
        let field = null;
        
        // Strategy 1: Try exact field name match using prefix + fieldName pattern
        // e.g., for incident_closed + app -> closed_incident_app[]
        const exactName = `${prefix}_${fieldName}[]`;
        field = item.querySelector(`[name="${exactName}"]`);
        console.log(`[Collab] Strategy 1 - Exact match for name="${exactName}":`, field ? 'FOUND' : 'not found');
        
        // Strategy 2: Try field name variations from map
        if (!field && fieldNameMap[fieldName]) {
            for (const suffix of fieldNameMap[fieldName]) {
                const tryName = `${prefix}${suffix}`;
                field = item.querySelector(`[name="${tryName}"]`);
                if (field) {
                    console.log(`[Collab] Strategy 2 - Found with name="${tryName}"`);
                    break;
                }
            }
        }
        
        // Strategy 3: Try data-collab-id attribute (if we set it)
        if (!field) {
            field = item.querySelector(`[data-collab-id$="_${fieldName}"], [data-collab-id$="_${fieldName}[]"]`);
            if (field) console.log(`[Collab] Strategy 3 - Found via data-collab-id`);
        }
        
        // Strategy 4: Find by field name ending with _fieldName[]
        if (!field) {
            const inputs = item.querySelectorAll('input, textarea, select');
            for (const input of inputs) {
                const inputName = input.name || '';
                // Match fields ending with _fieldName[] (e.g., closed_incident_app[])
                if (inputName.endsWith(`_${fieldName}[]`) || inputName.endsWith(`_${fieldName}`)) {
                    field = input;
                    console.log(`[Collab] Strategy 4 - Found via suffix match: ${inputName}`);
                    break;
                }
            }
        }
        
        if (field) {
            console.log(`[Collab] Found field for ${sectionType}:${itemId}:${fieldName}`, field.name);
            return field;
        }
        
        console.log(`[Collab] Field not found: ${sectionType}:${itemId}:${fieldName}`);
        return null;
    }
    
    /**
     * Update attribution badge on an entry showing who last modified it
     */
    updateEntryAttribution(entry, userName, action = 'Updated') {
        if (!entry) return;
        
        // Find or create attribution badge
        let badge = entry.querySelector('.collab-attribution-badge');
        if (!badge) {
            badge = document.createElement('div');
            badge.className = 'collab-attribution-badge';
            
            // Insert at the top of the entry
            entry.style.position = 'relative';
            entry.insertBefore(badge, entry.firstChild);
        }
        
        // Update badge content
        const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        badge.innerHTML = `<i class="fas fa-user-edit"></i> ${action} by <strong>${userName}</strong> at ${timestamp}`;
        badge.classList.add('collab-attribution-visible');
        
        // Keep the badge visible for 30 seconds, then make it subtle
        clearTimeout(badge._fadeTimer);
        badge._fadeTimer = setTimeout(() => {
            badge.classList.remove('collab-attribution-visible');
            badge.classList.add('collab-attribution-subtle');
        }, 30000);
    }
    
    /**
     * Show field update indicator (brief highlight)
     */
    showFieldUpdateIndicator(field, userName) {
        field.classList.add('collab-field-updated');
        
        // Add attribution tooltip
        const tooltip = document.createElement('span');
        tooltip.className = 'collab-update-tooltip';
        tooltip.textContent = `Updated by ${userName}`;
        field.parentElement.appendChild(tooltip);
        
        setTimeout(() => {
            field.classList.remove('collab-field-updated');
            tooltip.remove();
        }, 2000);
    }
    
    /**
     * Show typing indicator for a field
     */
    showTypingIndicator(sectionType, itemId, fieldName, userName) {
        const field = this.findFieldElement(sectionType, itemId, fieldName);
        if (!field) return;
        
        let indicator = field.parentElement.querySelector('.collab-typing-indicator');
        if (!indicator) {
            indicator = document.createElement('span');
            indicator.className = 'collab-typing-indicator';
            field.parentElement.appendChild(indicator);
        }
        
        indicator.innerHTML = `<span class="typing-dots"><span></span><span></span><span></span></span> ${userName} is typing...`;
        indicator.style.display = 'inline-flex';
    }
    
    /**
     * Hide typing indicator for a field
     */
    hideTypingIndicator(sectionType, itemId, fieldName) {
        const field = this.findFieldElement(sectionType, itemId, fieldName);
        if (!field) return;
        
        const indicator = field.parentElement.querySelector('.collab-typing-indicator');
        if (indicator) {
            indicator.style.display = 'none';
        }
    }
    
    /**
     * Show editing indicator on a section (softer than lock - doesn't disable inputs)
     */
    showEditingIndicator(sectionType, itemId, userName) {
        const element = this.findSectionElement(sectionType, itemId);
        if (!element) return;
        
        element.classList.add('collab-editing-entry');
        element.dataset.editingBy = userName;
        
        let indicator = element.querySelector('.collab-editing-indicator');
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.className = 'collab-editing-indicator';
            element.appendChild(indicator);
        }
        
        indicator.innerHTML = `<i class="fas fa-edit"></i> ${userName} is editing`;
    }
    
    /**
     * Hide editing indicator
     */
    hideEditingIndicator(sectionType, itemId) {
        const element = this.findSectionElement(sectionType, itemId);
        if (!element) return;
        
        element.classList.remove('collab-editing-entry');
        delete element.dataset.editingBy;
        
        const indicator = element.querySelector('.collab-editing-indicator');
        if (indicator) indicator.remove();
    }
    
    /**
     * Show lock indicator on a section
     */
    showLockIndicator(sectionType, itemId, userName) {
        const element = this.findSectionElement(sectionType, itemId);
        if (!element) return;
        
        element.classList.add('collab-locked');
        element.dataset.lockedBy = userName;
        
        let indicator = element.querySelector('.collab-lock-badge');
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.className = 'collab-lock-badge';
            element.appendChild(indicator);
        }
        
        indicator.innerHTML = `<i class="fas fa-lock"></i> ${userName} is editing`;
        
        // Disable inputs in the locked section
        element.querySelectorAll('input, textarea, select').forEach(input => {
            input.classList.add('collab-input-locked');
            input.dataset.wasDisabled = input.disabled;
            input.disabled = true;
        });
    }
    
    /**
     * Hide lock indicator
     */
    hideLockIndicator(sectionType, itemId) {
        const element = this.findSectionElement(sectionType, itemId);
        if (!element) return;
        
        element.classList.remove('collab-locked');
        delete element.dataset.lockedBy;
        
        const indicator = element.querySelector('.collab-lock-badge');
        if (indicator) indicator.remove();
        
        // Re-enable inputs
        element.querySelectorAll('input, textarea, select').forEach(input => {
            input.classList.remove('collab-input-locked');
            if (input.dataset.wasDisabled === 'false') {
                input.disabled = false;
            }
            delete input.dataset.wasDisabled;
        });
    }
    
    /**
     * Show lock conflict warning
     */
    showLockConflictWarning(sectionType, itemId, userName) {
        this.showNotification(`${userName} is currently editing this section. Please wait.`, 'warning');
    }
    
    /**
     * Find a section element in the DOM
     */
    findSectionElement(sectionType, itemId) {
        const containerMap = {
            'incident_open': '#open-incidents-container',
            'incident_closed': '#closed-incidents-container',
            'incident_priority': '#priority-incidents-container',
            'incident_handover': '#handover-incidents-container',
            'keypoint': '#keypoints-container',
            'change': '#changes-container',
            'changeinfo': '#changes-container',
            'kbupdate': '#kbupdates-container'
        };
        
        const container = document.querySelector(containerMap[sectionType]);
        if (!container) return null;
        
        if (!itemId) return container;
        
        const items = container.querySelectorAll('.incident-entry, .keypoint-entry, .changeinfo-entry, .kbupdate-entry, .kb-update-entry');
        
        // Extract index from itemId (e.g., "incident_open_0" -> 0)
        let targetIndex = 0;
        const indexMatch = itemId.match(/_([0-9]+)$/);
        if (indexMatch) {
            targetIndex = parseInt(indexMatch[1], 10);
        }
        
        // Return the item at the target index
        if (items[targetIndex]) {
            return items[targetIndex];
        }
        
        // Fallback: try matching by data attributes
        for (const item of items) {
            if (item.dataset.tempId === itemId || item.dataset.itemId === itemId) {
                return item;
            }
        }
        
        return null;
    }
    
    /**
     * Add an item to the DOM
     */
    addItemToDOM(sectionType, itemId, data, userName) {
        const containerMap = {
            'incident_open': { container: '#open-incidents-container', addFn: 'addIncident', type: 'open' },
            'incident_closed': { container: '#closed-incidents-container', addFn: 'addIncident', type: 'closed' },
            'incident_priority': { container: '#priority-incidents-container', addFn: 'addIncident', type: 'priority' },
            'incident_handover': { container: '#handover-incidents-container', addFn: 'addIncident', type: 'handover' },
            'keypoint': { container: '#keypoints-container', addFn: 'addKeyPoint' },
            'changeinfo': { container: '#changes-container', addFn: 'addChangeInfo' },
            'kbupdate': { container: '#kbupdates-container', addFn: 'addKBUpdate' }
        };
        
        const config = containerMap[sectionType];
        if (!config) return;
        
        // Use existing add function if available
        if (typeof window[config.addFn] === 'function') {
            window[config.addFn](config.type);
        }
        
        // Populate the new entry with data
        const container = document.querySelector(config.container);
        if (!container) return;
        
        const entries = container.querySelectorAll('.incident-entry, .keypoint-entry, .changeinfo-entry, .kbupdate-entry, .kb-update-entry');
        const newEntry = entries[entries.length - 1];
        
        if (newEntry) {
            newEntry.dataset.tempId = itemId;
            newEntry.classList.add('collab-new-item');
            
            // Populate fields
            this.populateEntryFields(newEntry, data);
            
            // Add attribution
            this.addAttributionBadge(newEntry, userName, 'Added');
            
            // Remove highlight after animation
            setTimeout(() => {
                newEntry.classList.remove('collab-new-item');
            }, 3000);
        }
    }
    
    /**
     * Update an item in the DOM
     */
    updateItemInDOM(sectionType, itemId, data, userName, changedField) {
        const element = this.findSectionElement(sectionType, itemId);
        if (!element) return;
        
        // Update fields
        this.populateEntryFields(element, data);
        
        // Highlight the changed field or entire entry
        element.classList.add('collab-updated-item');
        
        // Update attribution
        this.updateAttributionBadge(element, userName, changedField);
        
        setTimeout(() => {
            element.classList.remove('collab-updated-item');
        }, 2000);
    }
    
    /**
     * Remove an item from the DOM
     */
    removeItemFromDOM(sectionType, itemId) {
        const element = this.findSectionElement(sectionType, itemId);
        if (!element) return;
        
        element.classList.add('collab-deleted-item');
        
        setTimeout(() => {
            element.remove();
        }, 500);
    }
    
    /**
     * Populate entry fields with data
     */
    populateEntryFields(entry, data) {
        if (!data) return;
        
        Object.entries(data).forEach(([key, value]) => {
            const field = entry.querySelector(`[name*="${key}"], [data-field="${key}"]`);
            if (field && value !== undefined && value !== null) {
                field.value = value;
            }
        });
    }
    
    /**
     * Add attribution badge to an entry
     */
    addAttributionBadge(entry, userName, action) {
        let badge = entry.querySelector('.collab-attribution-badge');
        if (!badge) {
            badge = document.createElement('div');
            badge.className = 'collab-attribution-badge';
            entry.appendChild(badge);
        }
        
        const time = new Date().toLocaleTimeString();
        badge.innerHTML = `<i class="fas fa-user"></i> ${action} by ${userName} at ${time}`;
    }
    
    /**
     * Update attribution badge
     */
    updateAttributionBadge(entry, userName, field) {
        let badge = entry.querySelector('.collab-attribution-badge');
        if (!badge) {
            badge = document.createElement('div');
            badge.className = 'collab-attribution-badge';
            entry.appendChild(badge);
        }
        
        const time = new Date().toLocaleTimeString();
        const fieldLabel = field ? ` (${field})` : '';
        badge.innerHTML = `<i class="fas fa-edit"></i> Updated${fieldLabel} by ${userName} at ${time}`;
    }
    
    /**
     * Update active users UI
     */
    updateActiveUsersUI() {
        const container = document.getElementById('collab-users-container');
        if (!container) return;
        
        container.innerHTML = '';
        
        this.activeUsers.forEach((user, index) => {
            const color = this.userColors[index % this.userColors.length];
            // Use user_name from API, fallback to username for compatibility
            const displayName = user.user_name || user.username || 'Unknown';
            const initials = this.getInitials(displayName);
            const isCurrentUser = user.user_id === this.userId;
            
            const badge = document.createElement('div');
            badge.className = `collab-user-badge ${isCurrentUser ? 'current-user' : ''}`;
            badge.style.backgroundColor = color;
            badge.style.zIndex = 10 - index;
            badge.innerHTML = `
                <span>${initials}</span>
                <div class="collab-user-tooltip">
                    ${displayName}${isCurrentUser ? ' (You)' : ''}
                    ${user.current_section ? `<br><small>Editing: ${user.current_section}</small>` : ''}
                </div>
            `;
            
            container.appendChild(badge);
        });
        
        // Update count display
        const countEl = document.getElementById('collab-user-count');
        if (countEl) {
            countEl.textContent = `${this.activeUsers.length} active`;
        }
    }
    
    /**
     * Update connection status UI
     */
    updateConnectionStatusUI(connected) {
        const dot = document.getElementById('collab-status-dot');
        const text = document.getElementById('collab-status-text');
        
        if (dot) {
            dot.className = `collab-status-dot ${connected ? '' : 'disconnected'}`;
        }
        if (text) {
            text.textContent = connected ? 'Connected' : 'Reconnecting...';
        }
    }
    
    /**
     * Update lock indicators UI
     */
    updateLockIndicatorsUI() {
        // Clear old locks
        document.querySelectorAll('.collab-locked').forEach(el => {
            el.classList.remove('collab-locked');
            const badge = el.querySelector('.collab-lock-badge');
            if (badge) badge.remove();
        });
        
        // Apply current locks
        Object.values(this.locks).forEach(lock => {
            if (lock.user_id !== this.userId) {
                this.showLockIndicator(lock.section_type, lock.item_id, lock.user_name);
            }
        });
    }
    
    /**
     * Show notification toast
     */
    showNotification(message, type = 'info') {
        const container = document.getElementById('collab-toast-container');
        if (!container) return;
        
        const icons = {
            info: 'fa-info-circle',
            success: 'fa-check-circle',
            warning: 'fa-exclamation-triangle',
            error: 'fa-times-circle'
        };
        
        const toast = document.createElement('div');
        toast.className = `collab-toast ${type}`;
        toast.innerHTML = `
            <i class="fas ${icons[type]} collab-toast-icon"></i>
            <span class="collab-toast-message">${message}</span>
            <button class="collab-toast-close" onclick="this.parentElement.remove()">
                <i class="fas fa-times"></i>
            </button>
        `;
        
        container.appendChild(toast);
        
        setTimeout(() => {
            if (toast.parentElement) {
                toast.style.animation = 'slideOut 0.3s ease forwards';
                setTimeout(() => toast.remove(), 300);
            }
        }, 4000);
    }
    
    /**
     * Get user initials
     */
    getInitials(name) {
        if (!name) return '?';
        const parts = name.split(/[\s._-]+/);
        if (parts.length >= 2) {
            return (parts[0][0] + parts[1][0]).toUpperCase();
        }
        return name.substring(0, 2).toUpperCase();
    }
    
    /**
     * Get section label for notifications
     */
    getSectionLabel(sectionType) {
        const labels = {
            'incident_open': 'open incident',
            'incident_closed': 'closed incident',
            'incident_priority': 'priority incident',
            'incident_handover': 'handover incident',
            'keypoint': 'key point',
            'change': 'change',
            'kbupdate': 'KB update'
        };
        return labels[sectionType] || sectionType;
    }
    
    /**
     * Process locks from server format to map
     */
    _processLocks(locksArray) {
        const locksMap = {};
        (locksArray || []).forEach(lock => {
            locksMap[`${lock.section_type}:${lock.item_id}`] = lock;
        });
        return locksMap;
    }
    
    /**
     * Set the current editing context (section and item being edited)
     * Called when user focuses on a field
     */
    setEditingContext(sectionType, itemId) {
        this.currentSection = sectionType;
        this.currentItemId = itemId;
        
        // Update session on server with current context
        if (this.sessionToken) {
            fetch(`/api/collaboration/session/context/${this.shiftId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_token: this.sessionToken,
                    current_section: sectionType,
                    current_item_id: itemId
                })
            }).catch(err => console.log('Context update failed:', err));
        }
    }
    
    /**
     * Clear the current editing context
     * Called when user blurs from a field
     */
    clearEditingContext() {
        this.currentSection = null;
        this.currentItemId = null;
    }
}

// Export for use
window.CollaborativeHandoverV2 = CollaborativeHandoverV2;
