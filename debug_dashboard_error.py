#!/usr/bin/env python3

# Debug dashboard loading error
import sys
sys.path.append('/app')
import os
os.chdir('/app')

def check_dashboard_error():
    """Check what's causing the dashboard loading error"""
    
    try:
        from app import app
        from models.models import User
        from routes.shift_swap_leave import shift_swap_leave_bp
        
        print("=== Dashboard Error Debugging ===")
        
        with app.app_context():
            # Test the dashboard route function
            try:
                from routes.shift_swap_leave import dashboard
                print("✅ Dashboard route imported successfully")
                
                # Test with a mock request context
                with app.test_request_context():
                    from flask_login import login_user
                    
                    # Get techopsuser1
                    user = User.query.filter_by(username='techopsuser1').first()
                    if user:
                        print(f"✅ Found user: {user.username}")
                        
                        # Try to simulate login
                        login_user(user)
                        print("✅ User logged in for testing")
                        
                        # Try to call dashboard function
                        try:
                            result = dashboard()
                            print("✅ Dashboard function executed successfully")
                            print(f"Response type: {type(result)}")
                        except Exception as e:
                            print(f"❌ Dashboard function error: {str(e)}")
                            import traceback
                            traceback.print_exc()
                    else:
                        print("❌ User techopsuser1 not found")
                        
            except ImportError as e:
                print(f"❌ Import error: {str(e)}")
            except Exception as e:
                print(f"❌ Route error: {str(e)}")
                import traceback
                traceback.print_exc()
                
    except Exception as e:
        print(f"❌ General error: {str(e)}")
        import traceback
        traceback.print_exc()

def check_template_syntax():
    """Check if the dashboard template has syntax errors"""
    
    template_file = '/app/templates/shift_management/dashboard.html'
    
    print(f"\n=== Checking Template Syntax ===")
    
    if os.path.exists(template_file):
        print(f"✅ Template exists: {template_file}")
        
        try:
            with open(template_file, 'r') as f:
                content = f.read()
            
            # Check for common Jinja2 syntax issues
            issues = []
            
            # Check for unclosed tags
            if content.count('{%') != content.count('%}'):
                issues.append("Unmatched {% %} tags")
            
            if content.count('{{') != content.count('}}'):
                issues.append("Unmatched {{ }} tags")
                
            # Check for unclosed HTML tags
            if content.count('<div') > content.count('</div>'):
                issues.append("Unclosed <div> tags")
                
            if issues:
                print("❌ Template syntax issues found:")
                for issue in issues:
                    print(f"  - {issue}")
            else:
                print("✅ No obvious template syntax issues found")
                
        except Exception as e:
            print(f"❌ Error reading template: {str(e)}")
    else:
        print(f"❌ Template not found: {template_file}")

if __name__ == "__main__":
    check_dashboard_error()
    check_template_syntax()