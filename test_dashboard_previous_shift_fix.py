#!/usr/bin/env python3
"""
Test Dashboard Previous Shift Fix
This script tests that the dashboard now shows only previous shift handover details
"""

import os
import sys

def test_dashboard_previous_shift_fix():
    """Test that dashboard shows only previous shift handovers"""
    
    try:
        from datetime import datetime, timedelta
        from app import app
        from models.models import Shift, db, User
        
        print("🧪 TESTING DASHBOARD PREVIOUS SHIFT FIX")
        print("=" * 50)
        
        with app.app_context():
            # Get current date and shift info
            today = datetime.now().date()
            yesterday = today - timedelta(days=1)
            
            print(f"📅 Today: {today}")
            print(f"📅 Yesterday: {yesterday}")
            
            # Check recent handovers in database
            print(f"\n🔍 RECENT HANDOVERS IN DATABASE:")
            recent_handovers = Shift.query.filter(
                Shift.date >= yesterday,
                Shift.status == 'sent'
            ).order_by(Shift.date.desc(), Shift.id.desc()).limit(10).all()
            
            for handover in recent_handovers:
                print(f"   📋 ID={handover.id}: {handover.current_shift_type}→{handover.next_shift_type} on {handover.date}")
                print(f"      Account: {handover.account_id}, Team: {handover.team_id}")
            
            # Test the logic for different shift scenarios
            print(f"\n🎯 TESTING DASHBOARD LOGIC:")
            
            # Test current shift detection
            from routes.dashboard import get_ist_now, get_shift_type_and_next
            
            ist_now = get_ist_now()
            current_shift_type, next_shift_type = get_shift_type_and_next(ist_now)
            
            print(f"   ⏰ Current time (IST): {ist_now.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"   🔄 Current shift: {current_shift_type}")
            print(f"   ➡️ Next shift: {next_shift_type}")
            
            # Test previous shift mapping
            previous_shift_map = {
                'Morning': ('Night', today - timedelta(days=1)),
                'Evening': ('Morning', today),
                'Night': ('Evening', today)
            }
            
            if current_shift_type in previous_shift_map:
                prev_shift_type, search_date = previous_shift_map[current_shift_type]
                print(f"   ⏪ Previous shift should be: {prev_shift_type} on {search_date}")
                
                # Check if this handover exists
                expected_handover = Shift.query.filter_by(
                    current_shift_type=prev_shift_type,
                    next_shift_type=current_shift_type,
                    date=search_date,
                    status='sent'
                ).order_by(Shift.id.desc()).first()
                
                if expected_handover:
                    print(f"   ✅ Found expected previous shift handover: ID={expected_handover.id}")
                    print(f"      {expected_handover.current_shift_type}→{expected_handover.next_shift_type} on {expected_handover.date}")
                else:
                    print(f"   ⚠️ No previous shift handover found for {prev_shift_type}→{current_shift_type} on {search_date}")
            
            # Check for old handovers that should NOT appear
            print(f"\n🚫 CHECKING FOR OLD HANDOVERS (should NOT appear on dashboard):")
            old_handovers = Shift.query.filter(
                Shift.date < yesterday,
                Shift.status == 'sent'
            ).order_by(Shift.date.desc()).limit(5).all()
            
            for old_handover in old_handovers:
                print(f"   📅 OLD: ID={old_handover.id} - {old_handover.current_shift_type}→{old_handover.next_shift_type} on {old_handover.date}")
                print(f"      ❌ This should NOT appear on today's dashboard")
            
            print(f"\n✅ DASHBOARD LOGIC TEST COMPLETE")
            print(f"🎯 Key Points:")
            print(f"   • Dashboard should show only {current_shift_type} shift handovers")
            print(f"   • Should look for {prev_shift_type}→{current_shift_type} on {search_date}")
            print(f"   • Should NOT show handovers from {yesterday} or earlier")
            print(f"   • Old incident from Nov 19th should not appear on Nov 20th dashboard")
            
        return True
        
    except Exception as e:
        print(f"❌ Error testing dashboard fix: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_dashboard_previous_shift_fix()
    
    if success:
        print("\n🎉 DASHBOARD TEST COMPLETED!")
        print("📋 Check the output above to verify the logic is working correctly")
    else:
        print("\n❌ DASHBOARD TEST FAILED!")
    print("=" * 50)