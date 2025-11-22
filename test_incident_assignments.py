#!/usr/bin/env python3
"""
Test script to verify incident assignment creation in production
Run this on production server to test the incident notification system
"""

import sys
import os
from datetime import datetime

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_incident_assignment_creation():
    """Test creating incident assignments and notifications"""
    try:
        from app import create_app
        from models.models import db, User, TeamMember
        from models.handover_enhanced import IncidentAssignment, HandoverIncidentResponseLog
        from routes.handover import create_enhanced_incident_assignment
        
        app = create_app()
        
        with app.app_context():
            print("🧪 TESTING INCIDENT ASSIGNMENT CREATION 🧪")
            print("=" * 50)
            
            # 1. Find a test user
            print("\n1. Finding test user...")
            test_users = User.query.filter(
                User.role.in_(['user', 'team_admin']),
                User.email.isnot(None),
                User.email != ''
            ).limit(3).all()
            
            if not test_users:
                print("❌ No suitable test users found")
                print("   Users need: role='user' or 'team_admin' AND email is not empty")
                return
            
            test_user = test_users[0]
            print(f"✅ Using test user: {test_user.username} (ID: {test_user.id})")
            print(f"   Email: {test_user.email}")
            print(f"   Role: {test_user.role}")
            print(f"   Account: {test_user.account_id}, Team: {test_user.team_id}")
            
            # 2. Count existing assignments before test
            print("\n2. Checking existing data...")
            before_assignments = IncidentAssignment.query.count()
            before_logs = HandoverIncidentResponseLog.query.count()
            user_assignments_before = IncidentAssignment.query.filter_by(assigned_to_id=test_user.id).count()
            
            print(f"   Total assignments before: {before_assignments}")
            print(f"   Total logs before: {before_logs}")
            print(f"   User assignments before: {user_assignments_before}")
            
            # 3. Create test incident assignment
            print("\n3. Creating test incident assignment...")
            test_incident_title = f"TEST-{datetime.now().strftime('%Y%m%d-%H%M%S')} - Production Test"
            
            try:
                success = create_enhanced_incident_assignment(
                    incident_title=test_incident_title,
                    incident_description="This is a test incident to verify the notification system works in production",
                    incident_priority="High",
                    assigned_to_name=test_user.username,
                    account_id=test_user.account_id or 1,  # Use 1 as fallback
                    team_id=test_user.team_id or 1,        # Use 1 as fallback
                    handover_context=f"Production test created at {datetime.now()}",
                    handover_request_id=None
                )
                
                if success:
                    print("✅ Test incident assignment created successfully")
                else:
                    print("❌ Test incident assignment creation failed")
                    return
                    
            except Exception as e:
                print(f"❌ Error creating test assignment: {str(e)}")
                import traceback
                traceback.print_exc()
                return
            
            # 4. Verify assignment was created
            print("\n4. Verifying assignment creation...")
            after_assignments = IncidentAssignment.query.count()
            after_logs = HandoverIncidentResponseLog.query.count()
            user_assignments_after = IncidentAssignment.query.filter_by(assigned_to_id=test_user.id).count()
            
            print(f"   Total assignments after: {after_assignments} (diff: +{after_assignments - before_assignments})")
            print(f"   Total logs after: {after_logs} (diff: +{after_logs - before_logs})")
            print(f"   User assignments after: {user_assignments_after} (diff: +{user_assignments_after - user_assignments_before})")
            
            # 5. Find the specific assignment we created
            test_assignment = IncidentAssignment.query.filter_by(
                incident_title=test_incident_title
            ).first()
            
            if test_assignment:
                print(f"✅ Found test assignment:")
                print(f"   ID: {test_assignment.id}")
                print(f"   Title: {test_assignment.incident_title}")
                print(f"   Assigned to: {test_assignment.assigned_to_id} ({test_user.username})")
                print(f"   Status: {test_assignment.assignment_status}")
                print(f"   Priority: {test_assignment.incident_priority}")
                
                # 6. Check if response log was created
                test_log = HandoverIncidentResponseLog.query.filter_by(
                    incident_assignment_id=test_assignment.id
                ).first()
                
                if test_log:
                    print(f"✅ Found test response log:")
                    print(f"   ID: {test_log.id}")
                    print(f"   Assignment Status: {test_log.assignment_status}")
                    print(f"   Response Status: {test_log.response_status}")
                    print(f"   Assigned to: {test_log.accepted_by_id} ({test_log.accepted_by_name})")
                else:
                    print("❌ Response log not created")
                
                # 7. Test notification retrieval
                print("\n5. Testing notification retrieval...")
                user_notifications = IncidentAssignment.query.filter_by(
                    assigned_to_id=test_user.id
                ).order_by(IncidentAssignment.assigned_at.desc()).all()
                
                print(f"   User has {len(user_notifications)} total assignments")
                pending_count = len([a for a in user_notifications if a.assignment_status == 'pending'])
                print(f"   User has {pending_count} pending assignments")
                
                if test_incident_title in [a.incident_title for a in user_notifications]:
                    print("✅ Test assignment appears in user notifications")
                else:
                    print("❌ Test assignment does NOT appear in user notifications")
                
                # 8. Cleanup test data
                print("\n6. Cleaning up test data...")
                try:
                    if test_log:
                        db.session.delete(test_log)
                    db.session.delete(test_assignment)
                    db.session.commit()
                    print("✅ Test data cleaned up successfully")
                except Exception as e:
                    print(f"⚠️  Warning: Could not clean up test data: {str(e)}")
                    db.session.rollback()
                    
            else:
                print("❌ Test assignment not found in database")
            
            print(f"\n🎯 TEST COMPLETED at {datetime.now()}")
            print("\nIf test passed, the notification system should work.")
            print("If test failed, check the error messages above.")
            
    except Exception as e:
        print(f"❌ Fatal error in test: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_incident_assignment_creation()
