import sys
sys.path.append(/home/shifthandoversajid/shift_handover_app)

from flask import Flask
from models.models import db, User
from models.handover_enhanced import HandoverNotification, IncidentAssignment
from config import Config
from datetime import datetime

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

with app.app_context():
    print( Creating missing notifications for existing incident assignments...)
    
    # Find techopsuser3
    user3 = User.query.filter_by(username=techopsuser3).first()
    if not user3:
        print( techopsuser3 not found!)
        exit(1)
    
    print(f Found techopsuser3: ID {user3.id})
    
    # Find recent incident assignments for techopsuser3
    assignments = IncidentAssignment.query.filter_by(assigned_to_id=user3.id).all()
    print(fFound {len(assignments)} incident assignments for techopsuser3)
    
    notifications_created = 0
    
    for assignment in assignments:
        # Check if notification already exists
        existing = HandoverNotification.query.filter_by(
            recipient_id=user3.id,
            title=fIncident Assignment: {assignment.incident_title}
        ).first()
        
        if existing:
            print(f Notification already exists: {assignment.incident_title})
            continue
        
        # Create new notification
        notification = HandoverNotification(
            recipient_id=user3.id,
            handover_request_id=assignment.handover_request_id,
            notification_type=incident_assigned,
            title=fIncident Assignment: {assignment.incident_title},
            message=fYou have been assigned to handle incident: {assignment.incident_title}\n\nDescription: {assignment.incident_description}\n\nPriority: {assignment.incident_priority},
            action_url=/handover/assignments,
            action_text=View Assignment,
            is_read=False,
            is_dismissed=False,
            created_at=assignment.created_at or datetime.utcnow()
        )
        
        db.session.add(notification)
        notifications_created += 1
        print(f Created notification: {assignment.incident_title})
    
    if notifications_created > 0:
        try:
            db.session.commit()
            print(f\n Successfully created {notifications_created} notifications!)
        except Exception as e:
            db.session.rollback()
            print(f Error: {e})
    else:
        print(\n All notifications already exist)
    
    # Verify
    final_count = HandoverNotification.query.filter_by(
        recipient_id=user3.id, 
        is_read=False
    ).count()
    print(f\n techopsuser3 now has {final_count} unread notifications)
EOF
