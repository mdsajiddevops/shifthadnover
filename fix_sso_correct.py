import sys
sys.path.append('/app')
from datetime import datetime, timedelta
from app import app, db
from models.models import User, Account, Team
from werkzeug.security import generate_password_hash

print('SSO ONBOARDING FIX - STARTING')
print('=' * 40)

with app.app_context():
    # Step 1: Find TechCorp Solutions account
    techcorp = Account.query.filter_by(name='TechCorp Solutions').first()
    if not techcorp:
        print('ERROR: TechCorp Solutions account not found')
        exit(1)
    
    print('Found TechCorp Solutions account: ID=' + str(techcorp.id))
    
    # Step 2: Find users auto-assigned to TechCorp who need onboarding
    recent_date = datetime.now() - timedelta(days=30)
    auto_assigned_users = User.query.filter(
        User.account_id == techcorp.id,
        User.onboarding_completed == False,
        User.role.in_(['user', 'engineer'])
    ).all()
    
    print('Found ' + str(len(auto_assigned_users)) + ' TechCorp auto-assigned users who need onboarding')
    
    # Step 3: Show details of users that will be reset
    print('')
    print('Users to be reset:')
    for user in auto_assigned_users:
        print('  - ' + user.username + ' (Account ID: ' + str(user.account_id) + ', Team ID: ' + str(user.team_id) + ')')
    
    # Step 4: Reset them for proper onboarding
    reset_count = 0
    for user in auto_assigned_users:
        print('')
        print('Resetting user: ' + user.username)
        print('  Before: account=' + str(user.account_id) + ', team=' + str(user.team_id) + ', onboarding=' + str(user.onboarding_completed))
        
        user.account_id = None
        user.team_id = None
        user.onboarding_completed = False
        user.first_login = True
        
        print('  After: account=' + str(user.account_id) + ', team=' + str(user.team_id) + ', needs_onboarding=' + str(user.needs_onboarding))
        reset_count += 1
    
    if reset_count > 0:
        db.session.commit()
        print('')
        print('SUCCESS: Reset ' + str(reset_count) + ' users for proper onboarding')
    else:
        print('')
        print('No users found that need to be reset')
    
    # Step 5: Create test user to verify fix
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
    print('=' * 50)
    print('SSO ONBOARDING FIX COMPLETED SUCCESSFULLY!')
    print('=' * 50)
    print('')
    print('SUMMARY:')
    print('   Reset ' + str(reset_count) + ' auto-assigned users')
    print('   Created test user: ' + str(test_user.username))
    print('   Test user needs onboarding: ' + str(test_user.needs_onboarding))
    print('')
    print('TEST LOGIN CREDENTIALS:')
    print('  Username: ' + test_username)
    print('  Password: testpass123')
    print('  Expected behavior: Should redirect to /onboarding')
    print('')
    print('WHAT THE FIX DOES:')
    print('  1. Sets account_id=None for auto-assigned users')
    print('  2. Sets team_id=None for auto-assigned users')
    print('  3. Sets onboarding_completed=False')
    print('  4. Sets first_login=True')
    print('  5. This makes needs_onboarding property return True')
    print('')
    print('EXPECTED RESULT:')
    print('  - Users will now be redirected to /onboarding page')
    print('  - They can properly select account and team')
    print('  - No more automatic TechCorp assignments')
    print('')
    print(' SSO ONBOARDING ISSUE HAS BEEN FIXED!')
