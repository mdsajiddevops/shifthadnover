#!/usr/bin/env python3
"""
Update Team Details Template for Active/Inactive Team Members

This script updates the team_details.html template to:
1. Add enable/disable controls for admin users
2. Show status indicators for team members
3. Add toggle to show/hide inactive members
4. Improve the UI for better user experience
"""

import sys
import os
from datetime import datetime

# Add the application root to the Python path
app_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, app_root)

def update_team_details_template():
    """Update team_details.html template with status controls"""
    
    template_path = os.path.join(app_root, 'templates', 'team_details.html')
    
    try:
        with open(template_path, 'r') as f:
            original_content = f.read()
        
        # Read the new template from a separate file to avoid string length issues
        new_template_path = os.path.join(app_root, 'team_details_updated.html')
        
        # Create the updated template content in parts
        template_part1 = '''{% extends "base.html" %}
{% block content %}
<div class="container-fluid px-0">
    <!-- Header Section -->
    <div class="mb-4">
        <div class="d-flex justify-content-between align-items-center">
            <div>
                <h1 class="h3 mb-1 text-primary">Team Management</h1>
                <p class="text-muted mb-0">Manage team members and their contact information</p>
            </div>
            <div class="d-flex align-items-center gap-3">
                {% if current_user.role in ['super_admin', 'account_admin', 'team_admin'] %}
                <!-- Show/Hide Inactive Toggle -->
                <div class="form-check form-switch">
                    <input class="form-check-input" type="checkbox" id="showInactiveToggle" 
                           {% if show_inactive %}checked{% endif %}
                           onchange="toggleInactiveMembers(this.checked)">
                    <label class="form-check-label" for="showInactiveToggle">
                        Show Inactive Members
                    </label>
                </div>
                {% endif %}
                <span class="badge bg-primary fs-6 px-3 py-2">
                    <i class="bi bi-people-fill me-2"></i>{{ members|length }} Members
                </span>
            </div>
        </div>
    </div>

    <!-- Filter Section -->
    {% if current_user.role in ['super_admin', 'account_admin'] %}
    <div class="card mb-4 border-0 shadow-sm">
        <div class="card-body py-3">
            <form method="get" class="row g-3 align-items-end">
                <input type="hidden" name="show_inactive" value="{{ 'true' if show_inactive else 'false' }}">
                <div class="col-md-4">
                    <label for="account_id" class="form-label fw-semibold">
                        <i class="bi bi-building me-1"></i>Account
                    </label>
                    <select name="account_id" id="account_id" class="form-select" onchange="loadTeams(this.value)">
                        <option value="">All Accounts</option>
                        {% for account in accounts %}
                        <option value="{{ account.id }}" {% if account.id == selected_account_id %}selected{% endif %}>
                            {{ account.name }}
                        </option>
                        {% endfor %}
                    </select>
                </div>
                <div class="col-md-4">
                    <label for="team_id" class="form-label fw-semibold">
                        <i class="bi bi-people me-1"></i>Team
                    </label>
                    <select name="team_id" id="team_id" class="form-select">
                        <option value="">All Teams</option>
                        {% for team in teams %}
                        <option value="{{ team.id }}" {% if team.id == selected_team_id %}selected{% endif %}>
                            {{ team.name }}
                        </option>
                        {% endfor %}
                    </select>
                </div>
                <div class="col-md-4">
                    <button type="submit" class="btn btn-outline-primary">
                        <i class="bi bi-funnel me-1"></i>Filter
                    </button>
                </div>
            </form>
        </div>
    </div>
    {% endif %}'''
        
        with open(new_template_path, 'w') as f:
            f.write(template_part1)
        
        # Continue with the rest of the template
        template_part2 = '''
    <!-- Permission Notice for Regular Users -->
    {% if current_user.role not in ['super_admin', 'account_admin', 'team_admin'] %}
    <div class="alert alert-info d-flex align-items-center mb-4" role="alert">
        <i class="bi bi-info-circle me-2"></i>
        <div>
            <strong>View Only Access:</strong> You can view team member information but cannot make changes. 
            Contact an administrator to add, edit, or remove team members.
        </div>
    </div>
    {% endif %}

    <!-- Add New Member Section -->
    {% if current_user.role in ['super_admin', 'account_admin', 'team_admin'] %}
    <div class="card mb-4 border-0 shadow-sm">
        <div class="card-header bg-light border-0 py-3">
            <h5 class="mb-0">
                <i class="bi bi-person-plus text-success me-2"></i>Add New Team Member
            </h5>
        </div>
        <div class="card-body">
            <form method="POST" class="row g-3">
                <input type="hidden" name="action" value="add">
                <div class="col-md-3">
                    <label for="name" class="form-label fw-semibold">Name *</label>
                    <input type="text" name="name" id="name" class="form-control" required 
                           placeholder="Enter full name">
                </div>
                <div class="col-md-3">
                    <label for="email" class="form-label fw-semibold">Email *</label>
                    <input type="email" name="email" id="email" class="form-control" required 
                           placeholder="user@company.com">
                </div>
                <div class="col-md-3">
                    <label for="contact_number" class="form-label fw-semibold">Contact *</label>
                    <input type="text" name="contact_number" id="contact_number" class="form-control" required 
                           placeholder="Phone number">
                </div>
                <div class="col-md-2">
                    <label for="role" class="form-label fw-semibold">Role</label>
                    <input type="text" name="role" id="role" class="form-control" 
                           placeholder="e.g., Engineer">
                </div>
                <div class="col-md-1 d-flex align-items-end">
                    <button type="submit" class="btn btn-success w-100">
                        <i class="bi bi-plus-circle me-1"></i>Add
                    </button>
                </div>
            </form>
        </div>
    </div>
    {% endif %}'''
        
        with open(new_template_path, 'a') as f:
            f.write(template_part2)
        
        # Add the table section
        template_part3 = '''
    <!-- Team Members List -->
    <div class="card border-0 shadow-sm">
        <div class="card-header bg-white border-0 py-3">
            <h5 class="mb-0">
                <i class="bi bi-people text-primary me-2"></i>Team Members
                {% if not show_inactive %}
                    <small class="text-muted">(Active Only)</small>
                {% endif %}
            </h5>
        </div>
        <div class="card-body p-0">
            {% if members %}
            <div class="table-responsive">
                <table class="table table-hover align-middle mb-0">
                    <thead class="table-light">
                        <tr>
                            <th class="border-0 fw-semibold py-3 px-4">
                                <i class="bi bi-person me-1"></i>Name
                            </th>
                            <th class="border-0 fw-semibold py-3">
                                <i class="bi bi-envelope me-1"></i>Email
                            </th>
                            <th class="border-0 fw-semibold py-3">
                                <i class="bi bi-telephone me-1"></i>Contact
                            </th>
                            <th class="border-0 fw-semibold py-3">
                                <i class="bi bi-briefcase me-1"></i>Role
                            </th>
                            <th class="border-0 fw-semibold py-3">
                                <i class="bi bi-check-circle me-1"></i>Status
                            </th>
                            {% if current_user.role in ['super_admin', 'account_admin', 'team_admin'] %}
                            <th class="border-0 fw-semibold py-3 text-center">
                                <i class="bi bi-gear me-1"></i>Actions
                            </th>
                            {% endif %}
                        </tr>
                    </thead>
                    <tbody>'''
        
        with open(new_template_path, 'a') as f:
            f.write(template_part3)
        
        # Add the table body with member rows
        template_part4 = '''
                        {% for member in members %}
                        <tr class="border-bottom {% if not member.is_active %}table-secondary{% endif %}">
                            {% if current_user.role in ['super_admin', 'account_admin', 'team_admin'] %}
                            <form method="POST" style="display:contents;">
                                <input type="hidden" name="action" value="edit">
                                <td class="px-4 py-3">
                                    <input type="hidden" name="member_id" value="{{ member.id }}">
                                    <div class="d-flex align-items-center">
                                        <input type="text" name="name" class="form-control border-0 bg-transparent fw-semibold" 
                                               value="{{ member.name }}" required>
                                        {% if not member.is_active %}
                                            <i class="bi bi-pause-circle text-warning ms-2" title="Inactive"></i>
                                        {% endif %}
                                    </div>
                                </td>
                                <td class="py-3">
                                    <input type="email" name="email" class="form-control border-0 bg-transparent" 
                                           value="{{ member.email }}" required>
                                </td>
                                <td class="py-3">
                                    <input type="text" name="contact_number" class="form-control border-0 bg-transparent" 
                                           value="{{ member.contact_number }}" required>
                                </td>
                                <td class="py-3">
                                    <input type="text" name="role" class="form-control border-0 bg-transparent" 
                                           value="{{ member.role or '' }}">
                                </td>
                                <td class="py-3">
                                    {% if member.is_active %}
                                        <span class="badge bg-success">
                                            <i class="bi bi-check-circle me-1"></i>Active
                                        </span>
                                    {% else %}
                                        <span class="badge bg-warning">
                                            <i class="bi bi-pause-circle me-1"></i>Inactive
                                        </span>
                                    {% endif %}
                                </td>
                                <td class="text-center py-3">
                                    <div class="btn-group" role="group">
                                        <!-- Save/Update Button -->
                                        <button type="submit" class="btn btn-sm btn-outline-primary" title="Save Changes">
                                            <i class="bi bi-check"></i>
                                        </button>
                                    </div>
                                </td>
                            </form>'''
        
        with open(new_template_path, 'a') as f:
            f.write(template_part4)
        
        # Final part with closing tags and JavaScript
        template_part5 = '''
                            <!-- Status Control Buttons (separate forms) -->
                            <td class="text-center py-3" style="display: contents;">
                                <div class="btn-group" role="group">
                                    {% if member.is_active %}
                                        <!-- Disable Button -->
                                        <form method="POST" style="display: inline;">
                                            <input type="hidden" name="action" value="disable_member">
                                            <input type="hidden" name="member_id" value="{{ member.id }}">
                                            <button type="submit" class="btn btn-sm btn-outline-warning" title="Disable Member"
                                                    onclick="return confirm('Are you sure you want to disable {{ member.name }}?')">
                                                <i class="bi bi-pause"></i>
                                            </button>
                                        </form>
                                    {% else %}
                                        <!-- Enable Button -->
                                        <form method="POST" style="display: inline;">
                                            <input type="hidden" name="action" value="enable_member">
                                            <input type="hidden" name="member_id" value="{{ member.id }}">
                                            <button type="submit" class="btn btn-sm btn-outline-success" title="Enable Member">
                                                <i class="bi bi-play"></i>
                                            </button>
                                        </form>
                                    {% endif %}
                                    
                                    <!-- Delete Button -->
                                    <form method="POST" style="display: inline;">
                                        <input type="hidden" name="action" value="delete">
                                        <input type="hidden" name="member_id" value="{{ member.id }}">
                                        <button type="submit" class="btn btn-sm btn-outline-danger" title="Delete Member"
                                                onclick="return confirm('Are you sure you want to permanently delete {{ member.name }}?')">
                                            <i class="bi bi-trash"></i>
                                        </button>
                                    </form>
                                </div>
                            </td>
                            {% else %}
                            <!-- Read-only view for non-admin users -->
                            <td class="px-4 py-3">
                                <div class="d-flex align-items-center">
                                    <span class="fw-semibold">{{ member.name }}</span>
                                    {% if not member.is_active %}
                                        <i class="bi bi-pause-circle text-warning ms-2" title="Inactive"></i>
                                    {% endif %}
                                </div>
                            </td>
                            <td class="py-3">{{ member.email }}</td>
                            <td class="py-3">{{ member.contact_number }}</td>
                            <td class="py-3">
                                {% if member.role %}
                                    <span class="badge bg-light text-dark">{{ member.role }}</span>
                                {% else %}
                                    <span class="text-muted">Not specified</span>
                                {% endif %}
                            </td>
                            <td class="py-3">
                                {% if member.is_active %}
                                    <span class="badge bg-success">
                                        <i class="bi bi-check-circle me-1"></i>Active
                                    </span>
                                {% else %}
                                    <span class="badge bg-warning">
                                        <i class="bi bi-pause-circle me-1"></i>Inactive
                                    </span>
                                {% endif %}
                            </td>
                            {% endif %}
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
            {% else %}
            <div class="text-center py-5">
                <div class="mb-3">
                    <i class="bi bi-people" style="font-size: 3rem; color: #6c757d;"></i>
                </div>
                <h5 class="text-muted">No Team Members Found</h5>
                <p class="text-muted mb-0">
                    {% if current_user.role != 'viewer' %}
                    Add your first team member using the form above.
                    {% else %}
                    No team members are currently available.
                    {% endif %}
                </p>
            </div>
            {% endif %}
        </div>
    </div>
</div>

<script>
function toggleInactiveMembers(showInactive) {
    const url = new URL(window.location);
    url.searchParams.set('show_inactive', showInactive ? 'true' : 'false');
    window.location.href = url.toString();
}
</script>

<style>
.table-secondary {
    background-color: rgba(108, 117, 125, 0.1) !important;
}

.form-control.border-0.bg-transparent:focus {
    border: 1px solid #007bff !important;
    background-color: white !important;
}
</style>
{% endblock %}'''
        
        with open(new_template_path, 'a') as f:
            f.write(template_part5)
        
        # Now copy the complete template to the actual template file
        with open(new_template_path, 'r') as f:
            complete_template = f.read()
        
        with open(template_path, 'w') as f:
            f.write(complete_template)
        
        # Clean up temporary file
        os.remove(new_template_path)
        
        print("✅ Updated team_details.html template with status controls")
        return True
        
    except Exception as e:
        print(f"❌ Error updating team details template: {str(e)}")
        return False

def main():
    """Main execution function"""
    
    print("🚀 UPDATING TEAM DETAILS TEMPLATE")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Update team details template
    if not update_team_details_template():
        print("❌ Failed to update team details template")
        return False
    
    print("\n✅ TEMPLATE UPDATE COMPLETED")
    print("=" * 60)
    print("Updated:")
    print("1. ✅ team_details.html - Added status controls and enable/disable buttons")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)