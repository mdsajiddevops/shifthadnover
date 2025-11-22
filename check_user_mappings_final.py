#!/usr/bin/env python3
"""
Check current user mappings and recent handover data
"""

import sys
sys.path.append('/app')

from app import app, db
from models.models import User, Shift, TeamMember
from models.handover_enhanced import HandoverNotification, HandoverRequest

def check_user_mappings():
    """Check current user mappings for Operations Team"""
    with app.app_context():
        print("=== CURRENT USER MAPPINGS FOR OPERATIONS TEAM (team_id=2) ===")
        
        # Check users in Operations Team
        users = User.query.filter_by(team_id=2).all()
        print(f"\nFound {len(users)} users in Operations Team:")
        
        for user in users:
            print(f"  ID: {user.id}, Username: {user.username}, Email: {user.email}")
        
        print("\n=== RECENT HANDOVER DATA (OLD SHIFT MODEL) ===")
        
        # Check recent shift (should be shift_id=27 based on logs)
        recent_shift = Shift.query.filter_by(id=27).first()
        if recent_shift:
            print(f"\nShift ID 27 Details (Old Model):")
            print(f"  Date: {recent_shift.date}")
            print(f"  Current Shift: {recent_shift.current_shift_type}")
            print(f"  Next Shift: {recent_shift.next_shift_type}")
            print(f"  Status: {recent_shift.status}")
            print(f"  Current Engineers: {len(recent_shift.current_engineers) if recent_shift.current_engineers else 0}")
            print(f"  Next Engineers: {len(recent_shift.next_engineers) if recent_shift.next_engineers else 0}")
            
            # Get engineer details
            if recent_shift.current_engineers:
                print(f"  Current Engineers:")
                for eng in recent_shift.current_engineers:
                    user = User.query.get(eng.user_id) if hasattr(eng, 'user_id') else None
                    print(f"    - {user.username if user else 'Unknown'}")
            
            if recent_shift.next_engineers:
                print(f"  Next Engineers:")
                for eng in recent_shift.next_engineers:
                    user = User.query.get(eng.user_id) if hasattr(eng, 'user_id') else None
                    print(f"    - {user.username if user else 'Unknown'}")
        else:
            print("No shift found with ID 27")
        
        print("\n=== RECENT HANDOVER REQUEST DATA (NEW MODEL) ===")
        
        # Check recent handover request
        recent_handover = HandoverRequest.query.order_by(HandoverRequest.created_at.desc()).first()
        if recent_handover:
            print(f"\nRecent HandoverRequest ID {recent_handover.id} Details:")
            print(f"  Date: {recent_handover.shift_date}")
            print(f"  Current Shift: {recent_handover.current_shift_type}")
            print(f"  Next Shift: {recent_handover.next_shift_type}")
            print(f"  Status: {recent_handover.status}")
            print(f"  Created by ID: {recent_handover.created_by_id}")
            
            # Get user details
            creator = User.query.get(recent_handover.created_by_id)
            print(f"  Created by: {creator.username if creator else 'Unknown'}")
        else:
            print("No handover requests found")
        
        print("\n=== HANDOVER NOTIFICATIONS ===")
        notifications = HandoverNotification.query.filter_by(shift_id=27).all()
        print(f"Found {len(notifications)} notifications for shift 27:")
        
        for notif in notifications:
            user = User.query.get(notif.user_id)
            print(f"  User: {user.username if user else 'Unknown'} (ID: {notif.user_id})")
            print(f"  Read: {notif.is_read}")
            print(f"  Created: {notif.created_at}")
            print(f"  ---")
        
        # Also check for recent notifications not tied to shift 27
        print("\n=== ALL RECENT NOTIFICATIONS ===")
        recent_notifications = HandoverNotification.query.order_by(HandoverNotification.created_at.desc()).limit(10).all()
        print(f"Found {len(recent_notifications)} recent notifications:")
        
        for notif in recent_notifications:
            user = User.query.get(notif.user_id)
            print(f"  User: {user.username if user else 'Unknown'} (ID: {notif.user_id})")
            print(f"  Shift ID: {notif.shift_id}")
            print(f"  Read: {notif.is_read}")
            print(f"  Created: {notif.created_at}")
            print(f"  ---")
        
        print("\n=== SEARCH FOR TEST USERS ===")
        test_users = User.query.filter(User.username.like('%test%')).all()
        print(f"Found {len(test_users)} users with 'test' in username:")
        for user in test_users:
            print(f"  ID: {user.id}, Username: {user.username}, Team: {user.team_id}")

if __name__ == "__main__":
    check_user_mappings()