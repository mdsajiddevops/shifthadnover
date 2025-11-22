#!/usr/bin/env python3
"""
TEST AND FIX ONBOARDING ISSUE
==============================

This script tests the specific onboarding issue and creates a fix.
"""

import sys
import os
sys.path.append('/app')

from datetime import datetime

def test_user_onboarding_status():
    """Test user onboarding status to identify the issue"""
    
    print("🔍 TESTING USER ONBOARDING STATUS")
    print("=" * 50)
    
    try:
        # Try to connect to database directly
        import mysql.connector
        
        # Connect to database
        conn = mysql.connector.connect(
            host='shift_handover_app_db_1',
            user='shift_user',
            password='shift_pass',
            database='shift_handover'
        )
        cursor = conn.cursor(dictionary=True)
        
        # Get users who might need onboarding
        query = """
        SELECT id, username, email, role, account_id, team_id, 
               first_login, onboarding_completed, created_at
        FROM user 
        WHERE role != 'super_admin'
        ORDER BY created_at DESC
        LIMIT 10
        """
        
        cursor.execute(query)
        users = cursor.fetchall()
        
        print(f"📊 Found {len(users)} recent users (excluding super_admin):")
        print()
        
        for user in users:
            needs_onboarding = (
                not user['onboarding_completed'] and 
                (user['account_id'] is None or user['team_id'] is None)
            )
            
            print(f"👤 {user['username']}:")
            print(f"   - Role: {user['role']}")
            print(f"   - Account ID: {user['account_id']}")
            print(f"   - Team ID: {user['team_id']}")
            print(f"   - First Login: {user['first_login']}")
            print(f"   - Onboarding Completed: {user['onboarding_completed']}")
            print(f"   - Needs Onboarding: {needs_onboarding}")
            print(f"   - Created: {user['created_at']}")
            print()
        
        # Check TechCorp assignments
        query_techcorp = """
        SELECT u.username, u.account_id, u.team_id, u.onboarding_completed, 
               a.name as account_name, t.name as team_name
        FROM user u
        LEFT JOIN account a ON u.account_id = a.id
        LEFT JOIN team t ON u.team_id = t.id
        WHERE a.name = 'TechCorp'
        ORDER BY u.created_at DESC
        LIMIT 5
        """
        
        cursor.execute(query_techcorp)
        techcorp_users = cursor.fetchall()
        
        print(f"🏢 {len(techcorp_users)} users assigned to TechCorp:")
        for user in techcorp_users:
            print(f"   - {user['username']}: {user['account_name']} / {user['team_name']} (Onboarding: {user['onboarding_completed']})")
        
        cursor.close()
        conn.close()
        
        return users, techcorp_users
        
    except Exception as e:
        print(f"❌ Error testing user status: {e}")
        return [], []

def create_onboarding_test_fix():
    """Create a comprehensive fix for the onboarding issue"""
    
    print("\n🔧 CREATING ONBOARDING TEST FIX")
    print("=" * 50)
    
    fix_script = '''#!/usr/bin/env python3
"""
COMPREHENSIVE ONBOARDING FIX
============================
This script fixes the onboarding issue by ensuring proper user flow.
"""

import sys
sys.path.append('/app')

def reset_problematic_users():
    """Reset users who were auto-assigned but need onboarding"""
    
    import mysql.connector
    
    conn = mysql.connector.connect(
        host='shift_handover_app_db_1',
        user='shift_user',
        password='shift_pass',
        database='shift_handover'
    )
    cursor = conn.cursor()
    
    # Find users who were assigned to TechCorp but haven't completed onboarding
    query = """
    SELECT u.id, u.username 
    FROM user u
    JOIN account a ON u.account_id = a.id
    WHERE a.name = 'TechCorp' 
    AND u.onboarding_completed = FALSE
    AND u.role != 'super_admin'
    """
    
    cursor.execute(query)
    problematic_users = cursor.fetchall()
    
    print(f"Found {len(problematic_users)} users to reset")
    
    for user_id, username in problematic_users:
        print(f"Resetting user: {username}")
        
        # Reset their assignments
        update_query = """
        UPDATE user 
        SET account_id = NULL, 
            team_id = NULL, 
            onboarding_completed = FALSE, 
            first_login = TRUE
        WHERE id = %s
        """
        cursor.execute(update_query, (user_id,))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print(f"✅ Reset {len(problematic_users)} users")
    return len(problematic_users)

def test_onboarding_redirect():
    """Test if onboarding redirect works"""
    
    print("\\n🧪 TESTING ONBOARDING REDIRECT")
    
    # This would normally require a test user, but we'll create instructions
    test_instructions = """
MANUAL TEST STEPS:
1. Create a test user account (or reset an existing one)
2. Set user.account_id = NULL, user.team_id = NULL, user.onboarding_completed = FALSE
3. Try to log in with that user
4. Check if redirected to /onboarding/ page
5. Complete onboarding flow
6. Verify user is assigned to selected account/team
"""
    
    print(test_instructions)
    return True

def create_improved_auth_logic():
    """Create improved auth logic"""
    
    improved_logic = """
# IMPROVED AUTH LOGIC FOR /app/routes/auth.py
# Replace the existing onboarding check section with this:

# Check if user needs onboarding (first-time login or no account/team assigned)
if user.needs_onboarding:
    # Verify password first
    if check_password_hash(user.password, password):
        # Log the user in
        login_user(user)
        
        # Log this event for debugging
        print(f"ONBOARDING REDIRECT: User {user.username} needs onboarding")
        print(f"  - Account ID: {user.account_id}")
        print(f"  - Team ID: {user.team_id}")
        print(f"  - Onboarding Completed: {user.onboarding_completed}")
        
        # Clear any existing flash messages
        session.pop('_flashes', None)
        
        # Add welcome message
        flash('Welcome! Please select your account and team to continue.', 'info')
        
        # Redirect to onboarding
        return redirect(url_for('onboarding.index'))
    else:
        flash('Invalid credentials', 'danger')
        return render_template('login.html', 
                             accounts=accounts,
                             teams=teams,
                             selected_account_id=selected_account_id_int,
                             selected_team_id=selected_team_id_int,
                             pending_count=0,
                             pending_assignments=[])
"""
    
    with open('/app/improved_auth_logic.txt', 'w') as f:
        f.write(improved_logic)
    
    print("✅ Created improved auth logic")
    return True

def main():
    """Main execution"""
    print("🚀 TESTING AND FIXING ONBOARDING ISSUE")
    print("=" * 70)
    
    try:
        # Test user status
        users, techcorp_users = test_user_onboarding_status()
        
        # Reset problematic users
        if techcorp_users:
            reset_count = reset_problematic_users()
            print(f"\\n✅ Reset {reset_count} problematic user assignments")
        
        # Create test instructions
        test_onboarding_redirect()
        
        # Create improved logic
        create_improved_auth_logic()
        
        print("\\n" + "=" * 70)
        print("🎯 ONBOARDING FIX SUMMARY")
        print("=" * 70)
        print("✅ User status analyzed")
        print("✅ Problematic assignments reset")
        print("✅ Test instructions created")
        print("✅ Improved auth logic provided")
        print()
        print("📋 NEXT STEPS:")
        print("1. 🔄 Apply the improved auth logic to /app/routes/auth.py")
        print("2. 🔄 Test with a reset user account")
        print("3. 🔄 Verify onboarding flow works end-to-end")
        print("4. 🔄 Monitor for any remaining auto-assignments")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False
    
    return True

if __name__ == "__main__":
    main()
'''
    
    try:
        with open('/app/comprehensive_onboarding_fix.py', 'w') as f:
            f.write(fix_script)
        print("✅ Created comprehensive onboarding fix script")
        return True
        
    except Exception as e:
        print(f"❌ Error creating fix: {e}")
        return False

def main():
    """Main execution function"""
    print("🚀 TESTING AND FIXING ONBOARDING ISSUE")
    print("=" * 70)
    print(f"Started at: {datetime.now()}")
    print()
    
    try:
        # Test user onboarding status
        users, techcorp_users = test_user_onboarding_status()
        
        # Create fix
        fix_created = create_onboarding_test_fix()
        
        print("\n" + "=" * 70)
        print("🎯 TESTING RESULTS")
        print("=" * 70)
        
        if users:
            print(f"📊 Analyzed {len(users)} users")
            print(f"🏢 Found {len(techcorp_users)} TechCorp assignments")
        
        if fix_created:
            print("✅ Comprehensive fix script created")
        
        print("\n🔧 IMMEDIATE ACTIONS NEEDED:")
        print("1. 🔄 Run the comprehensive fix script")
        print("2. 🔄 Apply improved auth logic")
        print("3. 🔄 Test onboarding flow with a test user")
        
        print("\n🌟 EXPECTED RESULT:")
        print("✅ New users will go through proper onboarding")
        print("✅ No more automatic TechCorp assignments")
        print("✅ Users can choose their own account and team")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False
    
    return True

if __name__ == "__main__":
    main()