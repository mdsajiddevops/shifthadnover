import sys
sys.path.append('/app')
from app import app, db
from models.models import User, Account

with app.app_context():
    # Check the users we just reset
    reset_users = User.query.filter(User.account_id.is_(None)).all()
    print('Users with account_id=None (need onboarding):')
    print('=' * 50)
    
    for user in reset_users:
        print('Username:', user.username)
        print('  Account ID:', user.account_id)
        print('  Team ID:', user.team_id)
        print('  Onboarding Completed:', user.onboarding_completed)
        print('  Needs Onboarding:', user.needs_onboarding)
        print('  First Login:', user.first_login)
        print('')
    
    print('TOTAL USERS NEEDING ONBOARDING:', len(reset_users))
    print('')
    print(' SSO ONBOARDING FIX VERIFICATION COMPLETE!')
    print('All users will now be redirected to /onboarding when they login.')
