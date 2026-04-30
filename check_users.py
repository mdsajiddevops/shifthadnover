#!/usr/bin/env python3
from models.models import User, db
from app import app

with app.app_context():
    print("=== USERS BY ACCOUNT ===")
    users = User.query.all()
    for u in users:
        if u.username in ['superadmin', 'techopsuser1', 'techopsuser4', 'sachin_vakhare@epam.com', 'balamanivenkatesh_gangula@epam.com']:
            print(f"  User={u.username}, Account_ID={u.account_id}, Role={u.role}")




