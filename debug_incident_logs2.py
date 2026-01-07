#!/usr/bin/env python3
from models.handover_enhanced import HandoverIncidentResponseLog
from models.models import User, db
from app import app

with app.app_context():
    print("=== LOGS WITH CTC USERS (sachin, bala) ===")
    logs = HandoverIncidentResponseLog.query.all()
    
    for log in logs:
        # Check accepted_by_name for these users
        if log.accepted_by_name and ('sachin' in log.accepted_by_name.lower() or 'bala' in log.accepted_by_name.lower()):
            print(f"ID={log.id}, Incident={log.incident_number}, Account_ID={log.account_id}, "
                  f"AcceptedBy={log.accepted_by_name}")
    
    print("\n=== CHECK CURRENT USER (techcorp_admin) ===")
    user = User.query.filter_by(username='techcorp_admin').first()
    if user:
        print(f"Username: {user.username}, Account_ID: {user.account_id}, Role: {user.role}")
    else:
        print("User 'techcorp_admin' not found")
    
    # Also check Admin user
    admin = User.query.filter(User.username.ilike('%admin%')).all()
    print("\n=== ALL ADMIN USERS ===")
    for u in admin:
        print(f"Username: {u.username}, Account_ID: {u.account_id}, Role: {u.role}")



