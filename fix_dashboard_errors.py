#!/usr/bin/env python3
"""
Fix the dashboard template and routing errors
"""
import sys
import os

# Add the current directory to Python path
sys.path.append('/app')

def fix_dashboard_errors():
    """Fix the template formatting and routing errors"""
    
    print("🔧 FIXING DASHBOARD TEMPLATE AND ROUTING ERRORS")
    print("=" * 60)
    
    # Fix 1: Update the template to handle datetime formatting properly
    template_path = '/app/templates/shift_management/dashboard.html'
    
    try:
        with open(template_path, 'r') as f:
            content = f.read()
        
        # Replace the problematic datetime formatting
        old_datetime_pattern = "{{ request.created_at.strftime('%Y-%m-%d %H:%M') }}"
        new_datetime_pattern = "{{ request.created_at[:16] if request.created_at is string else request.created_at.strftime('%Y-%m-%d %H:%M') if request.created_at else 'Unknown' }}"
        
        content = content.replace(old_datetime_pattern, new_datetime_pattern)
        
        # Also fix any other datetime references
        content = content.replace(
            "{{ request.created_at.strftime('%Y-%m-%d %H:%M') }}",
            "{{ request.created_at[:16] if request.created_at is string else request.created_at.strftime('%Y-%m-%d %H:%M') if request.created_at else 'Unknown' }}"
        )
        
        with open(template_path, 'w') as f:
            f.write(content)
        
        print("✅ Fixed datetime formatting in template")
        
    except Exception as e:
        print(f"❌ Error fixing template: {e}")
    
    # Fix 2: Update the route to use correct endpoint
    route_path = '/app/routes/shift_swap_leave.py'
    
    try:
        with open(route_path, 'r') as f:
            content = f.read()
        
        # Replace the incorrect url_for call
        old_redirect = "return redirect(url_for('main.index'))"
        new_redirect = "return redirect('/')"  # Simple redirect to home
        
        content = content.replace(old_redirect, new_redirect)
        
        with open(route_path, 'w') as f:
            f.write(content)
        
        print("✅ Fixed routing redirect in shift_swap_leave.py")
        
    except Exception as e:
        print(f"❌ Error fixing route: {e}")
    
    # Fix 3: Also check if we need to handle the data serialization properly
    service_path = '/app/services/shift_swap_leave_service.py'
    
    try:
        with open(service_path, 'r') as f:
            content = f.read()
        
        # Find the _serialize_swap_request method and ensure it returns proper datetime strings
        if '_serialize_swap_request' in content:
            print("✅ Found _serialize_swap_request method - checking datetime serialization...")
            
            # Look for datetime serialization issues
            if '.isoformat()' not in content and 'strftime' not in content:
                print("⚠️  Datetime serialization might need improvement in service")
        
    except Exception as e:
        print(f"❌ Error checking service: {e}")
    
    print("\n🔄 Changes applied:")
    print("  • Fixed datetime formatting in template to handle different data types")
    print("  • Changed redirect from 'main.index' to simple '/' redirect")
    print("  • Template should now handle both string and datetime objects")

if __name__ == "__main__":
    fix_dashboard_errors()