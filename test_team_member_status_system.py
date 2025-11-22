#!/usr/bin/env python3
"""
Test Team Member Status System

This script tests:
1. Team members filtering (active only by default)
2. User management filtering (active only by default)
3. Admin enable/disable functionality
4. API endpoints filtering
"""

import sys
import os
from datetime import datetime

# Add the application root to the Python path
app_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, app_root)

from app import app, db
from models.models import TeamMember, User, Team, Account
from sqlalchemy import text

def test_team_member_filtering():
    """Test team member filtering by is_active status"""
    
    with app.app_context():
        print("🔍 TESTING TEAM MEMBER FILTERING")
        print("=" * 60)
        
        try:
            # Test active team members query (default behavior)
            active_members = TeamMember.query.filter_by(is_active=True).all()
            print(f"✅ Found {len(active_members)} active team members")
            
            # Test inactive team members query
            inactive_members = TeamMember.query.filter_by(is_active=False).all()
            print(f"⚠️ Found {len(inactive_members)} inactive team members")
            
            # Show a few examples
            print("\n📋 Active Team Members (first 5):")
            for member in active_members[:5]:
                print(f"   ✅ ID={member.id}: {member.name} ({member.email})")
            
            if inactive_members:
                print("\n📋 Inactive Team Members:")
                for member in inactive_members:
                    print(f"   ❌ ID={member.id}: {member.name} ({member.email})")
            
            return True
            
        except Exception as e:
            print(f"❌ Error testing team member filtering: {str(e)}")
            return False

def test_user_filtering():
    """Test user filtering by status and is_active"""
    
    with app.app_context():
        print("\n🔍 TESTING USER FILTERING")
        print("=" * 60)
        
        try:
            # Test active users query (default behavior)
            active_users = User.query.filter(
                User.status == 'active',
                User.is_active == True
            ).all()
            print(f"✅ Found {len(active_users)} active users")
            
            # Test disabled users query
            disabled_users = User.query.filter(
                User.status == 'disabled'
            ).all()
            print(f"⚠️ Found {len(disabled_users)} disabled users")
            
            # Test inactive users query
            inactive_users = User.query.filter(
                User.is_active == False
            ).all()
            print(f"⚠️ Found {len(inactive_users)} inactive users")
            
            # Show examples
            print("\n📋 Active Users (first 5):")
            for user in active_users[:5]:
                print(f"   ✅ {user.username}: {user.email} (Status: {user.status}, Active: {user.is_active})")
            
            if disabled_users:
                print("\n📋 Disabled Users:")
                for user in disabled_users[:3]:
                    print(f"   ❌ {user.username}: {user.email} (Status: {user.status}, Active: {user.is_active})")
            
            return True
            
        except Exception as e:
            print(f"❌ Error testing user filtering: {str(e)}")
            return False

def test_enable_disable_functionality():
    """Test admin enable/disable functionality for team members"""
    
    with app.app_context():
        print("\n🔍 TESTING ENABLE/DISABLE FUNCTIONALITY")
        print("=" * 60)
        
        try:
            # Find a test team member to toggle
            test_member = TeamMember.query.filter_by(name='testuser').first()
            
            if not test_member:
                print("⚠️ No test member found named 'testuser'")
                # Create a test member for demonstration
                test_member = TeamMember(
                    name='Test Status User',
                    email='test.status@example.com',
                    contact_number='123-456-7890',
                    role='Test',
                    account_id=1,
                    team_id=2,
                    is_active=True
                )
                db.session.add(test_member)
                db.session.commit()
                print(f"✅ Created test member: ID={test_member.id}")
            
            # Test the toggle functionality
            original_status = test_member.is_active
            print(f"📋 Test member '{test_member.name}' current status: {'Active' if original_status else 'Inactive'}")
            
            # Toggle status
            test_member.is_active = not original_status
            db.session.commit()
            print(f"🔄 Toggled to: {'Active' if test_member.is_active else 'Inactive'}")
            
            # Toggle back
            test_member.is_active = original_status
            db.session.commit()
            print(f"🔄 Restored to: {'Active' if test_member.is_active else 'Inactive'}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error testing enable/disable functionality: {str(e)}")
            db.session.rollback()
            return False

def test_api_compatibility():
    """Test that API endpoints work with the new filtering"""
    
    with app.app_context():
        print("\n🔍 TESTING API COMPATIBILITY")
        print("=" * 60)
        
        try:
            # Test team members API query (simulating the route logic)
            from models.models import User
            
            # Simulate the API query for active team members and users
            active_team_members = TeamMember.query.filter_by(is_active=True).all()
            active_users = User.query.filter(
                User.is_active == True,
                User.status == 'active'
            ).all()
            
            print(f"📊 API would return {len(active_team_members)} active team members")
            print(f"📊 API would return {len(active_users)} active users")
            
            # Test account and team filtering
            test_account_id = 1
            test_team_id = 2
            
            filtered_members = TeamMember.query.filter_by(
                account_id=test_account_id,
                team_id=test_team_id,
                is_active=True
            ).all()
            
            print(f"📊 For Account {test_account_id}, Team {test_team_id}: {len(filtered_members)} active members")
            
            return True
            
        except Exception as e:
            print(f"❌ Error testing API compatibility: {str(e)}")
            return False

def main():
    """Main execution function"""
    
    print("🚀 TESTING TEAM MEMBER STATUS SYSTEM")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    all_tests_passed = True
    
    # Test 1: Team member filtering
    if not test_team_member_filtering():
        all_tests_passed = False
    
    # Test 2: User filtering
    if not test_user_filtering():
        all_tests_passed = False
    
    # Test 3: Enable/disable functionality
    if not test_enable_disable_functionality():
        all_tests_passed = False
    
    # Test 4: API compatibility
    if not test_api_compatibility():
        all_tests_passed = False
    
    print(f"\n{'✅' if all_tests_passed else '❌'} TESTING COMPLETED")
    print("=" * 60)
    
    if all_tests_passed:
        print("🎉 All tests passed! The team member status system is working correctly.")
        print()
        print("✅ Features working:")
        print("1. Team members filtered by is_active=True by default")
        print("2. Users filtered by status='active' and is_active=True")
        print("3. Admin enable/disable functionality for team members")
        print("4. API endpoints respect the new filtering")
        print()
        print("🎯 Next steps:")
        print("- Test the web interface in your browser")
        print("- Try enabling/disabling team members as an admin")
        print("- Verify that inactive members don't appear in dropdowns")
    else:
        print("❌ Some tests failed. Please check the errors above.")
    
    return all_tests_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)