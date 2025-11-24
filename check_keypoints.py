#!/usr/bin/env python3
import sys
sys.path.append('/home/shifthandoversajid/shift_handover_app')
from app import app, db
from models import ShiftKeyPoint

with app.app_context():
    kps = ShiftKeyPoint.query.filter(
        ShiftKeyPoint.account_id == 1,
        ShiftKeyPoint.team_id == 2,
        ShiftKeyPoint.status.in_(['Open', 'In Progress'])
    ).order_by(ShiftKeyPoint.id.desc()).limit(8).all()
    
    print(f'Found {len(kps)} open/in-progress key points:')
    for kp in kps:
        print(f'  ID {kp.id}: "{kp.description}" | JIRA: {repr(kp.jira_id)} | Status: {kp.status}')
    
    # Show deduplication result
    print('\nAfter deduplication:')
    kp_map = {}
    for kp in kps:
        key = (kp.description, kp.jira_id)
        if key not in kp_map or kp.id > kp_map[key].id:
            kp_map[key] = kp
    unique_kps = list(kp_map.values())
    print(f'Unique count: {len(unique_kps)}')
    for kp in unique_kps:
        print(f'  ID {kp.id}: "{kp.description}" | JIRA: {repr(kp.jira_id)} | Status: {kp.status}')