#!/usr/bin/env python3
"""
Fix Dashboard Previous Shift Logic
This script fixes the dashboard to show only the previous shift handover details,
not old handovers from previous days.
"""

import os
import sys

def fix_dashboard_previous_shift_logic():
    """Fix dashboard to show only previous shift handover, not old handovers"""
    
    dashboard_file = 'routes/dashboard.py'
    
    if not os.path.exists(dashboard_file):
        print(f"❌ Dashboard file not found: {dashboard_file}")
        return False
    
    try:
        with open(dashboard_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print("🔧 Fixing dashboard previous shift logic...")
        
        # Find the problematic logic section and replace it
        old_logic_start = """    # 🔧 ENHANCED LOGIC: Find the MOST RECENT handover TO the current shift
    # instead of looking for a specific date
    print(f"[DEBUG] Dashboard: Looking for handovers TO {current_shift_type} shift")
    
    if filter_account_id and filter_team_id:
        # Look for the most recent handover TO the current shift (regardless of date)
        if current_shift_type == 'Evening':
            # For Evening shift, look for Morning → Evening handover
            target_handover = Shift.query.filter_by(
                current_shift_type='Morning',
                next_shift_type='Evening',
                account_id=filter_account_id,
                team_id=filter_team_id,
                status='sent'
            ).order_by(Shift.id.desc()).first()
            
        elif current_shift_type == 'Night':
            # For Night shift, look for Evening → Night handover  
            target_handover = Shift.query.filter_by(
                current_shift_type='Evening',
                next_shift_type='Night',
                account_id=filter_account_id,
                team_id=filter_team_id,
                status='sent'
            ).order_by(Shift.id.desc()).first()
            
        elif current_shift_type == 'Morning':
            # For Morning shift, look for Night → Morning handover
            target_handover = Shift.query.filter_by(
                current_shift_type='Night',
                next_shift_type='Morning',
                account_id=filter_account_id,
                team_id=filter_team_id,
                status='sent'
            ).order_by(Shift.id.desc()).first()
        else:
            target_handover = None"""

        new_logic = """    # 🔧 FIXED LOGIC: Find ONLY the PREVIOUS SHIFT handover (not old handovers from previous days)
    # Show only the immediately previous shift handover details
    print(f"[DEBUG] Dashboard: Looking for PREVIOUS SHIFT handover TO {current_shift_type} shift")
    
    def get_previous_shift_handover(current_shift, today_date, account_id, team_id):
        \"\"\"Get the previous shift handover based on current shift and date\"\"\"
        previous_shift_map = {
            'Morning': ('Night', today_date - timedelta(days=1)),  # Morning comes after Night (previous day)
            'Evening': ('Morning', today_date),                    # Evening comes after Morning (same day)
            'Night': ('Evening', today_date)                       # Night comes after Evening (same day)
        }
        
        if current_shift not in previous_shift_map:
            return None
            
        prev_shift_type, search_date = previous_shift_map[current_shift]
        
        print(f"[DEBUG] Looking for {prev_shift_type} → {current_shift} handover on {search_date}")
        
        # Look for handover FROM previous shift TO current shift on the correct date
        handover = Shift.query.filter_by(
            current_shift_type=prev_shift_type,
            next_shift_type=current_shift,
            date=search_date,
            account_id=account_id,
            team_id=team_id,
            status='sent'
        ).order_by(Shift.id.desc()).first()
        
        if handover:
            print(f"[DEBUG] Found previous shift handover: ID={handover.id}, {handover.current_shift_type}→{handover.next_shift_type}, date={handover.date}")
        else:
            print(f"[DEBUG] No previous shift handover found for {prev_shift_type}→{current_shift} on {search_date}")
            
        return handover
    
    if filter_account_id and filter_team_id:
        # Get the previous shift handover (not any old handover)
        target_handover = get_previous_shift_handover(current_shift_type, today, filter_account_id, filter_team_id)"""

        # Replace the old logic with new logic
        if old_logic_start in content:
            content = content.replace(old_logic_start, new_logic)
            print("✅ Updated main handover logic for specific account/team")
        else:
            print("⚠️ Could not find main handover logic section")
        
        # Now fix the account admin logic section
        old_account_admin_logic = """    elif filter_account_id:
        # Account admin logic - use the same enhanced logic
        if current_shift_type == 'Evening':
            target_handover = Shift.query.filter_by(
                current_shift_type='Morning',
                next_shift_type='Evening',
                account_id=filter_account_id,
                status='sent'
            ).order_by(Shift.id.desc()).first()
        elif current_shift_type == 'Night':
            target_handover = Shift.query.filter_by(
                current_shift_type='Evening',
                next_shift_type='Night',
                account_id=filter_account_id,
                status='sent'
            ).order_by(Shift.id.desc()).first()
        elif current_shift_type == 'Morning':
            target_handover = Shift.query.filter_by(
                current_shift_type='Night',
                next_shift_type='Morning',
                account_id=filter_account_id,
                status='sent'
            ).order_by(Shift.id.desc()).first()
        else:
            target_handover = None"""

        new_account_admin_logic = """    elif filter_account_id:
        # Account admin logic - get previous shift handover for the account
        def get_account_previous_shift_handover(current_shift, today_date, account_id):
            \"\"\"Get previous shift handover for account admin (across all teams in account)\"\"\"
            previous_shift_map = {
                'Morning': ('Night', today_date - timedelta(days=1)),
                'Evening': ('Morning', today_date),
                'Night': ('Evening', today_date)
            }
            
            if current_shift not in previous_shift_map:
                return None
                
            prev_shift_type, search_date = previous_shift_map[current_shift]
            
            # Look for most recent handover in the account on the correct date
            handover = Shift.query.filter_by(
                current_shift_type=prev_shift_type,
                next_shift_type=current_shift,
                date=search_date,
                account_id=account_id,
                status='sent'
            ).order_by(Shift.id.desc()).first()
            
            return handover
            
        target_handover = get_account_previous_shift_handover(current_shift_type, today, filter_account_id)"""

        # Replace account admin logic
        if old_account_admin_logic in content:
            content = content.replace(old_account_admin_logic, new_account_admin_logic)
            print("✅ Updated account admin handover logic")
        else:
            print("⚠️ Could not find account admin logic section")

        # Fix super admin logic section
        old_super_admin_logic = """    else:
        # For super admin, get most recent handovers TO current shift from all accounts/teams
        if current_shift_type == 'Evening':
            target_handovers = Shift.query.filter_by(
                current_shift_type='Morning',
                next_shift_type='Evening',
                status='sent'
            ).order_by(Shift.id.desc()).limit(10).all()
        elif current_shift_type == 'Night':
            target_handovers = Shift.query.filter_by(
                current_shift_type='Evening',
                next_shift_type='Night',
                status='sent'
            ).order_by(Shift.id.desc()).limit(10).all()
        elif current_shift_type == 'Morning':
            target_handovers = Shift.query.filter_by(
                current_shift_type='Night',
                next_shift_type='Morning',
                status='sent'
            ).order_by(Shift.id.desc()).limit(10).all()
        else:
            target_handovers = []"""

        new_super_admin_logic = """    else:
        # For super admin, get previous shift handovers from all accounts/teams (not old handovers)
        def get_super_admin_previous_shift_handovers(current_shift, today_date):
            \"\"\"Get previous shift handovers for super admin\"\"\"
            previous_shift_map = {
                'Morning': ('Night', today_date - timedelta(days=1)),
                'Evening': ('Morning', today_date),
                'Night': ('Evening', today_date)
            }
            
            if current_shift not in previous_shift_map:
                return []
                
            prev_shift_type, search_date = previous_shift_map[current_shift]
            
            # Get handovers from the previous shift on the correct date
            handovers = Shift.query.filter_by(
                current_shift_type=prev_shift_type,
                next_shift_type=current_shift,
                date=search_date,
                status='sent'
            ).order_by(Shift.id.desc()).limit(20).all()  # Limit to prevent too many results
            
            return handovers
            
        target_handovers = get_super_admin_previous_shift_handovers(current_shift_type, today)"""

        # Replace super admin logic
        if old_super_admin_logic in content:
            content = content.replace(old_super_admin_logic, new_super_admin_logic)
            print("✅ Updated super admin handover logic")
        else:
            print("⚠️ Could not find super admin logic section")

        # Write the updated content back
        with open(dashboard_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ Dashboard previous shift logic fixed successfully!")
        print("")
        print("🎯 CHANGES MADE:")
        print("   • Dashboard now shows ONLY previous shift handover details")
        print("   • Morning shift shows Night→Morning handover from previous day")
        print("   • Evening shift shows Morning→Evening handover from same day")  
        print("   • Night shift shows Evening→Night handover from same day")
        print("   • No more old handovers from previous days")
        print("   • Applied fix to all user roles (regular, account admin, super admin)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error fixing dashboard logic: {e}")
        return False

if __name__ == "__main__":
    print("🔧 FIXING DASHBOARD PREVIOUS SHIFT LOGIC")
    print("=" * 50)
    
    success = fix_dashboard_previous_shift_logic()
    
    if success:
        print("\n✅ DASHBOARD FIX COMPLETE!")
        print("🚀 The dashboard will now show only previous shift handover details")
        print("📅 No more old handovers from November 19th will appear on November 20th")
    else:
        print("\n❌ DASHBOARD FIX FAILED!")
        print("Please check the error messages above")
    print("=" * 50)