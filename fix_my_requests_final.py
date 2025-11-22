#!/usr/bin/env python3

# Fix the My Requests section to show actual user requests
import os

def fix_my_requests_section():
    template_file = '/app/templates/shift_management/dashboard.html'
    
    if not os.path.exists(template_file):
        print(f"Template file not found: {template_file}")
        return False
        
    with open(template_file, 'r') as f:
        content = f.read()
    
    # Find the My Requests section and replace it
    my_requests_start = content.find('<div class="modern-card">\n                <h3 class="card-title">\n                    <i class="fas fa-user"')
    
    if my_requests_start == -1:
        print("My Requests section not found")
        return False
    
    # Find the end of this card (next </div> that closes the modern-card)
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
        print("Could not find end of My Requests section")
        return False
    
    # Create the new My Requests section with proper data display
    new_my_requests = '''<div class="modern-card">
                <h3 class="card-title">
                    <i class="fas fa-user" style="color: #4a90e2;"></i>
                    My Requests
                </h3>

                <!-- Debug Info -->
                <div style="background: #f8f9fa; padding: 10px; margin: 10px 0; border-radius: 5px; font-family: monospace; font-size: 12px;">
                    <strong>Debug:</strong><br>
                    user_requests = {{ user_requests }}<br>
                    {% if user_requests %}
                        {% if user_requests.swap_requests %}
                            Swap count: {{ user_requests.swap_requests|length }}<br>
                        {% endif %}
                        {% if user_requests.leave_requests %}
                            Leave count: {{ user_requests.leave_requests|length }}<br>
                        {% endif %}
                    {% endif %}
                </div>

                <h4 style="color: #2c3e50; margin-top: 20px;">
                    <i class="fas fa-exchange-alt" style="color: #4a90e2;"></i>
                    Shift Swap Requests
                </h4>
                
                {% if user_requests and user_requests.swap_requests and user_requests.swap_requests|length > 0 %}
                    <div class="requests-list">
                        {% for request in user_requests.swap_requests %}
                        <div class="request-item" style="padding: 15px; margin: 10px 0; background: #f8f9fa; border-radius: 10px; border-left: 4px solid #007bff;">
                            <div class="request-title">
                                <strong>Swap with {{ request.swap_with_username or request.partner_user.username or 'Unknown User' }}</strong>
                                <span class="badge badge-{% if request.status == 'approved' %}success{% elif request.status == 'rejected' %}danger{% else %}warning{% endif %} ml-2">
                                    {{ request.status|title }}
                                </span>
                            </div>
                            <div class="shift-swap-info mt-2">
                                <div class="shift-change">
                                    <span>Your shift: {{ request.user_shift_date.strftime('%Y-%m-%d') if request.user_shift_date else request.original_date }}</span>
                                    <i class="fas fa-exchange-alt mx-2" style="color: #007bff;"></i>
                                    <span>Partner's shift: {{ request.partner_shift_date.strftime('%Y-%m-%d') if request.partner_shift_date else request.swap_date }}</span>
                                </div>
                            </div>
                            {% if request.reason %}
                            <div class="request-reason mt-2">
                                <small><strong>Reason:</strong> {{ request.reason }}</small>
                            </div>
                            {% endif %}
                            <small class="text-muted">
                                Requested: {{ request.request_date.strftime('%Y-%m-%d %H:%M') if request.request_date else request.created_at or 'Unknown' }}
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
                
                {% if user_requests and user_requests.leave_requests and user_requests.leave_requests|length > 0 %}
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
                                <div><strong>Date:</strong> {{ request.leave_date.strftime('%Y-%m-%d') if request.leave_date else 'Unknown' }}</div>
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
                                Requested: {{ request.request_date.strftime('%Y-%m-%d %H:%M') if request.request_date else request.created_at or 'Unknown' }}
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
    new_content = content[:my_requests_start] + new_my_requests + content[my_requests_end:]
    
    # Write the updated content
    with open(template_file, 'w') as f:
        f.write(new_content)
    
    print("✅ Successfully updated My Requests section with proper data display")
    return True

if __name__ == "__main__":
    print("=== Fixing My Requests Section ===")
    success = fix_my_requests_section()
    
    if success:
        print("\n✅ Template updated successfully!")
        print("📋 Changes made:")
        print("  - Added debug information to see what data is available")
        print("  - Fixed condition checks for user_requests.swap_requests and user_requests.leave_requests")
        print("  - Added proper display of swap request details")
        print("  - Added proper display of leave request details")
        print("  - Maintained fallback messages for empty states")
        print("\n🔗 Next steps:")
        print("  1. Check https://shiftops.lab.epam.com")
        print("  2. Login as techopsuser1")
        print("  3. Go to Shift Management dashboard")
        print("  4. Check the 'My Requests' section for your submitted requests")
    else:
        print("\n❌ Failed to update template")