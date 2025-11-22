#!/usr/bin/env python3
"""
Fix the user dashboard My Requests section to show actual user requests
"""
import sys
import os

# Add the current directory to Python path
sys.path.append('/app')

def fix_user_dashboard_my_requests():
    """Fix the My Requests section in user dashboard to show actual requests"""
    
    print("🔧 FIXING USER DASHBOARD MY REQUESTS SECTION")
    print("=" * 60)
    
    try:
        template_path = '/app/templates/shift_management/dashboard.html'
        
        with open(template_path, 'r') as f:
            content = f.read()
        
        # Find the My Requests section and replace it with proper data display
        old_my_requests_section = '''<div class="card-body">
                                <h6 class="text-muted mb-3">
                                    <i class="fas fa-exchange-alt"></i> Shift Swap Requests
                                </h6>
                                
                                <div class="text-center py-4">
                                    <i class="fas fa-exchange-alt fa-3x text-muted mb-3" style="opacity: 0.3;"></i>
                                    <h6 class="text-muted">No Shift Swap Requests</h6>
                                    <p class="text-muted small">You haven't submitted any shift swap requests yet.</p>
                                </div>
                            </div>'''

        new_my_requests_section = '''<div class="card-body">
                                <h6 class="text-muted mb-3">
                                    <i class="fas fa-exchange-alt"></i> Shift Swap Requests
                                </h6>
                                
                                {% if user_requests and user_requests.swap_requests %}
                                    <div class="requests-list">
                                        {% for request in user_requests.swap_requests %}
                                        <div class="request-item mb-3 p-3 border rounded">
                                            <div class="d-flex justify-content-between align-items-start">
                                                <div class="request-details flex-grow-1">
                                                    <div class="d-flex align-items-center mb-2">
                                                        <span class="badge badge-{{ 'success' if request.status == 'approved' else 'warning' if request.status == 'pending' else 'danger' }} mr-2">
                                                            {{ request.status.title() }}
                                                        </span>
                                                        <strong class="request-title">Request #{{ request.id }}</strong>
                                                    </div>
                                                    
                                                    <div class="swap-details mb-2">
                                                        <div class="d-flex align-items-center">
                                                            <span class="swap-partner mr-3">
                                                                <i class="fas fa-user"></i>
                                                                <strong>Swap with:</strong> {{ request.swap_with.full_name or request.swap_with.username }}
                                                            </span>
                                                        </div>
                                                        
                                                        <div class="shift-swap-info mt-2">
                                                            <span class="badge badge-info mr-1">{{ request.original_date.strftime('%Y-%m-%d') }}</span>
                                                            <span class="shift-change">
                                                                <span class="badge badge-secondary">{{ request.original_shift_code }}</span>
                                                                <i class="fas fa-arrow-right mx-1"></i>
                                                                <span class="badge badge-primary">{{ request.swap_shift_code }}</span>
                                                            </span>
                                                        </div>
                                                    </div>
                                                    
                                                    {% if request.reason %}
                                                    <div class="request-reason">
                                                        <small class="text-muted">
                                                            <i class="fas fa-comment"></i>
                                                            {{ request.reason[:80] }}{% if request.reason|length > 80 %}...{% endif %}
                                                        </small>
                                                    </div>
                                                    {% endif %}
                                                    
                                                    <small class="text-muted d-block mt-2">
                                                        <i class="fas fa-clock"></i>
                                                        Submitted: {{ request.created_at.strftime('%Y-%m-%d %H:%M') }}
                                                        {% if request.approved_at %}
                                                        | Processed: {{ request.approved_at.strftime('%Y-%m-%d %H:%M') }}
                                                        {% endif %}
                                                    </small>
                                                </div>
                                            </div>
                                        </div>
                                        {% endfor %}
                                    </div>
                                {% else %}
                                    <div class="text-center py-4">
                                        <i class="fas fa-exchange-alt fa-3x text-muted mb-3" style="opacity: 0.3;"></i>
                                        <h6 class="text-muted">No Shift Swap Requests</h6>
                                        <p class="text-muted small">You haven't submitted any shift swap requests yet.</p>
                                    </div>
                                {% endif %}
                            </div>'''

        content = content.replace(old_my_requests_section, new_my_requests_section)
        
        # Also fix the Leave Requests section
        old_leave_requests_section = '''<div class="card-body">
                                <h6 class="text-muted mb-3">
                                    <i class="fas fa-calendar-times"></i> Leave Requests
                                </h6>
                                
                                <div class="text-center py-4">
                                    <i class="fas fa-calendar-times fa-3x text-muted mb-3" style="opacity: 0.3;"></i>
                                    <h6 class="text-muted">No Leave Requests</h6>
                                    <p class="text-muted small">You haven't submitted any leave requests yet.</p>
                                </div>
                            </div>'''

        new_leave_requests_section = '''<div class="card-body">
                                <h6 class="text-muted mb-3">
                                    <i class="fas fa-calendar-times"></i> Leave Requests
                                </h6>
                                
                                {% if user_requests and user_requests.leave_requests %}
                                    <div class="requests-list">
                                        {% for request in user_requests.leave_requests %}
                                        <div class="request-item mb-3 p-3 border rounded">
                                            <div class="d-flex justify-content-between align-items-start">
                                                <div class="request-details flex-grow-1">
                                                    <div class="d-flex align-items-center mb-2">
                                                        <span class="badge badge-{{ 'success' if request.status == 'approved' else 'warning' if request.status == 'pending' else 'danger' }} mr-2">
                                                            {{ request.status.title() }}
                                                        </span>
                                                        <strong class="request-title">Leave Request #{{ request.id }}</strong>
                                                    </div>
                                                    
                                                    <div class="leave-details mb-2">
                                                        <div class="d-flex align-items-center flex-wrap">
                                                            <span class="badge badge-{{ 'danger' if request.leave_type == 'sick' else 'warning' if request.leave_type == 'emergency' else 'info' }} mr-2 mb-1">
                                                                <i class="fas fa-{{ 'user-md' if request.leave_type == 'sick' else 'exclamation-triangle' if request.leave_type == 'emergency' else 'user' }}"></i>
                                                                {{ request.leave_type.title() }}
                                                            </span>
                                                            <span class="badge badge-primary mr-2 mb-1">{{ request.leave_date.strftime('%Y-%m-%d') }}</span>
                                                            <span class="badge badge-dark mb-1">{{ request.shift_code }}</span>
                                                        </div>
                                                    </div>
                                                    
                                                    {% if request.reason %}
                                                    <div class="request-reason">
                                                        <small class="text-muted">
                                                            <i class="fas fa-comment"></i>
                                                            {{ request.reason[:80] }}{% if request.reason|length > 80 %}...{% endif %}
                                                        </small>
                                                    </div>
                                                    {% endif %}
                                                    
                                                    <small class="text-muted d-block mt-2">
                                                        <i class="fas fa-clock"></i>
                                                        Submitted: {{ request.created_at.strftime('%Y-%m-%d %H:%M') }}
                                                        {% if request.approved_at %}
                                                        | Processed: {{ request.approved_at.strftime('%Y-%m-%d %H:%M') }}
                                                        {% endif %}
                                                    </small>
                                                </div>
                                            </div>
                                        </div>
                                        {% endfor %}
                                    </div>
                                {% else %}
                                    <div class="text-center py-4">
                                        <i class="fas fa-calendar-times fa-3x text-muted mb-3" style="opacity: 0.3;"></i>
                                        <h6 class="text-muted">No Leave Requests</h6>
                                        <p class="text-muted small">You haven't submitted any leave requests yet.</p>
                                    </div>
                                {% endif %}
                            </div>'''

        content = content.replace(old_leave_requests_section, new_leave_requests_section)
        
        # Add CSS for the request items
        request_item_css = '''
/* My Requests Section Styling */
.request-item {
    background: #f8f9fa;
    border-left: 4px solid #007bff !important;
    transition: all 0.3s ease;
}

.request-item:hover {
    background: #e9ecef;
    transform: translateY(-1px);
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.request-title {
    color: #2c3e50;
    font-size: 1.1rem;
}

.swap-partner {
    font-size: 0.95rem;
}

.shift-swap-info {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 5px;
}

.shift-change {
    display: flex;
    align-items: center;
}

.request-reason {
    background: #fff;
    padding: 8px;
    border-radius: 4px;
    border-left: 3px solid #17a2b8;
    margin: 5px 0;
}

.leave-details {
    margin: 10px 0;
}

.requests-list {
    max-height: 400px;
    overflow-y: auto;
}

.requests-list::-webkit-scrollbar {
    width: 6px;
}

.requests-list::-webkit-scrollbar-track {
    background: #f1f1f1;
    border-radius: 3px;
}

.requests-list::-webkit-scrollbar-thumb {
    background: #c1c1c1;
    border-radius: 3px;
}

.requests-list::-webkit-scrollbar-thumb:hover {
    background: #a8a8a8;
}

@media (max-width: 768px) {
    .shift-swap-info {
        flex-direction: column;
        align-items: flex-start;
    }
    
    .shift-change {
        margin-top: 5px;
    }
}
'''

        # Add the CSS
        if '</style>' in content:
            content = content.replace('</style>', request_item_css + '\n</style>')
        
        with open(template_path, 'w') as f:
            f.write(content)
        
        print("✅ Fixed My Requests section with:")
        print("  • Actual user requests display")
        print("  • Enhanced request item styling")
        print("  • Status badges and visual indicators")
        print("  • Request details and timestamps")
        print("  • Scrollable request lists")
        
    except Exception as e:
        print(f"❌ Error fixing My Requests: {e}")
        import traceback
        traceback.print_exc()

def update_dashboard_route():
    """Ensure the dashboard route passes user requests to the template"""
    
    print(f"\n🔧 UPDATING DASHBOARD ROUTE")
    print("=" * 60)
    
    try:
        route_file = '/app/routes/shift_swap_leave.py'
        
        with open(route_file, 'r') as f:
            content = f.read()
        
        # Check if user_requests is already being passed
        if "'user_requests':" in content:
            print("✅ user_requests already being passed to template")
        else:
            # Find the dashboard function and add user_requests
            lines = content.split('\n')
            modified = False
            
            for i, line in enumerate(lines):
                if 'def dashboard()' in line:
                    # Look for the return render_template call
                    for j in range(i, min(len(lines), i + 100)):
                        if 'return render_template(' in lines[j] and 'dashboard.html' in lines[j]:
                            # Find the context dictionary
                            context_start = j
                            brace_count = 0
                            in_context = False
                            
                            for k in range(j, min(len(lines), j + 20)):
                                if '{' in lines[k]:
                                    in_context = True
                                    brace_count += lines[k].count('{') - lines[k].count('}')
                                elif in_context:
                                    brace_count += lines[k].count('{') - lines[k].count('}')
                                    
                                if in_context and brace_count == 0:
                                    # Insert user_requests before the closing brace
                                    lines.insert(k, "        'user_requests': shift_swap_leave_service.get_user_requests(current_user.id),")
                                    modified = True
                                    break
                            break
                    break
            
            if modified:
                content = '\n'.join(lines)
                with open(route_file, 'w') as f:
                    f.write(content)
                print("✅ Added user_requests to dashboard context")
            else:
                print("⚠️ Could not modify dashboard route automatically")
                
    except Exception as e:
        print(f"❌ Error updating route: {e}")

if __name__ == "__main__":
    fix_user_dashboard_my_requests()
    update_dashboard_route()