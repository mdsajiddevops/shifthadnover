#!/usr/bin/env python3
from models.models import Team, db
from app import app

with app.app_context():
    print("=== ALL TEAMS ===")
    teams = Team.query.all()
    for t in teams:
        print(f"  ID={t.id}, Name={t.name}, Account_ID={t.account_id}")




