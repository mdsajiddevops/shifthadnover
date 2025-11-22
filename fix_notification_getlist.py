#!/usr/bin/env python3
"""
Fix the notification service getlist issue
"""

import sys
sys.path.append('/app')

from app import app

def fix_notification_service():
    """Fix the getlist issue in notification service"""
    
    # Read the current notification service file
    with open('/app/services/notification_service_fix.py', 'r') as f:
        content = f.read()
    
    # Replace the getlist() calls with proper dictionary access
    fixes = [
        ("assigned_tos = form_data.getlist('open_incident_assigned[]')", 
         "assigned_tos = form_data.get('open_incident_assigned[]', []) if isinstance(form_data.get('open_incident_assigned[]'), list) else [form_data.get('open_incident_assigned[]', '')]"),
        
        ("incident_ids = form_data.getlist('open_incident_id[]')", 
         "incident_ids = form_data.get('open_incident_id[]', []) if isinstance(form_data.get('open_incident_id[]'), list) else [form_data.get('open_incident_id[]', '')]"),
        
        ("descriptions = form_data.getlist('open_incident_description[]')", 
         "descriptions = form_data.get('open_incident_description[]', []) if isinstance(form_data.get('open_incident_description[]'), list) else [form_data.get('open_incident_description[]', '')]"),
        
        ("priorities = form_data.getlist('open_incident_priority[]')", 
         "priorities = form_data.get('open_incident_priority[]', []) if isinstance(form_data.get('open_incident_priority[]'), list) else [form_data.get('open_incident_priority[]', '')]")
    ]
    
    for old, new in fixes:
        if old in content:
            content = content.replace(old, new)
            print(f"✅ Fixed: {old[:50]}...")
        else:
            print(f"⚠️ Not found: {old[:50]}...")
    
    # Write the fixed content back
    with open('/app/services/notification_service_fix.py', 'w') as f:
        f.write(content)
    
    print("✅ Notification service fix applied!")

if __name__ == "__main__":
    fix_notification_service()