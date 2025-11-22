#!/usr/bin/env python3
import sys
sys.path.append('/app')

from models.models import db, Account, Team, User
from werkzeug.security import generate_password_hash
from app import app

def create_sample_data():
    with app.app_context():
        print("🏢 Creating comprehensive user structure...")
        
        # Create Accounts
        print("\n📋 Creating Accounts...")
        account1 = Account(name="TechCorp Solutions", is_active=True, status="active")
        account2 = Account(name="Global Innovations", is_active=True, status="active")
        
        db.session.add(account1)
        db.session.add(account2)
        db.session.commit()
        
        print(f"✅ Account 1: {account1.name} (ID: {account1.id})")
        print(f"✅ Account 2: {account2.name} (ID: {account2.id})")
        
        # Create Teams for Account 1
        print(f"\n👥 Creating Teams for {account1.name}...")
        team1_acc1 = Team(name="Development Team", account_id=account1.id, is_active=True, status="active")
        team2_acc1 = Team(name="Operations Team", account_id=account1.id, is_active=True, status="active")
        
        # Create Teams for Account 2
        print(f"\n👥 Creating Teams for {account2.name}...")
        team1_acc2 = Team(name="Cloud Infrastructure", account_id=account2.id, is_active=True, status="active")
        team2_acc2 = Team(name="Security Team", account_id=account2.id, is_active=True, status="active")
        
        db.session.add_all([team1_acc1, team2_acc1, team1_acc2, team2_acc2])
        db.session.commit()
        
        print(f"✅ {account1.name}: {team1_acc1.name} (ID: {team1_acc1.id})")
        print(f"✅ {account1.name}: {team2_acc1.name} (ID: {team2_acc1.id})")
        print(f"✅ {account2.name}: {team1_acc2.name} (ID: {team1_acc2.id})")
        print(f"✅ {account2.name}: {team2_acc2.name} (ID: {team2_acc2.id})")
        
        # Create Account Admins
        print(f"\n👑 Creating Account Admins...")
        
        # Account Admin for TechCorp Solutions
        acc_admin1 = User(
            username="techcorp_admin",
            email="admin@techcorp.com",
            password=generate_password_hash("admin123"),
            role="account_admin",
            is_active=True,
            status="active",
            account_id=account1.id,
            team_id=None
        )
        
        # Account Admin for Global Innovations
        acc_admin2 = User(
            username="global_admin",
            email="admin@globalinnovations.com",
            password=generate_password_hash("admin123"),
            role="account_admin",
            is_active=True,
            status="active",
            account_id=account2.id,
            team_id=None
        )
        
        db.session.add_all([acc_admin1, acc_admin2])
        db.session.commit()
        
        print(f"✅ Account Admin: {acc_admin1.username} for {account1.name}")
        print(f"✅ Account Admin: {acc_admin2.username} for {account2.name}")
        
        # Create Team Admins
        print(f"\n🎯 Creating Team Admins...")
        
        # Team Admins for TechCorp Solutions
        team_admin1 = User(
            username="dev_team_admin",
            email="dev.admin@techcorp.com",
            password=generate_password_hash("admin123"),
            role="team_admin",
            is_active=True,
            status="active",
            account_id=account1.id,
            team_id=team1_acc1.id
        )
        
        team_admin2 = User(
            username="ops_team_admin",
            email="ops.admin@techcorp.com",
            password=generate_password_hash("admin123"),
            role="team_admin",
            is_active=True,
            status="active",
            account_id=account1.id,
            team_id=team2_acc1.id
        )
        
        # Team Admins for Global Innovations
        team_admin3 = User(
            username="cloud_team_admin",
            email="cloud.admin@globalinnovations.com",
            password=generate_password_hash("admin123"),
            role="team_admin",
            is_active=True,
            status="active",
            account_id=account2.id,
            team_id=team1_acc2.id
        )
        
        team_admin4 = User(
            username="security_team_admin",
            email="security.admin@globalinnovations.com",
            password=generate_password_hash("admin123"),
            role="team_admin",
            is_active=True,
            status="active",
            account_id=account2.id,
            team_id=team2_acc2.id
        )
        
        db.session.add_all([team_admin1, team_admin2, team_admin3, team_admin4])
        db.session.commit()
        
        print(f"✅ Team Admin: {team_admin1.username} for {team1_acc1.name}")
        print(f"✅ Team Admin: {team_admin2.username} for {team2_acc1.name}")
        print(f"✅ Team Admin: {team_admin3.username} for {team1_acc2.name}")
        print(f"✅ Team Admin: {team_admin4.username} for {team2_acc2.name}")
        
        # Create Regular Users
        print(f"\n👤 Creating Regular Users...")
        
        # Users for TechCorp Solutions - Development Team
        dev_users = [
            User(username="john_dev", email="john@techcorp.com", password=generate_password_hash("user123"), 
                 role="user", is_active=True, status="active", account_id=account1.id, team_id=team1_acc1.id),
            User(username="sarah_dev", email="sarah@techcorp.com", password=generate_password_hash("user123"), 
                 role="user", is_active=True, status="active", account_id=account1.id, team_id=team1_acc1.id),
            User(username="mike_dev", email="mike@techcorp.com", password=generate_password_hash("user123"), 
                 role="user", is_active=True, status="active", account_id=account1.id, team_id=team1_acc1.id)
        ]
        
        # Users for TechCorp Solutions - Operations Team
        ops_users = [
            User(username="lisa_ops", email="lisa@techcorp.com", password=generate_password_hash("user123"), 
                 role="user", is_active=True, status="active", account_id=account1.id, team_id=team2_acc1.id),
            User(username="david_ops", email="david@techcorp.com", password=generate_password_hash("user123"), 
                 role="user", is_active=True, status="active", account_id=account1.id, team_id=team2_acc1.id)
        ]
        
        # Users for Global Innovations - Cloud Infrastructure
        cloud_users = [
            User(username="alex_cloud", email="alex@globalinnovations.com", password=generate_password_hash("user123"), 
                 role="user", is_active=True, status="active", account_id=account2.id, team_id=team1_acc2.id),
            User(username="emma_cloud", email="emma@globalinnovations.com", password=generate_password_hash("user123"), 
                 role="user", is_active=True, status="active", account_id=account2.id, team_id=team1_acc2.id),
            User(username="ryan_cloud", email="ryan@globalinnovations.com", password=generate_password_hash("user123"), 
                 role="user", is_active=True, status="active", account_id=account2.id, team_id=team1_acc2.id)
        ]
        
        # Users for Global Innovations - Security Team
        security_users = [
            User(username="nina_security", email="nina@globalinnovations.com", password=generate_password_hash("user123"), 
                 role="user", is_active=True, status="active", account_id=account2.id, team_id=team2_acc2.id),
            User(username="tom_security", email="tom@globalinnovations.com", password=generate_password_hash("user123"), 
                 role="user", is_active=True, status="active", account_id=account2.id, team_id=team2_acc2.id)
        ]
        
        all_users = dev_users + ops_users + cloud_users + security_users
        db.session.add_all(all_users)
        db.session.commit()
        
        # Print user summary
        print(f"\n📊 User Creation Summary:")
        print(f"   TechCorp Solutions - Development Team: {len(dev_users)} users")
        for user in dev_users:
            print(f"      ✅ {user.username} ({user.email})")
            
        print(f"   TechCorp Solutions - Operations Team: {len(ops_users)} users")
        for user in ops_users:
            print(f"      ✅ {user.username} ({user.email})")
            
        print(f"   Global Innovations - Cloud Infrastructure: {len(cloud_users)} users")
        for user in cloud_users:
            print(f"      ✅ {user.username} ({user.email})")
            
        print(f"   Global Innovations - Security Team: {len(security_users)} users")
        for user in security_users:
            print(f"      ✅ {user.username} ({user.email})")

if __name__ == "__main__":
    create_sample_data()
    print(f"\n🎉 Complete user structure created successfully!")
    print(f"\n📝 Login Credentials Summary:")
    print(f"   🔑 Super Admin: superadmin / admin123")
    print(f"   🏢 Account Admins: techcorp_admin, global_admin / admin123")
    print(f"   👥 Team Admins: dev_team_admin, ops_team_admin, cloud_team_admin, security_team_admin / admin123")
    print(f"   👤 Regular Users: [username] / user123")
    print(f"      - TechCorp: john_dev, sarah_dev, mike_dev, lisa_ops, david_ops")
    print(f"      - Global: alex_cloud, emma_cloud, ryan_cloud, nina_security, tom_security")