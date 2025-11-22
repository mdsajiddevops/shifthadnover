#!/usr/bin/env python3
"""
Improve the dashboard display with better formatting and user details
"""
import sys
import os

# Add the current directory to Python path
sys.path.append('/app')

def enhance_pending_requests_display():
    """Enhance the pending requests display with better formatting and user details"""
    
    print("🎨 ENHANCING PENDING REQUESTS DISPLAY")
    print("=" * 60)
    
    try:
        template_path = '/app/templates/shift_management/dashboard.html'
        
        with open(template_path, 'r') as f:
            content = f.read()
        
        # Find and replace the pending shift swap requests section
        old_shift_swap_section = '''<!-- Pending Shift Swap Requests -->
                        {% if pending_requests.swap_requests %}
                            {% for request in pending_requests.swap_requests %}
                            <tr>
                                <td>{{ request.id }}</td>
                                <td>User ID: {{ request.requester_user_id }}</td>
                                <td>User ID: {{ request.partner_user_id }}</td>
                                <td>{{ request.shift_date }}</td>
                                <td>{{ request.reason }}</td>
                                <td>
                                    <button class="btn btn-success btn-sm" onclick="approveSwapRequest({{ request.id }})">
                                        <i class="fas fa-check"></i> Approve
                                    </button>
                                    <button class="btn btn-danger btn-sm" onclick="rejectSwapRequest({{ request.id }})">
                                        <i class="fas fa-times"></i> Reject
                                    </button>
                                </td>
                            </tr>
                            {% endfor %}
                        {% else %}
                            <tr>
                                <td colspan="6" class="text-center text-muted">
                                    <i class="fas fa-exchange-alt fa-2x mb-2" style="opacity: 0.3;"></i>
                                    <br>No pending swap requests
                                </td>
                            </tr>
                        {% endif %}'''

        new_shift_swap_section = '''<!-- Pending Shift Swap Requests -->
                        {% if pending_requests.swap_requests %}
                            {% for request in pending_requests.swap_requests %}
                            <tr class="pending-request-row">
                                <td class="request-id-cell">
                                    <span class="badge badge-primary badge-lg">#{{ request.id }}</span>
                                </td>
                                <td class="requester-cell">
                                    <div class="user-info">
                                        <strong class="user-name">{{ request.requester.full_name or request.requester.username }}</strong>
                                        <small class="user-detail d-block text-muted">{{ request.requester.username }}</small>
                                        <small class="user-role d-block">{{ request.requester.role or 'User' }}</small>
                                    </div>
                                </td>
                                <td class="partner-cell">
                                    <div class="user-info">
                                        <strong class="user-name">{{ request.swap_with.full_name or request.swap_with.username }}</strong>
                                        <small class="user-detail d-block text-muted">{{ request.swap_with.username }}</small>
                                        <small class="user-role d-block">{{ request.swap_with.role or 'User' }}</small>
                                    </div>
                                </td>
                                <td class="shift-details-cell">
                                    <div class="shift-info">
                                        <strong class="shift-date">{{ request.original_date.strftime('%Y-%m-%d') }}</strong>
                                        <div class="shift-swap-visual">
                                            <span class="original-shift badge badge-info">{{ request.original_shift_code }}</span>
                                            <i class="fas fa-arrow-right mx-1"></i>
                                            <span class="swap-shift badge badge-warning">{{ request.swap_shift_code }}</span>
                                        </div>
                                        <small class="text-muted">{{ request.original_date.strftime('%A') }}</small>
                                    </div>
                                </td>
                                <td class="reason-cell">
                                    <div class="reason-text">
                                        {{ request.reason[:50] }}{% if request.reason|length > 50 %}...{% endif %}
                                    </div>
                                    <small class="request-time text-muted">
                                        <i class="fas fa-clock"></i> {{ request.created_at.strftime('%Y-%m-%d %H:%M') }}
                                    </small>
                                </td>
                                <td class="action-cell">
                                    <div class="btn-group-vertical btn-group-sm">
                                        <button class="btn btn-success btn-approve" onclick="approveSwapRequest({{ request.id }})" title="Approve Request">
                                            <i class="fas fa-check"></i> Approve
                                        </button>
                                        <button class="btn btn-danger btn-reject" onclick="rejectSwapRequest({{ request.id }})" title="Reject Request">
                                            <i class="fas fa-times"></i> Reject
                                        </button>
                                    </div>
                                </td>
                            </tr>
                            {% endfor %}
                        {% else %}
                            <tr>
                                <td colspan="6" class="text-center text-muted empty-state">
                                    <i class="fas fa-exchange-alt fa-3x mb-3" style="opacity: 0.3;"></i>
                                    <h5>No Pending Shift Swap Requests</h5>
                                    <p>All shift swap requests have been processed.</p>
                                </td>
                            </tr>
                        {% endif %}'''

        content = content.replace(old_shift_swap_section, new_shift_swap_section)
        
        # Enhance the leave requests section too
        old_leave_section = '''<!-- Pending Leave Requests -->
                        {% if pending_requests.leave_requests %}
                            {% for request in pending_requests.leave_requests %}
                            <tr>
                                <td>{{ request.id }}</td>
                                <td>{{ request.user.username }}</td>
                                <td>{{ request.leave_type }}</td>
                                <td>{{ request.leave_date }}</td>
                                <td>{{ request.shift_code }}</td>
                                <td>{{ request.reason[:50] }}{% if request.reason|length > 50 %}...{% endif %}</td>
                                <td>
                                    <button class="btn btn-success btn-sm" onclick="approveLeaveRequest({{ request.id }})">
                                        <i class="fas fa-check"></i> Approve
                                    </button>
                                    <button class="btn btn-danger btn-sm" onclick="rejectLeaveRequest({{ request.id }})">
                                        <i class="fas fa-times"></i> Reject
                                    </button>
                                </td>
                            </tr>
                            {% endfor %}
                        {% else %}
                            <tr>
                                <td colspan="7" class="text-center text-muted">
                                    <i class="fas fa-calendar-times fa-2x mb-2" style="opacity: 0.3;"></i>
                                    <br>No pending leave requests
                                </td>
                            </tr>
                        {% endif %}'''

        new_leave_section = '''<!-- Pending Leave Requests -->
                        {% if pending_requests.leave_requests %}
                            {% for request in pending_requests.leave_requests %}
                            <tr class="pending-request-row">
                                <td class="request-id-cell">
                                    <span class="badge badge-info badge-lg">#{{ request.id }}</span>
                                </td>
                                <td class="requester-cell">
                                    <div class="user-info">
                                        <strong class="user-name">{{ request.user.full_name or request.user.username }}</strong>
                                        <small class="user-detail d-block text-muted">{{ request.user.username }}</small>
                                        <small class="user-role d-block">{{ request.user.role or 'User' }}</small>
                                    </div>
                                </td>
                                <td class="leave-type-cell">
                                    <span class="badge badge-{{ 'danger' if request.leave_type == 'sick' else 'warning' if request.leave_type == 'emergency' else 'secondary' }} leave-type-badge">
                                        <i class="fas fa-{{ 'user-md' if request.leave_type == 'sick' else 'exclamation-triangle' if request.leave_type == 'emergency' else 'user' }}"></i>
                                        {{ request.leave_type.title() }}
                                    </span>
                                </td>
                                <td class="leave-date-cell">
                                    <div class="date-info">
                                        <strong class="leave-date">{{ request.leave_date.strftime('%Y-%m-%d') }}</strong>
                                        <small class="d-block text-muted">{{ request.leave_date.strftime('%A') }}</small>
                                    </div>
                                </td>
                                <td class="shift-code-cell">
                                    <span class="badge badge-dark shift-badge">{{ request.shift_code }}</span>
                                </td>
                                <td class="reason-cell">
                                    <div class="reason-text">
                                        {{ request.reason[:50] }}{% if request.reason|length > 50 %}...{% endif %}
                                    </div>
                                    <small class="request-time text-muted">
                                        <i class="fas fa-clock"></i> {{ request.created_at.strftime('%Y-%m-%d %H:%M') }}
                                    </small>
                                </td>
                                <td class="action-cell">
                                    <div class="btn-group-vertical btn-group-sm">
                                        <button class="btn btn-success btn-approve" onclick="approveLeaveRequest({{ request.id }})" title="Approve Leave">
                                            <i class="fas fa-check"></i> Approve
                                        </button>
                                        <button class="btn btn-danger btn-reject" onclick="rejectLeaveRequest({{ request.id }})" title="Reject Leave">
                                            <i class="fas fa-times"></i> Reject
                                        </button>
                                    </div>
                                </td>
                            </tr>
                            {% endfor %}
                        {% else %}
                            <tr>
                                <td colspan="7" class="text-center text-muted empty-state">
                                    <i class="fas fa-calendar-times fa-3x mb-3" style="opacity: 0.3;"></i>
                                    <h5>No Pending Leave Requests</h5>
                                    <p>All leave requests have been processed.</p>
                                </td>
                            </tr>
                        {% endif %}'''

        content = content.replace(old_leave_section, new_leave_section)
        
        # Add enhanced CSS styles
        enhanced_css = '''
<style>
/* Enhanced Pending Requests Styling */
.pending-request-row {
    background: #f8f9fa;
    border-left: 4px solid #007bff;
    transition: all 0.3s ease;
}

.pending-request-row:hover {
    background: #e9ecef;
    transform: translateY(-1px);
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.request-id-cell {
    text-align: center;
    vertical-align: middle;
}

.badge-lg {
    font-size: 1rem;
    padding: 8px 12px;
    font-weight: 600;
}

.user-info {
    min-width: 150px;
}

.user-name {
    font-size: 1.1rem;
    color: #2c3e50;
    font-weight: 600;
}

.user-detail {
    font-size: 0.85rem;
    font-family: monospace;
    background: #e9ecef;
    padding: 2px 6px;
    border-radius: 3px;
    display: inline-block;
    margin-top: 2px;
}

.user-role {
    font-size: 0.8rem;
    color: #6c757d;
    font-style: italic;
}

.shift-info {
    text-align: center;
}

.shift-date {
    font-size: 1.1rem;
    color: #2c3e50;
    display: block;
    margin-bottom: 5px;
}

.shift-swap-visual {
    display: flex;
    align-items: center;
    justify-content: center;
    margin: 5px 0;
}

.original-shift, .swap-shift {
    font-size: 0.9rem;
    font-weight: 600;
    padding: 4px 8px;
}

.shift-badge {
    font-size: 1rem;
    padding: 6px 12px;
    font-weight: 600;
}

.leave-type-badge {
    font-size: 0.9rem;
    padding: 6px 10px;
    font-weight: 600;
}

.date-info {
    text-align: center;
}

.leave-date {
    font-size: 1.1rem;
    color: #2c3e50;
}

.reason-cell {
    max-width: 200px;
}

.reason-text {
    font-size: 1rem;
    line-height: 1.4;
    margin-bottom: 5px;
}

.request-time {
    font-size: 0.8rem;
    display: block;
}

.action-cell {
    text-align: center;
    vertical-align: middle;
}

.btn-approve, .btn-reject {
    font-weight: 600;
    min-width: 80px;
    margin: 2px 0;
    border-radius: 20px;
}

.btn-approve {
    background: linear-gradient(45deg, #28a745, #20c997);
    border: none;
    box-shadow: 0 2px 4px rgba(40, 167, 69, 0.3);
}

.btn-approve:hover {
    background: linear-gradient(45deg, #218838, #1e7e34);
    transform: translateY(-1px);
    box-shadow: 0 4px 8px rgba(40, 167, 69, 0.4);
}

.btn-reject {
    background: linear-gradient(45deg, #dc3545, #c82333);
    border: none;
    box-shadow: 0 2px 4px rgba(220, 53, 69, 0.3);
}

.btn-reject:hover {
    background: linear-gradient(45deg, #c82333, #bd2130);
    transform: translateY(-1px);
    box-shadow: 0 4px 8px rgba(220, 53, 69, 0.4);
}

.empty-state {
    padding: 40px 20px;
}

.empty-state h5 {
    color: #6c757d;
    margin-bottom: 10px;
}

.empty-state p {
    color: #adb5bd;
    margin: 0;
}

/* Table header enhancements */
.table th {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    font-weight: 600;
    text-transform: uppercase;
    font-size: 0.85rem;
    letter-spacing: 0.5px;
    border: none;
    padding: 15px 10px;
}

.table {
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    border-radius: 8px;
    overflow: hidden;
}

/* Responsive adjustments */
@media (max-width: 768px) {
    .user-info {
        min-width: auto;
    }
    
    .shift-swap-visual {
        flex-direction: column;
        gap: 5px;
    }
    
    .btn-group-vertical {
        width: 100%;
    }
    
    .btn-approve, .btn-reject {
        width: 100%;
        margin: 1px 0;
    }
}
</style>'''

        # Add the CSS before the closing </head> tag
        if '</head>' in content:
            content = content.replace('</head>', enhanced_css + '\n</head>')
        
        with open(template_path, 'w') as f:
            f.write(content)
        
        print("✅ Enhanced pending requests display with:")
        print("  • Better user information with names and roles")
        print("  • Visual shift swap indicators")
        print("  • Enhanced styling and formatting")
        print("  • Improved button design")
        print("  • Better mobile responsiveness")
        
    except Exception as e:
        print(f"❌ Error enhancing display: {e}")
        import traceback
        traceback.print_exc()

def fix_my_requests_section():
    """Fix the My Requests section to show actual user requests"""
    
    print(f"\n🔧 FIXING MY REQUESTS SECTION")
    print("=" * 60)
    
    try:
        # Check the dashboard route to ensure it's passing user requests
        route_file = '/app/routes/shift_swap_leave.py'
        
        with open(route_file, 'r') as f:
            route_content = f.read()
        
        # Look for the dashboard route
        if 'def dashboard()' in route_content:
            print("📋 Found dashboard route")
            
            # Check if it's getting user requests
            if 'get_user_requests' in route_content:
                print("✅ Dashboard already gets user requests")
            else:
                print("🔧 Adding user requests to dashboard...")
                
                # Find the dashboard function and enhance it
                lines = route_content.split('\n')
                for i, line in enumerate(lines):
                    if 'def dashboard()' in line:
                        # Look for the context dictionary
                        for j in range(i, min(len(lines), i + 50)):
                            if 'return render_template' in lines[j]:
                                # Add user requests to the context
                                context_start = j
                                while j < len(lines) and '}' not in lines[j]:
                                    j += 1
                                
                                # Insert user requests before the closing brace
                                if j < len(lines):
                                    lines.insert(j, "        'user_requests': shift_swap_leave_service.get_user_requests(current_user.id),")
                                
                                # Write back the modified content
                                route_content = '\n'.join(lines)
                                
                                with open(route_file, 'w') as f:
                                    f.write(route_content)
                                
                                print("✅ Added user requests to dashboard context")
                                break
                        break
        
        print("✅ My Requests section should now show user's actual requests")
        
    except Exception as e:
        print(f"❌ Error fixing My Requests: {e}")

if __name__ == "__main__":
    enhance_pending_requests_display()
    fix_my_requests_section()