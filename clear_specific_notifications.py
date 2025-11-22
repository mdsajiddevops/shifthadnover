#!/usr/bin/env python3
"""
Clear Specific Notifications Script
==================================
This script allows you to clear specific types of notifications or notifications for specific users.
"""

import os
import sys
from datetime import datetime, timedelta

# Add the application directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from models.handover_enhanced import HandoverNotification
from models.user import User

def clear_incident_notifications():
    """Clear only incident-related notifications"""
    
    app = create_app()
    with app.app_context():
        try:
            print("🧹 CLEARING INCIDENT NOTIFICATIONS")
            print("=" * 50)
            
            # Find incident notifications
            incident_notifications = HandoverNotification.query.filter(
                HandoverNotification.notification_type.in_([
                    'incident_accepted',
                    'incident_rejected', 
                    'incident_assignment',
                    'incident_updated'
                ])
            ).all()
            
            print(f"📊 Found {len(incident_notifications)} incident notifications")
            
            if len(incident_notifications) == 0:
                print("✅ No incident notifications to clear!")
                return
            
            # Show details
            for notif in incident_notifications[:10]:  # Show first 10
                print(f"   • {notif.notification_type}: {notif.title}")
                print(f"     Created: {notif.created_at}")
                print(f"     Read: {'Yes' if notif.is_read else 'No'}")
                print()
            
            if len(incident_notifications) > 10:
                print(f"   ... and {len(incident_notifications) - 10} more")
            
            # Confirm deletion
            confirm = input(f"Delete all {len(incident_notifications)} incident notifications? (y/N): ")
            
            if confirm.lower() not in ['y', 'yes']:
                print("❌ Operation cancelled.")
                return
            
            # Delete incident notifications
            deleted_count = HandoverNotification.query.filter(
                HandoverNotification.notification_type.in_([
                    'incident_accepted',
                    'incident_rejected', 
                    'incident_assignment',
                    'incident_updated'
                ])
            ).delete(synchronize_session=False)
            
            db.session.commit()
            
            print(f"✅ Successfully deleted {deleted_count} incident notifications!")
                
        except Exception as e:
            print(f"❌ Error clearing notifications: {str(e)}")
            db.session.rollback()
            raise

def clear_old_notifications(days=30):
    """Clear notifications older than specified days"""
    
    app = create_app()
    with app.app_context():
        try:
            print(f"🧹 CLEARING NOTIFICATIONS OLDER THAN {days} DAYS")
            print("=" * 50)
            
            # Calculate cutoff date
            cutoff_date = datetime.now() - timedelta(days=days)
            print(f"📅 Cutoff date: {cutoff_date.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Find old notifications
            old_notifications = HandoverNotification.query.filter(
                HandoverNotification.created_at < cutoff_date
            ).all()
            
            print(f"📊 Found {len(old_notifications)} old notifications")
            
            if len(old_notifications) == 0:
                print("✅ No old notifications to clear!")
                return
            
            # Show breakdown by type
            print("\n📋 Old notifications by type:")
            from collections import Counter
            type_count = Counter(notif.notification_type for notif in old_notifications)
            
            for notif_type, count in type_count.items():
                print(f"   • {notif_type}: {count}")
            
            # Confirm deletion
            confirm = input(f"Delete all {len(old_notifications)} old notifications? (y/N): ")
            
            if confirm.lower() not in ['y', 'yes']:
                print("❌ Operation cancelled.")
                return
            
            # Delete old notifications
            deleted_count = HandoverNotification.query.filter(
                HandoverNotification.created_at < cutoff_date
            ).delete(synchronize_session=False)
            
            db.session.commit()
            
            print(f"✅ Successfully deleted {deleted_count} old notifications!")
                
        except Exception as e:
            print(f"❌ Error clearing notifications: {str(e)}")
            db.session.rollback()
            raise

def clear_user_notifications(username):
    """Clear notifications for a specific user"""
    
    app = create_app()
    with app.app_context():
        try:
            print(f"🧹 CLEARING NOTIFICATIONS FOR USER: {username}")
            print("=" * 50)
            
            # Find user
            user = User.query.filter_by(username=username).first()
            if not user:
                print(f"❌ User '{username}' not found!")
                return
            
            # Find user's notifications
            user_notifications = HandoverNotification.query.filter_by(
                user_id=user.id
            ).all()
            
            print(f"📊 Found {len(user_notifications)} notifications for user '{username}'")
            
            if len(user_notifications) == 0:
                print("✅ No notifications to clear for this user!")
                return
            
            # Show details
            for notif in user_notifications[:10]:  # Show first 10
                print(f"   • {notif.notification_type}: {notif.title}")
                print(f"     Created: {notif.created_at}")
                print(f"     Read: {'Yes' if notif.is_read else 'No'}")
                print()
            
            if len(user_notifications) > 10:
                print(f"   ... and {len(user_notifications) - 10} more")
            
            # Confirm deletion
            confirm = input(f"Delete all {len(user_notifications)} notifications for user '{username}'? (y/N): ")
            
            if confirm.lower() not in ['y', 'yes']:
                print("❌ Operation cancelled.")
                return
            
            # Delete user notifications
            deleted_count = HandoverNotification.query.filter_by(
                user_id=user.id
            ).delete()
            
            db.session.commit()
            
            print(f"✅ Successfully deleted {deleted_count} notifications for user '{username}'!")
                
        except Exception as e:
            print(f"❌ Error clearing notifications: {str(e)}")
            db.session.rollback()
            raise

def main():
    """Main menu for notification cleanup"""
    
    print("🧹 NOTIFICATION CLEANUP UTILITY")
    print("=" * 40)
    print("1. Clear ALL notifications")
    print("2. Clear incident notifications only")
    print("3. Clear old notifications (30+ days)")
    print("4. Clear notifications for specific user")
    print("5. Exit")
    
    choice = input("\nSelect option (1-5): ").strip()
    
    if choice == '1':
        from clear_dashboard_notifications import clear_notifications
        clear_notifications()
    elif choice == '2':
        clear_incident_notifications()
    elif choice == '3':
        days = input("Enter number of days (default 30): ").strip()
        days = int(days) if days.isdigit() else 30
        clear_old_notifications(days)
    elif choice == '4':
        username = input("Enter username: ").strip()
        if username:
            clear_user_notifications(username)
        else:
            print("❌ Username cannot be empty!")
    elif choice == '5':
        print("👋 Goodbye!")
    else:
        print("❌ Invalid option!")

if __name__ == "__main__":
    main()