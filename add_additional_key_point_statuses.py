#!/usr/bin/env python3
"""
ADD ADDITIONAL STATUS OPTIONS TO KEY POINTS SYSTEM
================================================

This script adds more status options to provide better workflow management:
- Pending with Another Team
- On Hold  
- Under Review
- Escalated
- Waiting for Approval

Updates both the template and database handling for the new statuses.
"""

import sys
import os
sys.path.append('/app')

from datetime import datetime

def get_enhanced_status_options():
    """Define the enhanced status options with their properties"""
    return {
        'Open': {
            'color': 'secondary',
            'icon': 'bi-circle',
            'description': 'Task is ready to be worked on'
        },
        'In Progress': {
            'color': 'primary',
            'icon': 'bi-clock',
            'description': 'Currently being worked on'
        },
        'Pending with Another Team': {
            'color': 'warning',
            'icon': 'bi-people',
            'description': 'Waiting for another team to complete their part'
        },
        'On Hold': {
            'color': 'danger',
            'icon': 'bi-pause-circle',
            'description': 'Temporarily paused or blocked'
        },
        'Under Review': {
            'color': 'info',
            'icon': 'bi-eye',
            'description': 'Being reviewed or validated'
        },
        'Escalated': {
            'color': 'dark',
            'icon': 'bi-arrow-up-circle',
            'description': 'Escalated to higher level or management'
        },
        'Waiting for Approval': {
            'color': 'light text-dark',
            'icon': 'bi-check-circle-fill',
            'description': 'Completed work waiting for approval'
        },
        'Closed': {
            'color': 'success',
            'icon': 'bi-check-circle',
            'description': 'Task completed successfully'
        }
    }

def create_enhanced_keypoints_template_with_more_statuses():
    """Create enhanced template with additional status options"""
    
    status_options = get_enhanced_status_options()
    
    template_content = '''{% extends 'base.html' %}
{% block content %}
<div class="container-fluid px-0">
    <!-- Header Section -->
    <div class="mb-4">
        <div class="d-flex justify-content-between align-items-center">
            <div>
                <h1 class="h3 mb-1 text-primary">Key Points Management</h1>
                <p class="text-muted mb-0">Track, update, and manage key points with comprehensive status controls</p>
            </div>
            <div class="d-flex align-items-center gap-2">
                {% if key_points %}
                <span class="badge bg-primary fs-6 px-3 py-2">
                    <i class="bi bi-list-check me-2"></i>{{ key_points|length }} Key Points
                </span>
                {% endif %}
                {% if date_filter %}
                <span class="badge bg-info fs-6 px-3 py-2">
                    <i class="bi bi-calendar-date me-2"></i>{{ date_filter }}
                </span>
                {% endif %}
            </div>
        </div>
    </div>

    <!-- Status Legend -->
    <div class="card mb-4 border-0 shadow-sm">
        <div class="card-header bg-light border-0 py-3">
            <h6 class="mb-0 text-secondary">
                <i class="bi bi-info-circle me-2"></i>Status Legend
            </h6>
        </div>
        <div class="card-body py-2">
            <div class="row g-2">'''
    
    # Add status legend items
    for status, props in status_options.items():
        template_content += f'''
                <div class="col-md-3">
                    <span class="badge bg-{props['color']} me-2">
                        <i class="{props['icon']} me-1"></i>{status}
                    </span>
                    <small class="text-muted">{props['description']}</small>
                </div>'''
    
    template_content += '''
            </div>
        </div>
    </div>

    <!-- Filter Section -->
    <div class="card mb-4 border-0 shadow-sm">
        <div class="card-header bg-light border-0 py-3">
            <h5 class="mb-0 text-secondary">
                <i class="bi bi-funnel me-2"></i>Filter Key Points
            </h5>
        </div>
        <div class="card-body">
            <form method="get" class="row g-3 align-items-end">
                {% if current_user.role == 'super_admin' %}
                <div class="col-md-2">
                    <label for="account_id" class="form-label fw-semibold text-secondary">
                        <i class="bi bi-building me-1"></i>Account
                    </label>
                    <select name="account_id" id="account_id" class="form-select" onchange="updateTeamsDropdown(this.value)">
                        <option value="">All Accounts</option>
                        {% for account in accounts %}
                        <option value="{{ account.id }}" {% if account.id|string == selected_account_id|string %}selected{% endif %}>
                            {{ account.name }}
                        </option>
                        {% endfor %}
                    </select>
                </div>
                {% endif %}
                <div class="col-md-2">
                    <label for="team_id" class="form-label fw-semibold text-secondary">
                        <i class="bi bi-people me-1"></i>Team
                    </label>
                    <select name="team_id" id="team_id" class="form-select">
                        <option value="">All Teams</option>
                        {% for team in teams %}
                        <option value="{{ team.id }}" {% if team.id|string == selected_team_id|string %}selected{% endif %}>
                            {{ team.name }}
                        </option>
                        {% endfor %}
                    </select>
                </div>
                <div class="col-md-3">
                    <label for="status" class="form-label fw-semibold text-secondary">
                        <i class="bi bi-flag me-1"></i>Status
                    </label>
                    <select name="status" id="status" class="form-select">
                        <option value="all" {% if status_filter=='all' %}selected{% endif %}>All Status</option>'''
    
    # Add all status options to filter dropdown
    for status in status_options.keys():
        template_content += f'''
                        <option value="{status}" {{% if status_filter=='{status}' %}}selected{{% endif %}}>{status}</option>'''
    
    template_content += '''
                    </select>
                </div>
                <div class="col-md-2">
                    <label for="date" class="form-label fw-semibold text-secondary">
                        <i class="bi bi-calendar3 me-1"></i>Date
                    </label>
                    <input type="date" name="date" id="date" class="form-control" value="{{ date_filter or '' }}">
                </div>
                <div class="col-md-2">
                    <button type="submit" class="btn btn-primary w-100">
                        <i class="bi bi-search me-1"></i>Filter
                    </button>
                </div>
                <div class="col-md-1">
                    <a href="{{ url_for('keypoints.keypoints') }}" class="btn btn-outline-secondary w-100" title="Clear Filters">
                        <i class="bi bi-x-circle"></i>
                    </a>
                </div>
            </form>
        </div>
    </div>

    <!-- Key Points Section -->
    {% if key_points %}
        <div class="row g-4">
            {% for kp in key_points %}
            <div class="col-12">
                <div class="card border-0 shadow-sm keypoint-card">
                    <div class="card-header bg-white border-0 py-3">
                        <div class="d-flex justify-content-between align-items-start">
                            <div class="flex-grow-1">
                                <h5 class="mb-2 text-primary fw-bold">
                                    <i class="bi bi-bookmark me-2"></i>{{ kp.description }}
                                </h5>
                                <div class="d-flex flex-wrap gap-2 align-items-center mb-3">
                                    <!-- Dynamic Status Badge -->
                                    {% set status_info = {
                                        'Open': {'color': 'secondary', 'icon': 'bi-circle'},
                                        'In Progress': {'color': 'primary', 'icon': 'bi-clock'},
                                        'Pending with Another Team': {'color': 'warning', 'icon': 'bi-people'},
                                        'On Hold': {'color': 'danger', 'icon': 'bi-pause-circle'},
                                        'Under Review': {'color': 'info', 'icon': 'bi-eye'},
                                        'Escalated': {'color': 'dark', 'icon': 'bi-arrow-up-circle'},
                                        'Waiting for Approval': {'color': 'light text-dark', 'icon': 'bi-check-circle-fill'},
                                        'Closed': {'color': 'success', 'icon': 'bi-check-circle'}
                                    } %}
                                    
                                    <span class="badge bg-{{ status_info.get(kp.status, {'color': 'secondary'})['color'] }} fs-6 px-3 py-2">
                                        <i class="{{ status_info.get(kp.status, {'icon': 'bi-circle'})['icon'] }} me-1"></i>{{ kp.status }}
                                    </span>
                                    
                                    {% if kp.jira_id %}
                                    <span class="badge bg-info fs-6 px-3 py-2">
                                        <i class="bi bi-link-45deg me-1"></i>{{ kp.jira_id }}
                                    </span>
                                    {% else %}
                                    <span class="badge bg-light text-dark border fs-6 px-3 py-2">
                                        <i class="bi bi-dash-circle me-1"></i>No JIRA ID
                                    </span>
                                    {% endif %}
                                </div>
                                
                                <!-- Enhanced Status Update Controls -->
                                <div class="row align-items-center mb-3 bg-light p-3 rounded status-update-section">
                                    <div class="col-md-5">
                                        <label class="form-label fw-semibold mb-1">
                                            <i class="bi bi-arrow-repeat me-1 text-primary"></i>Update Status
                                        </label>
                                        <form method="post" action="{{ url_for('keypoints.update_keypoint_status', key_point_id=kp.id) }}" style="display:inline;">
                                            <div class="input-group">
                                                <select name="new_status" class="form-select" required onchange="showStatusDescription(this)">'''
    
    # Add all status options to update dropdown
    for status in status_options.keys():
        template_content += f'''
                                                    <option value="{status}" {{% if kp.status == '{status}' %}}selected{{% endif %}}>{status}</option>'''
    
    template_content += '''
                                                </select>
                                                <button type="submit" class="btn btn-outline-primary" title="Update Status">
                                                    <i class="bi bi-check-lg"></i>
                                                </button>
                                            </div>
                                        </form>
                                        <small class="text-muted status-description mt-1"></small>
                                    </div>
                                    <div class="col-md-3">
                                        <label class="form-label fw-semibold mb-1">
                                            <i class="bi bi-person me-1 text-info"></i>Assigned To
                                        </label>
                                        <div class="fw-normal text-muted">
                                            {% if kp.responsible_engineer %}
                                                {{ kp.responsible_engineer.name }}
                                            {% else %}
                                                <span class="text-muted">Unassigned</span>
                                            {% endif %}
                                        </div>
                                    </div>
                                    <div class="col-md-2">
                                        <label class="form-label fw-semibold mb-1">
                                            <i class="bi bi-calendar-date me-1 text-success"></i>Created
                                        </label>
                                        <div class="fw-normal text-muted">
                                            {% if kp.shift %}
                                                {{ kp.shift.date }}
                                            {% else %}
                                                <span class="text-muted">Unknown</span>
                                            {% endif %}
                                        </div>
                                    </div>
                                    <div class="col-md-2">
                                        <label class="form-label fw-semibold mb-1">
                                            <i class="bi bi-stopwatch me-1 text-warning"></i>Priority
                                        </label>
                                        <div class="fw-normal">
                                            {% if kp.status in ['On Hold', 'Escalated'] %}
                                                <span class="badge bg-danger">High</span>
                                            {% elif kp.status in ['Pending with Another Team', 'Waiting for Approval'] %}
                                                <span class="badge bg-warning">Medium</span>
                                            {% else %}
                                                <span class="badge bg-success">Normal</span>
                                            {% endif %}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="card-body">
                        <!-- Updates Section -->
                        <div class="mb-4">
                            <h6 class="mb-3 text-secondary">
                                <i class="bi bi-chat-dots me-1"></i>Daily Updates & Status History
                                {% if updates_by_kp.get(kp.id) %}
                                <span class="badge bg-secondary ms-2">{{ updates_by_kp[kp.id]|length }}</span>
                                {% endif %}
                            </h6>
                            
                            {% if updates_by_kp.get(kp.id) %}
                            <div class="updates-list mb-3">
                                {% for update in updates_by_kp[kp.id] %}
                                <div class="update-item border-start border-primary border-4 ps-3 pb-3 mb-3">
                                    <div class="d-flex justify-content-between align-items-start">
                                        <div class="flex-grow-1">
                                            <p class="mb-1 fw-normal">{{ update.update_text }}</p>
                                            <small class="text-muted">
                                                <i class="bi bi-calendar me-1"></i>{{ update.update_date }}
                                                <i class="bi bi-person ms-2 me-1"></i>{{ update.updated_by }}
                                                {% if 'Status changed' in update.update_text %}
                                                <span class="badge bg-info ms-2">Status Change</span>
                                                {% endif %}
                                            </small>
                                        </div>
                                        <div class="btn-group" role="group">
                                            <a href="{{ url_for('keypoints.edit_keypoint_update', update_id=update.id) }}" 
                                               class="btn btn-sm btn-outline-primary" title="Edit Update">
                                                <i class="bi bi-pencil"></i>
                                            </a>
                                            <form method="post" action="{{ url_for('keypoints.delete_keypoint_update', update_id=update.id) }}" 
                                                  style="display: inline;" onsubmit="return confirm('Delete this update?')">
                                                <button type="submit" class="btn btn-sm btn-outline-danger" title="Delete Update">
                                                    <i class="bi bi-trash"></i>
                                                </button>
                                            </form>
                                        </div>
                                    </div>
                                </div>
                                {% endfor %}
                            </div>
                            {% else %}
                            <div class="text-center py-3 text-muted">
                                <i class="bi bi-chat-dots" style="font-size: 2rem; opacity: 0.3;"></i>
                                <p class="mb-0 mt-2">No updates yet. Add the first update below.</p>
                            </div>
                            {% endif %}
                        </div>

                        <!-- Add New Update Form -->
                        <div class="border-top pt-3">
                            <h6 class="mb-3 text-secondary">
                                <i class="bi bi-plus-circle me-1"></i>Add New Update
                            </h6>
                            <form method="post" action="{{ url_for('keypoints.add_keypoint_update', key_point_id=kp.id) }}">
                                <div class="row align-items-end">
                                    <div class="col-md-7">
                                        <label for="update_text_{{ kp.id }}" class="form-label fw-semibold text-secondary">
                                            <i class="bi bi-chat-text me-1"></i>Update Details
                                        </label>
                                        <textarea name="update_text" id="update_text_{{ kp.id }}" 
                                                  class="form-control" rows="2" 
                                                  placeholder="Describe the progress, changes, blocking issues, or status update..." required></textarea>
                                    </div>
                                    <div class="col-md-3">
                                        <label for="update_date_{{ kp.id }}" class="form-label fw-semibold text-secondary">
                                            <i class="bi bi-calendar3 me-1"></i>Date
                                        </label>
                                        <input type="date" name="update_date" id="update_date_{{ kp.id }}" 
                                               class="form-control" value="{{ date_filter or '' }}">
                                    </div>
                                    <div class="col-md-2">
                                        <button type="submit" class="btn btn-success w-100">
                                            <i class="bi bi-plus me-1"></i>Add Update
                                        </button>
                                    </div>
                                </div>
                            </form>
                        </div>
                    </div>
                </div>
            </div>
            {% endfor %}
        </div>
    {% else %}
    <!-- Empty State -->
    <div class="card border-0 shadow-sm">
        <div class="card-body text-center py-5">
            <div class="mb-3">
                <i class="bi bi-bookmark" style="font-size: 4rem; color: #6c757d; opacity: 0.3;"></i>
            </div>
            <h4 class="text-muted mb-3">No Key Points Found</h4>
            <p class="text-muted mb-0">
                {% if status_filter != 'all' or date_filter %}
                Try adjusting your filters to see more key points.
                {% else %}
                Key points will appear here once they are created in shift handovers.
                {% endif %}
            </p>
        </div>
    </div>
    {% endif %}
</div>

<!-- Custom Styles -->
<style>
.keypoint-card {
    transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out;
}

.keypoint-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(0,0,0,0.15) !important;
}

.update-item {
    background-color: #f8f9fa;
    border-radius: 0.375rem;
    padding: 0.75rem;
    margin-left: 0.5rem;
}

.status-update-section {
    background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
    border-radius: 0.5rem;
    border: 1px solid #dee2e6;
}

.form-select:focus, .form-control:focus {
    border-color: #0d6efd;
    box-shadow: 0 0 0 0.2rem rgba(13, 110, 253, 0.25);
}

.btn:hover {
    transform: translateY(-1px);
}

.status-description {
    font-style: italic;
    display: block;
}

/* Status-specific styling */
.badge.bg-danger { background-color: #dc3545 !important; }
.badge.bg-warning { background-color: #ffc107 !important; color: #000 !important; }
.badge.bg-info { background-color: #0dcaf0 !important; }
.badge.bg-dark { background-color: #212529 !important; }
</style>

<!-- JavaScript for enhanced functionality -->
<script>
// Status descriptions for better UX
const statusDescriptions = {'''
    
    # Add JavaScript status descriptions
    for status, props in status_options.items():
        template_content += f'''
    '{status}': '{props["description"]}','''
    
    template_content += '''
};

function showStatusDescription(selectElement) {
    const description = selectElement.parentNode.parentNode.querySelector('.status-description');
    const selectedStatus = selectElement.value;
    if (description && statusDescriptions[selectedStatus]) {
        description.textContent = statusDescriptions[selectedStatus];
    }
}

function updateTeamsDropdown(accountId) {
    // Enhanced with AJAX for better UX - placeholder for future enhancement
    document.querySelector('form').submit();
}

// Auto-submit status update forms with enhanced confirmation
document.addEventListener('DOMContentLoaded', function() {
    const statusForms = document.querySelectorAll('form[action*="update_keypoint_status"]');
    statusForms.forEach(form => {
        const select = form.querySelector('select[name="new_status"]');
        const originalValue = select.value;
        
        // Show initial description
        showStatusDescription(select);
        
        select.addEventListener('change', function() {
            showStatusDescription(this);
            if (this.value !== originalValue) {
                const confirmMessage = `Change status from "${originalValue}" to "${this.value}"?\\n\\n${statusDescriptions[this.value]}`;
                if (confirm(confirmMessage)) {
                    form.submit();
                } else {
                    this.value = originalValue;
                    showStatusDescription(this);
                }
            }
        });
    });
    
    // Initialize all status descriptions
    document.querySelectorAll('select[name="new_status"]').forEach(showStatusDescription);
});
</script>
{% endblock %}'''
    
    return template_content

def create_enhanced_keypoints_route_with_more_statuses():
    """Create enhanced route handling additional status options"""
    
    status_options = list(get_enhanced_status_options().keys())
    
    route_content = f'''from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_required, current_user
from models.models import ShiftKeyPoint, ShiftKeyPointUpdate, db
from datetime import date

keypoints_bp = Blueprint('keypoints', __name__)

# Valid status options
VALID_STATUSES = {status_options}

@keypoints_bp.route('/keypoints/update/edit/<int:update_id>', methods=['GET', 'POST'])
@login_required
def edit_keypoint_update(update_id):
    update = ShiftKeyPointUpdate.query.get_or_404(update_id)
    if request.method == 'POST':
        update_text = request.form.get('update_text')
        update_date = request.form.get('update_date')
        if update_text:
            update.update_text = update_text
            if update_date:
                update.update_date = date.fromisoformat(update_date)
            db.session.commit()
            flash('Update edited!', 'success')
            return redirect(url_for('keypoints.keypoints'))
        else:
            flash('Update text required.', 'danger')
    return render_template('edit_keypoint_update.html', update=update)

@keypoints_bp.route('/keypoints/update/delete/<int:update_id>', methods=['POST'])
@login_required
def delete_keypoint_update(update_id):
    update = ShiftKeyPointUpdate.query.get_or_404(update_id)
    db.session.delete(update)
    db.session.commit()
    flash('Update deleted!', 'success')
    return redirect(url_for('keypoints.keypoints'))

# Enhanced STATUS UPDATE ROUTE with additional status options
@keypoints_bp.route('/keypoints/status/<int:key_point_id>', methods=['POST'])
@login_required
def update_keypoint_status(key_point_id):
    key_point = ShiftKeyPoint.query.get_or_404(key_point_id)
    new_status = request.form.get('new_status')
    
    if new_status in VALID_STATUSES:
        old_status = key_point.status
        key_point.status = new_status
        
        # Enhanced status change messages
        status_messages = {{
            'Open': 'Task is now ready to be worked on',
            'In Progress': 'Task is now being actively worked on',
            'Pending with Another Team': 'Task is now waiting for another team',
            'On Hold': 'Task is now temporarily paused or blocked',
            'Under Review': 'Task is now being reviewed or validated',
            'Escalated': 'Task has been escalated to higher level',
            'Waiting for Approval': 'Task is now waiting for approval',
            'Closed': 'Task has been completed successfully'
        }}
        
        # Add an automatic update entry for status change with enhanced message
        status_update = ShiftKeyPointUpdate(
            key_point_id=key_point_id,
            update_text=f"Status changed from '{{old_status}}' to '{{new_status}}' by {{current_user.username}}. {{status_messages.get(new_status, '')}}",
            update_date=date.today(),
            updated_by=current_user.username
        )
        
        db.session.add(status_update)
        db.session.commit()
        
        flash(f'Key point status updated to "{{new_status}}"! {{status_messages.get(new_status, "")}}', 'success')
    else:
        flash('Invalid status value.', 'danger')
    
    return redirect(url_for('keypoints.keypoints'))

@keypoints_bp.route('/keypoints', methods=['GET', 'POST'])
@login_required
def keypoints():
    from models.models import Account, Team
    status_filter = request.args.get('status', 'all')
    date_filter = request.args.get('date')
    account_id = None
    team_id = None
    accounts = []
    teams = []
    
    # Role-based filter logic
    if current_user.role == 'super_admin':
        accounts = Account.query.filter_by(is_active=True).all()
        account_id = request.args.get('account_id') or (session.get('selected_account_id') if hasattr(session, 'get') else None)
        teams = Team.query.filter_by(is_active=True)
        if account_id:
            teams = teams.filter_by(account_id=account_id)
        teams = teams.all()
        team_id = request.args.get('team_id')
        # If team_id is empty string or None, treat as 'All Teams'
        if not team_id:
            selected_team_id = None
        else:
            selected_team_id = team_id
    elif current_user.role == 'account_admin':
        account_id = current_user.account_id
        accounts = [Account.query.get(account_id)] if account_id else []
        teams = Team.query.filter_by(account_id=account_id, is_active=True).all()
        team_id = request.args.get('team_id') or (session.get('selected_team_id') if hasattr(session, 'get') else None)
    else:
        account_id = current_user.account_id
        team_id = current_user.team_id
        accounts = [Account.query.get(account_id)] if account_id else []
        teams = [Team.query.get(team_id)] if team_id else []
    
    query = ShiftKeyPoint.query
    if account_id:
        query = query.filter_by(account_id=account_id)
    # Only filter by team_id if it is set and not empty string
    if team_id:
        query = query.filter_by(team_id=team_id)
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    
    key_points = query.all()
    updates_by_kp = {{}}
    for kp in key_points:
        updates_query = ShiftKeyPointUpdate.query.filter_by(key_point_id=kp.id)
        if date_filter:
            updates_query = updates_query.filter_by(update_date=date.fromisoformat(date_filter))
        updates_by_kp[kp.id] = updates_query.order_by(ShiftKeyPointUpdate.update_date.desc()).all()
    
    return render_template('keypoints_updates.html', 
                         key_points=key_points, 
                         updates_by_kp=updates_by_kp, 
                         status_filter=status_filter, 
                         date_filter=date_filter, 
                         accounts=accounts, 
                         teams=teams, 
                         selected_account_id=account_id, 
                         selected_team_id=(selected_team_id if current_user.role == 'super_admin' else team_id))

@keypoints_bp.route('/keypoints/update/<int:key_point_id>', methods=['POST'])
@login_required
def add_keypoint_update(key_point_id):
    update_text = request.form.get('update_text')
    update_date = request.form.get('update_date') or date.today().isoformat()
    if update_text:
        update = ShiftKeyPointUpdate(
            key_point_id=key_point_id,
            update_text=update_text,
            update_date=date.fromisoformat(update_date),
            updated_by=current_user.username
        )
        db.session.add(update)
        db.session.commit()
        flash('Update added!', 'success')
    else:
        flash('Update text required.', 'danger')
    return redirect(url_for('keypoints.keypoints'))
'''
    
    return route_content

def update_handover_form_template():
    """Update handover form template to include new status options"""
    
    status_options = get_enhanced_status_options()
    
    # Read current handover form template
    try:
        with open('/app/templates/handover_form.html', 'r') as f:
            content = f.read()
        
        # Find the keypoint status dropdown and replace it
        old_status_options = '''<select class="form-select" name="keypoint_status[]">
                                                <option value="Open" selected>Open</option>
                                                <option value="In Progress">In Progress</option>
                                                <option value="Closed">Closed</option>
                                            </select>'''
        
        new_status_options = '''<select class="form-select" name="keypoint_status[]">'''
        for status in status_options.keys():
            selected = ' selected' if status == 'Open' else ''
            new_status_options += f'''
                                                <option value="{status}"{selected}>{status}</option>'''
        new_status_options += '''
                                            </select>'''
        
        updated_content = content.replace(old_status_options, new_status_options)
        
        with open('/app/templates/handover_form_updated.html', 'w') as f:
            f.write(updated_content)
            
        return True
    except Exception as e:
        print(f"Error updating handover form: {{e}}")
        return False

def main():
    """Main execution function"""
    print("🚀 ADDING ADDITIONAL STATUS OPTIONS TO KEY POINTS")
    print("=" * 70)
    print(f"Started at: {{datetime.now()}}")
    print()
    
    try:
        status_options = get_enhanced_status_options()
        
        print("📊 NEW STATUS OPTIONS BEING ADDED:")
        for status, props in status_options.items():
            print(f"   {props['icon']} {{status}} - {{props['description']}}")
        print()
        
        # Create enhanced template
        template_content = create_enhanced_keypoints_template_with_more_statuses()
        with open('/app/templates/keypoints_updates_enhanced.html', 'w') as f:
            f.write(template_content)
        print("✅ Created enhanced keypoints template with additional statuses")
        
        # Create enhanced route
        route_content = create_enhanced_keypoints_route_with_more_statuses()
        with open('/app/routes/keypoints_enhanced.py', 'w') as f:
            f.write(route_content)
        print("✅ Created enhanced keypoints route with additional statuses")
        
        # Update handover form
        if update_handover_form_template():
            print("✅ Updated handover form template with new status options")
        else:
            print("⚠️  Could not update handover form template")
        
        print("\\n" + "=" * 70)
        print("🎯 ENHANCEMENT SUMMARY")
        print("✅ Total status options: {{len(status_options)}}")
        print("✅ Enhanced template: keypoints_updates_enhanced.html")
        print("✅ Enhanced route: keypoints_enhanced.py")
        print("✅ Updated handover form: handover_form_updated.html")
        print()
        print("🔧 NEW STATUS OPTIONS ADDED:")
        print("1. ✅ Pending with Another Team - For inter-team dependencies")
        print("2. ✅ On Hold - For blocked or paused tasks")
        print("3. ✅ Under Review - For validation/review process")
        print("4. ✅ Escalated - For escalated issues")
        print("5. ✅ Waiting for Approval - For completed work awaiting approval")
        print()
        print("🎨 VISUAL ENHANCEMENTS:")
        print("1. ✅ Status legend with descriptions")
        print("2. ✅ Color-coded badges for each status")
        print("3. ✅ Priority indicators based on status")
        print("4. ✅ Enhanced confirmation dialogs")
        print("5. ✅ Status change audit trail")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False
    
    return True

if __name__ == "__main__":
    main()

    return template_content

def main():
    """Main execution function"""
    print("🚀 ADDING ADDITIONAL STATUS OPTIONS TO KEY POINTS")
    print("=" * 70)
    print(f"Started at: {datetime.now()}")
    print()
    
    try:
        status_options = get_enhanced_status_options()
        
        print("📊 NEW STATUS OPTIONS BEING ADDED:")
        for status, props in status_options.items():
            print(f"   {props['icon']} {status} - {props['description']}")
        print()
        
        # Create enhanced template
        template_content = create_enhanced_keypoints_template_with_more_statuses()
        with open('/app/templates/keypoints_updates_enhanced.html', 'w') as f:
            f.write(template_content)
        print("✅ Created enhanced keypoints template with additional statuses")
        
        # Create enhanced route
        route_content = create_enhanced_keypoints_route_with_more_statuses()
        with open('/app/routes/keypoints_enhanced.py', 'w') as f:
            f.write(route_content)
        print("✅ Created enhanced keypoints route with additional statuses")
        
        print("\n" + "=" * 70)
        print("🎯 ENHANCEMENT SUMMARY")
        print(f"✅ Total status options: {len(status_options)}")
        print("✅ Enhanced template: keypoints_updates_enhanced.html")
        print("✅ Enhanced route: keypoints_enhanced.py")
        print()
        print("🔧 NEW STATUS OPTIONS ADDED:")
        print("1. ✅ Pending with Another Team - For inter-team dependencies")
        print("2. ✅ On Hold - For blocked or paused tasks")
        print("3. ✅ Under Review - For validation/review process")
        print("4. ✅ Escalated - For escalated issues")
        print("5. ✅ Waiting for Approval - For completed work awaiting approval")
        print()
        print("🎨 VISUAL ENHANCEMENTS:")
        print("1. ✅ Status legend with descriptions")
        print("2. ✅ Color-coded badges for each status")
        print("3. ✅ Priority indicators based on status")
        print("4. ✅ Enhanced confirmation dialogs")
        print("5. ✅ Status change audit trail")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False
    
    return True

if __name__ == "__main__":
    main()