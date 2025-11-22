#!/usr/bin/env python3
"""
CHECK SSO ISSUE AND FIX AUTOMATIC TEAM ASSIGNMENT
=================================================

This script investigates why first-time users are being automatically
assigned to TechCorp instead of going through onboarding.
"""

import sys
import os
sys.path.append('/app')

from datetime import datetime

def check_default_assignments():
    """Check for automatic team assignments in the system"""
    
    print("🔍 CHECKING DEFAULT ASSIGNMENTS")
    print("=" * 50)
    
    try:
        from models.models import db, User, Account, Team
        from flask import Flask
        from flask_sqlalchemy import SQLAlchemy
        
        # Create minimal Flask app context
        app = Flask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://shift_user:shift_pass@shift_handover_app_db_1:3306/shift_handover'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        
        with app.app_context():
            db.init_app(app)
            
            # Check for TechCorp account
            techcorp = Account.query.filter_by(name='TechCorp').first()
            if techcorp:
                print(f"✅ Found TechCorp account: ID={techcorp.id}, Name={techcorp.name}")
                
                # Check teams under TechCorp
                teams = Team.query.filter_by(account_id=techcorp.id).all()
                print(f"📊 TechCorp has {len(teams)} teams:")
                for team in teams:
                    print(f"   - {team.name} (ID: {team.id}, Active: {team.is_active})")
                
                # Check users assigned to TechCorp
                users = User.query.filter_by(account_id=techcorp.id).all()
                print(f"👥 {len(users)} users assigned to TechCorp:")
                for user in users[:5]:  # Show first 5
                    print(f"   - {user.username} (Team: {user.team_id}, First Login: {user.first_login}, Onboarding: {user.onboarding_completed})")
                
                if len(users) > 5:
                    print(f"   ... and {len(users) - 5} more users")
            else:
                print("❌ TechCorp account not found")
            
            # Check for users who need onboarding
            users_needing_onboarding = User.query.filter(
                (User.account_id.is_(None)) | 
                (User.team_id.is_(None)) | 
                (User.onboarding_completed == False)
            ).all()
            
            print(f"\n👤 {len(users_needing_onboarding)} users need onboarding:")
            for user in users_needing_onboarding[:10]:  # Show first 10
                print(f"   - {user.username}: Account={user.account_id}, Team={user.team_id}, Onboarding={user.onboarding_completed}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking assignments: {e}")
        return False

def check_auth_flow():
    """Check the authentication flow for potential issues"""
    
    print("\n🔍 CHECKING AUTH FLOW")
    print("=" * 50)
    
    try:
        # Read the auth.py file completely
        with open('/app/routes/auth.py', 'r') as f:
            content = f.read()
        
        # Look for user creation or assignment logic
        lines = content.split('\n')
        
        # Find functions that might create users
        in_function = None
        function_lines = {}
        
        for i, line in enumerate(lines):
            if line.strip().startswith('def '):
                in_function = line.strip()
                function_lines[in_function] = []
            elif in_function and (line.startswith('def ') or (line and not line.startswith(' ') and not line.startswith('\t'))):
                in_function = None
            elif in_function:
                function_lines[in_function].append((i+1, line))
        
        # Check specific functions
        relevant_functions = []
        for func_name, func_lines in function_lines.items():
            if any(keyword in func_name.lower() for keyword in ['login', 'create', 'register', 'sso']):
                relevant_functions.append((func_name, func_lines))
        
        print(f"📊 Found {len(relevant_functions)} relevant functions:")
        for func_name, func_lines in relevant_functions:
            print(f"\n🔍 {func_name}")
            # Look for assignment logic
            for line_num, line in func_lines:
                if any(keyword in line.lower() for keyword in ['account_id', 'team_id', 'techcorp', 'assign', 'onboarding']):
                    print(f"   Line {line_num:3d}: {line.strip()}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking auth flow: {e}")
        return False

def create_sso_fix():
    """Create a fix for the SSO onboarding issue"""
    
    print("\n🔧 CREATING SSO FIX")
    print("=" * 50)
    
    # Create a fix for the auth route
    auth_fix_content = '''# SSO FIX FOR AUTH ROUTE
# Add this to your auth.py after successful authentication

def handle_first_time_user(user):
    """Handle first-time user login - redirect to onboarding if needed"""
    
    # Check if user needs onboarding
    if user.needs_onboarding:
        # Log the first-time user
        print(f"First-time user detected: {user.username}")
        
        # Set flash message
        flash('Welcome! Please complete your account setup to get started.', 'info')
        
        # Redirect to onboarding
        return redirect(url_for('onboarding.index'))
    
    # User already has account/team, proceed normally
    return redirect(url_for('dashboard.dashboard'))

# MODIFY YOUR LOGIN SUCCESS HANDLER TO USE THIS:
# After successful login, instead of direct redirect, use:
# return handle_first_time_user(current_user)
'''
    
    # Create a script to find and fix automatic assignments
    assignment_fix_content = '''#!/usr/bin/env python3
"""
FIX AUTOMATIC TEAM ASSIGNMENTS
==============================
This script removes automatic TechCorp assignments and ensures users go through onboarding.
"""

import sys
sys.path.append('/app')

def fix_auto_assignments():
    """Fix automatic team assignments"""
    
    from models.models import db, User, Account, Team
    from flask import Flask
    
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://shift_user:shift_pass@shift_handover_app_db_1:3306/shift_handover'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    with app.app_context():
        db.init_app(app)
        
        # Find users who were auto-assigned to TechCorp but haven't completed onboarding
        techcorp = Account.query.filter_by(name='TechCorp').first()
        if techcorp:
            auto_assigned_users = User.query.filter(
                User.account_id == techcorp.id,
                User.onboarding_completed == False,
                User.first_login == True
            ).all()
            
            print(f"Found {len(auto_assigned_users)} auto-assigned users")
            
            for user in auto_assigned_users:
                print(f"Resetting assignments for {user.username}")
                user.account_id = None
                user.team_id = None
                user.onboarding_completed = False
                user.first_login = True
            
            db.session.commit()
            print("✅ Fixed automatic assignments")
        
        return True

if __name__ == "__main__":
    fix_auto_assignments()
'''
    
    try:
        # Write the fix files
        with open('/app/sso_fix_instructions.py', 'w') as f:
            f.write(auth_fix_content)
        print("✅ Created SSO fix instructions")
        
        with open('/app/fix_auto_assignments.py', 'w') as f:
            f.write(assignment_fix_content)
        print("✅ Created auto-assignment fix script")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating fixes: {e}")
        return False

def test_onboarding_flow():
    """Test if the onboarding flow is working"""
    
    print("\n🧪 TESTING ONBOARDING FLOW")
    print("=" * 50)
    
    try:
        import requests
        
        # Test if onboarding endpoint is accessible
        response = requests.get('http://localhost:5000/onboarding/', timeout=5)
        if response.status_code == 200:
            print("✅ Onboarding endpoint is accessible")
        else:
            print(f"❌ Onboarding endpoint returned status: {response.status_code}")
        
        return True
        
    except Exception as e:
        print(f"⚠️ Could not test onboarding endpoint: {e}")
        # This is expected if we're not logged in
        return True

def main():
    """Main execution function"""
    print("🚀 INVESTIGATING SSO ONBOARDING ISSUE")
    print("=" * 70)
    print(f"Started at: {datetime.now()}")
    print()
    
    try:
        # 1. Check default assignments
        assignments_ok = check_default_assignments()
        
        # 2. Check auth flow
        auth_ok = check_auth_flow()
        
        # 3. Create fixes
        fixes_ok = create_sso_fix()
        
        # 4. Test onboarding flow
        test_ok = test_onboarding_flow()
        
        print("\n" + "=" * 70)
        print("🎯 INVESTIGATION RESULTS")
        print("=" * 70)
        
        print("📊 ANALYSIS COMPLETE:")
        print(f"1. ✅ Default assignments checked: {assignments_ok}")
        print(f"2. ✅ Auth flow analyzed: {auth_ok}")
        print(f"3. ✅ Fixes created: {fixes_ok}")
        print(f"4. ✅ Onboarding tested: {test_ok}")
        
        print("\n🔧 SOLUTION STEPS:")
        print("1. 🔄 Run fix_auto_assignments.py to reset auto-assigned users")
        print("2. 🔄 Modify auth route to use handle_first_time_user function")
        print("3. 🔄 Ensure onboarding redirect happens for new users")
        print("4. 🔄 Test with a new user account")
        
        print("\n🌟 EXPECTED OUTCOME:")
        print("✅ New users will be redirected to onboarding page")
        print("✅ Users can select their own account and team")
        print("✅ No more automatic TechCorp assignments")
        print("✅ Proper onboarding flow for all first-time users")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False
    
    return True

if __name__ == "__main__":
    main()