#!/usr/bin/env python3

# Fix the My Requests section by checking the current template and updating the route
import os
import sys
import re

def check_dashboard_route():
    """Check if the dashboard route is passing user_requests correctly"""
    route_file = '/app/routes/shift_swap_leave.py'
    
    print(f"Checking dashboard route in {route_file}")
    
    if not os.path.exists(route_file):
        print(f"Route file not found: {route_file}")
        return False
        
    with open(route_file, 'r') as f:
        content = f.read()
    
    # Check if user_requests is being passed to template
    if 'user_requests=' in content:
        print("✅ user_requests is being passed to template")
        return True
    else:
        print("❌ user_requests is NOT being passed to template")
        return False

def check_template_logic():
    """Check the current template logic"""
    template_file = '/app/templates/shift_management/dashboard.html'
    
    print(f"Checking template at {template_file}")
    
    if not os.path.exists(template_file):
        print(f"Template file not found: {template_file}")
        return False
        
    with open(template_file, 'r') as f:
        content = f.read()
    
    # Check for My Requests section
    if 'myRequests' in content:
        print("✅ My Requests section found in template")
        
        # Check if it uses user_requests variable
        if 'user_requests' in content:
            print("✅ user_requests variable found in template")
        else:
            print("❌ user_requests variable NOT found in template")
            
        return True
    else:
        print("❌ My Requests section NOT found in template")
        return False

def add_debug_to_template():
    """Add debug information to see what's being passed"""
    template_file = '/app/templates/shift_management/dashboard.html'
    
    if not os.path.exists(template_file):
        print(f"Template file not found: {template_file}")
        return False
        
    with open(template_file, 'r') as f:
        content = f.read()
    
    # Add debug section at the top of the body
    debug_html = '''
    <!-- DEBUG: Check what data is available -->
    <div style="background: #f0f0f0; padding: 10px; margin: 10px; border: 2px solid red; font-family: monospace;">
        <h4>DEBUG INFO:</h4>
        <p>Current User: {{ current_user.username if current_user else 'None' }}</p>
        <p>User ID: {{ current_user.id if current_user else 'None' }}</p>
        <p>user_requests variable: {{ user_requests }}</p>
        <p>user_requests type: {{ user_requests.__class__.__name__ if user_requests else 'None' }}</p>
        {% if user_requests %}
            {% if user_requests.get('swap_requests') %}
                <p>Swap requests count: {{ user_requests.swap_requests|length }}</p>
            {% endif %}
            {% if user_requests.get('leave_requests') %}  
                <p>Leave requests count: {{ user_requests.leave_requests|length }}</p>
            {% endif %}
        {% endif %}
    </div>
    '''
    
    # Find body tag and add debug after it
    if '<body' in content and 'DEBUG INFO:' not in content:
        body_pos = content.find('<body')
        if body_pos != -1:
            # Find the end of the body tag
            body_end = content.find('>', body_pos)
            if body_end != -1:
                content = content[:body_end+1] + debug_html + content[body_end+1:]
                
                with open(template_file, 'w') as f:
                    f.write(content)
                
                print("✅ Added debug information to template")
                return True
    
    print("❌ Could not add debug information to template")
    return False

def main():
    print("=== Fixing My Requests Section ===")
    
    # Check route
    route_ok = check_dashboard_route()
    
    # Check template
    template_ok = check_template_logic()
    
    # Add debug info
    debug_added = add_debug_to_template()
    
    print("\n=== Summary ===")
    print(f"Route passing user_requests: {'✅' if route_ok else '❌'}")
    print(f"Template has My Requests section: {'✅' if template_ok else '❌'}")
    print(f"Debug information added: {'✅' if debug_added else '❌'}")
    
    print("\nNext steps:")
    print("1. Check the application at https://shiftops.lab.epam.com")
    print("2. Login as techopsuser1")
    print("3. Go to Shift Management dashboard")
    print("4. Look for the red debug box to see what data is available")

if __name__ == "__main__":
    main()