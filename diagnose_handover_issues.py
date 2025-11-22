#!/usr/bin/env python3
"""
Diagnose Shift Handover Issues
- Key points not showing all entries
- Key points not appearing in Key Points tab
- Missing older reports (Nov 19th)
"""

import sys
sys.path.append('/app')

from app import app, db
from models.models import Shift, ShiftKeyPoint, Incident
from sqlalchemy import text
from datetime import datetime, date

def diagnose_handover_issues():
    """Diagnose the reported handover issues"""
    
    with app.app_context():
        print("🔍 DIAGNOSING SHIFT HANDOVER ISSUES")
        print("=" * 60)
        
        # Issue 1: Check recent shift handovers
        print("\n1️⃣ RECENT SHIFT HANDOVERS:")
        recent_shifts = Shift.query.order_by(Shift.date.desc()).limit(10).all()
        
        for shift in recent_shifts:
            incidents = Incident.query.filter_by(shift_id=shift.id).all()
            key_points = ShiftKeyPoint.query.filter_by(shift_id=shift.id).all()
            
            print(f"📋 Shift ID {shift.id}:")
            print(f"   📅 Date: {shift.date}")
            print(f"   🕐 Type: {shift.current_shift_type} → {shift.next_shift_type}")
            print(f"   ✅ Status: {shift.status}")
            print(f"   🚨 Incidents: {len(incidents)}")
            for inc in incidents:
                print(f"      - {inc.title} ({inc.status})")
            print(f"   🔑 Key Points: {len(key_points)}")
            for kp in key_points:
                print(f"      - {kp.description[:60]}... ({kp.status})")
            print()
        
        # Issue 2: Check for Nov 19th reports specifically
        print("\n2️⃣ NOVEMBER 19TH REPORTS:")
        nov_19_date = date(2025, 11, 19)
        nov_19_shifts = Shift.query.filter(Shift.date == nov_19_date).all()
        
        if nov_19_shifts:
            print(f"✅ Found {len(nov_19_shifts)} shifts for Nov 19th:")
            for shift in nov_19_shifts:
                incidents = Incident.query.filter_by(shift_id=shift.id).all()
                key_points = ShiftKeyPoint.query.filter_by(shift_id=shift.id).all()
                print(f"   📋 Shift {shift.id}: {shift.current_shift_type}, {len(incidents)} incidents, {len(key_points)} key points")
        else:
            print("❌ No shifts found for November 19th")
        
        # Issue 3: Check key point distribution across all shifts
        print("\n3️⃣ KEY POINT DISTRIBUTION ANALYSIS:")
        all_key_points = ShiftKeyPoint.query.all()
        print(f"📊 Total Key Points in Database: {len(all_key_points)}")
        
        # Group by shift_id
        shift_kp_count = {}
        for kp in all_key_points:
            shift_id = kp.shift_id
            if shift_id not in shift_kp_count:
                shift_kp_count[shift_id] = []
            shift_kp_count[shift_id].append(kp)
        
        print(f"📋 Key Points Distribution:")
        for shift_id, kps in shift_kp_count.items():
            shift = Shift.query.get(shift_id)
            if shift:
                print(f"   Shift {shift_id} ({shift.date}): {len(kps)} key points")
            else:
                print(f"   Shift {shift_id} (MISSING SHIFT): {len(kps)} key points")
        
        # Issue 4: Check for orphaned key points
        print("\n4️⃣ ORPHANED KEY POINTS CHECK:")
        orphaned_kps = []
        for kp in all_key_points:
            shift = Shift.query.get(kp.shift_id)
            if not shift:
                orphaned_kps.append(kp)
        
        if orphaned_kps:
            print(f"⚠️ Found {len(orphaned_kps)} orphaned key points:")
            for kp in orphaned_kps:
                print(f"   KP {kp.id}: shift_id={kp.shift_id} (missing), desc={kp.description[:50]}")
        else:
            print("✅ No orphaned key points found")
        
        # Issue 5: Check database schema for shift_key_point table
        print("\n5️⃣ DATABASE SCHEMA CHECK:")
        try:
            schema_result = db.session.execute(text("""
                SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT
                FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'shift_key_point'
                ORDER BY ORDINAL_POSITION
            """)).fetchall()
            
            print("📝 shift_key_point table schema:")
            for col in schema_result:
                print(f"   {col.COLUMN_NAME}: {col.DATA_TYPE} ({col.IS_NULLABLE}) default={col.COLUMN_DEFAULT}")
        except Exception as e:
            print(f"❌ Error checking schema: {e}")
        
        # Issue 6: Check foreign key relationships
        print("\n6️⃣ FOREIGN KEY RELATIONSHIP CHECK:")
        try:
            # Check if shift_id in shift_key_point references correct table
            fk_result = db.session.execute(text("""
                SELECT 
                    CONSTRAINT_NAME,
                    COLUMN_NAME,
                    REFERENCED_TABLE_NAME,
                    REFERENCED_COLUMN_NAME
                FROM information_schema.KEY_COLUMN_USAGE 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'shift_key_point'
                AND REFERENCED_TABLE_NAME IS NOT NULL
            """)).fetchall()
            
            print("🔗 Foreign key relationships:")
            for fk in fk_result:
                print(f"   {fk.COLUMN_NAME} → {fk.REFERENCED_TABLE_NAME}.{fk.REFERENCED_COLUMN_NAME}")
        except Exception as e:
            print(f"❌ Error checking foreign keys: {e}")
        
        # Issue 7: Sample data consistency check
        print("\n7️⃣ DATA CONSISTENCY CHECK:")
        print("Recent form submissions vs database storage:")
        
        # Check the most recent shift
        latest_shift = Shift.query.order_by(Shift.id.desc()).first()
        if latest_shift:
            print(f"🔍 Latest Shift (ID {latest_shift.id}):")
            print(f"   Date: {latest_shift.date}")
            print(f"   Status: {latest_shift.status}")
            print(f"   Submitted at: {latest_shift.submitted_at}")
            
            latest_incidents = Incident.query.filter_by(shift_id=latest_shift.id).all()
            latest_kps = ShiftKeyPoint.query.filter_by(shift_id=latest_shift.id).all()
            
            print(f"   Incidents stored: {len(latest_incidents)}")
            print(f"   Key points stored: {len(latest_kps)}")
            
            if len(latest_kps) < 3:
                print("   ⚠️ ISSUE CONFIRMED: Key points count is less than expected 3")
        
        print("\n" + "=" * 60)
        print("🎯 DIAGNOSIS COMPLETE")

if __name__ == "__main__":
    diagnose_handover_issues()