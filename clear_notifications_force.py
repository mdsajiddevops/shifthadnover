#!/usr/bin/env python3
"""
Clear All Dashboard Notifications - No Confirmation
==================================================
This script clears all notifications without asking for confirmation.
"""

import os
import sys
from datetime import datetime

# Add the application directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import app
from models.handover_enhanced import HandoverNotification

def clear_all_notifications():
    """Clear all notifications from the dashboard without confirmation"""
    
    with app.app.app_context():
        try:
            print("🧹 CLEARING ALL DASHBOARD NOTIFICATIONS")
            print("=" * 50)
            
            # Count existing notifications
            total_count = HandoverNotification.query.count()
            print(f"📊 Total notifications in database: {total_count}")
            
            if total_count == 0:
                print("✅ No notifications to clear!")
                return
            
            # Show breakdown by type
            print("\n📋 Notifications by type:")
            notification_types = app.db.session.query(
                HandoverNotification.notification_type, 
                app.db.func.count(HandoverNotification.id)
            ).group_by(HandoverNotification.notification_type).all()
            
            for notif_type, count in notification_types:
                print(f"   • {notif_type}: {count} notifications")
            
            # Show breakdown by read status
            unread_count = HandoverNotification.query.filter_by(is_read=False).count()
            read_count = HandoverNotification.query.filter_by(is_read=True).count()
            
            print(f"\n📬 By status:")
            print(f"   • Unread: {unread_count}")
            print(f"   • Read: {read_count}")
            
            # Delete all notifications WITHOUT confirmation
            print(f"\n🗑️  Deleting all {total_count} notifications...")
            deleted_count = HandoverNotification.query.delete()
            app.db.session.commit()
            
            print(f"✅ Successfully deleted {deleted_count} notifications!")
            
            # Verify deletion
            remaining_count = HandoverNotification.query.count()
            if remaining_count == 0:
                print("✅ Dashboard is now clean - no notifications remaining!")
            else:
                print(f"⚠️  Warning: {remaining_count} notifications still remain")
                
        except Exception as e:
            print(f"❌ Error clearing notifications: {str(e)}")
            app.db.session.rollback()
            raise

if __name__ == "__main__":
    clear_all_notifications()