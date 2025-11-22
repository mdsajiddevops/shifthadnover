#!/usr/bin/env python3
"""
Check Current Shift Roster and Engineer Assignments
Verify the current shift setup for TechCorp Solutions Operations Team
"""

import sys
sys.path.append('/app')

from app import app, db
from models.models import User, Shift
from sqlalchemy import text

def check_shift_roster():
    """Check current shift roster and engineer assignments"""
    
    print("📅 Current Shift Roster for TechCorp Solutions - Operations Team")
    print("=" * 80)
    
    with app.app_context():
        # Check current shifts
        shifts = Shift.query.filter_by(account_id=1, team_id=2).all()
        
        print(f"🏢 ACTIVE SHIFTS:")
        print("-" * 50)
        
        if shifts:
            for shift in shifts:
                print(f"Shift ID: {shift.id}")
                print(f"Date: {shift.date}")
                print(f"Current Shift: {shift.current_shift_type}")
                print(f"Next Shift: {shift.next_shift_type}")
                print(f"Status: {shift.status}")
                
                # Check current shift engineers
                current_engineers = db.session.execute(
                    text("SELECT user_id FROM current_shift_engineers WHERE shift_id = :shift_id"),
                    {"shift_id": shift.id}
                ).fetchall()
                
                # Check next shift engineers  
                next_engineers = db.session.execute(
                    text("SELECT user_id FROM next_shift_engineers WHERE shift_id = :shift_id"),
                    {"shift_id": shift.id}
                ).fetchall()
                
                print(f"Current Engineers:")
                if current_engineers:
                    for (user_id,) in current_engineers:
                        user = User.query.get(user_id)
                        print(f"   - {user.username if user else f'ID:{user_id}'} (ID: {user_id})")
                else:
                    print(f"   - None assigned")
                
                print(f"Next Engineers:")
                if next_engineers:
                    for (user_id,) in next_engineers:
                        user = User.query.get(user_id)
                        print(f"   - {user.username if user else f'ID:{user_id}'} (ID: {user_id})")
                else:
                    print(f"   - None assigned")
                
                print("-" * 30)
        else:
            print("❌ No active shifts found for TechCorp Solutions - Operations Team")
            print("ℹ️ This is expected after the cleanup - shifts were deleted")
        
        # Check if techops users are assigned to any shifts
        print(f"\n👥 TECHOPS USER SHIFT ASSIGNMENTS:")
        print("-" * 50)
        
        techops_users = User.query.filter(User.username.in_(['techopsuser1', 'techopsuser2', 'techopsuser3', 'techopsuser4'])).all()
        
        for user in techops_users:
            # Check current shift assignments
            current_shifts = db.session.execute(
                text("SELECT s.id, s.date, s.current_shift_type FROM shift s JOIN current_shift_engineers cse ON s.id = cse.shift_id WHERE cse.user_id = :user_id"),
                {"user_id": user.id}
            ).fetchall()
            
            # Check next shift assignments
            next_shifts = db.session.execute(
                text("SELECT s.id, s.date, s.next_shift_type FROM shift s JOIN next_shift_engineers nse ON s.id = nse.shift_id WHERE nse.user_id = :user_id"),
                {"user_id": user.id}
            ).fetchall()
            
            print(f"{user.username} (ID: {user.id}):")
            print(f"   Current shifts: {len(current_shifts)}")
            print(f"   Next shifts: {len(next_shifts)}")
            
            for shift_id, date, shift_type in current_shifts:
                print(f"     - Current: Shift {shift_id} ({date}, {shift_type})")
            
            for shift_id, date, shift_type in next_shifts:
                print(f"     - Next: Shift {shift_id} ({date}, {shift_type})")
            
            if not current_shifts and not next_shifts:
                print(f"     - No shift assignments")
            print()
        
        # Summary
        print(f"📊 SUMMARY:")
        print("-" * 50)
        
        if not shifts:
            print("⚠️ No active shifts - You'll need to create a shift first")
            print("📝 To test handovers:")
            print("   1. Create a new shift with current engineers")
            print("   2. Assign techopsuser1, techopsuser2, etc. to the shift")
            print("   3. Then create handovers between them")
        else:
            print("✅ Active shifts exist - Ready for handover testing")
            print("✅ You can create handovers between assigned engineers")

if __name__ == "__main__":
    check_shift_roster()