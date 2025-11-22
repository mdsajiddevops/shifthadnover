#!/usr/bin/env python3
"""
FIX AUTOMATIC TEAM ASSIGNMENTS
==============================
This script removes automatic TechCorp assignments and ensures users go through onboarding.
"""

import sys
sys.path.append('/app')

def fix_auto_assignments():
    """Fix automatic team assignments"""
    
    from models.models import db, User, Account, Team
    from flask import Flask
    
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://shift_user:shift_pass@shift_handover_app_db_1:3306/shift_handover'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    with app.app_context():
        db.init_app(app)
        
        # Find users who were auto-assigned to TechCorp but haven't completed onboarding
        techcorp = Account.query.filter_by(name='TechCorp').first()
        if techcorp:
            auto_assigned_users = User.query.filter(
                User.account_id == techcorp.id,
                User.onboarding_completed == False,
                User.first_login == True
            ).all()
            
            print(f"Found {len(auto_assigned_users)} auto-assigned users")
            
            for user in auto_assigned_users:
                print(f"Resetting assignments for {user.username}")
                user.account_id = None
                user.team_id = None
                user.onboarding_completed = False
                user.first_login = True
            
            db.session.commit()
            print("✅ Fixed automatic assignments")
        
        return True

if __name__ == "__main__":
    fix_auto_assignments()
