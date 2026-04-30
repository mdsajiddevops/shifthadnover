#!/usr/bin/env python3
from models.vendor_detail import VendorDetail
from models.models import db
from app import app

with app.app_context():
    print("=== VENDORS BY ACCOUNT ===")
    vendors = VendorDetail.query.filter_by(is_active=True).all()
    
    for acc_id in [1, 3]:
        print(f"\nAccount {acc_id}:")
        acc_vendors = [v for v in vendors if v.account_id == acc_id]
        print(f"  Count: {len(acc_vendors)}")
        apps = set([v.application for v in acc_vendors if v.application])
        print(f"  Applications: {list(apps)[:10]}...")  # First 10




