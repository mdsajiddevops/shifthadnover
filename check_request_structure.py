#!/usr/bin/env python3

# Check swap request data structure and create enhanced template
import sys
sys.path.append('/app')
import os
os.chdir('/app')

from app import app
from models.shift_swap_leave import ShiftSwapRequest
from services.shift_swap_leave_service import ShiftSwapLeaveService

def check_swap_request_structure():
    """Check the current swap request data structure"""
    
    with app.app_context():
        print("=== Checking Swap Request Data Structure ===")
        
        # Get a recent swap request
        request = ShiftSwapRequest.query.order_by(ShiftSwapRequest.created_at.desc()).first()
        if request:
            print("Raw SwapRequest fields:")
            print(f"ID: {request.id}")
            print(f"Requester ID: {request.requester_id}")
            print(f"Swap with ID: {request.swap_with_id}")
            print(f"Original date: {request.original_date}")
            print(f"Original shift: {request.original_shift_code}")
            print(f"Swap date: {request.swap_date}")
            print(f"Swap shift: {request.swap_shift_code}")
            print(f"Status: {request.status}")
            print(f"Reason: {request.reason}")
            print(f"Created at: {request.created_at}")
            
            # Check relationships
            if hasattr(request, 'requester') and request.requester:
                print(f"Requester name: {request.requester.username}")
                print(f"Requester full name: {request.requester.first_name} {request.requester.last_name}")
                
            if hasattr(request, 'swap_with') and request.swap_with:
                print(f"Swap with name: {request.swap_with.username}")
                print(f"Swap with full name: {request.swap_with.first_name} {request.swap_with.last_name}")
            
            print("\n" + "="*50)
            
            # Check serialized version
            service = ShiftSwapLeaveService()
            try:
                serialized = service._serialize_swap_request(request)
                print("Serialized version structure:")
                for key, value in serialized.items():
                    print(f"  {key}: {value}")
            except Exception as e:
                print(f"Error serializing: {e}")
        else:
            print("No swap requests found")

def check_pending_requests_format():
    """Check how pending requests are formatted for admin"""
    
    with app.app_context():
        print("\n=== Checking Pending Requests Format ===")
        
        service = ShiftSwapLeaveService()
        try:
            # Simulate getting pending requests for admin (user ID 1)
            pending = service.get_pending_requests_for_approval(1)
            print("Pending requests structure:")
            print(f"Success: {pending.get('success')}")
            if pending.get('swap_requests'):
                print(f"Found {len(pending['swap_requests'])} pending swap requests")
                for i, req in enumerate(pending['swap_requests'][:1]):  # Show first one
                    print(f"Request {i+1} structure:")
                    for key, value in req.items():
                        print(f"  {key}: {value}")
            else:
                print("No pending swap requests found")
                
        except Exception as e:
            print(f"Error getting pending requests: {e}")

if __name__ == "__main__":
    check_swap_request_structure()
    check_pending_requests_format()