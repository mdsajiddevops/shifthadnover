import pandas as pd
from models.models import Incident, ShiftKeyPoint
import csv
from io import StringIO
from models.models import db
from flask import send_file
from reportlab.pdfgen import canvas
import io

def _parse_incident_title(title):
    title = title or ''
    if title.startswith('[') and ']' in title:
        end_bracket = title.index(']')
        app_name = title[1:end_bracket].strip()
        remainder = title[end_bracket + 1:].strip()
    elif ' - ' in title:
        parts = title.split(' - ', 1)
        app_name = parts[0].strip()
        remainder = parts[1].strip()
    else:
        app_name = ''
        remainder = title.strip()
    # Extract leading incident ID token (e.g. INC123456, CHG001)
    parts = remainder.split(None, 1)
    if parts and parts[0].upper().startswith(('INC', 'CHG', 'PRB', 'TASK', 'RITM')):
        incident_id = parts[0]
        short_description = parts[1] if len(parts) > 1 else ''
    else:
        incident_id = ''
        short_description = remainder
    return app_name, incident_id, short_description


def export_incidents_csv(date, shift_id):
    incidents = Incident.query.filter_by(shift_id=shift_id).all()
    rows = []
    for i in incidents:
        app_name, incident_id, short_description = _parse_incident_title(i.title)
        rows.append({
            'Application': app_name,
            'Incident ID': incident_id,
            'Short Description': short_description,
            'Type': i.type,
            'Status': i.status,
            'Priority': i.priority,
            'Description / Notes': i.description or '',
            'Handover Notes': i.handover or '',
            'Assigned To': i.assigned_to or '',
            'Escalated To': i.escalated_to or '',
            'Resolved': 'Yes' if i.is_resolved else 'No',
            'Resolved At': i.resolved_at.strftime('%Y-%m-%d %H:%M') if i.resolved_at else '',
        })
    df = pd.DataFrame(rows)
    csv_io = io.StringIO()
    df.to_csv(csv_io, index=False)
    csv_io.seek(0)
    return send_file(io.BytesIO(csv_io.getvalue().encode()), mimetype='text/csv', as_attachment=True, download_name=f'incidents_{date}.csv')

def export_keypoints_pdf(date, shift_id):
    keypoints = ShiftKeyPoint.query.filter_by(shift_id=shift_id).all()
    pdf_io = io.BytesIO()
    c = canvas.Canvas(pdf_io)
    c.drawString(100, 800, f"Shift Key Points for {date}")
    y = 780
    for kp in keypoints:
        c.drawString(100, y, f"{kp.description} - {kp.status}")
        y -= 20
    c.save()
    pdf_io.seek(0)
    return send_file(pdf_io, mimetype='application/pdf', as_attachment=True, download_name=f'keypoints_{date}.pdf')
