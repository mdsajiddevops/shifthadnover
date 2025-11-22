#!/usr/bin/env python3
"""
Fix the shift management dashboard template to display pending requests
"""
import sys
import os

# Add the current directory to Python path
sys.path.append('/app')

def fix_dashboard_template():
    """Fix the dashboard template to show actual pending requests"""
    
    # Read the current template
    template_path = '/app/templates/shift_management/dashboard.html'
    
    try:
        with open(template_path, 'r') as f:
            content = f.read()
        
        print("🔧 FIXING SHIFT MANAGEMENT DASHBOARD TEMPLATE")
        print("=" * 60)
        
        # Find the hardcoded "No pending requests" sections and replace them
        
        # Replace the hardcoded swap requests section
        old_swap_section = '''<h4 style="color: #2c3e50; margin-top: 20px;">
                    <i class="fas fa-exchange-alt" style="color: #4a90e2;"></i>
                    Pending Shift Swap Requests
                </h4>
                <div style="text-align: center; padding: 20px; color: #6c757d; background: rgba(108, 117, 125, 0.05); border-radius: 10px; border: 1px dashed #dee2e6;">
                    <i class="fas fa-exchange-alt" style="font-size: 2rem; color: #28a745;"></i>
                    <p>No pending swap requests</p>
                </div>'''

        new_swap_section = '''<h4 style="color: #2c3e50; margin-top: 20px;">
                    <i class="fas fa-exchange-alt" style="color: #4a90e2;"></i>
                    Pending Shift Swap Requests
                </h4>
                
                {% if pending_requests.success and pending_requests.swap_requests %}
                    {% for request in pending_requests.swap_requests %}
                    <div style="padding: 15px; margin: 10px 0; background: rgba(255, 193, 7, 0.1); border-radius: 10px; border: 1px solid rgba(255, 193, 7, 0.3);">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <strong>{{ request.requester_username }}</strong> ↔ <strong>{{ request.swap_with_username }}</strong>
                                <br>
                                <small style="color: #6c757d;">
                                    {{ request.original_date }} ({{ request.original_shift_code }}) ↔ {{ request.swap_date }} ({{ request.swap_shift_code }})
                                </small>
                                <br>
                                <em>"{{ request.reason }}"</em>
                                <br>
                                <small>Requested: {{ request.created_at.strftime('%Y-%m-%d %H:%M') }}</small>
                            </div>
                            <div>
                                <button onclick="approveSwapRequest({{ request.id }})" class="btn btn-success btn-sm" style="margin: 2px;">
                                    <i class="fas fa-check"></i> Approve
                                </button>
                                <button onclick="rejectSwapRequest({{ request.id }})" class="btn btn-danger btn-sm" style="margin: 2px;">
                                    <i class="fas fa-times"></i> Reject
                                </button>
                            </div>
                        </div>
                    </div>
                    {% endfor %}
                {% else %}
                    <div style="text-align: center; padding: 20px; color: #6c757d; background: rgba(108, 117, 125, 0.05); border-radius: 10px; border: 1px dashed #dee2e6;">
                        <i class="fas fa-exchange-alt" style="font-size: 2rem; color: #28a745;"></i>
                        <p>No pending swap requests</p>
                    </div>
                {% endif %}'''

        # Replace the hardcoded leave requests section
        old_leave_section = '''<h4 style="color: #2c3e50; margin-top: 30px;">
                    <i class="fas fa-calendar-times" style="color: #4a90e2;"></i>
                    Pending Leave Requests
                </h4>
                <div style="text-align: center; padding: 20px; color: #6c757d; background: rgba(108, 117, 125, 0.05); border-radius: 10px; border: 1px dashed #dee2e6;">
                    <i class="fas fa-calendar-times" style="font-size: 2rem; color: #28a745;"></i>
                    <p>No pending leave requests</p>
                </div>'''

        new_leave_section = '''<h4 style="color: #2c3e50; margin-top: 30px;">
                    <i class="fas fa-calendar-times" style="color: #4a90e2;"></i>
                    Pending Leave Requests
                </h4>
                
                {% if pending_requests.success and pending_requests.leave_requests %}
                    {% for request in pending_requests.leave_requests %}
                    <div style="padding: 15px; margin: 10px 0; background: rgba(220, 53, 69, 0.1); border-radius: 10px; border: 1px solid rgba(220, 53, 69, 0.3);">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <strong>{{ request.requester_username }}</strong> - {{ request.leave_type|title }} Leave
                                <br>
                                <small style="color: #6c757d;">
                                    Date: {{ request.leave_date }} ({{ request.shift_code }})
                                </small>
                                <br>
                                <em>"{{ request.reason or 'No reason provided' }}"</em>
                                <br>
                                <small>Requested: {{ request.created_at.strftime('%Y-%m-%d %H:%M') }}</small>
                            </div>
                            <div>
                                <button onclick="approveLeaveRequest({{ request.id }})" class="btn btn-success btn-sm" style="margin: 2px;">
                                    <i class="fas fa-check"></i> Approve
                                </button>
                                <button onclick="rejectLeaveRequest({{ request.id }})" class="btn btn-danger btn-sm" style="margin: 2px;">
                                    <i class="fas fa-times"></i> Reject
                                </button>
                            </div>
                        </div>
                    </div>
                    {% endfor %}
                {% else %}
                    <div style="text-align: center; padding: 20px; color: #6c757d; background: rgba(108, 117, 125, 0.05); border-radius: 10px; border: 1px dashed #dee2e6;">
                        <i class="fas fa-calendar-times" style="font-size: 2rem; color: #28a745;"></i>
                        <p>No pending leave requests</p>
                    </div>
                {% endif %}'''

        # Apply the replacements
        content = content.replace(old_swap_section, new_swap_section)
        content = content.replace(old_leave_section, new_leave_section)
        
        # Add JavaScript functions for approval/rejection at the end
        js_functions = '''
<script>
function approveSwapRequest(requestId) {
    if (confirm('Are you sure you want to approve this shift swap request?')) {
        fetch(`/shift-management/admin/approve-swap/${requestId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Swap request approved successfully!');
                location.reload();
            } else {
                alert('Error: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An error occurred while approving the request');
        });
    }
}

function rejectSwapRequest(requestId) {
    const reason = prompt('Please provide a reason for rejection:');
    if (reason !== null && reason.trim() !== '') {
        fetch(`/shift-management/admin/reject-swap/${requestId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({ reason: reason })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Swap request rejected successfully!');
                location.reload();
            } else {
                alert('Error: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An error occurred while rejecting the request');
        });
    }
}

function approveLeaveRequest(requestId) {
    if (confirm('Are you sure you want to approve this leave request?')) {
        fetch(`/shift-management/admin/approve-leave/${requestId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Leave request approved successfully!');
                location.reload();
            } else {
                alert('Error: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An error occurred while approving the request');
        });
    }
}

function rejectLeaveRequest(requestId) {
    const reason = prompt('Please provide a reason for rejection:');
    if (reason !== null && reason.trim() !== '') {
        fetch(`/shift-management/admin/reject-leave/${requestId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({ reason: reason })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Leave request rejected successfully!');
                location.reload();
            } else {
                alert('Error: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An error occurred while rejecting the request');
        });
    }
}
</script>'''
        
        # Insert JavaScript before the closing endblock
        content = content.replace('{% endblock %}', js_functions + '\n{% endblock %}')
        
        # Write the updated template
        with open(template_path, 'w') as f:
            f.write(content)
        
        print("✅ Dashboard template updated successfully!")
        print("📋 Changes made:")
        print("  • Added dynamic display of pending swap requests")
        print("  • Added dynamic display of pending leave requests")
        print("  • Added approve/reject buttons with JavaScript handlers")
        print("  • Template now uses the pending_requests data from backend")
        print()
        print("🔄 The admin users should now see the 2 pending requests!")
        
    except Exception as e:
        print(f"❌ Error fixing template: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    fix_dashboard_template()