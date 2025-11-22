#!/usr/bin/env python3
"""
Fix Leave Type to Roster Code Mapping
This script fixes the issue where all leave types show as 'LE' instead of proper codes like 'SL' for sick leave
"""

def fix_leave_type_mapping():
    """Fix the leave type to roster code mapping in the service"""
    
    print("🔧 FIXING LEAVE TYPE TO ROSTER CODE MAPPING")
    print("=" * 60)
    
    try:
        service_file = '/app/services/shift_swap_leave_service.py'
        
        with open(service_file, 'r') as f:
            content = f.read()
        
        # Find the _execute_leave_roster_update method and add leave type mapping
        old_roster_update_section = '''            if roster_entry:
                # Mark as leave
                roster_entry.shift_code = 'LE'  # Leave code
            else:
                # Create leave entry
                leave_entry = ShiftRoster(
                    date=leave_request.leave_date,
                    team_member_id=requester_tm_id,
                    shift_code='LE',
                    account_id=leave_request.account_id,
                    team_id=leave_request.team_id
                )'''
        
        new_roster_update_section = '''            # Map leave types to proper roster codes
            leave_code_map = {
                'sick': 'SL',           # Sick Leave
                'vacation': 'VL',       # Vacation Leave  
                'personal': 'CL',       # Casual Leave
                'emergency': 'CL',      # Casual Leave (Emergency)
                'family': 'CL',         # Casual Leave (Family)
                'other': 'OL'           # Other Leave
            }
            
            # Get the appropriate leave code
            leave_code = leave_code_map.get(leave_request.leave_type, 'OL')
            
            if roster_entry:
                # Mark as leave with proper code
                roster_entry.shift_code = leave_code
            else:
                # Create leave entry with proper code
                leave_entry = ShiftRoster(
                    date=leave_request.leave_date,
                    team_member_id=requester_tm_id,
                    shift_code=leave_code,
                    account_id=leave_request.account_id,
                    team_id=leave_request.team_id
                )'''
        
        if old_roster_update_section in content:
            content = content.replace(old_roster_update_section, new_roster_update_section)
            print("✅ Updated roster update logic with proper leave type mapping")
        else:
            print("❌ Could not find the roster update section to replace")
            return False
        
        # Write the updated content back
        with open(service_file, 'w') as f:
            f.write(content)
        
        print("\n📋 LEAVE TYPE MAPPING FIXED:")
        print("- Sick Leave → SL")
        print("- Vacation Leave → VL") 
        print("- Personal Leave → CL")
        print("- Emergency Leave → CL")
        print("- Family Leave → CL")
        print("- Other Leave → OL")
        
        print("\n✅ Leave type mapping fix applied successfully!")
        print("🔄 Flask will auto-reload to apply changes")
        
        return True
        
    except Exception as e:
        print(f"❌ Error fixing leave type mapping: {e}")
        return False

if __name__ == "__main__":
    fix_leave_type_mapping()