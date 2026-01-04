#!/usr/bin/env python3
from models.vendor_detail import VendorDetail
from models.handover_enhanced import HandoverIncidentResponseLog
from models.models import db
from app import app

with app.app_context():
    # Check vendors
    vendors = VendorDetail.query.filter_by(is_active=True).all()
    print(f"=== VENDORS ===")
    print(f"Total active vendors: {len(vendors)}")
    null_account = len([v for v in vendors if v.account_id is None])
    print(f"Vendors with NULL account_id: {null_account}")
    
    # Group by account
    by_account = {}
    for v in vendors:
        acc = v.account_id if v.account_id else 'NULL'
        if acc not in by_account:
            by_account[acc] = 0
        by_account[acc] += 1
    print(f"By account_id: {by_account}")
    
    # Check incident logs
    print(f"\n=== INCIDENT RESPONSE LOGS ===")
    logs = HandoverIncidentResponseLog.query.all()
    print(f"Total logs: {len(logs)}")
    null_account_logs = len([l for l in logs if l.account_id is None])
    print(f"Logs with NULL account_id: {null_account_logs}")
    
    # Group by account
    by_account_logs = {}
    for l in logs:
        acc = l.account_id if l.account_id else 'NULL'
        if acc not in by_account_logs:
            by_account_logs[acc] = 0
        by_account_logs[acc] += 1
    print(f"By account_id: {by_account_logs}")
