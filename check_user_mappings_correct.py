#!/usr/bin/env python3
"""
Check current user mappings and recent handover data
"""

import sys
sys.path.append('/app')

from app import app, db
from models.models import User, Shift
from models.handover_enhanced import HandoverNotification

def check_user_mappings():
    """Check current user mappings for Operations Team"""
    with app.app_context():
        print("=== CURRENT USER MAPPINGS FOR OPERATIONS TEAM (team_id=2) ===")
        
        # Check users in Operations Team
        users = User.query.filter_by(team_id=2).all()
        print(f"\nFound {len(users)} users in Operations Team:")
        
        for user in users:
            print(f"  ID: {user.id}, Username: {user.username}, Email: {user.email}")
        
        print("\n=== RECENT HANDOVER DATA ===")
        
        # Check recent shift (should be shift_id=27 based on logs)
        recent_shift = Shift.query.filter_by(id=27).first()
        if recent_shift:
            print(f"\nShift ID 27 Details:")
            print(f"  From User ID: {recent_shift.from_user_id}")
            print(f"  To User IDs: {recent_shift.to_user_ids}")
            print(f"  Date: {recent_shift.date}")
            print(f"  From Shift: {recent_shift.from_shift}")
            print(f"  To Shift: {recent_shift.to_shift}")
            
            # Get user details
            from_user = User.query.get(recent_shift.from_user_id)
            print(f"  From User: {from_user.username if from_user else 'Unknown'}")
            
            if recent_shift.to_user_ids:
                to_user_ids = recent_shift.to_user_ids.split(',')
                print(f"  To Users:")
                for user_id in to_user_ids:
                    to_user = User.query.get(int(user_id.strip()))
                    print(f"    - {to_user.username if to_user else 'Unknown'} (ID: {user_id.strip()})")
        else:
            print("No shift found with ID 27")
        
        print("\n=== HANDOVER NOTIFICATIONS ===")
        notifications = HandoverNotification.query.filter_by(shift_id=27).all()
        print(f"Found {len(notifications)} notifications for shift 27:")
        
        for notif in notifications:
            user = User.query.get(notif.user_id)
            print(f"  User: {user.username if user else 'Unknown'} (ID: {notif.user_id})")
            print(f"  Read: {notif.is_read}")
            print(f"  Created: {notif.created_at}")
            print(f"  ---")
        
        print("\n=== ALL USERS FOR REFERENCE ===")
        all_users = User.query.all()
        for user in all_users:
            print(f"  ID: {user.id}, Username: {user.username}, Team: {user.team_id}")

if __name__ == "__main__":
    check_user_mappings()