#!/usr/bin/env python3
"""
Test script to verify draft handover issues are fixed
"""
import sys
sys.path.append('.')
from models.models import Shift, Incident, ShiftKeyPoint, db
from app import app

def test_draft_visibility():
    """Test that draft shifts are visible in the system"""
    with app.app_context():
        print("=== TESTING DRAFT VISIBILITY ===")
        
        # Check all shifts
        all_shifts = Shift.query.all()
        draft_shifts = Shift.query.filter_by(status='draft').all()
        sent_shifts = Shift.query.filter_by(status='sent').all()
        
        print(f"Total shifts: {len(all_shifts)}")
        print(f"Draft shifts: {len(draft_shifts)}")
        print(f"Sent shifts: {len(sent_shifts)}")
        
        print("\n=== ALL SHIFTS DETAILS ===")
        for shift in all_shifts:
            print(f"ID: {shift.id}, Date: {shift.date}, Status: {shift.status}, "
                  f"Type: {shift.current_shift_type}->{shift.next_shift_type}, "
                  f"Account: {shift.account_id}, Team: {shift.team_id}")
            
            # Count associated data
            inc_count = Incident.query.filter_by(shift_id=shift.id).count()
            kp_count = ShiftKeyPoint.query.filter_by(shift_id=shift.id).count()
            print(f"    → {inc_count} incidents, {kp_count} key points")
        
        print("\n=== DRAFT SHIFTS ANALYSIS ===")
        if draft_shifts:
            for draft in draft_shifts:
                print(f"Draft ID {draft.id}: Created {draft.created_at}, "
                      f"Submitted: {draft.submitted_at}")
        else:
            print("No draft shifts found!")
            
        return len(draft_shifts) > 0

def test_shift_creation_logic():
    """Test that new shifts are created properly without overriding"""
    with app.app_context():
        print("\n=== TESTING SHIFT CREATION LOGIC ===")
        
        # Get current max shift ID
        max_shift = Shift.query.order_by(Shift.id.desc()).first()
        max_id = max_shift.id if max_shift else 0
        print(f"Current max shift ID: {max_id}")
        
        # Check for any duplicate entries on same date/type
        from sqlalchemy import func
        duplicates = (db.session.query(
            Shift.date,
            Shift.current_shift_type,
            Shift.next_shift_type,
            Shift.account_id,
            Shift.team_id,
            func.count().label('count')
        )
        .group_by(
            Shift.date,
            Shift.current_shift_type,
            Shift.next_shift_type,
            Shift.account_id,
            Shift.team_id
        )
        .having(func.count() > 1)
        .all())
        
        print(f"Found {len(duplicates)} duplicate shift combinations:")
        for dup in duplicates:
            print(f"  Date: {dup.date}, Type: {dup.current_shift_type}->{dup.next_shift_type}, "
                  f"Account: {dup.account_id}, Team: {dup.team_id}, Count: {dup.count}")
            
            # Show the specific shifts
            matching_shifts = Shift.query.filter_by(
                date=dup.date,
                current_shift_type=dup.current_shift_type,
                next_shift_type=dup.next_shift_type,
                account_id=dup.account_id,
                team_id=dup.team_id
            ).all()
            
            for shift in matching_shifts:
                print(f"    Shift ID {shift.id}: Status {shift.status}, Created {shift.created_at}")

if __name__ == "__main__":
    print("Starting draft handover fix verification...")
    
    has_drafts = test_draft_visibility()
    test_shift_creation_logic()
    
    if has_drafts:
        print("\n✅ SUCCESS: Draft shifts are visible in the system")
    else:
        print("\n⚠️ WARNING: No draft shifts found - may need to test draft creation")
    
    print("\nTest completed. Check the output above for any issues.")