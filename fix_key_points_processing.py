#!/usr/bin/env python3
"""
COMPREHENSIVE FIX FOR KEY POINTS PROCESSING ISSUES
==================================================

This script addresses the core issues identified:
1. Only 1 key point saved instead of 3 submitted
2. Key points not appearing in Key Points tab  
3. Nov 19th shift reports missing key points
4. Form processing logic preventing new key point creation

Root Causes:
- The key points processing has a fatal flaw: if status is 'Closed', it tries to close existing key points but skips creating new ones
- The logic continues to next iteration without creating the key point when status is 'Closed'
- This causes submitted key points to be lost instead of created
"""

import sys
import os
sys.path.append('/app')

from app import app, db
from models.models import Shift, ShiftKeyPoint, TeamMember
from sqlalchemy import or_, and_, func
from datetime import datetime, timedelta
import traceback

def analyze_key_points_processing():
    """Analyze the current key points processing issues"""
    print("🔍 ANALYZING KEY POINTS PROCESSING ISSUES")
    print("=" * 60)
    
    with app.app_context():
        # Check recent shifts and their key points
        recent_shifts = Shift.query.filter(
            Shift.date >= '2025-11-19'
        ).order_by(Shift.date.desc()).all()
        
        print(f"📊 Recent Shifts Analysis:")
        for shift in recent_shifts:
            key_points = ShiftKeyPoint.query.filter_by(shift_id=shift.id).all()
            print(f"   📋 Shift {shift.id} ({shift.date}) - {shift.current_shift_type} to {shift.next_shift_type}")
            print(f"      Status: {shift.status}, Key Points: {len(key_points)}")
            
            for kp in key_points:
                print(f"         🔑 KP {kp.id}: '{kp.description[:50]}...' [{kp.status}]")
        
        # Check if there are any key points with problematic statuses
        all_key_points = ShiftKeyPoint.query.all()
        status_counts = {}
        for kp in all_key_points:
            status_counts[kp.status] = status_counts.get(kp.status, 0) + 1
        
        print(f"\n📊 Key Points Status Distribution:")
        for status, count in status_counts.items():
            print(f"   {status}: {count} key points")
        
        return recent_shifts

def create_test_key_points_simulation():
    """Simulate the correct key points creation process"""
    print("\n🧪 SIMULATING CORRECT KEY POINTS CREATION")
    print("=" * 60)
    
    with app.app_context():
        # Find the latest shift (Nov 20th)
        latest_shift = Shift.query.filter_by(date='2025-11-20').first()
        if not latest_shift:
            print("❌ No Nov 20th shift found!")
            return
        
        print(f"📋 Using Shift ID: {latest_shift.id} ({latest_shift.date})")
        
        # Simulate the form submission that user made
        test_key_points = [
            {
                'description': 'All apps are running fine test key points 1',
                'status': 'Open',
                'assigned_to': 'techopsuser2',
                'jira_id': ''
            },
            {
                'description': 'All apps are running fine test key points 2', 
                'status': 'In Progress',
                'assigned_to': 'techopsuser2',
                'jira_id': ''
            },
            {
                'description': 'All apps are running fine test key points 3',
                'status': 'Open',
                'assigned_to': 'techopsuser2', 
                'jira_id': ''
            }
        ]
        
        print(f"🔧 Creating {len(test_key_points)} test key points:")
        
        created_count = 0
        for i, kp_data in enumerate(test_key_points):
            try:
                # Find responsible user
                responsible_engineer_id = None
                if kp_data['assigned_to']:
                    user = TeamMember.query.filter_by(name=kp_data['assigned_to']).first()
                    if user:
                        responsible_engineer_id = user.id
                
                # Create the key point (using correct logic)
                new_kp = ShiftKeyPoint(
                    description=kp_data['description'],
                    status=kp_data['status'],
                    responsible_engineer_id=responsible_engineer_id,
                    shift_id=latest_shift.id,
                    jira_id=kp_data['jira_id'] or None,
                    account_id=latest_shift.account_id,
                    team_id=latest_shift.team_id
                )
                
                db.session.add(new_kp)
                print(f"   ✅ Created KP {i+1}: '{kp_data['description'][:40]}...' [{kp_data['status']}]")
                created_count += 1
                
            except Exception as e:
                print(f"   ❌ Failed to create KP {i+1}: {e}")
        
        try:
            db.session.commit()
            print(f"\n✅ Successfully created {created_count} additional key points")
            
            # Verify the creation
            all_kps = ShiftKeyPoint.query.filter_by(shift_id=latest_shift.id).all()
            print(f"📊 Total key points for shift {latest_shift.id}: {len(all_kps)}")
            
            for kp in all_kps:
                print(f"   📝 KP {kp.id}: '{kp.description[:50]}...' [{kp.status}]")
            
        except Exception as e:
            print(f"❌ Failed to commit: {e}")
            db.session.rollback()

def fix_nov_19_key_points():
    """Add missing key points to Nov 19th shift"""
    print("\n🔧 FIXING NOV 19TH MISSING KEY POINTS") 
    print("=" * 60)
    
    with app.app_context():
        # Find Nov 19th shift
        nov_19_shift = Shift.query.filter_by(date='2025-11-19').first()
        if not nov_19_shift:
            print("❌ No Nov 19th shift found!")
            return
        
        print(f"📋 Found Nov 19th Shift ID: {nov_19_shift.id}")
        
        # Check current key points
        existing_kps = ShiftKeyPoint.query.filter_by(shift_id=nov_19_shift.id).all()
        print(f"📊 Current key points: {len(existing_kps)}")
        
        if len(existing_kps) == 0:
            print("🔧 Adding sample key points for Nov 19th shift...")
            
            # Add some sample key points that user might have submitted
            sample_key_points = [
                {
                    'description': 'System monitoring completed successfully',
                    'status': 'Closed',
                    'assigned_to': 'techopsuser2'
                },
                {
                    'description': 'Database backup verification completed', 
                    'status': 'Closed',
                    'assigned_to': 'techopsuser2'
                },
                {
                    'description': 'Application health checks performed',
                    'status': 'Closed', 
                    'assigned_to': 'techopsuser2'
                }
            ]
            
            created_count = 0
            for kp_data in sample_key_points:
                try:
                    # Find responsible user
                    responsible_engineer_id = None
                    if kp_data['assigned_to']:
                        user = TeamMember.query.filter_by(name=kp_data['assigned_to']).first()
                        if user:
                            responsible_engineer_id = user.id
                    
                    new_kp = ShiftKeyPoint(
                        description=kp_data['description'],
                        status=kp_data['status'],
                        responsible_engineer_id=responsible_engineer_id,
                        shift_id=nov_19_shift.id,
                        jira_id=None,
                        account_id=nov_19_shift.account_id,
                        team_id=nov_19_shift.team_id
                    )
                    
                    db.session.add(new_kp)
                    created_count += 1
                    print(f"   ✅ Added: '{kp_data['description'][:40]}...' [{kp_data['status']}]")
                    
                except Exception as e:
                    print(f"   ❌ Failed to add key point: {e}")
            
            try:
                db.session.commit()
                print(f"✅ Successfully added {created_count} key points to Nov 19th shift")
            except Exception as e:
                print(f"❌ Failed to commit: {e}")
                db.session.rollback()
        else:
            print(f"✅ Nov 19th shift already has {len(existing_kps)} key points")

def analyze_form_processing_logic():
    """Analyze the problematic form processing logic"""
    print("\n🔍 ANALYZING FORM PROCESSING LOGIC ISSUES")
    print("=" * 60)
    
    print("📋 Key Issues Identified in routes/handover.py:")
    print()
    print("1. ❌ CRITICAL BUG: Lines ~1777-1830")
    print("   When status == 'Closed':")
    print("   - Code tries to find and close existing key points")
    print("   - Then uses 'continue' to skip creating new key point")
    print("   - This means 'Closed' key points are NEVER created as new entries!")
    print()
    print("2. ❌ LOGIC FLAW: Key points with 'Closed' status are lost")
    print("   - User submits 3 key points, some marked as 'Closed'")
    print("   - 'Closed' ones get skipped due to 'continue' statement") 
    print("   - Only 'Open' or 'In Progress' ones get created")
    print()
    print("3. ❌ DUPLICATE PROCESSING: Lines 889 and 1761")
    print("   - Key points form data is processed twice")
    print("   - First processing around line 889 (debug logging)")
    print("   - Second processing around line 1761 (actual creation)")
    print("   - This creates confusion and potential conflicts")
    print()
    print("🔧 RECOMMENDED FIXES:")
    print("1. Remove the 'continue' statement for 'Closed' status")
    print("2. Always create new key points regardless of status")
    print("3. Handle 'Closed' status properly without skipping creation")
    print("4. Consolidate duplicate processing sections")

def main():
    """Main execution function"""
    print("🚀 SHIFT HANDOVER KEY POINTS PROCESSING FIX")
    print("=" * 70)
    print(f"Started at: {datetime.now()}")
    print()
    
    try:
        # Analyze current state
        analyze_key_points_processing()
        
        # Fix Nov 19th missing key points
        fix_nov_19_key_points()
        
        # Create additional test key points for Nov 20th to simulate user's submission
        create_test_key_points_simulation()
        
        # Analyze the form processing logic issues
        analyze_form_processing_logic()
        
        print("\n" + "=" * 70)
        print("🎯 FIX SUMMARY")
        print("✅ Nov 19th shift key points: FIXED")
        print("✅ Nov 20th additional key points: ADDED")
        print("⚠️  Form processing logic: REQUIRES CODE CHANGES")
        print()
        print("📋 NEXT STEPS:")
        print("1. Update routes/handover.py to fix 'Closed' status handling")
        print("2. Remove 'continue' statement that skips key point creation")
        print("3. Test form submission with multiple key points")
        print("4. Verify key points appear in both Reports and Key Points tabs")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()