#!/usr/bin/env python3
"""
Simple Database Check - No Flask Required
Run this after fixing the Python environment
"""

def check_mysql_without_flask():
    print("🔍 SIMPLE DATABASE CHECK (System Python)")
    print("=" * 50)
    
    # Try to import mysql.connector using system Python
    try:
        import mysql.connector
        print("✅ mysql.connector available")
    except ImportError:
        print("❌ mysql.connector not available")
        print("Run: sudo apt install python3-mysql.connector")
        print("Or: pip3 install mysql-connector-python")
        return False
    
    # Database connection details - UPDATE THESE
    db_config = {
        'host': 'localhost',
        'user': 'root',                     # Update with your MySQL username
        'password': 'your_password',        # Update with your MySQL password
        'database': 'shift_handover_db'     # Update with your database name
    }
    
    print(f"\nTrying to connect to MySQL...")
    print(f"Host: {db_config['host']}")
    print(f"Database: {db_config['database']}")
    print(f"User: {db_config['user']}")
    
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        print("✅ Database connection successful!")
        
        # Check incident assignment table
        cursor.execute("SELECT COUNT(*) FROM incident_assignment")
        ia_count = cursor.fetchone()[0]
        print(f"📊 incident_assignment records: {ia_count}")
        
        # Check response log table
        cursor.execute("SELECT COUNT(*) FROM handover_incident_response_log")
        log_count = cursor.fetchone()[0]
        print(f"📊 handover_incident_response_log records: {log_count}")
        
        # Check users
        cursor.execute("SELECT COUNT(*) FROM user")
        user_count = cursor.fetchone()[0]
        print(f"📊 user records: {user_count}")
        
        # Check recent shifts
        cursor.execute("SELECT COUNT(*) FROM shift ORDER BY date DESC LIMIT 5")
        shift_count = cursor.fetchone()[0]
        print(f"📊 shift records: {shift_count}")
        
        if ia_count == 0 and log_count == 0:
            print("\n🎯 DIAGNOSIS:")
            print("❌ No incident assignments or response logs found")
            print("💡 This confirms the notification issue")
            print("🔧 Need to check why handover creation isn't making assignments")
        
        conn.close()
        return True
        
    except mysql.connector.Error as e:
        print(f"❌ Database connection failed: {e}")
        print("\nTroubleshooting:")
        print("1. Update the database credentials in this script")
        print("2. Ensure MySQL is running: sudo systemctl status mysql")
        print("3. Check if database exists: mysql -u root -p -e 'SHOW DATABASES;'")
        return False

def install_mysql_connector():
    """Install mysql-connector using system package manager"""
    print("\n🔧 INSTALLING MYSQL CONNECTOR")
    print("=" * 50)
    
    import subprocess
    import sys
    
    try:
        # Try system package first
        print("Installing python3-mysql.connector...")
        result = subprocess.run([
            'sudo', 'apt', 'install', '-y', 'python3-mysql.connector'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ System package installed")
        else:
            print("⚠️  System package failed, trying pip...")
            # Try pip3
            result = subprocess.run([
                'pip3', 'install', 'mysql-connector-python'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ Pip package installed")
            else:
                print("❌ Both installation methods failed")
                print("Manual commands to try:")
                print("sudo apt install python3-mysql.connector")
                print("pip3 install mysql-connector-python")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Installation error: {e}")
        return False

def main():
    print("🐍 PYTHON DATABASE CONNECTIVITY TEST")
    print("=" * 60)
    
    # First try to check database
    success = check_mysql_without_flask()
    
    if not success:
        print("\n💡 Attempting to install MySQL connector...")
        if install_mysql_connector():
            print("\n🔄 Retrying database connection...")
            success = check_mysql_without_flask()
    
    if success:
        print("\n✅ Database connectivity is working!")
        print("🎯 Next step: Fix Python virtual environment for Flask")
    else:
        print("\n❌ Database connectivity issues need to be resolved first")
        
    print(f"\n🎯 Test completed!")

if __name__ == '__main__':
    print("📋 INSTRUCTIONS:")
    print("1. Update database credentials in this script (lines 16-21)")
    print("2. Run: python3 simple_db_test.py")
    print("3. This will test database connectivity without Flask")
    print("\nPress Enter to continue or Ctrl+C to exit...")
    
    try:
        input()
        main()
    except KeyboardInterrupt:
        print("\n👋 Test cancelled.")
