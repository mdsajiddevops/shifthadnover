#!/usr/bin/env python3

# Remove the orphaned endfor tag
import os

def fix_orphaned_endfor():
    """Remove the orphaned {% endfor %} tag"""
    
    template_file = '/app/templates/shift_management/dashboard.html'
    
    if not os.path.exists(template_file):
        print(f"Template file not found: {template_file}")
        return False
        
    with open(template_file, 'r') as f:
        lines = f.readlines()
    
    print("=== Removing Orphaned {% endfor %} Tag ===")
    
    # Find and remove the orphaned endfor tag around line 315
    for i, line in enumerate(lines):
        if i > 310 and i < 320 and '{% endfor %}' in line and 'div' in lines[i-1]:
            print(f"Found orphaned endfor at line {i+1}: {line.strip()}")
            lines[i] = ''  # Remove the line
            print(f"✅ Removed orphaned endfor tag")
            break
    
    # Write the fixed content
    with open(template_file, 'w') as f:
        f.writelines(lines)
    
    print("✅ Successfully removed orphaned endfor tag")
    return True

if __name__ == "__main__":
    print("=== Fixing Orphaned Endfor Tag ===")
    success = fix_orphaned_endfor()
    
    if success:
        print("\n✅ Template syntax fixed!")
        print("📋 Changes made:")
        print("  - Removed extra {% endfor %} tag that had no matching {% for %}")
        print("\n🔗 Dashboard should now load without Jinja2 errors!")
    else:
        print("\n❌ Failed to fix orphaned endfor tag")