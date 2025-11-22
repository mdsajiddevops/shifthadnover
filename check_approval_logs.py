
import sys
sys.path.append('/app')

import os
os.chdir('/app')

from app import app
from models.shift_swap_leave import SwapLeaveAuditLog
from datetime import datetime, timedelta

def check_recent_logs():
    """Check recent audit logs for approval activities"""
    
    with app.app_context():
        print("\n=== Recent Approval Activities ===")
        
        # Get logs from last 7 days
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_logs = SwapLeaveAuditLog.query.filter(
            SwapLeaveAuditLog.created_at >= week_ago,
            SwapLeaveAuditLog.action.in_(['approved', 'rejected'])
        ).order_by(SwapLeaveAuditLog.created_at.desc()).limit(10).all()
        
        print(f"📋 Found {len(recent_logs)} recent approval activities")
        
        for log in recent_logs:
            print(f"\n📝 Log {log.id}:")
            print(f"   Action: {log.action}")
            print(f"   Details: {log.details}")
            print(f"   Target user: {log.target_user_id}")
            print(f"   Approved by: {log.approved_by_id}")
            print(f"   Created: {log.created_at}")
            
            if 'roster updated' in log.details.lower():
                print("   ✅ Roster update mentioned in log")
            else:
                print("   ⚠️ No roster update mentioned in log")

if __name__ == "__main__":
    check_recent_logs()
