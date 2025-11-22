import sys
sys.path.append('/app')
from app import app, db
from models.models import Account, User

with app.app_context():
    accounts = Account.query.all()
    print('Found', len(accounts), 'accounts:')
    for acc in accounts:
        print('ID:', acc.id, 'Name:', acc.name)
    
    print('')
    print('Recent users:')
    users = User.query.order_by(User.created_at.desc()).limit(10).all()
    for user in users:
        print('User:', user.username, 'Account ID:', user.account_id, 'Team ID:', user.team_id, 'Onboarding:', user.onboarding_completed)
