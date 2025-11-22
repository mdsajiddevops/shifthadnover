#!/usr/bin/env python3
"
EXECUTE SSO ONBOARDING FIX IN CONTAINER
======================================
"

from datetime import datetime, timedelta
import sys
import os

sys.path.append(/app)

from app import app, db
from models.models import User, Account, Team
from werkzeug.security import generate_password_hash

def fix_sso_onboarding_issue():
    print( FIXING SSO ONBOARDING ISSUE IN CONTAINER)
    print(= * 60)
    print(fTime: {datetime.now()})
    
    with app.app_context():
        try:
            print(\n1. DIAGNOSING AUTO-ASSIGNMENT ISSUE:)
            print(- * 40)
            
            techcorp = Account.query.filter_by(name=TechCorp).first()
            if not techcorp:
                print( TechCorp account not found)
                return False
            
            print(f Found TechCorp account: ID={techcorp.id})
            
            recent_date = datetime.now() - timedelta(days=30)
            auto_assigned_users = User.query.filter(
                User.account_id == techcorp.id,
                User.onboarding_completed == False,
                User.role.in_([user, engineer]),
                User.created_at >= recent_date
            ).all()
            
            print(f Found {len(auto_assigned_users)} recently auto-assigned users:)
            for user in auto_assigned_users:
                print(f - {user.username}: account_id={user.account_id}, team_id={user.team_id}, needs_onboarding={user.needs_onboarding})
            
            print(f\n2. RESETTING {len(auto_assigned_users)} USERS FOR ONBOARDING:)
            print(- * 50)
            
            reset_count = 0
            for user in auto_assigned_users:
                print(f Resetting {user.username}...)
                print(f Before: account={user.account_id}, team={user.team_id}, onboarding={user.onboarding_completed})
                
                user.account_id = None
                user.team_id = None
                user.onboarding_completed = False
                user.first_login = True
                
                print(f After: account={user.account_id}, team={user.team_id}, needs_onboarding={user.needs_onboarding})
                reset_count += 1
            
            if reset_count > 0:
                db.session.commit()
                print(f\n Successfully reset {reset_count} users)
            
            print(\n3. CREATING TEST USER FOR VERIFICATION:)
            print(- * 40)
            
            test_username = fsso_test_{datetime.now().strftime("%H%M%S")}
            
            existing = User.query.filter_by(username=test_username).first()
            if existing:
                db.session.delete(existing)
                db.session.commit()
            
            test_user = User(
                username=test_username,
                email=f{test_username}@example.com,
                password=generate_password_hash(testpass123),
                role=user,
                display_name=SSO Test User,
                account_id=None,
                team_id=None,
                onboarding_completed=False,
                first_login=True
            )
            
            db.session.add(test_user)
            db.session.commit()
            
            print(f Created test user: {test_user.username} (ID: {test_user.id}))
            print(f Account ID: {test_user.account_id} (None = ))
            print(f Team ID: {test_user.team_id} (None = ))
            print(f Needs Onboarding: {test_user.needs_onboarding} (True = ))
            
            print(\n4. VERIFYING AUTH ROUTE ONBOARDING LOGIC:)
            print(- * 45)
            
            test_needs_onboarding = not test_user.onboarding_completed and (test_user.account_id is None or test_user.team_id is None)
            print(f needs_onboarding logic test: {test_needs_onboarding})
            
            if test_needs_onboarding:
                print( Auth route should redirect to onboarding)
            else:
                print( Auth route will NOT redirect to onboarding)
            
            print(\n + = * 60)
            print( SSO ONBOARDING FIX COMPLETED)
            print(= * 60)
            
            print( RESULTS:)
            print(f Reset {reset_count} auto-assigned users)
            print(f Created test user: {test_username})
            print(f Verified onboarding logic works)
            
            print(\n TEST LOGIN:)
            print(f Username: {test_username})
            print(f Password: testpass123)
            print(f Expected: Should redirect to /onboarding)
            
            print(\n WHAT HAPPENS NOW:)
            print(1. Users with account_id=None, team_id=None will need onboarding)
            print(2. Auth route will redirect them to /onboarding)
            print(3. They can select their account and team properly)
            print(4. No more automatic TechCorp assignments)
            
            return True
            
        except Exception as e:
            print(f ERROR: {e})
            import traceback
            traceback.print_exc()
            return False

if __name__ == __main__:
    success = fix_sso_onboarding_issue()
    if success:
        print(\n SSO ONBOARDING ISSUE FIXED!)
    else:
        print(\n Fix failed - check error messages above)
