#!/usr/bin/env python3
"
Fix for missing HandoverNotification creation during handover submission.

The issue: When handover incidents are assigned to engineers, the system creates:
1. Incident records 
2. IncidentAssignment records 
3. HandoverNotification records (MISSING!)

The dashboard looks for HandoverNotification records to show notifications,
but they are never created during handover submission.
"
import os
import sys
sys.path.append(/home/shifthandoversajid/shift_handover_app)

from flask import Flask
from models.models import db, User, Incident
from models.handover_enhanced import HandoverNotification, IncidentAssignment
from config import Config
from datetime import datetime

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

def create_missing_notifications():
    "Create HandoverNotification records for existing incident assignments that dont have them"
    
    with app.app_context():
        print( Analyzing current notification situation...)
        
        # Get all users
        users = User.query.all()
        user_map = {user.username: user for user in users}
        print(fFound {len(users)} users: {[u.username for u in users]})
        
        # Get all incident assignments that should have notifications
        assignments = IncidentAssignment.query.filter(
            IncidentAssignment.assigned_to_name.like(techopsuser%)
        ).all()
        
        print(f\\nFound {len(assignments)} incident assignments to techops users:)
        for assignment in assignments:
            print(f - Assignment {assignment.id}: {assignment.incident_title} {assignment.assigned_to_name})
        
        # Check existing notifications
        existing_notifications = HandoverNotification.query.all()
        print(f\\nExisting notifications: {len(existing_notifications)})
        
        # Create missing notifications
        notifications_created = 0
        
        for assignment in assignments:
            assigned_user = user_map.get(assignment.assigned_to_name)
            if not assigned_user:
                print(f User not found: {assignment.assigned_to_name})
                continue
            
            # Check if notification already exists for this assignment
            existing = HandoverNotification.query.filter_by(
                recipient_id=assigned_user.id,
                title=fIncident Assignment: {assignment.incident_title}
            ).first()
            
            if existing:
                print(f Notification already exists for {assignment.incident_title} {assigned_user.username})
                continue
            
            # Create new notification
            notification = HandoverNotification(
                recipient_id=assigned_user.id,
                handover_request_id=assignment.handover_request_id,
                notification_type=incident_assigned,
                title=fIncident Assignment: {assignment.incident_title},
                message=fYou have been assigned to handle incident: {assignment.incident_title}\\n\\nDescription: {assignment.incident_description}\\n\\nPriority: {assignment.incident_priority},
                action_url=f/handover/assignments,
                action_text=View Assignment,
                is_read=False,
                is_dismissed=False,
                created_at=assignment.created_at or datetime.utcnow()
            )
            
            db.session.add(notification)
            notifications_created += 1
            print(f Created notification: {assignment.incident_title} {assigned_user.username})
        
        if notifications_created > 0:
            try:
                db.session.commit()
                print(f\\n Successfully created {notifications_created} notifications!)
            except Exception as e:
                db.session.rollback()
                print(f Error saving notifications: {e})
        else:
            print(\\n No new notifications needed)
        
        # Verify the fix
        print(\\n Verification:)
        user3 = User.query.filter_by(username=techopsuser3).first()
        if user3:
            user3_notifications = HandoverNotification.query.filter_by(
                recipient_id=user3.id, 
                is_read=False
            ).all()
            print(ftechopsuser3 now has {len(user3_notifications)} unread notifications:)
            for notif in user3_notifications:
                print(f - {notif.title} (created: {notif.created_at}))
        
        return notifications_created

if __name__ == __main__:
    create_missing_notifications()
EOF
