#!/usr/bin/env python3
"""
Flask-based Migration Script
Uses Flask-SQLAlchemy models for safer migration with proper ORM handling

Usage:
    python migrate_with_flask.py --action export
    python migrate_with_flask.py --action import --file exports/shift_data.json
    python migrate_with_flask.py --action count
"""

import os
import sys
import json
import argparse
from datetime import datetime, date

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup Flask app context
from app import create_app, db
from models.models import (
    Account, Team, User, TeamMember, UserTeamMembership,
    Shift, Incident, ShiftKeyPoint, ShiftKeyPointUpdate,
    ShiftChangeInfo, ShiftKBUpdate, ShiftRoster
)
from models.handover_enhanced import (
    HandoverRequest, IncidentAssignment, IncidentAssignmentResponse,
    HandoverIncidentResponseLog, HandoverResponse, HandoverNotification,
    HandoverAuditLog
)

# Create directories
EXPORT_DIR = os.path.join(os.path.dirname(__file__), 'exports')
os.makedirs(EXPORT_DIR, exist_ok=True)


def json_serializer(obj):
    """Custom JSON serializer"""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def model_to_dict(obj):
    """Convert SQLAlchemy model to dictionary"""
    data = {}
    for column in obj.__table__.columns:
        value = getattr(obj, column.name)
        if isinstance(value, (datetime, date)):
            value = value.isoformat() if value else None
        data[column.name] = value
    return data


def export_shift_handover_data():
    """Export all shift handover related data"""
    app = create_app()
    
    with app.app_context():
        export_data = {
            'exported_at': datetime.now().isoformat(),
            'tables': {}
        }
        
        # Export Shifts
        print("Exporting shifts...")
        shifts = Shift.query.all()
        export_data['tables']['shift'] = {
            'count': len(shifts),
            'data': [model_to_dict(s) for s in shifts]
        }
        print(f"  ✅ {len(shifts)} shifts")
        
        # Export Incidents
        print("Exporting incidents...")
        incidents = Incident.query.all()
        export_data['tables']['incident'] = {
            'count': len(incidents),
            'data': [model_to_dict(i) for i in incidents]
        }
        print(f"  ✅ {len(incidents)} incidents")
        
        # Export Key Points
        print("Exporting key points...")
        key_points = ShiftKeyPoint.query.all()
        export_data['tables']['shift_key_point'] = {
            'count': len(key_points),
            'data': [model_to_dict(kp) for kp in key_points]
        }
        print(f"  ✅ {len(key_points)} key points")
        
        # Export Key Point Updates
        print("Exporting key point updates...")
        kp_updates = ShiftKeyPointUpdate.query.all()
        export_data['tables']['shift_key_point_update'] = {
            'count': len(kp_updates),
            'data': [model_to_dict(u) for u in kp_updates]
        }
        print(f"  ✅ {len(kp_updates)} key point updates")
        
        # Export Change Info
        print("Exporting change info...")
        change_infos = ShiftChangeInfo.query.all()
        export_data['tables']['shift_change_info'] = {
            'count': len(change_infos),
            'data': [model_to_dict(ci) for ci in change_infos]
        }
        print(f"  ✅ {len(change_infos)} change infos")
        
        # Export KB Updates
        print("Exporting KB updates...")
        kb_updates = ShiftKBUpdate.query.all()
        export_data['tables']['shift_kb_update'] = {
            'count': len(kb_updates),
            'data': [model_to_dict(kb) for kb in kb_updates]
        }
        print(f"  ✅ {len(kb_updates)} KB updates")
        
        # Export Handover Requests (Enhanced)
        print("Exporting handover requests...")
        try:
            handover_requests = HandoverRequest.query.all()
            export_data['tables']['handover_request'] = {
                'count': len(handover_requests),
                'data': [model_to_dict(hr) for hr in handover_requests]
            }
            print(f"  ✅ {len(handover_requests)} handover requests")
        except Exception as e:
            print(f"  ⚠️ Could not export handover_request: {e}")
        
        # Export Incident Assignments
        print("Exporting incident assignments...")
        try:
            incident_assignments = IncidentAssignment.query.all()
            export_data['tables']['incident_assignment'] = {
                'count': len(incident_assignments),
                'data': [model_to_dict(ia) for ia in incident_assignments]
            }
            print(f"  ✅ {len(incident_assignments)} incident assignments")
        except Exception as e:
            print(f"  ⚠️ Could not export incident_assignment: {e}")
        
        # Export Handover Incident Response Logs
        print("Exporting handover incident response logs...")
        try:
            response_logs = HandoverIncidentResponseLog.query.all()
            export_data['tables']['handover_incident_response_log'] = {
                'count': len(response_logs),
                'data': [model_to_dict(rl) for rl in response_logs]
            }
            print(f"  ✅ {len(response_logs)} response logs")
        except Exception as e:
            print(f"  ⚠️ Could not export handover_incident_response_log: {e}")
        
        # Export Shift Roster
        print("Exporting shift roster...")
        try:
            rosters = ShiftRoster.query.all()
            export_data['tables']['shift_roster'] = {
                'count': len(rosters),
                'data': [model_to_dict(r) for r in rosters]
            }
            print(f"  ✅ {len(rosters)} roster entries")
        except Exception as e:
            print(f"  ⚠️ Could not export shift_roster: {e}")
        
        # Save to file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"shift_handover_export_{timestamp}.json"
        filepath = os.path.join(EXPORT_DIR, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, default=json_serializer, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Export complete: {filepath}")
        
        # Summary
        total_records = sum(t.get('count', 0) for t in export_data['tables'].values())
        print(f"\nTotal records exported: {total_records}")
        
        return filepath


def import_shift_handover_data(filepath):
    """Import shift handover data from JSON file"""
    app = create_app()
    
    if not os.path.exists(filepath):
        print(f"❌ File not found: {filepath}")
        return False
    
    with open(filepath, 'r', encoding='utf-8') as f:
        import_data = json.load(f)
    
    with app.app_context():
        print(f"Importing from: {filepath}")
        print(f"Export date: {import_data.get('exported_at', 'Unknown')}")
        
        tables = import_data.get('tables', {})
        
        # Import Shifts
        if 'shift' in tables:
            print("\nImporting shifts...")
            count = 0
            for shift_data in tables['shift']['data']:
                # Check if shift already exists
                existing = Shift.query.get(shift_data['id'])
                if not existing:
                    # Parse date
                    if shift_data.get('date'):
                        shift_data['date'] = datetime.fromisoformat(shift_data['date']).date() if isinstance(shift_data['date'], str) else shift_data['date']
                    if shift_data.get('submitted_at'):
                        shift_data['submitted_at'] = datetime.fromisoformat(shift_data['submitted_at']) if isinstance(shift_data['submitted_at'], str) else shift_data['submitted_at']
                    if shift_data.get('created_at'):
                        shift_data['created_at'] = datetime.fromisoformat(shift_data['created_at']) if isinstance(shift_data['created_at'], str) else shift_data['created_at']
                    
                    shift = Shift(**shift_data)
                    db.session.add(shift)
                    count += 1
            
            db.session.commit()
            print(f"  ✅ Imported {count} shifts")
        
        # Import Incidents
        if 'incident' in tables:
            print("\nImporting incidents...")
            count = 0
            for incident_data in tables['incident']['data']:
                existing = Incident.query.get(incident_data['id'])
                if not existing:
                    incident = Incident(**incident_data)
                    db.session.add(incident)
                    count += 1
            
            db.session.commit()
            print(f"  ✅ Imported {count} incidents")
        
        # Import Key Points
        if 'shift_key_point' in tables:
            print("\nImporting key points...")
            count = 0
            for kp_data in tables['shift_key_point']['data']:
                existing = ShiftKeyPoint.query.get(kp_data['id'])
                if not existing:
                    kp = ShiftKeyPoint(**kp_data)
                    db.session.add(kp)
                    count += 1
            
            db.session.commit()
            print(f"  ✅ Imported {count} key points")
        
        # Import Key Point Updates
        if 'shift_key_point_update' in tables:
            print("\nImporting key point updates...")
            count = 0
            for update_data in tables['shift_key_point_update']['data']:
                existing = ShiftKeyPointUpdate.query.get(update_data['id'])
                if not existing:
                    if update_data.get('update_date'):
                        update_data['update_date'] = datetime.fromisoformat(update_data['update_date']).date() if isinstance(update_data['update_date'], str) else update_data['update_date']
                    
                    update = ShiftKeyPointUpdate(**update_data)
                    db.session.add(update)
                    count += 1
            
            db.session.commit()
            print(f"  ✅ Imported {count} key point updates")
        
        # Import Change Info
        if 'shift_change_info' in tables:
            print("\nImporting change info...")
            count = 0
            for ci_data in tables['shift_change_info']['data']:
                existing = ShiftChangeInfo.query.get(ci_data['id'])
                if not existing:
                    if ci_data.get('change_datetime'):
                        ci_data['change_datetime'] = datetime.fromisoformat(ci_data['change_datetime']) if isinstance(ci_data['change_datetime'], str) else ci_data['change_datetime']
                    if ci_data.get('created_at'):
                        ci_data['created_at'] = datetime.fromisoformat(ci_data['created_at']) if isinstance(ci_data['created_at'], str) else ci_data['created_at']
                    
                    ci = ShiftChangeInfo(**ci_data)
                    db.session.add(ci)
                    count += 1
            
            db.session.commit()
            print(f"  ✅ Imported {count} change infos")
        
        # Import KB Updates
        if 'shift_kb_update' in tables:
            print("\nImporting KB updates...")
            count = 0
            for kb_data in tables['shift_kb_update']['data']:
                existing = ShiftKBUpdate.query.get(kb_data['id'])
                if not existing:
                    if kb_data.get('created_at'):
                        kb_data['created_at'] = datetime.fromisoformat(kb_data['created_at']) if isinstance(kb_data['created_at'], str) else kb_data['created_at']
                    
                    kb = ShiftKBUpdate(**kb_data)
                    db.session.add(kb)
                    count += 1
            
            db.session.commit()
            print(f"  ✅ Imported {count} KB updates")
        
        print("\n✅ Import complete!")
        return True


def show_record_counts():
    """Show current record counts in database"""
    app = create_app()
    
    with app.app_context():
        print("\n" + "=" * 50)
        print("CURRENT DATABASE RECORD COUNTS")
        print("=" * 50)
        
        counts = [
            ("Accounts", Account.query.count()),
            ("Teams", Team.query.count()),
            ("Users", User.query.count()),
            ("Team Members", TeamMember.query.count()),
            ("User Team Memberships", UserTeamMembership.query.count()),
            ("Shifts (Handovers)", Shift.query.count()),
            ("Incidents", Incident.query.count()),
            ("Key Points", ShiftKeyPoint.query.count()),
            ("Key Point Updates", ShiftKeyPointUpdate.query.count()),
            ("Change Infos", ShiftChangeInfo.query.count()),
            ("KB Updates", ShiftKBUpdate.query.count()),
            ("Shift Rosters", ShiftRoster.query.count()),
        ]
        
        # Try enhanced tables
        try:
            counts.append(("Handover Requests", HandoverRequest.query.count()))
            counts.append(("Incident Assignments", IncidentAssignment.query.count()))
            counts.append(("Handover Response Logs", HandoverIncidentResponseLog.query.count()))
        except:
            pass
        
        for name, count in counts:
            print(f"  {name:<30} {count:>10}")
        
        print("=" * 50)
        print(f"  {'TOTAL':<30} {sum(c for _, c in counts):>10}")
        print("=" * 50)


def main():
    parser = argparse.ArgumentParser(description='Flask-based Shift Handover Migration')
    parser.add_argument('--action', required=True, 
                       choices=['export', 'import', 'count'],
                       help='Action to perform')
    parser.add_argument('--file', help='Import file path')
    
    args = parser.parse_args()
    
    if args.action == 'export':
        export_shift_handover_data()
    
    elif args.action == 'import':
        if not args.file:
            print("❌ Please specify --file for import")
            sys.exit(1)
        import_shift_handover_data(args.file)
    
    elif args.action == 'count':
        show_record_counts()


if __name__ == '__main__':
    main()




