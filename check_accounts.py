#!/usr/bin/env python3
from models.models import Account, User, db
from app import app

with app.app_context():
    print("=== ACCOUNTS ===")
    accounts = Account.query.all()
    for a in accounts:
        print(f"  ID={a.id}, Name={a.name}")
    
    print("\n=== ACCOUNT ADMINS ===")
    admins = User.query.filter_by(role='account_admin').all()
    for u in admins:
        print(f"  User={u.username}, Account_ID={u.account_id}")



