#!/usr/bin/env python3

# Fix the template block structure
import os

def fix_template_structure():
    """Fix the Jinja2 template block structure"""
    
    template_file = '/app/templates/shift_management/dashboard.html'
    
    if not os.path.exists(template_file):
        print(f"Template file not found: {template_file}")
        return False
        
    with open(template_file, 'r') as f:
        content = f.read()
    
    print("=== Fixing Template Block Structure ===")
    
    # The issue is that the template has broken block structure
    # Let's rebuild it with proper structure
    
    # Extract the main content (everything after the initial broken structure)
    # Find where the actual content starts (after the broken JavaScript)
    content_start = content.find('{% endblock %}')
    
    if content_start == -1:
        print("❌ Could not find content structure")
        return False
    
    # Get everything after the first endblock
    main_content = content[content_start + len('{% endblock %}'):].strip()
    
    # Remove any trailing {% endblock %} from the end
    if main_content.endswith('{% endblock %}'):
        main_content = main_content[:-len('{% endblock %}')].strip()
    
    # Create a properly structured template
    new_template = '''{% extends "base.html" %}

{% block title %}Shift Management Dashboard{% endblock %}

{% block content %}
''' + main_content + '''
{% endblock %}'''
    
    # Write the fixed template
    with open(template_file, 'w') as f:
        f.write(new_template)
    
    print("✅ Successfully fixed template block structure")
    return True

if __name__ == "__main__":
    print("=== Fixing Template Block Structure ===")
    success = fix_template_structure()
    
    if success:
        print("\n✅ Template structure fixed!")
        print("📋 Changes made:")
        print("  - Fixed broken {% block title %} structure")
        print("  - Properly structured {% block content %} section")
        print("  - Removed duplicate {% endblock %} tags")
        print("\n🔗 Dashboard should now load correctly!")
    else:
        print("\n❌ Failed to fix template structure")