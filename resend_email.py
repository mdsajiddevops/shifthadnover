#!/usr/bin/env python3
"""Script to resend handover email for a specific shift"""
import sys

# Get shift ID from command line argument
shift_id = int(sys.argv[1]) if len(sys.argv) > 1 else 186

from app import app

with app.app_context():
    from models.models import Shift, Team
    from services.email_service import send_handover_email
    
    shift = Shift.query.get(shift_id)
    if shift:
        team = Team.query.get(shift.team_id) if shift.team_id else None
        print(f'Resending email for Shift {shift.id}: {shift.date} {shift.current_shift_type} to {shift.next_shift_type}')
        print(f'Team: {team.name if team else "N/A"}')
        send_handover_email(shift)
        print('Email resend triggered successfully!')
    else:
        print(f'Shift {shift_id} not found!')

