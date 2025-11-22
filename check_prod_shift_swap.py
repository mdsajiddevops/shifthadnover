#!/usr/bin/env python3
"""
Check production database for shift swap tables and workflow
"""
import mysql.connector
import sys
import os
from datetime import datetime

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config import get_mysql_config

def check_production_shift_swap():
    """Check production database for shift swap functionality"""
    try:
        # Get MySQL connection
        mysql_config = get_mysql_config()
        print(f"🔗 Connecting to production MySQL: {mysql_config['host']}")
        
        conn = mysql.connector.connect(**mysql_config)
        cursor = conn.cursor()
        
        print("🚀 Production Shift Swap Workflow Analysis")
        print("=" * 60)
        
        # 1. Check if shift swap tables exist
        print("\n🔍 Checking for shift swap tables...")
        cursor.execute("SHOW TABLES LIKE '%swap%' OR SHOW TABLES LIKE '%leave%'")
        swap_tables = cursor.fetchall()
        
        if swap_tables:
            print("✅ Found shift swap/leave tables:")
            for table in swap_tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
                count = cursor.fetchone()[0]
                print(f"  📋 {table[0]}: {count} records")
                
                # Show table structure
                cursor.execute(f"DESCRIBE {table[0]}")
                columns = cursor.fetchall()
                col_names = [col[0] for col in columns]
                print(f"      Columns: {', '.join(col_names)}")
                
                # Show sample data if exists
                if count > 0 and count <= 5:
                    cursor.execute(f"SELECT * FROM {table[0]} LIMIT 3")
                    samples = cursor.fetchall()
                    for i, sample in enumerate(samples, 1):
                        print(f"      Sample {i}: {sample}")
                elif count > 5:
                    cursor.execute(f"SELECT * FROM {table[0]} ORDER BY created_at DESC LIMIT 2")
                    samples = cursor.fetchall()
                    for i, sample in enumerate(samples, 1):
                        print(f"      Recent {i}: {sample}")
                print()
        else:
            print("❌ NO shift swap/leave tables found in production!")
            print("   This explains why admin can't see approval requests.")
            
            # Check if shift_swap_request table exists at all
            cursor.execute("SHOW TABLES")
            all_tables = [table[0] for table in cursor.fetchall()]
            print(f"\n📋 All tables in production ({len(all_tables)} total):")
            for table in sorted(all_tables):
                print(f"  • {table}")
        
        # 2. Check users and their roles
        print("\n👥 Checking users and roles for shift swap workflow...")
        try:
            cursor.execute("SELECT id, username, email, role FROM user WHERE username LIKE '%admin%' OR username LIKE '%techops%' ORDER BY username")
            admin_users = cursor.fetchall()
            
            if admin_users:
                print("🔑 Admin and TechOps users:")
                for user in admin_users:
                    print(f"  ID: {user[0]}, Username: {user[1]}, Email: {user[2]}, Role: {user[3]}")
                    
                    # Check if this user has any shift swap requests
                    if swap_tables:
                        for table in swap_tables:
                            table_name = table[0]
                            if 'request' in table_name:
                                cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE requester_id = %s OR approved_by_id = %s", (user[0], user[0]))
                                request_count = cursor.fetchone()[0]
                                if request_count > 0:
                                    print(f"    📝 {request_count} requests in {table_name}")
            else:
                print("❌ No admin or techops users found!")
                
        except Exception as e:
            print(f"❌ Error checking users: {e}")
        
        # 3. Check if the shift swap routes are registered
        print("\n🛣️  Checking application routes...")
        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='route_registry'")
            # This is just to check - routes are usually not stored in DB
            print("   Routes are defined in Flask application, not database")
        except:
            pass
        
        conn.close()
        
        print("\n" + "=" * 60)
        print("💡 DIAGNOSIS:")
        
        if not swap_tables:
            print("🔥 CRITICAL ISSUE: Shift swap tables are MISSING from production!")
            print("   - Tables like 'shift_swap_request', 'leave_request' need to be created")
            print("   - This is why admin users can't see approval requests")
            print("   - The shift swap functionality is not properly deployed")
            
        print("\n🔧 RECOMMENDED ACTIONS:")
        print("1. Create missing shift swap tables in production database")
        print("2. Verify Flask routes are properly registered")
        print("3. Test the complete workflow: submit → approve → roster update")
        print("4. Check notification system integration")
        
    except Exception as e:
        print(f"❌ Production database connection error: {e}")
        print("   Make sure the production MySQL credentials are correct")

if __name__ == "__main__":
    check_production_shift_swap()