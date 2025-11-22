import os
import datetime
from models.models import EscalationMatrixFile, Account, Team, db
from app import app

def populate_escalation_matrix_files():
    with app.app_context():
        # Get accounts and teams
        accounts = {a.name.lower(): a.id for a in Account.query.all()}
        teams = {t.name.lower(): t.id for t in Team.query.all()}
        
        print('Available accounts:', list(accounts.keys()))
        print('Available teams:', list(teams.keys()))
        
        upload_folder = 'uploads/escalation_matrix'
        xlsx_files = [f for f in os.listdir(upload_folder) if f.endswith('.xlsx')]
        
        for filename in xlsx_files:
            print(f'Processing: {filename}')
            
            # Extract account and team from filename
            # Expected format: 'acme_corp_team_a escalation.xlsx'
            name_part = filename.replace(' escalation.xlsx', '').replace('_escalation.xlsx', '')
            
            account_id = None
            team_id = None
            
            # Try to match account and team
            for acc_name, acc_id in accounts.items():
                if acc_name in name_part.lower():
                    account_id = acc_id
                    break
            
            for team_name, t_id in teams.items():
                if team_name in name_part.lower():
                    team_id = t_id
                    break
            
            # If we couldn't match, try some fallbacks
            if not account_id:
                if 'acme' in name_part.lower():
                    account_id = accounts.get('acme corp', accounts.get('acme', None))
                elif 'beta' in name_part.lower():  
                    account_id = accounts.get('beta inc', accounts.get('beta', None))
            
            if not team_id:
                if 'team_a' in name_part.lower() or 'teama' in name_part.lower():
                    team_id = teams.get('team a', teams.get('team_a', None))
                elif 'team_b' in name_part.lower() or 'teamb' in name_part.lower():
                    team_id = teams.get('team b', teams.get('team_b', None))
            
            print(f'  Account ID: {account_id}, Team ID: {team_id}')
            
            # Check if record already exists
            existing = EscalationMatrixFile.query.filter_by(filename=filename).first()
            
            if existing:
                existing.account_id = account_id
                existing.team_id = team_id
                existing.upload_time = datetime.datetime.now()
                print(f'  Updated existing record')
            else:
                matrix_file = EscalationMatrixFile(
                    filename=filename,
                    account_id=account_id,
                    team_id=team_id,
                    upload_time=datetime.datetime.now()
                )
                db.session.add(matrix_file)
                print(f'  Added new record')
        
        db.session.commit()
        print('Database updated successfully!')

if __name__ == '__main__':
    populate_escalation_matrix_files()
