#!/usr/bin/env python3
"""
Debug script for incident notifications and response logs
This script helps identify why notifications aren't working in production
"""

import sys
import os
from datetime import datetime

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models.models import db, User, TeamMember, Shift, Incident
from models.handover_enhanced import IncidentAssignment, HandoverIncidentResponseLog

def debug_incident_notifications():
    """Debug incident notification system"""
    app = create_app()
    
    with app.app_context():
        print("🔍 DEBUGGING INCIDENT NOTIFICATIONS SYSTEM 🔍")
        print("=" * 60)
        
        # 1. Check database connection and tables
        print("\n1. DATABASE CONNECTION CHECK:")
        try:
            # Test basic database connection
            user_count = User.query.count()
            print(f"   ✅ Database connected - {user_count} users found")
            
            # Check if required tables exist
            tables_to_check = [
                ('incident_assignment', IncidentAssignment),
                ('handover_incident_response_log', HandoverIncidentResponseLog),
                ('shift', Shift),
                ('incident', Incident),
                ('user', User),
                ('team_member', TeamMember)
            ]
            
            for table_name, model_class in tables_to_check:
                try:
                    count = model_class.query.count()
                    print(f"   ✅ Table '{table_name}': {count} records")
                except Exception as e:
                    print(f"   ❌ Table '{table_name}': ERROR - {str(e)}")
                    
        except Exception as e:
            print(f"   ❌ Database connection failed: {str(e)}")
            return
        
        # 2. Check recent handovers and their incident assignments
        print("\n2. RECENT HANDOVERS AND INCIDENT ASSIGNMENTS:")
        try:
            recent_shifts = Shift.query.order_by(Shift.date.desc()).limit(5).all()
            print(f"   Found {len(recent_shifts)} recent shifts")
            
            for shift in recent_shifts:
                print(f"\n   📋 Shift ID {shift.id}: {shift.date} ({shift.current_shift_type} → {shift.next_shift_type})")
                print(f"       Status: {shift.status}, Account: {shift.account_id}, Team: {shift.team_id}")
                
                # Check incidents for this shift
                incidents = Incident.query.filter_by(shift_id=shift.id).all()
                print(f"       📊 {len(incidents)} incidents found")
                
                for inc in incidents[:3]:  # Show first 3 incidents
                    print(f"         - {inc.type}: {inc.title} (Assigned: {inc.assigned_to or 'None'})")
                
                # Check incident assignments for this shift
                assignments = IncidentAssignment.query.filter_by(handover_request_id=shift.id).all()
                print(f"       🎯 {len(assignments)} incident assignments found")
                
                for assignment in assignments[:3]:  # Show first 3 assignments
                    assigned_user = User.query.get(assignment.assigned_to_id) if assignment.assigned_to_id else None
                    print(f"         - Assignment ID {assignment.id}: {assignment.incident_title}")
                    print(f"           Assigned to: {assigned_user.username if assigned_user else 'Unknown'} (ID: {assignment.assigned_to_id})")
                    print(f"           Status: {assignment.assignment_status}, Priority: {assignment.incident_priority}")
                
                # Check handover incident response logs for this shift
                logs = HandoverIncidentResponseLog.query.filter_by(handover_request_id=shift.id).all()
                print(f"       📝 {len(logs)} response logs found")
                
                for log in logs[:3]:  # Show first 3 logs
                    print(f"         - Log ID {log.id}: {log.incident_title}")
                    print(f"           Status: {log.assignment_status}, Response: {log.response_status}")
                    print(f"           Assigned to: {log.accepted_by_name} (ID: {log.accepted_by_id})")
                
        except Exception as e:
            print(f"   ❌ Error checking recent handovers: {str(e)}")
        
        # 3. Check users and their pending assignments
        print("\n3. USER ASSIGNMENT CHECK:")
        try:
            # Get all users who should receive notifications
            users = User.query.filter(User.role.in_(['user', 'team_admin'])).limit(10).all()
            print(f"   Found {len(users)} regular users")
            
            for user in users:
                # Check pending assignments for this user
                pending_assignments = IncidentAssignment.query.filter_by(
                    assigned_to_id=user.id,
                    assignment_status='pending'
                ).all()
                
                # Check pending response logs for this user
                pending_logs = HandoverIncidentResponseLog.query.filter_by(
                    accepted_by_id=user.id,
                    assignment_status='pending'
                ).all()
                
                if pending_assignments or pending_logs:
                    print(f"\n   👤 User: {user.username} ({user.display_name}) - ID: {user.id}")
                    print(f"       Email: {user.email}")
                    print(f"       Role: {user.role}, Account: {user.account_id}, Team: {user.team_id}")
                    print(f"       📋 Pending assignments: {len(pending_assignments)}")
                    print(f"       📝 Pending logs: {len(pending_logs)}")
                    
                    # Show details of pending assignments
                    for assignment in pending_assignments[:2]:
                        print(f"         - Assignment: {assignment.incident_title} (Priority: {assignment.incident_priority})")
                    
                    for log in pending_logs[:2]:
                        print(f"         - Log: {log.incident_title} (Status: {log.assignment_status})")
                        
        except Exception as e:
            print(f"   ❌ Error checking user assignments: {str(e)}")
        
        # 4. Check notification system components
        print("\n4. NOTIFICATION SYSTEM CHECK:")
        try:
            from flask import current_app
            
            # Check email configuration
            mail_server = current_app.config.get('MAIL_SERVER')
            mail_username = current_app.config.get('MAIL_USERNAME')
            print(f"   📧 Email server configured: {'✅ Yes' if mail_server else '❌ No'}")
            if mail_server:
                print(f"       Server: {mail_server}")
                print(f"       Username: {mail_username}")
            
            # Check if Flask-Mail extension is loaded
            mail_ext = current_app.extensions.get('mail')
            print(f"   📧 Flask-Mail extension: {'✅ Loaded' if mail_ext else '❌ Not loaded'}")
            
        except Exception as e:
            print(f"   ❌ Error checking notification system: {str(e)}")
        
        # 5. Database status summary
        print("\n5. SUMMARY AND RECOMMENDATIONS:")
        try:
            total_assignments = IncidentAssignment.query.count()
            pending_assignments = IncidentAssignment.query.filter_by(assignment_status='pending').count()
            total_logs = HandoverIncidentResponseLog.query.count()
            pending_logs = HandoverIncidentResponseLog.query.filter_by(assignment_status='pending').count()
            
            print(f"   📊 Total incident assignments: {total_assignments}")
            print(f"   ⏳ Pending assignments: {pending_assignments}")
            print(f"   📝 Total response logs: {total_logs}")
            print(f"   ⏳ Pending response logs: {pending_logs}")
            
            print("\n   🔧 RECOMMENDATIONS:")
            if pending_assignments == 0 and pending_logs == 0:
                print("   ⚠️  No pending incidents found - this suggests:")
                print("      - No recent handovers with incident assignments, OR")
                print("      - Incident assignments are not being created properly, OR")
                print("      - All assignments have been processed already")
                print("   🎯 Action: Create a test handover with incident assignments")
            
            if not mail_server:
                print("   ⚠️  Email not configured - notifications will be skipped")
                print("   🎯 Action: Configure MAIL_SERVER in production environment")
                
            print(f"\n   📅 Debug completed at: {datetime.now()}")
            
        except Exception as e:
            print(f"   ❌ Error generating summary: {str(e)}")

if __name__ == '__main__':
    debug_incident_notifications()
