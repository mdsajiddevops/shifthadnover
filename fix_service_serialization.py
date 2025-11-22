#!/usr/bin/env python3
"""
Fix the datetime serialization in shift swap service
"""
import sys
import os

# Add the current directory to Python path
sys.path.append('/app')

def fix_service_serialization():
    """Fix datetime serialization in the shift swap service"""
    
    print("🔧 FIXING DATETIME SERIALIZATION IN SERVICE")
    print("=" * 60)
    
    service_path = '/app/services/shift_swap_leave_service.py'
    
    try:
        with open(service_path, 'r') as f:
            content = f.read()
        
        # Find the _serialize_swap_request method
        if '_serialize_swap_request(self, request: ShiftSwapRequest)' in content:
            print("✅ Found _serialize_swap_request method")
            
            # Look for the return statement and fix datetime formatting
            old_pattern = '''return {
            'id': request.id,
            'requester_id': request.requester_id,
            'requester_username': request.requester.username if request.requester else 'Unknown',
            'swap_with_id': request.swap_with_id,
            'swap_with_username': request.swap_with.username if request.swap_with else 'Unknown',
            'reason': request.reason,
            'original_date': request.original_date.isoformat() if request.original_date else None,
            'original_shift_code': request.original_shift_code,
            'swap_date': request.swap_date.isoformat() if request.swap_date else None,
            'swap_shift_code': request.swap_shift_code,
            'status': request.status,
            'created_at': request.created_at,
            'approved_at': request.approved_at
        }'''
            
            new_pattern = '''return {
            'id': request.id,
            'requester_id': request.requester_id,
            'requester_username': request.requester.username if request.requester else 'Unknown',
            'swap_with_id': request.swap_with_id,
            'swap_with_username': request.swap_with.username if request.swap_with else 'Unknown',
            'reason': request.reason,
            'original_date': request.original_date.isoformat() if request.original_date else None,
            'original_shift_code': request.original_shift_code,
            'swap_date': request.swap_date.isoformat() if request.swap_date else None,
            'swap_shift_code': request.swap_shift_code,
            'status': request.status,
            'created_at': request.created_at.strftime('%Y-%m-%d %H:%M:%S') if request.created_at else None,
            'approved_at': request.approved_at.strftime('%Y-%m-%d %H:%M:%S') if request.approved_at else None
        }'''
            
            content = content.replace(old_pattern, new_pattern)
            
            # Also fix _serialize_leave_request if it exists
            old_leave_pattern = '''return {
            'id': request.id,
            'requester_id': request.requester_id,
            'requester_username': request.requester.username if request.requester else 'Unknown',
            'leave_type': request.leave_type,
            'leave_date': request.leave_date.isoformat() if request.leave_date else None,
            'shift_code': request.shift_code,
            'reason': request.reason,
            'status': request.status,
            'created_at': request.created_at,
            'approved_at': request.approved_at
        }'''
            
            new_leave_pattern = '''return {
            'id': request.id,
            'requester_id': request.requester_id,
            'requester_username': request.requester.username if request.requester else 'Unknown',
            'leave_type': request.leave_type,
            'leave_date': request.leave_date.isoformat() if request.leave_date else None,
            'shift_code': request.shift_code,
            'reason': request.reason,
            'status': request.status,
            'created_at': request.created_at.strftime('%Y-%m-%d %H:%M:%S') if request.created_at else None,
            'approved_at': request.approved_at.strftime('%Y-%m-%d %H:%M:%S') if request.approved_at else None
        }'''
            
            content = content.replace(old_leave_pattern, new_leave_pattern)
            
            with open(service_path, 'w') as f:
                content = f.write(content)
            
            print("✅ Fixed datetime serialization in service methods")
            
        else:
            print("⚠️  _serialize_swap_request method not found - might need manual review")
            
    except Exception as e:
        print(f"❌ Error fixing service: {e}")
        import traceback
        traceback.print_exc()

    # Also create a simple template update to be safer
    template_path = '/app/templates/shift_management/dashboard.html'
    
    try:
        with open(template_path, 'r') as f:
            content = f.read()
        
        # Use a much simpler datetime display approach
        content = content.replace(
            "{{ request.created_at[:16] if request.created_at is string else request.created_at.strftime('%Y-%m-%d %H:%M') if request.created_at else 'Unknown' }}",
            "{{ request.created_at if request.created_at else 'Unknown' }}"
        )
        
        # Replace all other complex datetime formatting with simple display
        content = content.replace(
            ".strftime('%Y-%m-%d %H:%M')",
            ""
        )
        
        with open(template_path, 'w') as f:
            f.write(content)
        
        print("✅ Simplified template datetime display")
        
    except Exception as e:
        print(f"❌ Error simplifying template: {e}")

if __name__ == "__main__":
    fix_service_serialization()