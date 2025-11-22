#!/usr/bin/env python3
"""
Check production database for shift swap tables using Flask app context
"""
import sys
import os
from datetime import datetime

# Add the current directory to Python path
sys.path.append('/app')

def check_production_shift_swap():
    """Check production database for shift swap functionality"""
    try:
        # Import Flask app and database
        from app import app, db
        
        with app.app_context():
            print("🚀 Production Shift Swap Workflow Analysis")
            print("=" * 60)
            
            # Get database engine
            engine = db.engine
            
            # 1. Check if shift swap tables exist
            print("\n🔍 Checking for shift swap tables...")
            
            # Get all table names
            result = engine.execute("SHOW TABLES")
            all_tables = [row[0] for row in result]
            
            # Look for shift swap related tables
            swap_tables = [table for table in all_tables if 'swap' in table.lower() or 'leave' in table.lower()]
            
            if swap_tables:
                print("✅ Found shift swap/leave tables:")
                for table in swap_tables:
                    count_result = engine.execute(f"SELECT COUNT(*) FROM {table}")
                    count = count_result.fetchone()[0]
                    print(f"  📋 {table}: {count} records")
                    
                    # Show table structure
                    desc_result = engine.execute(f"DESCRIBE {table}")
                    columns = desc_result.fetchall()
                    col_names = [col[0] for col in columns]
                    print(f"      Columns: {', '.join(col_names)}")
                    
                    # Show sample data if exists
                    if count > 0 and count <= 5:
                        sample_result = engine.execute(f"SELECT * FROM {table} LIMIT 3")
                        samples = sample_result.fetchall()
                        for i, sample in enumerate(samples, 1):
                            print(f"      Sample {i}: {sample}")
                    elif count > 5:
                        sample_result = engine.execute(f"SELECT * FROM {table} ORDER BY created_at DESC LIMIT 2")
                        samples = sample_result.fetchall()
                        for i, sample in enumerate(samples, 1):
                            print(f"      Recent {i}: {sample}")
                    print()
            else:
                print("❌ NO shift swap/leave tables found in production!")
                print("   This explains why admin can't see approval requests.")
                
                print(f"\n📋 All tables in production ({len(all_tables)} total):")
                for table in sorted(all_tables):
                    print(f"  • {table}")
            
            # 2. Check users and their roles
            print("\n👥 Checking users and roles for shift swap workflow...")
            try:
                user_result = engine.execute("SELECT id, username, email, role FROM user WHERE username LIKE '%admin%' OR username LIKE '%techops%' ORDER BY username")
                admin_users = user_result.fetchall()
                
                if admin_users:
                    print("🔑 Admin and TechOps users:")
                    for user in admin_users:
                        print(f"  ID: {user[0]}, Username: {user[1]}, Email: {user[2]}, Role: {user[3]}")
                        
                        # Check if this user has any shift swap requests
                        if swap_tables:
                            for table in swap_tables:
                                if 'request' in table:
                                    req_result = engine.execute(f"SELECT COUNT(*) FROM {table} WHERE requester_id = %s OR approved_by_id = %s", (user[0], user[0]))
                                    request_count = req_result.fetchone()[0]
                                    if request_count > 0:
                                        print(f"    📝 {request_count} requests in {table}")
                else:
                    print("❌ No admin or techops users found!")
                    
            except Exception as e:
                print(f"❌ Error checking users: {e}")
            
            # 3. Check if shift swap models are imported
            print("\n🔧 Checking if shift swap models are available...")
            try:
                from models.shift_swap_leave import ShiftSwapRequest, LeaveRequest
                print("✅ Shift swap models are imported successfully")
                
                # Try to query using ORM
                swap_requests = ShiftSwapRequest.query.limit(5).all()
                leave_requests = LeaveRequest.query.limit(5).all()
                
                print(f"  📝 ShiftSwapRequest records: {len(swap_requests)}")
                print(f"  📝 LeaveRequest records: {len(leave_requests)}")
                
                if swap_requests:
                    print("  Recent swap requests:")
                    for req in swap_requests[:3]:
                        print(f"    • ID {req.id}: {req.requester.username if req.requester else 'Unknown'} → {req.swap_with.username if req.swap_with else 'Unknown'} (Status: {req.status})")
                        
            except ImportError as e:
                print(f"❌ Shift swap models not available: {e}")
            except Exception as e:
                print(f"❌ Error checking models: {e}")
            
            print("\n" + "=" * 60)
            print("💡 DIAGNOSIS:")
            
            if not swap_tables:
                print("🔥 CRITICAL ISSUE: Shift swap tables are MISSING from production!")
                print("   - Tables like 'shift_swap_request', 'leave_request' need to be created")
                print("   - This is why admin users can't see approval requests")
                print("   - The shift swap functionality is not properly deployed")
                
            print("\n🔧 RECOMMENDED ACTIONS:")
            print("1. Create missing shift swap tables in production database")
            print("2. Run database migrations to add shift swap schema")
            print("3. Verify Flask routes are properly registered")
            print("4. Test the complete workflow: submit → approve → roster update")
            
    except Exception as e:
        print(f"❌ Production database connection error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_production_shift_swap()