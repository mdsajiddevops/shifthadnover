#!/usr/bin/env python3
from models.handover_enhanced import HandoverIncidentResponseLog
from models.models import User, db
from app import app

with app.app_context():
    print("=== INCIDENT RESPONSE LOGS DETAILS ===")
    logs = HandoverIncidentResponseLog.query.order_by(HandoverIncidentResponseLog.id.desc()).limit(20).all()
    
    # First, let's see what columns exist
    if logs:
        first_log = logs[0]
        print(f"Columns: {[c.name for c in first_log.__table__.columns]}")
    
    for log in logs:
        print(f"ID={log.id}, Incident={log.incident_number}, "
              f"Account_ID={log.account_id}, Team_ID={log.team_id}")
    
    print("\n=== SUMMARY BY ACCOUNT ===")
    from sqlalchemy import func
    account_counts = db.session.query(
        HandoverIncidentResponseLog.account_id, 
        func.count(HandoverIncidentResponseLog.id)
    ).group_by(HandoverIncidentResponseLog.account_id).all()
    
    for acc_id, count in account_counts:
        print(f"Account {acc_id}: {count} logs")
