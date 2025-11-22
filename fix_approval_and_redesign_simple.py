#!/usr/bin/env python3
"""
Fix the approval JavaScript and create modern leave request template
"""
import sys
import os

# Add the current directory to Python path
sys.path.append('/app')

def fix_approval_javascript():
    """Fix the JavaScript approval issue in dashboard.html"""
    
    print("🔧 FIXING APPROVAL JAVASCRIPT ISSUE")
    print("=" * 60)
    
    template_path = '/app/templates/shift_management/dashboard.html'
    
    try:
        with open(template_path, 'r') as f:
            content = f.read()
        
        # Replace the approve function with better error handling
        if 'approveSwapRequest(requestId)' in content:
            # Find and replace the function
            start_marker = 'function approveSwapRequest(requestId) {'
            end_marker = '}'
            
            # Find the function
            start_pos = content.find(start_marker)
            if start_pos != -1:
                # Count braces to find the end
                brace_count = 0
                pos = start_pos + len(start_marker)
                while pos < len(content):
                    if content[pos] == '{':
                        brace_count += 1
                    elif content[pos] == '}':
                        if brace_count == 0:
                            end_pos = pos + 1
                            break
                        brace_count -= 1
                    pos += 1
                
                # Replace the function
                new_function = '''function approveSwapRequest(requestId) {
    console.log('Attempting to approve request:', requestId);
    
    if (confirm('Are you sure you want to approve this shift swap request?')) {
        // Show loading state
        const button = event.target;
        if (button) {
            const originalText = button.innerHTML;
            button.disabled = true;
            button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Approving...';
        }
        
        fetch('/shift-management/admin/approve-swap/' + requestId, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({
                comments: 'Approved via admin dashboard'
            })
        })
        .then(response => {
            console.log('Response status:', response.status);
            console.log('Response headers:', response.headers);
            
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
            console.error('Network/Parse error:', error);
            alert('❌ Error approving request: ' + error.message);
            if (button) {
                button.disabled = false;
                button.innerHTML = originalText;
            }
        });
    }
}'''
                
                content = content[:start_pos] + new_function + content[end_pos:]
                
                with open(template_path, 'w') as f:
                    f.write(content)
                
                print("✅ Fixed approval JavaScript with:")
                print("  • Enhanced error logging and debugging")
                print("  • Better button state management")
                print("  • More robust error handling")
                print("  • Cleaner user feedback")
        
        else:
            print("⚠️  Approval function not found in template")
        
    except Exception as e:
        print(f"❌ Error fixing JavaScript: {e}")

def create_modern_leave_template():
    """Create a modern leave request template"""
    
    print(f"\n🎨 CREATING MODERN LEAVE REQUEST TEMPLATE")
    print("=" * 60)
    
    template_path = '/app/templates/shift_management/request_leave.html'
    
    try:
        # Read the template content from a separate file to avoid Python string issues
        template_content = """{% extends "base.html" %}

{% block title %}Request Leave{% endblock %}

{% block content %}
<style>
/* Modern Leave Request Styling */
body {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif !important;
    color: #2c3e50 !important;
    min-height: 100vh;
}

.page-header {
    background: linear-gradient(135deg, #4a90e2 0%, #357abd 100%) !important;
    color: white !important;
    padding: 2rem;
    margin: 20px;
    text-align: center;
    border-radius: 20px;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
}

.modern-form-card {
    background: white !important;
    border-radius: 25px !important;
    padding: 3rem !important;
    margin: 20px auto !important;
    max-width: 800px;
    box-shadow: 0 15px 35px rgba(0, 0, 0, 0.15) !important;
    border: 1px solid #e9ecef !important;
    position: relative;
    overflow: hidden;
}

.modern-form-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 6px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.section-header {
    font-size: 1.4rem;
    font-weight: 700;
    color: #2c3e50;
    margin: 2rem 0 1.5rem 0;
    display: flex;
    align-items: center;
    gap: 12px;
    padding-bottom: 10px;
    border-bottom: 2px solid #f8f9fa;
}

.section-header i {
    color: #667eea;
    font-size: 1.2rem;
}

.leave-type-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 15px;
    margin: 20px 0;
}

.leave-type-option {
    position: relative;
    background: #f8f9fa;
    border: 2px solid #e9ecef;
    border-radius: 15px;
    padding: 20px 15px;
    text-align: center;
    cursor: pointer;
    transition: all 0.3s ease;
    min-height: 120px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
}

.leave-type-option:hover {
    transform: translateY(-3px);
    box-shadow: 0 8px 25px rgba(102, 126, 234, 0.2);
    border-color: #667eea;
}

.leave-type-option.selected {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border-color: #667eea;
    transform: translateY(-5px);
    box-shadow: 0 10px 30px rgba(102, 126, 234, 0.3);
}

.leave-type-option input[type="radio"] {
    display: none;
}

.leave-type-option i {
    font-size: 2rem;
    margin-bottom: 8px;
    color: #667eea;
}

.leave-type-option.selected i {
    color: white;
}

.form-group {
    margin-bottom: 2rem;
}

.form-label {
    display: block;
    font-weight: 600;
    color: #2c3e50;
    margin-bottom: 8px;
    font-size: 1rem;
}

.form-control {
    width: 100%;
    padding: 12px 16px;
    border: 2px solid #e9ecef;
    border-radius: 12px;
    font-size: 1rem;
    transition: all 0.3s ease;
    background: #f8f9fa;
}

.form-control:focus {
    outline: none;
    border-color: #667eea;
    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
    background: white;
}

.btn-modern {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
    color: white !important;
    padding: 15px 30px;
    border: none;
    border-radius: 25px;
    font-size: 1.1rem;
    font-weight: 600;
    text-decoration: none;
    display: inline-flex;
    align-items: center;
    gap: 10px;
    margin: 10px;
    box-shadow: 0 6px 20px rgba(102, 126, 234, 0.3);
    transition: all 0.3s ease;
    cursor: pointer;
}

.btn-modern:hover {
    transform: translateY(-3px);
    box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
    color: white !important;
    text-decoration: none;
}

.btn-secondary {
    background: linear-gradient(135deg, #6c757d 0%, #5a6268 100%) !important;
    box-shadow: 0 6px 20px rgba(108, 117, 125, 0.3);
}

.btn-secondary:hover {
    box-shadow: 0 8px 25px rgba(108, 117, 125, 0.4);
}

@media (max-width: 768px) {
    .modern-form-card {
        margin: 10px;
        padding: 2rem;
    }
    
    .leave-type-grid {
        grid-template-columns: repeat(2, 1fr);
    }
    
    .page-header {
        margin: 10px;
        padding: 1.5rem;
    }
}
</style>

<div class="page-header">
    <h1 style="margin: 0; font-size: 2.5rem;">
        <i class="fas fa-calendar-times"></i>
        Request Leave
    </h1>
    <p style="margin: 10px 0 0 0; font-size: 1.1rem; opacity: 0.9;">
        Submit a leave request for approval by your team administrator
    </p>
</div>

<div class="modern-form-card">
    <form method="POST" id="leaveRequestForm">
        <!-- Leave Type Selection -->
        <div class="section-header">
            <i class="fas fa-tags"></i>
            Leave Type
        </div>
        
        <div class="leave-type-grid">
            <div class="leave-type-option" onclick="selectLeaveType('sick', this)">
                <input type="radio" name="leave_type" value="sick" id="sick">
                <i class="fas fa-user-md"></i>
                <div style="font-weight: 600; font-size: 0.9rem;">Sick Leave</div>
                <div style="font-size: 0.75rem; opacity: 0.8; margin-top: 5px;">Medical reasons</div>
            </div>
            
            <div class="leave-type-option" onclick="selectLeaveType('personal', this)">
                <input type="radio" name="leave_type" value="personal" id="personal">
                <i class="fas fa-user"></i>
                <div style="font-weight: 600; font-size: 0.9rem;">Personal Leave</div>
                <div style="font-size: 0.75rem; opacity: 0.8; margin-top: 5px;">Personal matters</div>
            </div>
            
            <div class="leave-type-option" onclick="selectLeaveType('vacation', this)">
                <input type="radio" name="leave_type" value="vacation" id="vacation">
                <i class="fas fa-plane"></i>
                <div style="font-weight: 600; font-size: 0.9rem;">Vacation</div>
                <div style="font-size: 0.75rem; opacity: 0.8; margin-top: 5px;">Planned time off</div>
            </div>
            
            <div class="leave-type-option" onclick="selectLeaveType('emergency', this)">
                <input type="radio" name="leave_type" value="emergency" id="emergency">
                <i class="fas fa-exclamation-triangle"></i>
                <div style="font-weight: 600; font-size: 0.9rem;">Emergency</div>
                <div style="font-size: 0.75rem; opacity: 0.8; margin-top: 5px;">Urgent situations</div>
            </div>
            
            <div class="leave-type-option" onclick="selectLeaveType('family', this)">
                <input type="radio" name="leave_type" value="family" id="family">
                <i class="fas fa-home"></i>
                <div style="font-weight: 600; font-size: 0.9rem;">Family Leave</div>
                <div style="font-size: 0.75rem; opacity: 0.8; margin-top: 5px;">Family obligations</div>
            </div>
            
            <div class="leave-type-option" onclick="selectLeaveType('other', this)">
                <input type="radio" name="leave_type" value="other" id="other">
                <i class="fas fa-ellipsis-h"></i>
                <div style="font-weight: 600; font-size: 0.9rem;">Other</div>
                <div style="font-size: 0.75rem; opacity: 0.8; margin-top: 5px;">Specify in reason</div>
            </div>
        </div>

        <!-- Leave Details -->
        <div class="section-header">
            <i class="fas fa-calendar-alt"></i>
            Leave Details
        </div>
        
        <div class="form-group">
            <label class="form-label" for="leave_date">
                <i class="fas fa-calendar"></i> Leave Date
            </label>
            <input type="date" id="leave_date" name="leave_date" class="form-control" required>
        </div>
        
        <div class="form-group">
            <label class="form-label" for="shift_code">
                <i class="fas fa-clock"></i> Shift to Miss
            </label>
            <select id="shift_code" name="shift_code" class="form-control" required>
                <option value="">Select shift</option>
                <option value="D">Day Shift (D)</option>
                <option value="E">Evening Shift (E)</option>
                <option value="N">Night Shift (N)</option>
                <option value="OS">On-Site (OS)</option>
                <option value="OF">Off Duty (OF)</option>
            </select>
        </div>

        <!-- Reason for Leave -->
        <div class="section-header">
            <i class="fas fa-comment-alt"></i>
            Reason for Leave
        </div>
        
        <div class="form-group">
            <textarea id="reason" name="reason" class="form-control" 
                      placeholder="Please explain your reason for leave (optional but recommended)..." 
                      rows="4"></textarea>
        </div>

        <!-- Action Buttons -->
        <div style="text-align: center; margin-top: 3rem;">
            <button type="submit" class="btn-modern">
                <i class="fas fa-paper-plane"></i>
                Submit Leave Request
            </button>
            
            <a href="{{ url_for('shift_swap_leave.dashboard') }}" class="btn-modern btn-secondary">
                <i class="fas fa-arrow-left"></i>
                Back to Dashboard
            </a>
        </div>
    </form>
</div>

<script>
function selectLeaveType(type, element) {
    // Remove selection from all options
    document.querySelectorAll('.leave-type-option').forEach(opt => {
        opt.classList.remove('selected');
    });
    
    // Add selection to clicked option
    element.classList.add('selected');
    
    // Check the radio button
    document.getElementById(type).checked = true;
}

// Form validation
document.getElementById('leaveRequestForm').addEventListener('submit', function(e) {
    const leaveType = document.querySelector('input[name="leave_type"]:checked');
    const leaveDate = document.getElementById('leave_date').value;
    const shiftCode = document.getElementById('shift_code').value;
    
    if (!leaveType) {
        e.preventDefault();
        alert('Please select a leave type');
        return;
    }
    
    if (!leaveDate) {
        e.preventDefault();
        alert('Please select a leave date');
        return;
    }
    
    if (!shiftCode) {
        e.preventDefault();
        alert('Please select which shift you need to miss');
        return;
    }
    
    // Check if date is in the past
    const selectedDate = new Date(leaveDate);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    
    if (selectedDate < today) {
        e.preventDefault();
        alert('Cannot request leave for past dates');
        return;
    }
    
    // Confirm submission
    if (!confirm('Are you sure you want to submit this leave request?')) {
        e.preventDefault();
    }
});

// Set minimum date to today
document.addEventListener('DOMContentLoaded', function() {
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('leave_date').setAttribute('min', today);
});
</script>

{% endblock %}"""

        with open(template_path, 'w') as f:
            f.write(template_content)
        
        print("✅ Created modern leave request template with:")
        print("  • Beautiful gradient design and modern cards")
        print("  • Interactive leave type selection grid")
        print("  • Form validation and user feedback")
        print("  • Responsive design for mobile")
        print("  • Consistent styling with shift management")
        
    except Exception as e:
        print(f"❌ Error creating template: {e}")

if __name__ == "__main__":
    fix_approval_javascript()
    create_modern_leave_template()