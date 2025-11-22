import sys
sys.path.append('/app')
from app import app, db
from models.models import Account, Team

print('TEAM DROPDOWN FIX VERIFICATION')
print('=' * 40)

with app.app_context():
    # Get accounts and their teams
    accounts = Account.query.all()
    print('Accounts and their teams:')
    print('-' * 30)
    
    for account in accounts:
        teams = Team.query.filter_by(account_id=account.id).all()
        print(f'Account: {account.name} (ID: {account.id})')
        for team in teams:
            print(f'  - Team: {team.name} (ID: {team.id})')
        if not teams:
            print('  - No teams found')
        print()
    
    print('Template Verification:')
    print('-' * 20)
    
    # Check if the template file exists and has the fix
    try:
        with open('/app/templates/user_management.html', 'r') as f:
            content = f.read()
            
        # Check for key fix indicators
        fixes_present = []
        
        if 'updateTeamOptions()' in content:
            fixes_present.append(' updateTeamOptions function found')
        else:
            fixes_present.append(' updateTeamOptions function missing')
            
        if 'window.updateEditTeamOptions' in content:
            fixes_present.append(' Global updateEditTeamOptions function found')
        else:
            fixes_present.append(' Global updateEditTeamOptions function missing')
            
        if 'accountSelect.addEventListener' in content:
            fixes_present.append(' Account change event listener found')
        else:
            fixes_present.append(' Account change event listener missing')
            
        if 'data-account=' in content:
            fixes_present.append(' Team data-account attributes found')
        else:
            fixes_present.append(' Team data-account attributes missing')
        
        for fix in fixes_present:
            print(fix)
            
        print()
        if all('' in fix for fix in fixes_present):
            print(' ALL FIXES SUCCESSFULLY DEPLOYED!')
            print('The team dropdown should now update when account is selected.')
        else:
            print(' Some fixes may be missing. Please check the deployment.')
            
    except Exception as e:
        print(f' Error reading template: {e}')

print()
print('Next steps:')
print('1. Open the application in browser')
print('2. Go to User Management')
print('3. Try adding a new user')
print('4. Select an account - team dropdown should update automatically')
print('5. Try editing a user - same behavior should work')
