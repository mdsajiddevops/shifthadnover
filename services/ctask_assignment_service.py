"""
CTask Assignment Service
Automatically assigns change tasks to engineers based on shift roster and planned execution time
"""
from datetime import datetime, time, date, timedelta
from typing import List, Dict, Optional, Tuple
from models.models import ShiftRoster, TeamMember, db
from services.servicenow_service import ServiceNowService
from services.console_service import console
import logging

class CTaskAssignmentService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        # Use the global configured ServiceNow instance
        from services.servicenow_service import servicenow_service
        self.servicenow = servicenow_service
        
        # Initialize scheduler state
        self.scheduler_state = {
            'status': 'Stopped',
            'last_check': None,
            'next_check': None,
            'check_interval': '2 minutes',
            'last_started': None,
            'last_stopped': None
        }
        
        # Define shift time mappings
        self.shift_times = {
            'D': {'start_time': time(6, 30), 'end_time': time(15, 30), 'name': 'Day/Morning'},
            'E': {'start_time': time(14, 45), 'end_time': time(23, 45), 'name': 'Evening'},
            'N': {'start_time': time(21, 45), 'end_time': time(6, 45), 'name': 'Night', 'crosses_midnight': True}
        }
    
    def get_engineer_on_duty(self, planned_date: date, planned_time: time, assignment_group: str = "Supply Chain - L2") -> Optional[Dict]:
        """
        Find engineer on duty during the planned execution time
        
        Args:
            planned_date: Date of planned execution
            planned_time: Time of planned execution
            assignment_group: Target assignment group
            
        Returns:
            Dict with engineer details or None if no engineer found
        """
        try:
            # Determine which shift covers the planned time
            target_shift_code = self._determine_shift_for_time(planned_time, planned_date)
            
            if not target_shift_code:
                console.warning(f"⚠️ Could not determine shift for time {planned_time}")
                self.logger.warning(f"Could not determine shift for time {planned_time}")
                return None
            
            shift_name = self.shift_times[target_shift_code]['name']
            console.info(f"🕒 Shift Detection: {planned_time} → {target_shift_code} ({shift_name})", {
                'time': str(planned_time),
                'shift_code': target_shift_code,
                'shift_name': shift_name,
                'date': str(planned_date)
            })
            
            self.logger.info(f"Looking for {target_shift_code} shift engineer on {planned_date} at {planned_time}")
            
            # Query shift roster for engineers on duty
            engineers_on_duty = self._get_engineers_on_shift(planned_date, target_shift_code)
            
            if not engineers_on_duty:
                console.warning(f"❌ No engineers found on {target_shift_code} shift for {planned_date}")
                self.logger.warning(f"No engineers found on {target_shift_code} shift for {planned_date}")
                return None
            
            console.info(f"👥 Found {len(engineers_on_duty)} engineers on {target_shift_code} shift", {
                'engineers': [e['name'] for e in engineers_on_duty],
                'shift_code': target_shift_code,
                'date': str(planned_date)
            })
            
            # Sort engineers alphabetically and return the first one
            engineers_on_duty.sort(key=lambda x: x['name'].lower())
            selected_engineer = engineers_on_duty[0]
            
            console.success(f"🎯 Selected engineer (alphabetical): {selected_engineer['name']}", {
                'selected_engineer': selected_engineer['name'],
                'all_available': [e['name'] for e in engineers_on_duty],
                'selection_method': 'First alphabetically'
            })
            
            self.logger.info(f"Selected engineer: {selected_engineer['name']} for {target_shift_code} shift")
            return selected_engineer
            
        except Exception as e:
            self.logger.error(f"Error finding engineer on duty: {str(e)}")
            return None
    
    def _determine_shift_for_time(self, planned_time: time, planned_date: date) -> Optional[str]:
        """
        Determine which shift code covers the given time
        
        Args:
            planned_time: Time to check
            planned_date: Date to check (needed for night shift logic)
            
        Returns:
            Shift code ('D', 'E', 'N') or None
        """
        try:
            # Convert time to datetime for easier comparison
            planned_datetime = datetime.combine(planned_date, planned_time)
            
            for shift_code, shift_info in self.shift_times.items():
                if shift_info.get('crosses_midnight', False):
                    # Night shift: 21:45 to 06:45 next day
                    start_datetime = datetime.combine(planned_date, shift_info['start_time'])
                    end_datetime = datetime.combine(planned_date + timedelta(days=1), shift_info['end_time'])
                    
                    if start_datetime <= planned_datetime <= end_datetime:
                        return shift_code
                else:
                    # Day/Evening shift: same day
                    start_datetime = datetime.combine(planned_date, shift_info['start_time'])
                    end_datetime = datetime.combine(planned_date, shift_info['end_time'])
                    
                    if start_datetime <= planned_datetime <= end_datetime:
                        return shift_code
            
            # Check if it's early morning (before 6:30) - could be night shift from previous day
            if planned_time < time(6, 30):
                # Check if this is within night shift from previous day
                prev_date = planned_date - timedelta(days=1)
                night_start = datetime.combine(prev_date, self.shift_times['N']['start_time'])
                night_end = datetime.combine(planned_date, self.shift_times['N']['end_time'])
                
                if night_start <= planned_datetime <= night_end:
                    return 'N'
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error determining shift for time {planned_time}: {str(e)}")
            return None
    
    def _get_engineers_on_shift(self, shift_date: date, shift_code: str) -> List[Dict]:
        """
        Get engineers assigned to a specific shift on a given date
        
        Args:
            shift_date: Date to check
            shift_code: Shift code ('D', 'E', 'N')
            
        Returns:
            List of engineer dictionaries
        """
        try:
            # Query shift roster for engineers on the specified shift
            roster_entries = db.session.query(ShiftRoster, TeamMember).join(
                TeamMember, ShiftRoster.team_member_id == TeamMember.id
            ).filter(
                ShiftRoster.date == shift_date,
                ShiftRoster.shift_code == shift_code
            ).all()
            
            engineers = []
            for roster_entry, team_member in roster_entries:
                engineers.append({
                    'id': team_member.id,
                    'name': team_member.name,
                    'email': team_member.email,
                    'contact_number': team_member.contact_number,
                    'shift_code': roster_entry.shift_code,
                    'date': roster_entry.date
                })
            
            self.logger.info(f"Found {len(engineers)} engineers on {shift_code} shift for {shift_date}")
            return engineers
            
        except Exception as e:
            self.logger.error(f"Error getting engineers on shift: {str(e)}")
            return []
    
    def auto_assign_ctask(self, ctask_number: str, planned_date_str: str, planned_time_str: str) -> Dict:
        """
        Automatically assign a CTask to an engineer based on shift roster
        
        Args:
            ctask_number: Change task number (e.g., 'CTASK0010001')
            planned_date_str: Planned date in 'YYYY-MM-DD' format
            planned_time_str: Planned time in 'HH:MM:SS' format
            
        Returns:
            Dict with assignment result
        """
        try:
            # Parse date and time
            planned_date = datetime.strptime(planned_date_str, '%Y-%m-%d').date()
            planned_time = datetime.strptime(planned_time_str, '%H:%M:%S').time()
            
            console.info(f"🎯 Starting auto-assignment for {ctask_number}", {
                'ctask': ctask_number,
                'planned_date': planned_date_str,
                'planned_time': planned_time_str
            })
            
            self.logger.info(f"Auto-assigning {ctask_number} for {planned_date} at {planned_time}")
            
            # Find engineer on duty
            engineer = self.get_engineer_on_duty(planned_date, planned_time)
            
            if not engineer:
                console.warning(f"❌ No engineer found on duty", {
                    'ctask': ctask_number,
                    'planned_date': planned_date_str,
                    'planned_time': planned_time_str
                })
                return {
                    'success': False,
                    'message': f'No engineer found on duty for {planned_date} at {planned_time}',
                    'ctask_number': ctask_number
                }
            
            console.success(f"✅ Found engineer on duty: {engineer['name']}", {
                'engineer_name': engineer['name'],
                'engineer_email': engineer['email'],
                'shift_code': engineer['shift_code'],
                'shift_date': planned_date_str
            })
            
            # Assign the CTask to the engineer via ServiceNow API
            assignment_result = self._assign_ctask_in_servicenow(ctask_number, engineer)
            
            if assignment_result['success']:
                console.success(f"🎉 Assignment completed successfully!", {
                    'ctask': ctask_number,
                    'assigned_to': engineer['name'],
                    'assignment_method': 'Automatic shift-based assignment',
                    'shift_logic': f"Time {planned_time_str} → {engineer['shift_code']} shift → First engineer alphabetically"
                })
                
                return {
                    'success': True,
                    'message': f'Successfully assigned {ctask_number} to {engineer["name"]}',
                    'ctask_number': ctask_number,
                    'assigned_to': engineer['name'],
                    'assigned_email': engineer['email'],
                    'shift_code': engineer['shift_code'],
                    'planned_date': planned_date_str,
                    'planned_time': planned_time_str,
                    'assignment_method': 'Automatic shift-based assignment'
                }
            else:
                console.error(f"❌ ServiceNow assignment failed", {
                    'ctask': ctask_number,
                    'intended_engineer': engineer['name'],
                    'error': assignment_result.get('message', 'Unknown error')
                })
                
                return {
                    'success': False,
                    'message': f'Found engineer {engineer["name"]} but failed to assign in ServiceNow: {assignment_result["message"]}',
                    'ctask_number': ctask_number,
                    'suggested_engineer': engineer['name']
                }
                
        except Exception as e:
            self.logger.error(f"Error auto-assigning CTask {ctask_number}: {str(e)}")
            console.error(f"💥 Exception during assignment", {
                'ctask': ctask_number,
                'error': str(e)
            })
            return {
                'success': False,
                'message': f'Error auto-assigning CTask: {str(e)}',
                'ctask_number': ctask_number
            }
    
    def _assign_ctask_in_servicenow(self, ctask_number: str, engineer: Dict) -> Dict:
        """
        Assign the CTask to engineer in ServiceNow
        
        Args:
            ctask_number: Change task number
            engineer: Engineer details dictionary
            
        Returns:
            Dict with assignment result
        """
        try:
            self.logger.info(f"Assigning {ctask_number} to {engineer['name']} ({engineer['email']}) in ServiceNow")
            
            # Check if ServiceNow is properly configured
            if not self.servicenow.is_configured():
                self.logger.warning("ServiceNow not configured - simulating assignment")
                return {
                    'success': True,
                    'message': f'Assignment simulated (ServiceNow not configured in dev mode)',
                    'simulated': True
                }
            
            # Use ServiceNow API to assign the change task
            result = self.servicenow.assign_change_task(ctask_number, engineer['email'])
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error assigning CTask in ServiceNow: {str(e)}")
            return {
                'success': False,
                'message': f'ServiceNow assignment failed: {str(e)}'
            }
    
    def process_pending_ctasks(self) -> List[Dict]:
        """
        Process all pending CTasks that need assignment
        
        Returns:
            List of assignment results
        """
        try:
            self.logger.info("Processing pending CTasks for auto-assignment...")
            
            # Get all unassigned CTasks from ServiceNow
            unassigned_data = self.servicenow.get_unassigned_change_tasks()
            
            if 'error' in unassigned_data:
                self.logger.error(f"Error fetching unassigned CTasks: {unassigned_data['error']}")
                return []
            
            unassigned_ctasks = unassigned_data.get('change_tasks', [])
            self.logger.info(f"Found {len(unassigned_ctasks)} unassigned CTasks")
            
            results = []
            
            for ctask in unassigned_ctasks:
                try:
                    ctask_number = ctask.get('number')
                    
                    # Try to extract planned date and time from the task
                    planned_date_str, planned_time_str = self._extract_planned_datetime(ctask)
                    
                    if not planned_date_str or not planned_time_str:
                        # Check if this is a Supply Chain L2 task that should get fallback timing
                        assignment_group = ctask.get('assignment_group', '')
                        state = ctask.get('state', '')
                        
                        # Handle different data formats
                        if isinstance(assignment_group, dict):
                            group_name = assignment_group.get('display_value', '')
                        else:
                            group_name = assignment_group
                            
                        if isinstance(state, dict):
                            state_name = state.get('display_value', '')
                        else:
                            state_name = state
                        
                        if group_name == 'Supply Chain - L2' and state_name == 'Open':
                            # Use current time as fallback for eligible CTasks
                            from datetime import datetime
                            now = datetime.now()
                            planned_date_str = now.strftime('%Y-%m-%d')
                            planned_time_str = now.strftime('%H:%M:%S')
                            self.logger.info(f"Using current time fallback for eligible CTask {ctask_number}")
                        else:
                            results.append({
                                'success': False,
                                'message': f'CTask {ctask_number} not eligible: Group={group_name}, State={state_name}',
                                'ctask_number': ctask_number
                            })
                            continue
                    
                    if not planned_date_str or not planned_time_str:
                        results.append({
                            'success': False,
                            'message': f'No planned date/time found for {ctask_number}',
                            'ctask_number': ctask_number
                        })
                        continue
                    
                    # Auto-assign the CTask
                    assignment_result = self.auto_assign_ctask(ctask_number, planned_date_str, planned_time_str)
                    results.append(assignment_result)
                    
                except Exception as e:
                    self.logger.error(f"Error processing CTask {ctask.get('number', 'Unknown')}: {str(e)}")
                    results.append({
                        'success': False,
                        'message': f'Error processing {ctask.get("number", "Unknown")}: {str(e)}',
                        'ctask_number': ctask.get('number', 'Unknown')
                    })
            
            successful = len([r for r in results if r['success']])
            self.logger.info(f"Processed {len(results)} CTasks: {successful} successful, {len(results) - successful} failed")
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error processing pending CTasks: {str(e)}")
            return []
    
    def _extract_planned_datetime(self, ctask: Dict) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract planned date and time from CTask record
        
        Args:
            ctask: CTask record dictionary
            
        Returns:
            Tuple of (date_str, time_str) or (None, None) if not found
        """
        try:
            # Try different date/time fields
            date_fields = ['planned_start_date', 'work_start', 'planned_end_date', 'work_end']
            
            for field in date_fields:
                datetime_str = ctask.get(field, '')
                
                # Handle both string and dict formats
                if isinstance(datetime_str, dict):
                    # ServiceNow returns dict with display_value and value
                    datetime_str = datetime_str.get('display_value') or datetime_str.get('value', '')
                
                if datetime_str and datetime_str.strip():
                    try:
                        # Parse ServiceNow datetime format
                        if ' ' in datetime_str:
                            date_part, time_part = datetime_str.split(' ', 1)
                            # Return first valid date/time found
                            return date_part, time_part
                        else:
                            # If only date is provided, assume 09:00:00
                            return datetime_str, '09:00:00'
                    except:
                        continue
            
            # FALLBACK: If no timing data found but CTask has proper assignment group and is Open,
            # use current time to allow immediate assignment
            ctask_number = ctask.get('number', '')
            assignment_group = ctask.get('assignment_group', '')
            state = ctask.get('state', '')
            
            # Handle assignment group formats
            if isinstance(assignment_group, dict):
                group_name = assignment_group.get('display_value', '')
            else:
                group_name = assignment_group
            
            # Handle state formats  
            if isinstance(state, dict):
                state_name = state.get('display_value', '')
            else:
                state_name = state
            
            # If CTask is eligible but has no timing, use current time as fallback
            if group_name == 'Supply Chain - L2' and state_name == 'Open':
                self.logger.info(f"Using current time fallback for {ctask_number} - no timing data in ServiceNow")
                from datetime import datetime
                now = datetime.now()
                return now.strftime('%Y-%m-%d'), now.strftime('%H:%M:%S')
            
            return None, None
            
        except Exception as e:
            self.logger.error(f"Error extracting planned datetime: {str(e)}")
            return None, None
    
    def get_shift_schedule(self, start_date: date, end_date: date) -> Dict:
        """
        Get shift schedule for a date range
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            Dict with shift schedule
        """
        try:
            schedule = {}
            
            roster_entries = db.session.query(ShiftRoster, TeamMember).join(
                TeamMember, ShiftRoster.team_member_id == TeamMember.id
            ).filter(
                ShiftRoster.date >= start_date,
                ShiftRoster.date <= end_date
            ).order_by(ShiftRoster.date, ShiftRoster.shift_code, TeamMember.name).all()
            
            for roster_entry, team_member in roster_entries:
                date_str = roster_entry.date.strftime('%Y-%m-%d')
                if date_str not in schedule:
                    schedule[date_str] = {'D': [], 'E': [], 'N': []}
                
                if roster_entry.shift_code in schedule[date_str]:
                    schedule[date_str][roster_entry.shift_code].append({
                        'name': team_member.name,
                        'email': team_member.email,
                        'contact': team_member.contact_number
                    })
            
            return schedule
            
        except Exception as e:
            self.logger.error(f"Error getting shift schedule: {str(e)}")
            return {}
    
    def start_scheduler(self) -> Dict:
        """
        Start the automatic assignment scheduler
        
        Returns:
            Dict with operation result
        """
        try:
            current_time = datetime.now()
            
            # Update scheduler state
            self.scheduler_state.update({
                'status': 'Running',
                'last_started': current_time,
                'last_check': current_time,
                'next_check': current_time + timedelta(minutes=2)
            })
            
            # For now, this is a placeholder - in a real implementation,
            # this would start a background scheduler service
            console.success("🚀 Automatic assignment scheduler started")
            self.logger.info("Automatic assignment scheduler started")
            
            return {
                'success': True,
                'status': 'Running',
                'message': 'Scheduler started successfully',
                'last_started': current_time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            console.error(f"❌ Failed to start scheduler: {str(e)}")
            self.logger.error(f"Error starting scheduler: {str(e)}")
            return {
                'success': False,
                'status': 'Stopped',
                'message': f'Error starting scheduler: {str(e)}'
            }
    
    def stop_scheduler(self) -> Dict:
        """
        Stop the automatic assignment scheduler
        
        Returns:
            Dict with operation result
        """
        try:
            current_time = datetime.now()
            
            # Update scheduler state
            self.scheduler_state.update({
                'status': 'Stopped',
                'last_stopped': current_time,
                'next_check': None
            })
            
            # For now, this is a placeholder - in a real implementation,
            # this would stop a background scheduler service
            console.warning("⏹️ Automatic assignment scheduler stopped")
            self.logger.info("Automatic assignment scheduler stopped")
            
            return {
                'success': True,
                'status': 'Stopped',
                'message': 'Scheduler stopped successfully',
                'last_stopped': current_time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            console.error(f"❌ Failed to stop scheduler: {str(e)}")
            self.logger.error(f"Error stopping scheduler: {str(e)}")
            return {
                'success': False,
                'status': 'Unknown',
                'message': f'Error stopping scheduler: {str(e)}'
            }
    
    def get_scheduler_status(self) -> Dict:
        """
        Get current scheduler status
        
        Returns:
            Dict with scheduler status information
        """
        try:
            current_time = datetime.now()
            
            # Format times for display
            last_check = 'Never'
            next_check = 'Unknown'
            
            if self.scheduler_state.get('last_check'):
                last_check = self.scheduler_state['last_check'].strftime('%Y-%m-%d %H:%M:%S')
            
            if self.scheduler_state.get('next_check'):
                next_check = self.scheduler_state['next_check'].strftime('%Y-%m-%d %H:%M:%S')
            
            return {
                'status': self.scheduler_state.get('status', 'Stopped'),
                'last_check': last_check,
                'next_check': next_check,
                'check_interval': self.scheduler_state.get('check_interval', '2 minutes'),
                'last_updated': current_time.strftime('%Y-%m-%d %H:%M:%S'),
                'last_started': self.scheduler_state.get('last_started'),
                'last_stopped': self.scheduler_state.get('last_stopped')
            }
            
        except Exception as e:
            self.logger.error(f"Error getting scheduler status: {str(e)}")
            return {
                'status': 'Unknown',
                'last_check': 'Error',
                'next_check': 'Error',
                'check_interval': 'Unknown',
                'error': str(e)
            }