#!/usr/bin/env python3
"""
Fix the approval issues - reset approved requests and fix authentication
"""
import sys
import os

# Add the current directory to Python path
sys.path.append('/app')

def reset_approved_requests():
    """Reset approved requests to pending for testing"""
    
    print("🔄 RESETTING APPROVED REQUESTS TO PENDING")
    print("=" * 60)
    
    try:
        from app import app, db
        from models.shift_swap_leave import ShiftSwapRequest
        
        with app.app_context():
            # Get all approved requests
            approved_requests = ShiftSwapRequest.query.filter_by(status='approved').all()
            
            print(f"📋 Found {len(approved_requests)} approved requests")
            
            for req in approved_requests:
                print(f"🔄 Resetting Request ID {req.id} to pending")
                req.status = 'pending'
                req.approved_by_username = None
                req.approved_at = None
                
            db.session.commit()
            print("✅ All requests reset to pending status")
            
            # Verify the reset
            pending_requests = ShiftSwapRequest.query.filter_by(status='pending').all()
            print(f"📋 Now have {len(pending_requests)} pending requests")
            
    except Exception as e:
        print(f"❌ Error resetting requests: {e}")
        import traceback
        traceback.print_exc()

def fix_dashboard_javascript():
    """Fix the dashboard JavaScript to handle authentication properly"""
    
    print(f"\n🔧 FIXING DASHBOARD JAVASCRIPT FOR AUTHENTICATION")
    print("=" * 60)
    
    try:
        template_path = '/app/templates/shift_management/dashboard.html'
        
        with open(template_path, 'r') as f:
            content = f.read()
        
        # Find the approve function and replace it with a version that handles auth
        if 'function approveSwapRequest(requestId)' in content:
            # Replace the entire script section with a better version
            new_approve_function = '''function approveSwapRequest(requestId) {
    console.log('Attempting to approve request:', requestId);
    
    if (confirm('Are you sure you want to approve this shift swap request?')) {
        // Show loading state
        const button = event.target;
        if (button) {
            const originalText = button.innerHTML;
            button.disabled = true;
            button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Approving...';
        }
        
        // Get CSRF token if available
        let csrfToken = null;
        const csrfMeta = document.querySelector('meta[name="csrf-token"]');
        if (csrfMeta) {
            csrfToken = csrfMeta.getAttribute('content');
        }
        
        const headers = {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        };
        
        if (csrfToken) {
            headers['X-CSRFToken'] = csrfToken;
        }
        
        fetch('/shift-management/admin/approve-swap/' + requestId, {
            method: 'POST',
            headers: headers,
            credentials: 'same-origin', // Include cookies for authentication
            body: JSON.stringify({
                comments: 'Approved via admin dashboard'
            })
        })
        .then(response => {
            console.log('Response status:', response.status);
            console.log('Response type:', response.type);
            
            // Check if we got redirected to login
            if (response.status === 302 || response.url.includes('/login')) {
                throw new Error('Authentication required - please refresh the page and try again');
            }
            
            if (!response.ok) {
                throw new Error('HTTP ' + response.status + ': ' + response.statusText);
            }
            
            return response.json();
        })
        .then(data => {
            console.log('Success response:', data);
            if (data.success) {
                alert('✅ Swap request approved successfully!');
                location.reload();
            } else {
                alert('❌ Error: ' + (data.error || data.message || 'Unknown error'));
                console.error('Approval failed:', data);
                if (button) {
                    button.disabled = false;
                    button.innerHTML = originalText;
                }
            }
        })
        .catch(error => {
            console.error('Approval error:', error);
            if (error.message.includes('Authentication required')) {
                alert('❌ Session expired. Please refresh the page and try again.');
                location.reload();
            } else {
                alert('❌ Error approving request: ' + error.message);
            }
            if (button) {
                button.disabled = false;
                button.innerHTML = originalText;
            }
        });
    }
}'''
            
            # Find the start and end of the current function
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
                
                with open(template_path, 'w') as f:
                    f.write(content)
                
                print("✅ Updated approval JavaScript with:")
                print("  • Better authentication handling")
                print("  • Session expiry detection")
                print("  • CSRF token support")
                print("  • Credential inclusion for cookies")
            else:
                print("⚠️ Approval function not found in template")
        
    except Exception as e:
        print(f"❌ Error fixing JavaScript: {e}")

def add_csrf_token_to_template():
    """Add CSRF token meta tag to the template"""
    
    print(f"\n🔐 ADDING CSRF TOKEN SUPPORT")
    print("=" * 60)
    
    try:
        template_path = '/app/templates/shift_management/dashboard.html'
        
        with open(template_path, 'r') as f:
            content = f.read()
        
        # Add CSRF meta tag if not present
        if 'csrf-token' not in content:
            # Find the head section and add the meta tag
            head_marker = '</head>'
            if head_marker in content:
                csrf_meta = '''    <meta name="csrf-token" content="{{ csrf_token() }}">
</head>'''
                content = content.replace(head_marker, csrf_meta)
                
                with open(template_path, 'w') as f:
                    f.write(content)
                
                print("✅ Added CSRF token meta tag to template")
            else:
                print("⚠️ Could not find head section in template")
        else:
            print("✅ CSRF token already present in template")
            
    except Exception as e:
        print(f"❌ Error adding CSRF token: {e}")

if __name__ == "__main__":
    reset_approved_requests()
    fix_dashboard_javascript()
    add_csrf_token_to_template()