#!/usr/bin/env python3

# Fix the template to use correct serialized object field names
import os

def fix_template_field_names():
    """Fix the template to use correct field names from serialized objects"""
    
    template_file = '/app/templates/shift_management/dashboard.html'
    
    if not os.path.exists(template_file):
        print(f"Template file not found: {template_file}")
        return False
        
    with open(template_file, 'r') as f:
        content = f.read()
    
    print("=== Fixing Template Field Names ===")
    
    # Fix swap request field names
    replacements = {
        # Swap request fields
        'request.partner_user.username': 'request.swap_with.username',
        'request.user_shift_date.strftime': 'request.original_date',
        'request.partner_shift_date.strftime': 'request.swap_date', 
        'request.request_date.strftime': 'request.created_at',
        
        # Leave request fields - these seem correct already
        # 'request.leave_date.strftime': 'request.leave_date',
        # 'request.request_date.strftime': 'request.created_at',
    }
    
    for old_field, new_field in replacements.items():
        if old_field in content:
            content = content.replace(old_field, new_field)
            print(f"✅ Replaced: {old_field} -> {new_field}")
    
    # Also need to handle the date formatting since serialized dates are ISO strings
    # Let's create a simpler version that works with the serialized data
    
    # Find and replace the My Requests section with a corrected version
    my_requests_start = content.find('<div class="modern-card">\n                <h3 class="card-title">\n                    <i class="fas fa-user"')
    
    if my_requests_start == -1:
        print("❌ My Requests section not found")
        return False
    
    # Find the end of this card
    card_depth = 0
    search_pos = my_requests_start
    my_requests_end = -1
    
    while search_pos < len(content):
        if content[search_pos:search_pos+5] == '<div ':
            card_depth += 1
        elif content[search_pos:search_pos+6] == '</div>':
            card_depth -= 1
            if card_depth == 0:
                my_requests_end = search_pos + 6
                break
        search_pos += 1
    
    if my_requests_end == -1:
        print("❌ Could not find end of My Requests section")
        return False
    
    # Create corrected My Requests section
    corrected_section = '''<div class="modern-card">
                <h3 class="card-title">
                    <i class="fas fa-user" style="color: #4a90e2;"></i>
                    My Requests
                </h3>

                <h4 style="color: #2c3e50; margin-top: 20px;">
                    <i class="fas fa-exchange-alt" style="color: #4a90e2;"></i>
                    Shift Swap Requests
                </h4>
                
                {% if user_requests and user_requests.success and user_requests.swap_requests and user_requests.swap_requests|length > 0 %}
                    <div class="requests-list">
                        {% for request in user_requests.swap_requests %}
                        <div class="request-item" style="padding: 15px; margin: 10px 0; background: #f8f9fa; border-radius: 10px; border-left: 4px solid #007bff;">
                            <div class="request-title">
                                <strong>Swap with {{ request.swap_with.username }}</strong>
                                <span class="badge badge-{% if request.status == 'approved' %}success{% elif request.status == 'rejected' %}danger{% else %}warning{% endif %} ml-2">
                                    {{ request.status|title }}
                                </span>
                            </div>
                            <div class="shift-swap-info mt-2">
                                <div class="shift-change">
                                    <span>Your shift: {{ request.original_date }} ({{ request.original_shift_code }})</span>
                                    <i class="fas fa-exchange-alt mx-2" style="color: #007bff;"></i>
                                    <span>Partner's shift: {{ request.swap_date }} ({{ request.swap_shift_code }})</span>
                                </div>
                            </div>
                            {% if request.reason %}
                            <div class="request-reason mt-2">
                                <small><strong>Reason:</strong> {{ request.reason }}</small>
                            </div>
                            {% endif %}
                            <small class="text-muted">
                                Requested: {{ request.created_at[:19] }}
                            </small>
                        </div>
                        {% endfor %}
                    </div>
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
                    <div class="requests-list">
                        {% for request in user_requests.leave_requests %}
                        <div class="request-item" style="padding: 15px; margin: 10px 0; background: #f8f9fa; border-radius: 10px; border-left: 4px solid #dc3545;">
                            <div class="request-title">
                                <strong>{{ request.leave_type|title or 'Leave' }} Request</strong>
                                <span class="badge badge-{% if request.status == 'approved' %}success{% elif request.status == 'rejected' %}danger{% else %}warning{% endif %} ml-2">
                                    {{ request.status|title }}
                                </span>
                            </div>
                            <div class="leave-details mt-2">
                                <div><strong>Date:</strong> {{ request.leave_date }}</div>
                                {% if request.shift_code %}
                                <div><strong>Shift:</strong> {{ request.shift_code }}</div>
                                {% endif %}
                            </div>
                            {% if request.reason %}
                            <div class="request-reason mt-2">
                                <small><strong>Reason:</strong> {{ request.reason }}</small>
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
                    </div>
                {% else %}
                    <div style="text-align: center; padding: 20px; color: #6c757d; background: rgba(108, 117, 125, 0.05); border-radius: 10px; border: 1px dashed #dee2e6;">
                        <i class="fas fa-calendar-times" style="font-size: 2rem; color: #28a745; margin-bottom: 10px;"></i>
                        <p><strong>No Leave Requests</strong></p>
                        <p>You haven't submitted any leave requests yet.</p>
                    </div>
                {% endif %}
            </div>'''
    
    # Replace the My Requests section
    new_content = content[:my_requests_start] + corrected_section + content[my_requests_end:]
    
    # Write the updated content
    with open(template_file, 'w') as f:
        f.write(new_content)
    
    print("✅ Successfully fixed template field names")
    return True

if __name__ == "__main__":
    print("=== Fixing Dashboard Template Error ===")
    success = fix_template_field_names()
    
    if success:
        print("\n✅ Template fixed successfully!")
        print("📋 Changes made:")
        print("  - Fixed field names to match serialized object structure")
        print("  - Updated swap request fields: partner_user -> swap_with")
        print("  - Updated date fields to work with ISO string format")
        print("  - Added proper conditional checks for user_requests.success")
        print("\n🔗 Dashboard should now load without errors!")
    else:
        print("\n❌ Failed to fix template")