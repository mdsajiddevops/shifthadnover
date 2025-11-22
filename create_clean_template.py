#!/usr/bin/env python3

# Create a completely clean dashboard template
import os

def create_clean_template():
    """Create a clean, working dashboard template"""
    
    template_file = '/app/templates/shift_management/dashboard.html'
    
    clean_template = '''{% extends "base.html" %}

{% block title %}Shift Management Dashboard{% endblock %}

{% block content %}
<style>
/* Essential Modern Styling */
body {
    background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%) !important;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif !important;
    color: #2c3e50 !important;
}

.dashboard-header {
    background: linear-gradient(135deg, #4a90e2 0%, #357abd 100%) !important;
    color: white !important;
    padding: 2rem;
    margin: 20px;
    text-align: center;
    border-radius: 15px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
}

.modern-card {
    background: white !important;
    border-radius: 20px !important;
    padding: 2rem !important;
    margin: 20px !important;
    box-shadow: 0 8px 25px rgba(0, 0, 0, 0.12) !important;
    border: 1px solid #e9ecef !important;
    position: relative;
    overflow: hidden;
}

.modern-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 4px;
    background: linear-gradient(135deg, #4a90e2 0%, #357abd 100%);
}

.modern-card:hover {
    transform: translateY(-5px);
    box-shadow: 0 15px 40px rgba(0, 0, 0, 0.2);
}

.card-title {
    font-size: 1.5rem;
    font-weight: 700;
    color: #2c3e50;
    margin-bottom: 1rem;
    display: flex;
    align-items: center;
    gap: 10px;
}

.btn-modern {
    background: linear-gradient(135deg, #4a90e2 0%, #357abd 100%) !important;
    color: white !important;
    padding: 12px 25px;
    border: none;
    border-radius: 25px;
    text-decoration: none;
    display: inline-flex;
    align-items: center;
    gap: 8px;
    margin: 5px;
    box-shadow: 0 4px 15px rgba(74, 144, 226, 0.3);
    transition: all 0.3s ease;
}

.btn-modern:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(74, 144, 226, 0.4);
    color: white !important;
    text-decoration: none;
}

.stat-box {
    background: rgba(74, 144, 226, 0.1);
    padding: 15px;
    border-radius: 10px;
    margin: 10px 0;
    border: 1px solid rgba(74, 144, 226, 0.2);
    font-weight: 600;
}

/* Request Item Styling */
.request-item {
    background: #f8f9fa;
    border-left: 4px solid #007bff;
    padding: 15px;
    margin: 10px 0;
    border-radius: 10px;
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
    font-weight: bold;
}

.request-reason {
    background: #fff;
    padding: 8px;
    border-radius: 4px;
    border-left: 3px solid #17a2b8;
    margin: 5px 0;
}
</style>

<div class="dashboard-header">
    <h1 style="margin: 0; font-size: 2.5rem;">
        <i class="fas fa-calendar-alt"></i>
        Shift Management Dashboard
    </h1>
    <p style="margin: 10px 0 0 0; font-size: 1.1rem; opacity: 0.9;">
        Manage your shift swaps and leave requests with ease
    </p>
</div>

<div class="container-fluid">
    <div class="row">
        <div class="col-md-6">
            <div class="modern-card">
                <h3 class="card-title">
                    <i class="fas fa-bolt" style="color: #4a90e2;"></i>
                    Quick Actions
                </h3>
                <div>
                    <a href="{{ url_for('shift_swap_leave.simple_swap_request') }}" class="btn-modern">
                        <i class="fas fa-exchange-alt"></i>
                        Request Shift Swap
                    </a>
                    <a href="{{ url_for('shift_swap_leave.request_leave') }}" class="btn-modern" style="background: linear-gradient(135deg, #6c757d 0%, #5a6268 100%) !important;">
                        <i class="fas fa-calendar-times"></i>
                        Request Leave
                    </a>
                </div>
            </div>
        </div>

        <div class="col-md-6">
            <div class="modern-card">
                <h3 class="card-title">
                    <i class="fas fa-info-circle" style="color: #4a90e2;"></i>
                    Quick Status
                </h3>
                <div class="stat-box">
                    <i class="fas fa-exchange-alt" style="color: #4a90e2;"></i>
                    My Swaps: {{ user_requests.swap_requests|length if user_requests.success and user_requests.swap_requests else 0 }}
                </div>
                <div class="stat-box">
                    <i class="fas fa-calendar-times" style="color: #6c757d;"></i>
                    My Leaves: {{ user_requests.leave_requests|length if user_requests.success and user_requests.leave_requests else 0 }}
                </div>
            </div>
        </div>
    </div>

    <div class="row">
        <div class="col-12">
            <div class="modern-card">
                <h3 class="card-title">
                    <i class="fas fa-user" style="color: #4a90e2;"></i>
                    My Requests
                </h3>

                <h4 style="color: #2c3e50; margin-top: 20px;">
                    <i class="fas fa-exchange-alt" style="color: #4a90e2;"></i>
                    Shift Swap Requests
                </h4>
                
                {% if user_requests and user_requests.success and user_requests.swap_requests and user_requests.swap_requests|length > 0 %}
                    {% for request in user_requests.swap_requests %}
                    <div class="request-item">
                        <div class="request-title">
                            Swap with {{ request.swap_with.username }}
                            <span class="badge badge-{{ 'success' if request.status == 'approved' else 'danger' if request.status == 'rejected' else 'warning' }} ml-2">
                                {{ request.status|title }}
                            </span>
                        </div>
                        <div class="mt-2">
                            <strong>Your shift:</strong> {{ request.original_date }} ({{ request.original_shift_code }})
                            <i class="fas fa-exchange-alt mx-2" style="color: #007bff;"></i>
                            <strong>Partner's shift:</strong> {{ request.swap_date }} ({{ request.swap_shift_code }})
                        </div>
                        {% if request.reason %}
                        <div class="request-reason mt-2">
                            <strong>Reason:</strong> {{ request.reason }}
                        </div>
                        {% endif %}
                        <small class="text-muted">
                            Requested: {{ request.created_at[:19] }}
                        </small>
                    </div>
                    {% endfor %}
                {% else %}
                    <div style="text-align: center; padding: 20px; color: #6c757d; background: rgba(108, 117, 125, 0.05); border-radius: 10px; border: 1px dashed #dee2e6;">
                        <i class="fas fa-exchange-alt" style="font-size: 2rem; color: #28a745; margin-bottom: 10px;"></i>
                        <p><strong>No Shift Swap Requests</strong></p>
                        <p>You haven't submitted any shift swap requests yet.</p>
                    </div>
                {% endif %}

                <h4 style="color: #2c3e50; margin-top: 30px;">
                    <i class="fas fa-calendar-times" style="color: #4a90e2;"></i>
                    Leave Requests
                </h4>
                
                {% if user_requests and user_requests.success and user_requests.leave_requests and user_requests.leave_requests|length > 0 %}
                    {% for request in user_requests.leave_requests %}
                    <div class="request-item" style="border-left: 4px solid #dc3545;">
                        <div class="request-title">
                            {{ request.leave_type|title or 'Leave' }} Request
                            <span class="badge badge-{{ 'success' if request.status == 'approved' else 'danger' if request.status == 'rejected' else 'warning' }} ml-2">
                                {{ request.status|title }}
                            </span>
                        </div>
                        <div class="mt-2">
                            <strong>Date:</strong> {{ request.leave_date }}
                            {% if request.shift_code %}
                            | <strong>Shift:</strong> {{ request.shift_code }}
                            {% endif %}
                        </div>
                        {% if request.reason %}
                        <div class="request-reason mt-2">
                            <strong>Reason:</strong> {{ request.reason }}
                        </div>
                        {% endif %}
                        <small class="text-muted">
                            Requested: {{ request.created_at[:19] }}
                            {% if request.approved_by %}
                            | Approved by: {{ request.approved_by }}
                            {% endif %}
                        </small>
                    </div>
                    {% endfor %}
                {% else %}
                    <div style="text-align: center; padding: 20px; color: #6c757d; background: rgba(108, 117, 125, 0.05); border-radius: 10px; border: 1px dashed #dee2e6;">
                        <i class="fas fa-calendar-times" style="font-size: 2rem; color: #28a745; margin-bottom: 10px;"></i>
                        <p><strong>No Leave Requests</strong></p>
                        <p>You haven't submitted any leave requests yet.</p>
                    </div>
                {% endif %}
            </div>
        </div>
    </div>

    {% if current_user.role in ['super_admin', 'account_admin', 'team_admin'] %}
    <div class="row">
        <div class="col-12">
            <div class="modern-card">
                <h3 class="card-title">
                    <i class="fas fa-clock" style="color: #4a90e2;"></i>
                    Pending Approvals
                </h3>

                <h4 style="color: #2c3e50; margin-top: 20px;">
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
                                <small>Requested: {{ request.created_at if request.created_at else 'Unknown' }}</small>
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
                {% endif %}

                <h4 style="color: #2c3e50; margin-top: 30px;">
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
                                <small>Requested: {{ request.created_at if request.created_at else 'Unknown' }}</small>
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
                {% endif %}
            </div>
        </div>
    </div>
    {% endif %}
</div>

<script>
// Clean Approval Functions
function approveSwapRequest(requestId) {
    console.log('Approving swap request:', requestId);
    const comments = prompt('Enter approval comments (optional):') || '';
    
    fetch(`/shift-management/admin/approve-swap/${requestId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        },
        credentials: 'same-origin',
        body: JSON.stringify({
            action: 'approve',
            comments: comments
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('✅ Swap request approved successfully!');
            location.reload();
        } else {
            alert(`❌ Error: ${data.message || 'Failed to approve request'}`);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('❌ Network error occurred. Please try again.');
    });
}

function rejectSwapRequest(requestId) {
    console.log('Rejecting swap request:', requestId);
    const comments = prompt('Enter rejection reason:') || '';
    if (!comments.trim()) {
        alert('Please provide a reason for rejection.');
        return;
    }

    fetch(`/shift-management/admin/approve-swap/${requestId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        },
        credentials: 'same-origin',
        body: JSON.stringify({
            action: 'reject',
            comments: comments
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('✅ Swap request rejected successfully!');
            location.reload();
        } else {
            alert(`❌ Error: ${data.message || 'Failed to reject request'}`);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('❌ Network error occurred. Please try again.');
    });
}

function approveLeaveRequest(requestId) {
    console.log('Approving leave request:', requestId);
    const comments = prompt('Enter approval comments (optional):') || '';
    
    fetch(`/shift-management/admin/approve-leave/${requestId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        },
        credentials: 'same-origin',
        body: JSON.stringify({
            action: 'approve',
            comments: comments
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('✅ Leave request approved successfully!');
            location.reload();
        } else {
            alert(`❌ Error: ${data.message || 'Failed to approve request'}`);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('❌ Network error occurred. Please try again.');
    });
}

function rejectLeaveRequest(requestId) {
    console.log('Rejecting leave request:', requestId);
    const comments = prompt('Enter rejection reason:') || '';
    if (!comments.trim()) {
        alert('Please provide a reason for rejection.');
        return;
    }

    fetch(`/shift-management/admin/approve-leave/${requestId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        },
        credentials: 'same-origin',
        body: JSON.stringify({
            action: 'reject',
            comments: comments
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('✅ Leave request rejected successfully!');
            location.reload();
        } else {
            alert(`❌ Error: ${data.message || 'Failed to reject request'}`);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('❌ Network error occurred. Please try again.');
    });
}
</script>
{% endblock %}'''

    # Write the clean template
    with open(template_file, 'w') as f:
        f.write(clean_template)
    
    print("✅ Successfully created clean dashboard template")
    return True

if __name__ == "__main__":
    print("=== Creating Clean Dashboard Template ===")
    success = create_clean_template()
    
    if success:
        print("\n✅ Clean template created!")
        print("📋 Features included:")
        print("  - Proper Jinja2 block structure")
        print("  - Fixed field names for serialized objects")
        print("  - Working My Requests section")
        print("  - Admin approval functionality")
        print("  - Clean JavaScript functions")
        print("  - Modern responsive styling")
        print("\n🔗 Dashboard should now load perfectly!")
    else:
        print("\n❌ Failed to create clean template")