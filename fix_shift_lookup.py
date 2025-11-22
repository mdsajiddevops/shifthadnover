#!/usr/bin/env python3
"""
Fix for shift auto-population issue in leave request form.
The issue is that the API endpoint is filtering by account_id which might not match
or the team member lookup is failing.
"""

import os
import sys

# Add the app directory to Python path
sys.path.append('/app')

# Set up Flask app context
os.environ.setdefault('FLASK_APP', 'app.py')

from app import create_app, db
from datetime import datetime, date

def fix_shift_lookup_endpoint():
    """Fix the get_user_shift_for_date endpoint"""
    
    routes_file = '/app/routes/shift_swap_leave.py'
    
    # Read the current file
    with open(routes_file, 'r') as f:
        content = f.read()
    
    # Find and replace the problematic function
    old_function = '''@shift_swap_leave_bp.route("/api/user-shift/<date>", methods=["GET"])
@login_required
def get_user_shift_for_date(date):
    """Get user's scheduled shift for a specific date"""
    try:
        from datetime import datetime
        from models.shift_roster import ShiftRoster
        from models.team_member import TeamMember

        # Parse the date
        try:
            leave_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"success": False, "error": "Invalid date format"}), 400

        # Get user's team member record
        team_member = TeamMember.query.filter_by(user_id=current_user.id).first()
        if not team_member:
            return jsonify({"success": False, "error": "Team member record not found"}), 404

        # Get scheduled shift for the date
        roster_entry = ShiftRoster.query.filter_by(
            date=leave_date,
            team_member_id=team_member.id,
            account_id=current_user.account_id
        ).first()

        if roster_entry:
            shift_names = {
                "D": "Day Shift",
                "E": "Evening Shift",
                "N": "Night Shift",
                "OS": "On-Site",
                "OF": "Off Duty",
                "O": "Week Off"
            }

            return jsonify({
                "success": True,
                "shift": {
                    "code": roster_entry.shift_code,
                    "name": shift_names.get(roster_entry.shift_code, roster_entry.shift_code)
                },
                "date": date
            })
        else:
            return jsonify({
                "success": True,
                "shift": None,
                "message": "No shift scheduled for this date"
            })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500'''

    new_function = '''@shift_swap_leave_bp.route("/api/user-shift/<date>", methods=["GET"])
@login_required
def get_user_shift_for_date(date):
    """Get user's scheduled shift for a specific date"""
    try:
        from datetime import datetime
        from models.shift_roster import ShiftRoster
        from models.team_member import TeamMember

        # Parse the date
        try:
            leave_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"success": False, "error": "Invalid date format"}), 400

        # Get user's team member record - try multiple approaches
        team_member = TeamMember.query.filter_by(user_id=current_user.id).first()
        if not team_member:
            return jsonify({"success": False, "error": "Team member record not found"}), 404

        # Get scheduled shift for the date - try without account_id first, then with
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
            ).first()

        if roster_entry:
            shift_names = {
                "D": "Day Shift",
                "E": "Evening Shift", 
                "N": "Night Shift",
                "OS": "On-Site",
                "OF": "Off Duty",
                "O": "Week Off"
            }

            return jsonify({
                "success": True,
                "shift": {
                    "code": roster_entry.shift_code,
                    "name": shift_names.get(roster_entry.shift_code, roster_entry.shift_code)
                },
                "date": date
            })
        else:
            # Debug info to help troubleshoot
            from flask import current_app
            current_app.logger.info(f"No roster entry found for user {current_user.id}, team_member {team_member.id}, date {leave_date}")
            
            return jsonify({
                "success": True,
                "shift": None,
                "message": "No shift scheduled for this date"
            })

    except Exception as e:
        from flask import current_app
        current_app.logger.error(f"Error in get_user_shift_for_date: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500'''

    # Replace the function
    if old_function in content:
        content = content.replace(old_function, new_function)
        
        # Write back to file
        with open(routes_file, 'w') as f:
            f.write(content)
            
        print("✅ Fixed shift lookup endpoint - removed strict account_id filtering")
        return True
    else:
        print("❌ Could not find the function to replace")
        return False

def test_shift_lookup():
    """Test the shift lookup functionality"""
    print("\n🔍 Testing shift lookup...")
    
    app = create_app()
    with app.app_context():
        from models.user import User
        from models.team_member import TeamMember
        from models.shift_roster import ShiftRoster
        
        # Get techopsuser1
        user = User.query.filter_by(username='techopsuser1').first()
        if not user:
            print("❌ User techopsuser1 not found")
            return
            
        print(f"✅ Found user: {user.username} (ID: {user.id})")
        
        # Get team member
        team_member = TeamMember.query.filter_by(user_id=user.id).first()
        if not team_member:
            print("❌ Team member record not found")
            return
            
        print(f"✅ Found team member: {team_member.id}")
        
        # Check for roster entries around the test date
        test_date = date(2025, 11, 28)
        print(f"🔍 Looking for roster entry on {test_date}")
        
        roster_entry = ShiftRoster.query.filter_by(
            date=test_date,
            team_member_id=team_member.id
        ).first()
        
        if roster_entry:
            print(f"✅ Found roster entry: {roster_entry.shift_code} on {roster_entry.date}")
        else:
            print("❌ No roster entry found for exact date")
            
            # Look for nearby dates
            print("🔍 Checking nearby dates...")
            nearby_entries = ShiftRoster.query.filter_by(
                team_member_id=team_member.id
            ).filter(
                ShiftRoster.date >= date(2025, 11, 25),
                ShiftRoster.date <= date(2025, 11, 30)
            ).all()
            
            if nearby_entries:
                print("📅 Nearby roster entries:")
                for entry in nearby_entries:
                    print(f"  {entry.date}: {entry.shift_code}")
            else:
                print("❌ No roster entries found in date range")

if __name__ == "__main__":
    print("🔧 Fixing shift auto-population issue...")
    
    if fix_shift_lookup_endpoint():
        test_shift_lookup()
        print("\n✅ Shift lookup fix applied successfully!")
        print("🔄 Please restart the application to apply changes.")
    else:
        print("\n❌ Failed to apply fix")