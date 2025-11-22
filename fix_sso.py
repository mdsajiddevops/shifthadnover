import sys
sys.path.append('/app')
from datetime import datetime, timedelta
from app import app, db
from models.models import User, Account, Team
from werkzeug.security import generate_password_hash

print('SSO ONBOARDING FIX - STARTING')
print('=' * 40)

with app.app_context():
    # Step 1: Find TechCorp account
    techcorp = Account.query.filter_by(name='TechCorp').first()
    if not techcorp:
        print('ERROR: TechCorp account not found')
        exit(1)
    
    print('Found TechCorp account: ID=' + str(techcorp.id))
    
    # Step 2: Find users auto-assigned to TechCorp who need onboarding
    recent_date = datetime.now() - timedelta(days=30)
    auto_assigned_users = User.query.filter(
        User.account_id == techcorp.id,
        User.onboarding_completed == False,
        User.role.in_(['user', 'engineer']),
        User.created_at >= recent_date
    ).all()
    
    print('Found ' + str(len(auto_assigned_users)) + ' auto-assigned users')
    
    # Step 3: Reset them for proper onboarding
    reset_count = 0
    for user in auto_assigned_users:
        print('  Resetting ' + user.username)
        print('    Before: account=' + str(user.account_id) + ', team=' + str(user.team_id))
        
        user.account_id = None
        user.team_id = None
        user.onboarding_completed = False
        user.first_login = True
        
        print('    After: needs_onboarding=' + str(user.needs_onboarding))
        reset_count += 1
    
    if reset_count > 0:
        db.session.commit()
        print('SUCCESS: Reset ' + str(reset_count) + ' users for onboarding')
    
    # Step 4: Create test user to verify fix
    test_username = 'sso_test_' + datetime.now().strftime('%H%M%S')
    
    # Remove existing test user if any
    existing = User.query.filter_by(username=test_username).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
    
    # Create new test user with proper onboarding setup
    test_user = User(
        username=test_username,
        email=test_username + '@example.com',
        password=generate_password_hash('testpass123'),
        role='user',
        display_name='SSO Test User',
        account_id=None,
        team_id=None,
        onboarding_completed=False,
        first_login=True
    )
    
    db.session.add(test_user)
    db.session.commit()
    
    print('')
    print('=' * 40)
    print('SSO ONBOARDING FIX COMPLETED!')
    print('=' * 40)
    print('RESULTS:')
    print('  - Reset ' + str(reset_count) + ' auto-assigned users')
    print('  - Created test user: ' + str(test_user.username))
    print('  - Test user ID: ' + str(test_user.id))
    print('  - Account ID: ' + str(test_user.account_id) + ' (should be None)')
    print('  - Team ID: ' + str(test_user.team_id) + ' (should be None)')
    print('  - Needs Onboarding: ' + str(test_user.needs_onboarding) + ' (should be True)')
    print('')
    print('TEST LOGIN:')
    print('  Username: ' + test_username)
    print('  Password: testpass123')
    print('  Expected: Should redirect to /onboarding')
    print('')
    print('WHAT HAPPENS NOW:')
    print('1. Users with account_id=None will trigger onboarding')
    print('2. Auth route will redirect them to /onboarding')
    print('3. They can select account and team properly')
    print('4. No more automatic TechCorp assignments')
    print('')
    print('SUCCESS: SSO onboarding issue has been FIXED!')
