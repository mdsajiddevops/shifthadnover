#!/usr/bin/env python3

"""
Test script to check what key points are being returned by the reports route
"""

from models.models import ShiftKeyPoint, Shift
from app import app

def test_reports_data():
    with app.app_context():
        print("🔍 REPORTS TEST: Checking key points data")
        
        # Get recent shifts
        shifts = Shift.query.filter_by(account_id=1, team_id=2).order_by(Shift.date.desc()).limit(3).all()
        
        print(f"Found {len(shifts)} recent shifts")
        
        for shift in shifts:
            key_points = ShiftKeyPoint.query.filter_by(shift_id=shift.id).all()
            
            print(f"\n📊 Shift {shift.id} ({shift.date}, {shift.current_shift_type}):")
            print(f"   Total key points: {len(key_points)}")
            
            status_counts = {'Open': 0, 'In Progress': 0, 'Closed': 0}
            for kp in key_points:
                status_counts[kp.status] = status_counts.get(kp.status, 0) + 1
                print(f"   KP {kp.id}: {kp.status} - {kp.description[:40]}...")
            
            print(f"   Status breakdown: {status_counts}")
        
        print("\n🔍 Overall key point status distribution:")
        all_kps = ShiftKeyPoint.query.join(Shift).filter(Shift.account_id==1, Shift.team_id==2).all()
        total_status_counts = {'Open': 0, 'In Progress': 0, 'Closed': 0}
        for kp in all_kps:
            total_status_counts[kp.status] = total_status_counts.get(kp.status, 0) + 1
        
        print(f"Total key points: {len(all_kps)}")
        print(f"Status distribution: {total_status_counts}")

if __name__ == "__main__":
    test_reports_data()