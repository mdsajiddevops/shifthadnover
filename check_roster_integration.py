#!/usr/bin/env python3

# Check if roster updates are integrated after approval
import os
import sys

def check_roster_integration():
    """Check if there's roster update logic after approval"""
    
    # Check the approval service for roster updates
    service_file = '/app/services/shift_swap_leave_service.py'
    
    print(f"Checking roster integration in {service_file}")
    
    if not os.path.exists(service_file):
        print(f"Service file not found: {service_file}")
        return False
        
    with open(service_file, 'r') as f:
        content = f.read()
    
    # Look for roster-related code
    roster_keywords = ['roster', 'shift_roster', 'update_roster', 'shift_schedule']
    found_roster = False
    
    for keyword in roster_keywords:
        if keyword.lower() in content.lower():
            print(f"✅ Found roster-related code: '{keyword}'")
            found_roster = True
            
            # Find the line containing this keyword
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if keyword.lower() in line.lower():
                    start = max(0, i-2)
                    end = min(len(lines), i+3)
                    print(f"Context (lines {start+1}-{end}):")
                    for j in range(start, end):
                        marker = ">>> " if j == i else "    "
                        print(f"{marker}{j+1:3}: {lines[j]}")
                    print()
    
    if not found_roster:
        print("❌ No roster-related code found in approval service")
        
    return found_roster

def check_roster_tables():
    """Check what roster tables exist in the database"""
    check_script = '''
import sys
sys.path.append('/app')

from app import create_app
from flask import current_app
from sqlalchemy import inspect

def check_tables():
    app = create_app()
    with app.app_context():
        engine = current_app.extensions['migrate'].db.engine
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        print("Available tables:")
        roster_tables = []
        for table in sorted(tables):
            if 'roster' in table.lower() or 'shift' in table.lower():
                roster_tables.append(table)
                print(f"  🎯 {table} (potential roster table)")
            else:
                print(f"     {table}")
        
        print(f"\\nFound {len(roster_tables)} potential roster tables:")
        for table in roster_tables:
            print(f"  - {table}")
            
        return roster_tables

if __name__ == "__main__":
    check_tables()
'''
    
    with open('/app/check_roster_tables.py', 'w') as f:
        f.write(check_script)
    
    print("\n=== Checking Database Tables ===")
    os.system('cd /app && python3 check_roster_tables.py')

def check_models_for_roster():
    """Check if there are roster models defined"""
    models_file = '/app/models/models.py'
    
    print(f"\n=== Checking Models in {models_file} ===")
    
    if not os.path.exists(models_file):
        print(f"Models file not found: {models_file}")
        return False
        
    with open(models_file, 'r') as f:
        content = f.read()
    
    # Look for roster-related models
    roster_keywords = ['roster', 'shift_schedule', 'schedule', 'shift_assignment']
    found_models = []
    
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if 'class ' in line and any(keyword.lower() in line.lower() for keyword in roster_keywords):
            found_models.append(line.strip())
            print(f"✅ Found potential roster model: {line.strip()}")
            
            # Show some context
            start = max(0, i)
            end = min(len(lines), i+10)
            for j in range(start, end):
                if j == i:
                    print(f">>> {j+1:3}: {lines[j]}")
                else:
                    print(f"    {j+1:3}: {lines[j]}")
                if lines[j].strip().startswith('class ') and j > i:
                    break
            print()
    
    if not found_models:
        print("❌ No roster-related models found")
        
    return found_models

def main():
    print("=== Checking Roster Integration After Approval ===")
    
    # Check service file
    service_has_roster = check_roster_integration()
    
    # Check database tables
    check_roster_tables()
    
    # Check models
    models_found = check_models_for_roster()
    
    print("\n=== Summary ===")
    print(f"Service has roster code: {'✅' if service_has_roster else '❌'}")
    print(f"Roster models found: {'✅' if models_found else '❌'}")
    
    if not service_has_roster:
        print("\n🔧 Recommendation:")
        print("The approval service doesn't seem to update the roster after approval.")
        print("This means approved swaps/leaves are not reflected in the actual shift roster.")
        print("You may need to implement roster update logic in the approval functions.")

if __name__ == "__main__":
    main()