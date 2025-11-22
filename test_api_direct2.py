#!/usr/bin/env python3
"""
Direct API test script
"""
import sys
import os
sys.path.append('/app')

try:
    from app import app, db
    from models.models import User, TeamMember, ShiftRoster
    from datetime import datetime
    from flask_login import login_user
    
    with app.app_context():
        print("=== Direct API Test ===")
        
        # Find techopsuser1
        user = User.query.filter_by(username='techopsuser1').first()
        print(f"✅ Found user: {user.username} (ID: {user.id})")
        
        # Simulate the actual API call by calling the function directly
        with app.test_request_context():
            # Manually set current_user to simulate login
            from flask_login import current_user
            from flask import g
            
            # Simulate login
            login_user(user)
            
            # Now call our API function directly
            try:
                from routes.shift_swap_leave import get_user_shift_for_date
                result = get_user_shift_for_date("2025-11-28")
                print(f"✅ API call result: {result}")
                
                # Get the response data
                if hasattr(result, 'get_json'):
                    data = result.get_json()
                    print(f"Response data: {data}")
                elif hasattr(result, 'data'):
                    print(f"Response data: {result.data}")
                else:
                    print(f"Result type: {type(result)}")
                    
            except Exception as e:
                print(f"❌ API call failed: {str(e)}")
                import traceback
                traceback.print_exc()
    
except Exception as e:
    print(f"❌ Error: {str(e)}")
    import traceback
    traceback.print_exc()