#!/usr/bin/env python3
"""
Debug script to check user and team member relationships
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the Flask app and database
from app import app, db
from models.models import User, Team, TeamMember
from models.handover_enhanced import HandoverNotification, IncidentAssignment
from sqlalchemy import text

def check_users_and_teams():
    """Check users and their team relationships"""
    
    with app.app_context():
        print("🔍 Checking techops users and their team memberships:")
        print("=" * 60)
        
        # Get all techops users
        techops_users = User.query.filter(User.username.like('techops%')).all()
        
        for user in techops_users:
            print(f"👤 User: {user.username} (ID: {user.id}) - {user.email}")
            
            # Check team memberships
            team_memberships = db.session.execute(
                text("SELECT tm.team_id, t.name FROM team_member tm JOIN team t ON tm.team_id = t.id WHERE tm.user_id = :user_id"),
                {"user_id": user.id}
            ).fetchall()
            
            if team_memberships:
                for membership in team_memberships:
                    print(f"   📋 Team: {membership[1]} (ID: {membership[0]})")
            else:
                print(f"   ❌ No team memberships found!")
        
        print("\n🔍 Checking ALL users with team memberships:")
        print("=" * 60)
        
        # Get all users with team memberships
        users_with_teams = db.session.execute(
            text("SELECT u.id, u.username, u.email, tm.team_id, t.name as team_name FROM user u JOIN team_member tm ON u.id = tm.user_id JOIN team t ON tm.team_id = t.id ORDER BY u.username")
        ).fetchall()
        
        if users_with_teams:
            for user_team in users_with_teams:
                print(f"👤 User: {user_team[1]} (ID: {user_team[0]}) - Team: {user_team[4]} (ID: {user_team[3]})")
        else:
            print("❌ No users with team memberships found!")
        
        print("\n🔍 Checking recent handover notifications:")
        print("=" * 60)
        
        # Check recent notifications
        recent_notifications = HandoverNotification.query.order_by(HandoverNotification.created_at.desc()).limit(10).all()
        
        if recent_notifications:
            for notification in recent_notifications:
                print(f"📧 Notification ID: {notification.id}")
                print(f"   Title: {notification.title}")
                print(f"   Recipient ID: {notification.recipient_id}")
                print(f"   Created: {notification.created_at}")
                print(f"   Read: {notification.is_read}")
                print("---")
        else:
            print("❌ No recent notifications found!")
        
        print("\n🔍 Checking recent incident assignments:")
        print("=" * 60)
        
        # Check recent incident assignments
        recent_assignments = IncidentAssignment.query.order_by(IncidentAssignment.assigned_at.desc()).limit(10).all()
        
        if recent_assignments:
            for assignment in recent_assignments:
                print(f"📋 Assignment ID: {assignment.id}")
                print(f"   Incident: {assignment.incident_title}")
                print(f"   Assigned By ID: {assignment.assigned_by_id}")
                print(f"   Assigned To ID: {assignment.assigned_to_id}")
                print(f"   Status: {assignment.assignment_status}")
                print(f"   Created: {assignment.assigned_at}")
                print("---")
        else:
            print("❌ No recent incident assignments found!")

if __name__ == "__main__":
    check_users_and_teams()