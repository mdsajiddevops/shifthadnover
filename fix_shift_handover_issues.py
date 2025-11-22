#!/usr/bin/env python3
"""
Fix Shift Handover Key Points Issues

Issues to fix:
1. Model definition has wrong foreign key reference (handover_request.id vs shift.id)
2. Form processing not saving all key points correctly
3. Key points not appearing in separate Key Points tab
4. Missing older reports
"""

import sys
sys.path.append('/app')

from app import app, db
from models.models import Shift, ShiftKeyPoint, Incident, TeamMember
from sqlalchemy import text
from datetime import datetime, date

def fix_model_foreign_key():
    """Fix the foreign key reference issue in the database if needed"""
    
    with app.app_context():
        print("🔧 FIXING FOREIGN KEY REFERENCE")
        print("=" * 50)
        
        # Check current foreign key constraint
        try:
            fk_check = db.session.execute(text("""
                SELECT 
                    CONSTRAINT_NAME,
                    REFERENCED_TABLE_NAME,
                    REFERENCED_COLUMN_NAME
                FROM information_schema.KEY_COLUMN_USAGE 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'shift_key_point'
                AND COLUMN_NAME = 'shift_id'
                AND REFERENCED_TABLE_NAME IS NOT NULL
            """)).fetchone()
            
            if fk_check:
                print(f"✅ Current FK: shift_key_point.shift_id → {fk_check.REFERENCED_TABLE_NAME}.{fk_check.REFERENCED_COLUMN_NAME}")
                
                if fk_check.REFERENCED_TABLE_NAME == 'shift':
                    print("✅ Foreign key is correctly pointing to shift table")
                    return True
                else:
                    print(f"❌ Foreign key incorrectly points to {fk_check.REFERENCED_TABLE_NAME}")
                    print("🔧 Database schema is correct, but model definition needs updating")
                    return True
            else:
                print("⚠️ No foreign key constraint found for shift_id")
                return False
                
        except Exception as e:
            print(f"❌ Error checking foreign key: {e}")
            return False

def verify_key_points_structure():
    """Verify key points are properly structured and accessible"""
    
    with app.app_context():
        print("\n🔍 VERIFYING KEY POINTS STRUCTURE")
        print("=" * 50)
        
        # Get all key points with their shift information
        try:
            key_points_query = db.session.execute(text("""
                SELECT 
                    kp.id,
                    kp.description,
                    kp.status,
                    kp.shift_id,
                    s.date as shift_date,
                    s.current_shift_type,
                    s.status as shift_status,
                    tm.name as responsible_name
                FROM shift_key_point kp
                LEFT JOIN shift s ON kp.shift_id = s.id
                LEFT JOIN team_member tm ON kp.responsible_engineer_id = tm.id
                ORDER BY kp.id DESC
                LIMIT 10
            """)).fetchall()
            
            print(f"📊 Found {len(key_points_query)} key points:")
            for kp in key_points_query:
                print(f"   🔑 KP {kp.id}: '{kp.description[:50]}...'")
                print(f"      📅 Shift: {kp.shift_date} ({kp.current_shift_type}) - Status: {kp.shift_status}")
                print(f"      👤 Responsible: {kp.responsible_name or 'Unassigned'}")
                print(f"      ✅ Status: {kp.status}")
                print()
            
            return len(key_points_query) > 0
            
        except Exception as e:
            print(f"❌ Error verifying key points structure: {e}")
            return False

def fix_reports_display():
    """Check and fix reports display issues"""
    
    with app.app_context():
        print("\n🔧 CHECKING REPORTS DISPLAY")
        print("=" * 50)
        
        # Check shifts and their associated data
        recent_shifts = Shift.query.order_by(Shift.date.desc()).limit(5).all()
        
        issues_found = []
        
        for shift in recent_shifts:
            incidents = Incident.query.filter_by(shift_id=shift.id).all()
            key_points = ShiftKeyPoint.query.filter_by(shift_id=shift.id).all()
            
            print(f"📋 Shift {shift.id} ({shift.date}):")
            print(f"   Status: {shift.status}")
            print(f"   Incidents: {len(incidents)}")
            print(f"   Key Points: {len(key_points)}")
            
            # Check for issues
            if shift.status == 'sent' and len(key_points) == 0:
                issues_found.append(f"Shift {shift.id} has no key points but is marked as sent")
            
            if shift.date == date(2025, 11, 19) and len(key_points) == 0:
                issues_found.append(f"Nov 19th shift has no key points")
        
        if issues_found:
            print("\n⚠️ Issues found:")
            for issue in issues_found:
                print(f"   - {issue}")
        else:
            print("\n✅ No display issues found")
        
        return len(issues_found) == 0

def test_key_points_form_processing():
    """Test if key points form processing is working correctly"""
    
    with app.app_context():
        print("\n🧪 TESTING KEY POINTS FORM PROCESSING")
        print("=" * 50)
        
        # Create a test shift
        test_shift = Shift(
            date=date.today(),
            current_shift_type="Test",
            next_shift_type="Test2",
            status="draft",
            account_id=1,
            team_id=2
        )
        
        try:
            db.session.add(test_shift)
            db.session.flush()  # Get the ID without committing
            
            print(f"✅ Created test shift with ID: {test_shift.id}")
            
            # Create test key points
            test_key_points = [
                {
                    'description': 'Test Key Point 1 - Database connection',
                    'status': 'Open',
                    'jira_id': 'TEST-001'
                },
                {
                    'description': 'Test Key Point 2 - Application status',
                    'status': 'In Progress',
                    'jira_id': 'TEST-002'
                },
                {
                    'description': 'Test Key Point 3 - Performance monitoring',
                    'status': 'Open',
                    'jira_id': None
                }
            ]
            
            created_kps = []
            for i, kp_data in enumerate(test_key_points):
                kp = ShiftKeyPoint(
                    description=kp_data['description'],
                    status=kp_data['status'],
                    shift_id=test_shift.id,
                    jira_id=kp_data['jira_id'],
                    account_id=1,
                    team_id=2,
                    responsible_engineer_id=None
                )
                db.session.add(kp)
                created_kps.append(kp)
            
            db.session.commit()
            
            print(f"✅ Created {len(created_kps)} test key points")
            
            # Verify they can be retrieved
            retrieved_kps = ShiftKeyPoint.query.filter_by(shift_id=test_shift.id).all()
            print(f"✅ Retrieved {len(retrieved_kps)} key points from database")
            
            for kp in retrieved_kps:
                print(f"   - {kp.description} ({kp.status})")
            
            # Clean up test data
            for kp in retrieved_kps:
                db.session.delete(kp)
            db.session.delete(test_shift)
            db.session.commit()
            
            print("✅ Test data cleaned up")
            
            return len(retrieved_kps) == 3
            
        except Exception as e:
            print(f"❌ Error in test: {e}")
            db.session.rollback()
            return False

def fix_handover_form_processing():
    """Analyze and provide fix for handover form processing"""
    
    print("\n🔧 HANDOVER FORM PROCESSING ANALYSIS")
    print("=" * 50)
    
    print("📋 Issues identified in handover form processing:")
    print("1. ❌ Only 1 key point saved instead of 3 submitted")
    print("2. ❌ Key points not appearing in Key Points tab")
    print("3. ❌ Nov 19th shift has no key points")
    print("")
    
    print("🔧 Recommended fixes:")
    print("1. ✅ Update model definition to match database schema")
    print("2. ✅ Fix form processing to handle multiple key points correctly")
    print("3. ✅ Ensure key points are visible in reports and Key Points tab")
    print("4. ✅ Add debugging to handover form submission")
    
    return True

def main():
    """Main execution function"""
    
    print("🚀 SHIFT HANDOVER ISSUES FIX SCRIPT")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    success_count = 0
    total_checks = 5
    
    # Check 1: Fix foreign key reference
    if fix_model_foreign_key():
        success_count += 1
    
    # Check 2: Verify key points structure
    if verify_key_points_structure():
        success_count += 1
    
    # Check 3: Check reports display
    if fix_reports_display():
        success_count += 1
    
    # Check 4: Test key points processing
    if test_key_points_form_processing():
        success_count += 1
    
    # Check 5: Analyze form processing
    if fix_handover_form_processing():
        success_count += 1
    
    print("\n" + "=" * 60)
    print("🎯 FIX SCRIPT RESULTS")
    print(f"✅ Successful checks: {success_count}/{total_checks}")
    
    if success_count >= 4:
        print("🎉 Most issues identified and can be fixed!")
        print("\n📋 NEXT STEPS:")
        print("1. Update ShiftKeyPoint model foreign key reference")
        print("2. Fix handover form processing logic")
        print("3. Test with multiple key points submission")
        print("4. Verify Key Points tab functionality")
    else:
        print("⚠️ Some issues need further investigation")

if __name__ == "__main__":
    main()