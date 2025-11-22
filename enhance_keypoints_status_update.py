#!/usr/bin/env python3
"""
ENHANCE KEY POINTS WITH STATUS UPDATE FUNCTIONALITY
=================================================

This script adds status update functionality to the Key Points tab:
1. Add status dropdown for each key point
2. Allow users to change status directly
3. Add audit trail for status changes
4. Improve UI/UX with better controls
"""

import sys
import os
sys.path.append('/app')

from datetime import datetime

def create_enhanced_keypoints_template():
    """Create enhanced key points template with status update functionality"""
    
    template_content = '''{% extends 'base.html' %}
{% block content %}
<div class="container-fluid px-0">
    <!-- Header Section -->
    <div class="mb-4">
        <div class="d-flex justify-content-between align-items-center">
            <div>
                <h1 class="h3 mb-1 text-primary">Key Points Management</h1>
                <p class="text-muted mb-0">Track, update, and manage key points with status controls</p>
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
                <div class="col-md-3">
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
                <div class="col-md-3">
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
                <div class="col-md-2">
                    <label for="status" class="form-label fw-semibold text-secondary">
                        <i class="bi bi-flag me-1"></i>Status
                    </label>
                    <select name="status" id="status" class="form-select">
                        <option value="all" {% if status_filter=='all' %}selected{% endif %}>All Status</option>
                        <option value="Open" {% if status_filter=='Open' %}selected{% endif %}>Open</option>
                        <option value="Closed" {% if status_filter=='Closed' %}selected{% endif %}>Closed</option>
                        <option value="In Progress" {% if status_filter=='In Progress' %}selected{% endif %}>In Progress</option>
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
                                    <span class="badge bg-{{ 'success' if kp.status == 'Closed' else 'warning' if kp.status == 'In Progress' else 'secondary' }} fs-6 px-3 py-2">
                                        {% if kp.status == 'Closed' %}<i class="bi bi-check-circle me-1"></i>{% elif kp.status == 'In Progress' %}<i class="bi bi-clock me-1"></i>{% else %}<i class="bi bi-circle me-1"></i>{% endif %}
                                        {{ kp.status }}
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
                                
                                <!-- 🔧 NEW: STATUS UPDATE CONTROLS -->
                                <div class="row align-items-center mb-3 bg-light p-3 rounded">
                                    <div class="col-md-4">
                                        <label class="form-label fw-semibold mb-1">
                                            <i class="bi bi-arrow-repeat me-1 text-primary"></i>Update Status
                                        </label>
                                        <form method="post" action="{{ url_for('keypoints.update_keypoint_status', key_point_id=kp.id) }}" style="display:inline;">
                                            <div class="input-group">
                                                <select name="new_status" class="form-select" required>
                                                    <option value="Open" {% if kp.status == 'Open' %}selected{% endif %}>Open</option>
                                                    <option value="In Progress" {% if kp.status == 'In Progress' %}selected{% endif %}>In Progress</option>
                                                    <option value="Closed" {% if kp.status == 'Closed' %}selected{% endif %}>Closed</option>
                                                </select>
                                                <button type="submit" class="btn btn-outline-primary" title="Update Status">
                                                    <i class="bi bi-check-lg"></i>
                                                </button>
                                            </div>
                                        </form>
                                    </div>
                                    <div class="col-md-4">
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
                                    <div class="col-md-4">
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
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="card-body">
                        <!-- Updates Section -->
                        <div class="mb-4">
                            <h6 class="mb-3 text-secondary">
                                <i class="bi bi-chat-dots me-1"></i>Daily Updates
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
                                                  placeholder="Describe the progress, changes, or status update..." required></textarea>
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
    transition: transform 0.2s ease-in-out;
}

.keypoint-card:hover {
    transform: translateY(-2px);
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

.btn-outline-primary:hover {
    transform: translateY(-1px);
}
</style>

<!-- JavaScript for dynamic functionality -->
<script>
function updateTeamsDropdown(accountId) {
    // This would be enhanced with AJAX to dynamically load teams
    // For now, just submit the form to reload with new account filter
    document.querySelector('form').submit();
}

// Auto-submit status update forms with confirmation
document.addEventListener('DOMContentLoaded', function() {
    const statusForms = document.querySelectorAll('form[action*="update_keypoint_status"]');
    statusForms.forEach(form => {
        const select = form.querySelector('select[name="new_status"]');
        const originalValue = select.value;
        
        select.addEventListener('change', function() {
            if (this.value !== originalValue) {
                const confirmMessage = `Change status to "${this.value}"?`;
                if (confirm(confirmMessage)) {
                    form.submit();
                } else {
                    this.value = originalValue;
                }
            }
        });
    });
});
</script>
{% endblock %}'''
    
    return template_content

def create_enhanced_keypoints_route():
    """Create enhanced route with status update functionality"""
    
    route_content = '''from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_required, current_user
from models.models import ShiftKeyPoint, ShiftKeyPointUpdate, db
from datetime import date

keypoints_bp = Blueprint('keypoints', __name__)

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

# 🔧 NEW: STATUS UPDATE ROUTE
@keypoints_bp.route('/keypoints/status/<int:key_point_id>', methods=['POST'])
@login_required
def update_keypoint_status(key_point_id):
    key_point = ShiftKeyPoint.query.get_or_404(key_point_id)
    new_status = request.form.get('new_status')
    
    if new_status in ['Open', 'In Progress', 'Closed']:
        old_status = key_point.status
        key_point.status = new_status
        
        # Add an automatic update entry for status change
        status_update = ShiftKeyPointUpdate(
            key_point_id=key_point_id,
            update_text=f"Status changed from '{old_status}' to '{new_status}' by {current_user.username}",
            update_date=date.today(),
            updated_by=current_user.username
        )
        
        db.session.add(status_update)
        db.session.commit()
        
        flash(f'Key point status updated to "{new_status}"!', 'success')
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
    updates_by_kp = {}
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

def main():
    """Main execution function"""
    print("🚀 CREATING ENHANCED KEY POINTS WITH STATUS UPDATE FUNCTIONALITY")
    print("=" * 70)
    print(f"Started at: {datetime.now()}")
    print()
    
    try:
        # Create enhanced template
        template_content = create_enhanced_keypoints_template()
        with open('/app/templates/keypoints_updates_enhanced.html', 'w') as f:
            f.write(template_content)
        print("✅ Created enhanced keypoints template")
        
        # Create enhanced route
        route_content = create_enhanced_keypoints_route()
        with open('/app/routes/keypoints_enhanced.py', 'w') as f:
            f.write(route_content)
        print("✅ Created enhanced keypoints route")
        
        print("\n" + "=" * 70)
        print("🎯 ENHANCEMENT SUMMARY")
        print("✅ Enhanced template: keypoints_updates_enhanced.html")
        print("✅ Enhanced route: keypoints_enhanced.py")
        print()
        print("🔧 NEW FEATURES ADDED:")
        print("1. ✅ Status dropdown for each key point")
        print("2. ✅ Direct status update (Open → In Progress → Closed)")
        print("3. ✅ Automatic audit trail for status changes")
        print("4. ✅ Better UI with status indicators")
        print("5. ✅ Confirmation dialogs for status changes")
        print("6. ✅ Improved visual design")
        print()
        print("📋 NEXT STEPS:")
        print("1. Replace current template with enhanced version")
        print("2. Update route registration")
        print("3. Test the new functionality")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False
    
    return True

if __name__ == "__main__":
    main()