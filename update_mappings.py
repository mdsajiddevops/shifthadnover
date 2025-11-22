from models.models import EscalationMatrixFile, Account, Team, db
from app import app
import datetime

with app.app_context():
    # Get some sample accounts and teams
    accounts = Account.query.limit(4).all()
    teams = Team.query.limit(4).all()
    
    print('Available accounts:')
    for i, acc in enumerate(accounts):
        print(f'  {i+1}. {acc.name} (ID: {acc.id})')
    
    print('Available teams:')
    for i, team in enumerate(teams):
        print(f'  {i+1}. {team.name} (ID: {team.id})')
    
    # Update the escalation matrix files with some mappings
    files = EscalationMatrixFile.query.all()
    
    for i, f in enumerate(files):
        if i < len(accounts) and i < len(teams):
            f.account_id = accounts[i].id  
            f.team_id = teams[i].id
            f.upload_time = datetime.datetime.now()
            print(f'Updated {f.filename} -> Account: {accounts[i].name}, Team: {teams[i].name}')
    
    db.session.commit()
    print('Database updated!')
