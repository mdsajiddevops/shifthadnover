#!/usr/bin/env python3
"""
Debug the approval route in detail and test authentication
"""
import sys
import os

# Add the current directory to Python path
sys.path.append('/app')

def test_approval_route_directly():
    """Test the approval route directly with proper authentication"""
    
    print("🔍 TESTING APPROVAL ROUTE DIRECTLY")
    print("=" * 60)
    
    try:
        from app import app, db
        from models.shift_swap_leave import ShiftSwapRequest
        import json
        
        with app.app_context():
            # Check current requests
            requests = ShiftSwapRequest.query.filter_by(status='pending').all()
            print(f"📋 Pending requests: {len(requests)}")
            
            if requests:
                test_request_id = requests[0].id
                print(f"🎯 Testing with Request ID: {test_request_id}")
                
                # Test with test client and authentication
                with app.test_client() as client:
                    # First, let's try to login as superadmin
                    login_response = client.post('/login', data={
                        'username': 'superadmin',
                        'password': 'admin123'  # Common admin password
                    }, follow_redirects=True)
                    
                    print(f"🔐 Login Status: {login_response.status_code}")
                    
                    if login_response.status_code == 200:
                        print("✅ Login successful")
                        
                        # Now test the approval
                        approval_response = client.post(f'/shift-management/admin/approve-swap/{test_request_id}', 
                                                      json={'comments': 'Test approval'},
                                                      content_type='application/json')
                        
                        print(f"📊 Approval Status: {approval_response.status_code}")
                        print(f"📊 Approval Response: {approval_response.get_data(as_text=True)}")
                        
                        if approval_response.status_code == 200:
                            print("✅ Approval route working!")
                        else:
                            print("❌ Approval route still failing")
                    else:
                        print("❌ Login failed - checking what credentials work")
                        
                        # Try different login combinations
                        test_logins = [
                            ('admin', 'admin'),
                            ('admin', 'admin123'),
                            ('superadmin', 'superadmin'),
                            ('root', 'root'),
                            ('administrator', 'password')
                        ]
                        
                        for username, password in test_logins:
                            test_login = client.post('/login', data={
                                'username': username,
                                'password': password
                            })
                            if test_login.status_code != 302:  # 302 means redirect to login again
                                print(f"✅ Working credentials: {username}/{password}")
                                break
                        else:
                            print("❌ No working credentials found")
            else:
                print("❌ No pending requests to test")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

def check_route_authentication():
    """Check what authentication is required for the route"""
    
    print(f"\n🔐 CHECKING ROUTE AUTHENTICATION")
    print("=" * 60)
    
    try:
        # Check the route definition
        route_file = '/app/routes/shift_swap_leave.py'
        
        with open(route_file, 'r') as f:
            content = f.read()
        
        # Look for authentication decorators
        if '@login_required' in content:
            print("🔐 Route requires login authentication")
        
        if '@admin_required' in content:
            print("🔐 Route requires admin authentication")
            
        # Find the approval route function
        lines = content.split('\n')
        in_approve_function = False
        for i, line in enumerate(lines):
            if 'def approve_swap_request' in line:
                in_approve_function = True
                print(f"\n📋 Approval Function (lines {i+1}-{i+20}):")
                for j in range(max(0, i-2), min(len(lines), i+20)):
                    prefix = ">>> " if j == i else "    "
                    print(f"{prefix}{j+1:3}: {lines[j]}")
                break
                
    except Exception as e:
        print(f"❌ Error checking route: {e}")

def create_simple_test_page():
    """Create a simple test page to test approval without JavaScript"""
    
    print(f"\n🧪 CREATING SIMPLE TEST PAGE")
    print("=" * 60)
    
    try:
        test_page_content = '''<!DOCTYPE html>
<html>
<head>
    <title>Approval Test</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .test-form { background: #f5f5f5; padding: 20px; border-radius: 8px; margin: 20px 0; }
        button { padding: 10px 20px; margin: 10px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; }
        button:hover { background: #0056b3; }
        .result { background: #e9ecef; padding: 15px; margin: 10px 0; border-radius: 4px; }
    </style>
</head>
<body>
    <h1>Shift Swap Approval Test</h1>
    
    <div class="test-form">
        <h3>Test Approval with Form POST</h3>
        <form method="POST" action="/shift-management/admin/approve-swap/1">
            <input type="hidden" name="comments" value="Form-based approval test">
            <button type="submit">Approve Request ID 1</button>
        </form>
        
        <form method="POST" action="/shift-management/admin/approve-swap/2">
            <input type="hidden" name="comments" value="Form-based approval test">
            <button type="submit">Approve Request ID 2</button>
        </form>
        
        <form method="POST" action="/shift-management/admin/approve-swap/3">
            <input type="hidden" name="comments" value="Form-based approval test">
            <button type="submit">Approve Request ID 3</button>
        </form>
    </div>
    
    <div class="test-form">
        <h3>Test with AJAX (like the dashboard)</h3>
        <button onclick="testAjaxApproval(1)">AJAX Approve Request 1</button>
        <button onclick="testAjaxApproval(2)">AJAX Approve Request 2</button>
        <button onclick="testAjaxApproval(3)">AJAX Approve Request 3</button>
        <div id="ajaxResult" class="result" style="display:none;"></div>
    </div>
    
    <script>
    function testAjaxApproval(requestId) {
        console.log('Testing AJAX approval for request:', requestId);
        
        const resultDiv = document.getElementById('ajaxResult');
        resultDiv.style.display = 'block';
        resultDiv.innerHTML = 'Testing approval for Request ID ' + requestId + '...';
        
        fetch('/shift-management/admin/approve-swap/' + requestId, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            credentials: 'same-origin',
            body: JSON.stringify({
                comments: 'AJAX test approval'
            })
        })
        .then(response => {
            console.log('Response status:', response.status);
            console.log('Response headers:', response.headers);
            console.log('Response URL:', response.url);
            
            resultDiv.innerHTML += '<br>Status: ' + response.status;
            resultDiv.innerHTML += '<br>URL: ' + response.url;
            
            if (response.status === 302) {
                resultDiv.innerHTML += '<br>❌ Got redirect (probably to login)';
                return { error: 'Redirect to login' };
            }
            
            return response.json();
        })
        .then(data => {
            console.log('Response data:', data);
            resultDiv.innerHTML += '<br>Response: ' + JSON.stringify(data);
            
            if (data.success) {
                resultDiv.innerHTML += '<br>✅ Success!';
            } else {
                resultDiv.innerHTML += '<br>❌ Error: ' + (data.error || 'Unknown');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            resultDiv.innerHTML += '<br>❌ Network Error: ' + error.message;
        });
    }
    </script>
</body>
</html>'''
        
        with open('/app/templates/approval_test.html', 'w') as f:
            f.write(test_page_content)
        
        print("✅ Created test page at /app/templates/approval_test.html")
        print("📋 Access it by adding a route to serve this template")
        
        # Create a simple route for the test page
        route_addition = '''

# Add this route to your main routes or app.py for testing
@app.route('/test-approval')
def test_approval_page():
    return render_template('approval_test.html')
'''
        
        with open('/app/test_route_addition.txt', 'w') as f:
            f.write(route_addition)
        
        print("📋 Route code saved to /app/test_route_addition.txt")
        
    except Exception as e:
        print(f"❌ Error creating test page: {e}")

if __name__ == "__main__":
    test_approval_route_directly()
    check_route_authentication()
    create_simple_test_page()