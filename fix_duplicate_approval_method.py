#!/usr/bin/env python3
"""
Remove the duplicate approve_swap_request method that overrides the correct one
"""

def remove_duplicate_method():
    """Remove the second approve_swap_request method that doesn't update roster"""
    
    print("=== REMOVING DUPLICATE METHOD ===")
    
    # Read the file
    with open('/app/services/shift_swap_leave_service.py', 'r') as f:
        lines = f.readlines()
    
    # Find the duplicate method starting at line 744 (0-indexed would be 743)
    duplicate_start = None
    duplicate_end = None
    
    for i, line in enumerate(lines):
        if i >= 743 and 'def approve_swap_request(self, request_id, approver_id, comments=\'\')' in line:
            duplicate_start = i
            print(f"Found duplicate method start at line {i+1}")
            break
    
    if duplicate_start is None:
        print("❌ Could not find duplicate method")
        return False
    
    # Find the end of the method (next method or class end)
    indent_level = len(lines[duplicate_start]) - len(lines[duplicate_start].lstrip())
    
    for i in range(duplicate_start + 1, len(lines)):
        line = lines[i]
        if line.strip() == '':
            continue
        
        current_indent = len(line) - len(line.lstrip())
        if current_indent <= indent_level and (line.strip().startswith('def ') or line.strip().startswith('class ')):
            duplicate_end = i
            print(f"Found duplicate method end at line {i}")
            break
    
    if duplicate_end is None:
        duplicate_end = len(lines)
        print(f"Method extends to end of file at line {len(lines)}")
    
    # Remove the duplicate method
    new_lines = lines[:duplicate_start] + lines[duplicate_end:]
    
    # Write back the fixed file
    with open('/app/services/shift_swap_leave_service.py', 'w') as f:
        f.writelines(new_lines)
    
    print(f"✅ Removed duplicate method (lines {duplicate_start+1} to {duplicate_end})")
    print(f"📝 Removed {duplicate_end - duplicate_start} lines")
    
    return True

def verify_fix():
    """Verify that only one approve_swap_request method remains"""
    
    print("\n=== VERIFYING FIX ===")
    
    with open('/app/services/shift_swap_leave_service.py', 'r') as f:
        content = f.read()
    
    # Count occurrences of the method
    method_count = content.count('def approve_swap_request')
    print(f"📊 Found {method_count} approve_swap_request methods")
    
    # Check if _execute_roster_swap is called
    has_roster_update = '_execute_roster_swap' in content
    print(f"🔄 Roster update logic present: {'✅ Yes' if has_roster_update else '❌ No'}")
    
    return method_count == 1 and has_roster_update

if __name__ == "__main__":
    print("🔧 FIXING ROSTER UPDATE ISSUE")
    print("Problem: Duplicate approve_swap_request method overrides the correct one")
    print()
    
    success = remove_duplicate_method()
    
    if success:
        verified = verify_fix()
        if verified:
            print("\n🎉 SUCCESS!")
            print("✅ Duplicate method removed")
            print("✅ Roster update logic preserved")
            print("✅ Only one approve_swap_request method remains")
            print("\n📋 Now when swap requests are approved:")
            print("   1. Request status changes to 'approved'")
            print("   2. _execute_roster_swap() is called")
            print("   3. Roster entries are swapped in database")
            print("   4. Users see updated shifts")
            print("\n🔄 Application restart recommended to ensure changes take effect")
        else:
            print("\n⚠️ Fix applied but verification failed")
    else:
        print("\n❌ Failed to remove duplicate method")