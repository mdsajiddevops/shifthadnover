#!/usr/bin/env python3
"""
Simple fix for shift auto-population issue in leave request form.
"""

def fix_shift_lookup_endpoint():
    """Fix the get_user_shift_for_date endpoint"""
    
    routes_file = '/app/routes/shift_swap_leave.py'
    
    # Read the current file
    with open(routes_file, 'r') as f:
        content = f.read()
    
    # Find and replace the problematic roster query
    old_query = '''        # Get scheduled shift for the date
        roster_entry = ShiftRoster.query.filter_by(
            date=leave_date,
            team_member_id=team_member.id,
            account_id=current_user.account_id
        ).first()'''

    new_query = '''        # Get scheduled shift for the date - try without account_id first, then with
        roster_entry = ShiftRoster.query.filter_by(
            date=leave_date,
            team_member_id=team_member.id
        ).first()

        # If not found and user has account_id, try with account_id filter
        if not roster_entry and current_user.account_id:
            roster_entry = ShiftRoster.query.filter_by(
                date=leave_date,
                team_member_id=team_member.id,
                account_id=current_user.account_id
            ).first()'''

    # Replace the query
    if old_query in content:
        content = content.replace(old_query, new_query)
        
        # Also add better error logging
        old_error_handling = '''        else:
            return jsonify({
                "success": True,
                "shift": None,
                "message": "No shift scheduled for this date"
            })'''

        new_error_handling = '''        else:
            # Debug info to help troubleshoot
            print(f"DEBUG: No roster entry found for user {current_user.id}, team_member {team_member.id}, date {leave_date}")
            
            return jsonify({
                "success": True,
                "shift": None,
                "message": "No shift scheduled for this date"
            })'''

        if old_error_handling in content:
            content = content.replace(old_error_handling, new_error_handling)
        
        # Write back to file
        with open(routes_file, 'w') as f:
            f.write(content)
            
        print("✅ Fixed shift lookup endpoint - removed strict account_id filtering")
        return True
    else:
        print("❌ Could not find the query to replace")
        print("Current content length:", len(content))
        return False

if __name__ == "__main__":
    print("🔧 Fixing shift auto-population issue...")
    
    if fix_shift_lookup_endpoint():
        print("\n✅ Shift lookup fix applied successfully!")
        print("🔄 Please restart the application to apply changes.")
    else:
        print("\n❌ Failed to apply fix")