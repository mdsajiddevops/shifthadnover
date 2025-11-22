from models.models import EscalationMatrixFile, User, Account, Team, db
from app import app

with app.app_context():
    print('=== ESCALATION MATRIX FILES ===')
    files = EscalationMatrixFile.query.all()
    for f in files:
        print(f'File: {f.filename}, Account ID: {f.account_id}, Team ID: {f.team_id}')
    print(f'Total files: {len(files)}')
    
    print('\n=== SAMPLE REGULAR USERS ===')
    regular_users = User.query.filter_by(role='user').limit(3).all()
    for u in regular_users:
        account = Account.query.get(u.account_id) if u.account_id else None
        team = Team.query.get(u.team_id) if u.team_id else None
        print(f'User: {u.employee_id}, Account ID: {u.account_id} ({account.name if account else " None\}), Team ID: {u.team_id} ({team.name if team else \None\})')
 
 print('\n=== EXCEL FILES ON DISK ===')
 import os
 upload_folder = 'uploads/escalation_matrix'
 if os.path.exists(upload_folder):
 files_on_disk = [f for f in os.listdir(upload_folder) if f.endswith('.xlsx')]
 print(f'Files on disk: {files_on_disk}')
 else:
 print('Upload folder does not exist')
