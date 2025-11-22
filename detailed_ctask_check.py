#!/usr/bin/env python3
"""
Detailed fetch of CTASK0010016 with all fields and fresh data
"""
from app import app
from services.servicenow_service import servicenow_service
from urllib.parse import urljoin
import json
from datetime import datetime

def detailed_check():
    with app.app_context():
        print("🔍 DETAILED FETCH OF CTASK0010016")
        print("=" * 60)
        
        # Try multiple approaches to get fresh data
        queries = [
            f'/api/now/table/change_task?sysparm_query=number=CTASK0010016&sysparm_display_value=all&sysparm_exclude_reference_link=true',
            f'/api/now/table/change_task?sysparm_query=number=CTASK0010016',
            f'/api/now/table/change_task?sysparm_query=numberSTARTSWITHCTASK0010016'
        ]
        
        for i, query_path in enumerate(queries, 1):
            print(f"\n{i}️⃣ ATTEMPT {i}: {query_path.split('?')[1] if '?' in query_path else 'Basic query'}")
            print("-" * 50)
            
            try:
                ct_url = urljoin(servicenow_service.instance_url, query_path)
                response = servicenow_service.session.get(ct_url, timeout=servicenow_service.timeout)
                
                print(f"   📡 Response Status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"   📊 Results Count: {len(data.get('result', []))}")
                    
                    if data['result']:
                        ctask = data['result'][0]
                        
                        print(f"   📋 Number: {ctask.get('number')}")
                        print(f"   📝 Description: {ctask.get('short_description', 'N/A')}")
                        
                        # State handling
                        state = ctask.get('state', '')
                        if isinstance(state, dict):
                            state_value = state.get('value', '')
                            state_display = state.get('display_value', 'Unknown')
                            print(f"   🔄 State: {state_display} (value: {state_value})")
                        else:
                            state_display = state
                            print(f"   🔄 State: {state} (raw)")
                        
                        # Assignment Group handling
                        assignment_group = ctask.get('assignment_group', '')
                        if isinstance(assignment_group, dict):
                            group_value = assignment_group.get('value', '')
                            group_display = assignment_group.get('display_value', 'Not set')
                            print(f"   👥 Assignment Group: {group_display} (ID: {group_value})")
                        else:
                            print(f"   👥 Assignment Group: {assignment_group or 'Not set'} (raw)")
                        
                        # Assigned To
                        assigned_to = ctask.get('assigned_to', '')
                        if assigned_to:
                            if isinstance(assigned_to, dict):
                                assigned_display = assigned_to.get('display_value', 'Unknown')
                                assigned_value = assigned_to.get('value', '')
                                print(f"   ✅ ASSIGNED TO: {assigned_display} (ID: {assigned_value})")
                            else:
                                print(f"   ✅ ASSIGNED TO: {assigned_to}")
                        else:
                            print(f"   ❌ NOT ASSIGNED")
                        
                        # Timing fields
                        print(f"   📅 Planned Start: {ctask.get('planned_start_date') or 'Not set'}")
                        print(f"   📅 Planned End: {ctask.get('planned_end_date') or 'Not set'}")
                        print(f"   🔨 Work Start: {ctask.get('work_start') or 'Not set'}")
                        print(f"   🔨 Work End: {ctask.get('work_end') or 'Not set'}")
                        
                        # Timestamps
                        print(f"   📅 Created: {ctask.get('sys_created_on', 'Unknown')}")
                        print(f"   📅 Updated: {ctask.get('sys_updated_on', 'Unknown')}")
                        
                        # Check eligibility
                        has_timing = ctask.get('planned_start_date') or ctask.get('work_start')
                        
                        if isinstance(assignment_group, dict):
                            has_correct_group = assignment_group.get('display_value') == 'Supply Chain - L2'
                        else:
                            has_correct_group = assignment_group == 'Supply Chain - L2' or assignment_group == 'b7cc19d8836432104b5fe590ceaad33d'
                        
                        if isinstance(state, dict):
                            is_open = state.get('display_value') == 'Open' or state.get('value') == '2'
                        else:
                            is_open = state == 'Open' or state == '2'
                        
                        print(f"\n   🎯 ELIGIBILITY CHECK:")
                        print(f"      📅 Has timing: {'✅ Yes' if has_timing else '❌ No'}")
                        print(f"      👥 Correct group: {'✅ Yes' if has_correct_group else '❌ No'}")
                        print(f"      🔓 Is Open: {'✅ Yes' if is_open else '❌ No'}")
                        
                        eligible = has_timing and has_correct_group and is_open
                        print(f"      🎯 ELIGIBLE: {'✅ YES' if eligible else '❌ NO'}")
                        
                        if eligible and not assigned_to:
                            print(f"\n   💡 This CTask should be picked up by the background scheduler!")
                            print(f"      ⏰ Next scheduler run: Within 2 minutes")
                            
                            # Test manual assignment
                            print(f"\n   🧪 TESTING MANUAL ASSIGNMENT:")
                            try:
                                from services.ctask_assignment_service import CTaskAssignmentService
                                
                                timing_source = ctask.get('planned_start_date') or ctask.get('work_start')
                                if timing_source:
                                    # Parse timing
                                    if isinstance(timing_source, dict):
                                        timing_str = timing_source.get('display_value') or timing_source.get('value', '')
                                    else:
                                        timing_str = timing_source
                                    
                                    print(f"      📅 Using timing: {timing_str}")
                                    
                                    if timing_str:
                                        try:
                                            # Parse the datetime
                                            if 'T' in timing_str:
                                                dt = datetime.fromisoformat(timing_str.replace('Z', '+00:00'))
                                            else:
                                                dt = datetime.strptime(timing_str, '%Y-%m-%d %H:%M:%S')
                                            
                                            planned_date = dt.strftime('%Y-%m-%d')
                                            planned_time = dt.strftime('%H:%M:%S')
                                            
                                            assignment_service = CTaskAssignmentService()
                                            result = assignment_service.auto_assign_ctask('CTASK0010016', planned_date, planned_time)
                                            
                                            if result.get('success'):
                                                print(f"      ✅ MANUAL TEST SUCCESS!")
                                                print(f"      👤 Would assign to: {result.get('assigned_to')}")
                                                print(f"      🕐 Shift: {result.get('shift_code')}")
                                            else:
                                                print(f"      ❌ Manual test failed: {result.get('message')}")
                                        except Exception as e:
                                            print(f"      ❌ Error parsing timing: {e}")
                                            
                            except Exception as e:
                                print(f"      ❌ Error testing assignment: {e}")
                        
                        break  # Found the CTask, no need to try other queries
                    else:
                        print(f"   ❌ No results found")
                else:
                    print(f"   ❌ HTTP Error: {response.status_code}")
                    print(f"   Response: {response.text[:200]}...")
                    
            except Exception as e:
                print(f"   ❌ Exception: {e}")

if __name__ == '__main__':
    detailed_check()