#!/usr/bin/env python3
"""
Fix the JavaScript issue in the dashboard - the backend works but frontend doesn't handle response properly
"""
import sys
import os

# Add the current directory to Python path
sys.path.append('/app')

def fix_javascript_response_handling():
    """Fix the JavaScript to properly handle the successful response"""
    
    print("🔧 FIXING JAVASCRIPT RESPONSE HANDLING")
    print("=" * 60)
    
    try:
        template_path = '/app/templates/shift_management/dashboard.html'
        
        with open(template_path, 'r') as f:
            content = f.read()
        
        # The issue is likely in the response parsing or error handling
        # Let's create a completely new, robust approval function
        
        new_approve_function = '''function approveSwapRequest(requestId) {
    console.log('🚀 Starting approval for request:', requestId);
    
    if (confirm('Are you sure you want to approve this shift swap request?')) {
        // Show loading state
        const button = event.target;
        let originalText = '';
        if (button) {
            originalText = button.innerHTML;
            button.disabled = true;
            button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Approving...';
        }
        
        console.log('📡 Sending approval request...');
        
        fetch('/shift-management/admin/approve-swap/' + requestId, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            credentials: 'same-origin',
            body: JSON.stringify({
                comments: 'Approved via admin dashboard'
            })
        })
        .then(response => {
            console.log('📨 Raw response received:', response);
            console.log('📊 Response status:', response.status);
            console.log('📊 Response ok:', response.ok);
            console.log('📊 Response statusText:', response.statusText);
            console.log('📊 Response url:', response.url);
            
            // Check if response is ok (status 200-299)
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            // Check content type
            const contentType = response.headers.get('content-type');
            console.log('📊 Content-Type:', contentType);
            
            if (contentType && contentType.includes('application/json')) {
                return response.json();
            } else {
                // If not JSON, get as text and try to parse
                return response.text().then(text => {
                    console.log('📄 Response text:', text);
                    try {
                        return JSON.parse(text);
                    } catch (e) {
                        console.error('❌ Failed to parse as JSON:', e);
                        throw new Error('Response is not valid JSON: ' + text);
                    }
                });
            }
        })
        .then(data => {
            console.log('✅ Parsed response data:', data);
            
            // Check if the response indicates success
            if (data && data.success) {
                console.log('🎉 Approval successful!');
                alert('✅ Swap request approved successfully!\\n\\n' + (data.message || 'Request has been approved.'));
                
                // Reload the page to show updated status
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
            } else {
                console.error('❌ Approval failed:', data);
                const errorMsg = data.error || data.message || 'Unknown error occurred';
                alert('❌ Error approving request:\\n\\n' + errorMsg);
                
                // Restore button
                if (button) {
                    button.disabled = false;
                    button.innerHTML = originalText;
                }
            }
        })
        .catch(error => {
            console.error('💥 Request failed:', error);
            
            // Show user-friendly error message
            let errorMessage = 'Network error occurred while approving the request.';
            
            if (error.message.includes('HTTP 302') || error.message.includes('login')) {
                errorMessage = 'Your session has expired. Please refresh the page and try again.';
            } else if (error.message.includes('HTTP 403')) {
                errorMessage = 'You do not have permission to approve this request.';
            } else if (error.message.includes('HTTP 404')) {
                errorMessage = 'The request was not found. It may have already been processed.';
            } else if (error.message) {
                errorMessage = error.message;
            }
            
            alert('❌ Error: ' + errorMessage);
            
            // Restore button
            if (button) {
                button.disabled = false;
                button.innerHTML = originalText;
            }
        });
    }
}'''

        # Find and replace the approve function
        start_marker = 'function approveSwapRequest(requestId) {'
        start_pos = content.find(start_marker)
        
        if start_pos != -1:
            # Count braces to find the end of the function
            brace_count = 0
            pos = start_pos + len(start_marker) - 1  # Start at the opening brace
            while pos < len(content):
                if content[pos] == '{':
                    brace_count += 1
                elif content[pos] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end_pos = pos + 1
                        break
                pos += 1
            
            # Replace the function
            content = content[:start_pos] + new_approve_function + content[end_pos:]
            
            # Also fix the reject function
            new_reject_function = '''function rejectSwapRequest(requestId) {
    const reason = prompt('Please provide a reason for rejection:');
    if (reason !== null && reason.trim() !== '') {
        console.log('🚀 Starting rejection for request:', requestId);
        
        const button = event.target;
        let originalText = '';
        if (button) {
            originalText = button.innerHTML;
            button.disabled = true;
            button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Rejecting...';
        }
        
        fetch('/shift-management/admin/reject-swap/' + requestId, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            credentials: 'same-origin',
            body: JSON.stringify({ reason: reason })
        })
        .then(response => {
            console.log('📨 Reject response:', response);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('✅ Reject response data:', data);
            if (data && data.success) {
                alert('✅ Swap request rejected successfully!\\n\\n' + (data.message || 'Request has been rejected.'));
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
            } else {
                alert('❌ Error rejecting request:\\n\\n' + (data.error || data.message || 'Unknown error'));
                if (button) {
                    button.disabled = false;
                    button.innerHTML = originalText;
                }
            }
        })
        .catch(error => {
            console.error('💥 Reject failed:', error);
            alert('❌ Error rejecting request: ' + error.message);
            if (button) {
                button.disabled = false;
                button.innerHTML = originalText;
            }
        });
    }
}'''
            
            # Find and replace reject function
            reject_start = content.find('function rejectSwapRequest(requestId) {')
            if reject_start != -1:
                brace_count = 0
                pos = reject_start + len('function rejectSwapRequest(requestId) {') - 1
                while pos < len(content):
                    if content[pos] == '{':
                        brace_count += 1
                    elif content[pos] == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            reject_end = pos + 1
                            break
                    pos += 1
                
                content = content[:reject_start] + new_reject_function + content[reject_end:]
            
            with open(template_path, 'w') as f:
                f.write(content)
            
            print("✅ Fixed JavaScript functions with:")
            print("  • Detailed console logging for debugging")
            print("  • Better response parsing and error handling")
            print("  • Content-type checking")
            print("  • User-friendly error messages")
            print("  • Proper button state management")
            
        else:
            print("❌ Could not find approval function to replace")
            
    except Exception as e:
        print(f"❌ Error fixing JavaScript: {e}")
        import traceback
        traceback.print_exc()

def add_test_route():
    """Add a test route to make debugging easier"""
    
    print(f"\n🧪 ADDING TEST ROUTE")
    print("=" * 60)
    
    try:
        # Add test route to main app
        app_file = '/app/app.py'
        
        with open(app_file, 'r') as f:
            content = f.read()
        
        # Add test route before the final return
        if 'return app' in content and '@app.route(\'/test-approval\')' not in content:
            test_route = '''
    @app.route('/test-approval')
    @login_required
    def test_approval_page():
        """Test page for approval debugging"""
        return render_template('approval_test.html')
'''
            
            # Insert before return app
            return_pos = content.rfind('return app')
            if return_pos != -1:
                content = content[:return_pos] + test_route + '\n    ' + content[return_pos:]
                
                with open(app_file, 'w') as f:
                    f.write(content)
                
                print("✅ Added test route /test-approval")
                print("📋 Access it at: https://shiftops.lab.epam.com/test-approval")
            else:
                print("❌ Could not find 'return app' in app.py")
        else:
            print("✅ Test route already exists or not needed")
            
    except Exception as e:
        print(f"❌ Error adding test route: {e}")

if __name__ == "__main__":
    fix_javascript_response_handling()
    add_test_route()