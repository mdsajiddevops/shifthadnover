"""
Shift Swap & Leave Management Service
Handles the business logic for shift swap and leave requests with approval workflow
"""

from datetime import datetime, date
from flask import current_app
from flask_login import current_user
from models.models import db, User, TeamMember, ShiftRoster, Team, Account
from models.shift_swap_leave import (
    ShiftSwapRequest, LeaveRequest, SwapLeaveNotification, SwapLeaveAuditLog
)
from services.email_service import send_incident_assignment_notification
from services.shift_email_service import shift_email_service
from typing import List, Dict, Optional, Tuple
import logging
import json

logger = logging.getLogger(__name__)

class ShiftSwapLeaveService:
    """Service for managing shift swap and leave requests"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def get_eligible_swap_partners(self, requester_id: int, request_date: date, shift_code: str) -> List[Dict]:
        """Get list of eligible team members for shift swapping"""
        try:
            requester = User.query.get(requester_id)
            if not requester:
                return []
            
            # Get team members from same account/team
            eligible_members = User.query.filter(
                User.account_id == requester.account_id,
                User.team_id == requester.team_id,
                User.id != requester_id,
                User.is_active == True,
                User.role.in_(['user', 'team_admin'])  # Only regular users and team admins can swap
            ).all()
            
            # Check who is available on the requested date
            available_partners = []
            for member in eligible_members:
                # Check if they have any shift on that date
                existing_roster = ShiftRoster.query.filter_by(
                    date=request_date,
                    team_member_id=self._get_team_member_id_for_user(member.id),
                    account_id=requester.account_id,
                    team_id=requester.team_id
                ).first()
                
                # If they have a different shift or no shift, they're eligible
                if not existing_roster or existing_roster.shift_code != shift_code:
                    available_partners.append({
                        'id': member.id,
                        'username': member.username,
                        'full_name': f"{member.first_name} {member.last_name}",
                        'email': member.email,
                        'current_shift': existing_roster.shift_code if existing_roster else 'Off',
                        'can_swap': True
                    })
            
            return available_partners
            
        except Exception as e:
            self.logger.error(f"Error getting eligible swap partners: {str(e)}")
            return []
    
    def create_shift_swap_request(self, requester_id: int, swap_with_id: int, 
                                original_date: date, original_shift_code: str,
                                swap_date: date, swap_shift_code: str, reason: str) -> Dict:
        """Create a new shift swap request"""
        try:
            requester = User.query.get(requester_id)
            swap_with = User.query.get(swap_with_id)
            
            if not requester or not swap_with:
                return {'success': False, 'error': 'Invalid users'}
            
            # Validate that both users are in the same team
            if requester.account_id != swap_with.account_id or requester.team_id != swap_with.team_id:
                return {'success': False, 'error': 'Can only swap with team members'}
            
            # Check for existing pending requests
            existing_request = ShiftSwapRequest.query.filter(
                ShiftSwapRequest.requester_id == requester_id,
                ShiftSwapRequest.swap_with_id == swap_with_id,
                ShiftSwapRequest.status == 'pending',
                ShiftSwapRequest.original_date == original_date
            ).first()
            
            if existing_request:
                return {'success': False, 'error': 'Pending swap request already exists'}
            
            # Create the swap request
            swap_request = ShiftSwapRequest(
                requester_id=requester_id,
                swap_with_id=swap_with_id,
                reason=reason,
                original_date=original_date,
                original_shift_code=original_shift_code,
                swap_date=swap_date,
                swap_shift_code=swap_shift_code,
                account_id=requester.account_id,
                team_id=requester.team_id
            )
            
            db.session.add(swap_request)
            db.session.flush()  # Get the ID
            
            # Create audit log
            self._create_audit_log(
                action='swap_request_created',
                performed_by_id=requester_id,
                target_user_id=swap_with_id,
                swap_request_id=swap_request.id,
                details=f"Swap request created: {original_date} {original_shift_code} <-> {swap_date} {swap_shift_code}",
                account_id=requester.account_id,
                team_id=requester.team_id
            )
            
            # Send notifications
            self._send_swap_request_notifications(swap_request)
            
            db.session.commit()
            
            return {'success': True, 'request_id': swap_request.id}
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Error creating shift swap request: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def create_leave_request(self, requester_id: int, leave_type: str, leave_date: date, 
                           shift_code: str, reason: str = '') -> Dict:
        """Create a new leave request"""
        try:
            requester = User.query.get(requester_id)
            if not requester:
                return {'success': False, 'error': 'Invalid user'}
            
            # Check for existing requests on the same date
            existing_request = LeaveRequest.query.filter(
                LeaveRequest.requester_id == requester_id,
                LeaveRequest.leave_date == leave_date,
                LeaveRequest.status.in_(['pending', 'approved'])
            ).first()
            
            if existing_request:
                return {'success': False, 'error': 'Leave request already exists for this date'}
            
            # Create the leave request
            leave_request = LeaveRequest(
                requester_id=requester_id,
                leave_type=leave_type,
                leave_date=leave_date,
                shift_code=shift_code,
                reason=reason,
                account_id=requester.account_id,
                team_id=requester.team_id
            )
            
            db.session.add(leave_request)
            db.session.flush()  # Get the ID
            
            # Create audit log
            self._create_audit_log(
                action='leave_request_created',
                performed_by_id=requester_id,
                leave_request_id=leave_request.id,
                details=f"Leave request created: {leave_type} on {leave_date} ({shift_code} shift)",
                account_id=requester.account_id,
                team_id=requester.team_id
            )
            
            # Send notifications
            self._send_leave_request_notifications(leave_request)
            
            db.session.commit()
            
            return {'success': True, 'request_id': leave_request.id}
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Error creating leave request: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def approve_swap_request(self, request_id: int, approver_id: int, comments: str = '') -> Dict:
        """Approve a shift swap request and update roster"""
        try:
            swap_request = ShiftSwapRequest.query.get(request_id)
            if not swap_request:
                return {'success': False, 'error': 'Request not found'}
            
            if swap_request.status != 'pending':
                return {'success': False, 'error': 'Request is not pending'}
            
            approver = User.query.get(approver_id)
            if not approver:
                return {'success': False, 'error': 'Invalid approver'}
            
            # Check approver permissions
            if not self._can_approve_request(approver, swap_request.account_id, swap_request.team_id):
                return {'success': False, 'error': 'Insufficient permissions to approve'}
            
            # Update the swap request
            swap_request.status = 'approved'
            swap_request.approved_by_id = approver_id
            swap_request.approval_comments = comments
            swap_request.approved_at = datetime.utcnow()
            
            # Update the roster entries
            result = self._execute_roster_swap(swap_request)
            if not result['success']:
                db.session.rollback()
                return result
            
            # Create audit log
            self._create_audit_log(
                action='swap_request_approved',
                performed_by_id=approver_id,
                target_user_id=swap_request.requester_id,
                swap_request_id=request_id,
                details=f"Swap request approved and roster updated. Comments: {comments}",
                account_id=swap_request.account_id,
                team_id=swap_request.team_id
            )
            
            # Send approval notifications
            self._send_swap_approval_notifications(swap_request, True)
            
            db.session.commit()
            
            return {'success': True, 'message': 'Swap request approved and roster updated'}
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Error approving swap request: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def approve_leave_request(self, request_id: int, approver_id: int, comments: str = '', 
                            covered_by_id: int = None) -> Dict:
        """Approve a leave request and update roster"""
        try:
            leave_request = LeaveRequest.query.get(request_id)
            if not leave_request:
                return {'success': False, 'error': 'Request not found'}
            
            if leave_request.status != 'pending':
                return {'success': False, 'error': 'Request is not pending'}
            
            approver = User.query.get(approver_id)
            if not approver:
                return {'success': False, 'error': 'Invalid approver'}
            
            # Check approver permissions
            if not self._can_approve_request(approver, leave_request.account_id, leave_request.team_id):
                return {'success': False, 'error': 'Insufficient permissions to approve'}
            
            # Update the leave request
            leave_request.status = 'approved'
            leave_request.approved_by_id = approver_id
            leave_request.approval_comments = comments
            leave_request.approved_at = datetime.utcnow()
            leave_request.covered_by_id = covered_by_id
            
            # Update the roster
            result = self._execute_leave_roster_update(leave_request, covered_by_id)
            if not result['success']:
                db.session.rollback()
                return result
            
            # Create audit log
            self._create_audit_log(
                action='leave_request_approved',
                performed_by_id=approver_id,
                target_user_id=leave_request.requester_id,
                leave_request_id=request_id,
                details=f"Leave request approved and roster updated. Coverage: {covered_by_id or 'None'}",
                account_id=leave_request.account_id,
                team_id=leave_request.team_id
            )
            
            # Send approval notifications
            self._send_leave_approval_notifications(leave_request, True)
            
            db.session.commit()
            
            return {'success': True, 'message': 'Leave request approved and roster updated'}
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Error approving leave request: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def reject_request(self, request_type: str, request_id: int, approver_id: int, comments: str) -> Dict:
        """Reject a swap or leave request"""
        try:
            if request_type == 'swap':
                request_obj = ShiftSwapRequest.query.get(request_id)
            else:
                request_obj = LeaveRequest.query.get(request_id)
            
            if not request_obj:
                return {'success': False, 'error': 'Request not found'}
            
            if request_obj.status != 'pending':
                return {'success': False, 'error': 'Request is not pending'}
            
            approver = User.query.get(approver_id)
            if not approver:
                return {'success': False, 'error': 'Invalid approver'}
            
            # Check approver permissions
            if not self._can_approve_request(approver, request_obj.account_id, request_obj.team_id):
                return {'success': False, 'error': 'Insufficient permissions to reject'}
            
            # Update the request
            request_obj.status = 'rejected'
            request_obj.approved_by_id = approver_id
            request_obj.approval_comments = comments
            request_obj.approved_at = datetime.utcnow()
            
            # Create audit log
            self._create_audit_log(
                action=f'{request_type}_request_rejected',
                performed_by_id=approver_id,
                target_user_id=request_obj.requester_id,
                swap_request_id=request_id if request_type == 'swap' else None,
                leave_request_id=request_id if request_type == 'leave' else None,
                details=f"{request_type.title()} request rejected. Comments: {comments}",
                account_id=request_obj.account_id,
                team_id=request_obj.team_id
            )
            
            # Send rejection notifications
            if request_type == 'swap':
                self._send_swap_approval_notifications(request_obj, False)
            else:
                self._send_leave_approval_notifications(request_obj, False)
            
            db.session.commit()
            
            return {'success': True, 'message': f'{request_type.title()} request rejected'}
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Error rejecting {request_type} request: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_pending_requests_for_approval(self, approver_id: int) -> Dict:
        """Get pending requests that the user can approve"""
        try:
            approver = User.query.get(approver_id)
            if not approver:
                return {'success': False, 'error': 'Invalid approver'}
            
            # Build query based on role
            swap_query = ShiftSwapRequest.query.filter_by(status='pending')
            leave_query = LeaveRequest.query.filter_by(status='pending')
            
            if approver.role == 'super_admin':
                # Super admin sees all requests
                pass
            elif approver.role == 'account_admin':
                # Account admin sees requests from their account
                swap_query = swap_query.filter_by(account_id=approver.account_id)
                leave_query = leave_query.filter_by(account_id=approver.account_id)
            elif approver.role == 'team_admin':
                # Team admin sees requests from their team
                swap_query = swap_query.filter_by(account_id=approver.account_id, team_id=approver.team_id)
                leave_query = leave_query.filter_by(account_id=approver.account_id, team_id=approver.team_id)
            else:
                # Regular users can't approve requests
                return {'success': True, 'swap_requests': [], 'leave_requests': []}
            
            swap_requests = swap_query.order_by(ShiftSwapRequest.created_at.desc()).all()
            leave_requests = leave_query.order_by(LeaveRequest.created_at.desc()).all()
            
            return {
                'success': True,
                'swap_requests': [self._serialize_swap_request(req) for req in swap_requests],
                'leave_requests': [self._serialize_leave_request(req) for req in leave_requests]
            }
            
        except Exception as e:
            self.logger.error(f"Error getting pending requests: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_user_requests(self, user_id: int) -> Dict:
        """Get all requests submitted by a user"""
        try:
            user = User.query.get(user_id)
            if not user:
                return {'success': False, 'error': 'Invalid user'}
            
            swap_requests = ShiftSwapRequest.query.filter_by(
                requester_id=user_id
            ).order_by(ShiftSwapRequest.created_at.desc()).all()
            
            leave_requests = LeaveRequest.query.filter_by(
                requester_id=user_id
            ).order_by(LeaveRequest.created_at.desc()).all()
            
            return {
                'success': True,
                'swap_requests': [self._serialize_swap_request(req) for req in swap_requests],
                'leave_requests': [self._serialize_leave_request(req) for req in leave_requests]
            }
            
        except Exception as e:
            self.logger.error(f"Error getting user requests: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    # Helper methods
    def _get_team_member_id_for_user(self, user_id: int) -> Optional[int]:
        """Get TeamMember ID for a User ID"""
        user = User.query.get(user_id)
        if not user:
            return None
        
        team_member = TeamMember.query.filter_by(
            name=user.username,
            account_id=user.account_id,
            team_id=user.team_id
        ).first()
        
        return team_member.id if team_member else None
    
    def _can_approve_request(self, approver: User, account_id: int, team_id: int) -> bool:
        """Check if user can approve requests for the given account/team"""
        if approver.role == 'super_admin':
            return True
        elif approver.role == 'account_admin':
            return approver.account_id == account_id
        elif approver.role == 'team_admin':
            return approver.account_id == account_id and approver.team_id == team_id
        return False
    
    def _execute_roster_swap(self, swap_request: ShiftSwapRequest) -> Dict:
        """Execute the actual roster swap"""
        try:
            # Get team member IDs
            requester_tm_id = self._get_team_member_id_for_user(swap_request.requester_id)
            swap_with_tm_id = self._get_team_member_id_for_user(swap_request.swap_with_id)
            
            if not requester_tm_id or not swap_with_tm_id:
                return {'success': False, 'error': 'Could not find team member records'}
            
            # Get existing roster entries
            requester_entry = ShiftRoster.query.filter_by(
                date=swap_request.original_date,
                team_member_id=requester_tm_id,
                account_id=swap_request.account_id,
                team_id=swap_request.team_id
            ).first()
            
            swap_with_entry = ShiftRoster.query.filter_by(
                date=swap_request.swap_date,
                team_member_id=swap_with_tm_id,
                account_id=swap_request.account_id,
                team_id=swap_request.team_id
            ).first()
            
            # Swap the shifts
            if requester_entry:
                requester_entry.shift_code = swap_request.swap_shift_code
            else:
                # Create new entry if it doesn't exist
                new_entry = ShiftRoster(
                    date=swap_request.original_date,
                    team_member_id=requester_tm_id,
                    shift_code=swap_request.swap_shift_code,
                    account_id=swap_request.account_id,
                    team_id=swap_request.team_id
                )
                db.session.add(new_entry)
            
            if swap_with_entry:
                swap_with_entry.shift_code = swap_request.original_shift_code
            else:
                # Create new entry if it doesn't exist
                new_entry = ShiftRoster(
                    date=swap_request.swap_date,
                    team_member_id=swap_with_tm_id,
                    shift_code=swap_request.original_shift_code,
                    account_id=swap_request.account_id,
                    team_id=swap_request.team_id
                )
                db.session.add(new_entry)
            
            return {'success': True}
            
        except Exception as e:
            self.logger.error(f"Error executing roster swap: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _execute_leave_roster_update(self, leave_request: LeaveRequest, covered_by_id: int = None) -> Dict:
        """Update roster for approved leave"""
        try:
            requester_tm_id = self._get_team_member_id_for_user(leave_request.requester_id)
            if not requester_tm_id:
                return {'success': False, 'error': 'Could not find requester team member record'}
            
            # Get existing roster entry
            roster_entry = ShiftRoster.query.filter_by(
                date=leave_request.leave_date,
                team_member_id=requester_tm_id,
                account_id=leave_request.account_id,
                team_id=leave_request.team_id
            ).first()
            
            # Map leave types to proper roster codes
            leave_code_map = {
                'sick': 'SL',           # Sick Leave
                'vacation': 'VL',       # Vacation Leave  
                'personal': 'CL',       # Casual Leave
                'emergency': 'CL',      # Casual Leave (Emergency)
                'family': 'CL',         # Casual Leave (Family)
                'other': 'OL'           # Other Leave
            }
            
            # Get the appropriate leave code
            leave_code = leave_code_map.get(leave_request.leave_type, 'OL')
            
            if roster_entry:
                # Mark as leave with proper code
                roster_entry.shift_code = leave_code
            else:
                # Create leave entry with proper code
                leave_entry = ShiftRoster(
                    date=leave_request.leave_date,
                    team_member_id=requester_tm_id,
                    shift_code=leave_code,
                    account_id=leave_request.account_id,
                    team_id=leave_request.team_id
                )
                db.session.add(leave_entry)
            
            # If someone is covering, add their shift
            if covered_by_id:
                cover_tm_id = self._get_team_member_id_for_user(covered_by_id)
                if cover_tm_id:
                    cover_entry = ShiftRoster(
                        date=leave_request.leave_date,
                        team_member_id=cover_tm_id,
                        shift_code=leave_request.shift_code,
                        account_id=leave_request.account_id,
                        team_id=leave_request.team_id
                    )
                    db.session.add(cover_entry)
            
            return {'success': True}
            
        except Exception as e:
            self.logger.error(f"Error executing leave roster update: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _create_audit_log(self, action: str, performed_by_id: int, account_id: int, team_id: int,
                         details: str = '', target_user_id: int = None, swap_request_id: int = None,
                         leave_request_id: int = None):
        """Create audit log entry"""
        try:
            audit_log = SwapLeaveAuditLog(
                action=action,
                performed_by_id=performed_by_id,
                target_user_id=target_user_id,
                swap_request_id=swap_request_id,
                leave_request_id=leave_request_id,
                details=details,
                account_id=account_id,
                team_id=team_id
            )
            db.session.add(audit_log)
        except Exception as e:
            self.logger.error(f"Error creating audit log: {str(e)}")
    
    def _send_swap_request_notifications(self, swap_request: ShiftSwapRequest):
        """Send notifications for new swap request"""
        try:
            # Notify the person being asked to swap
            self._create_notification(
                recipient_id=swap_request.swap_with_id,
                notification_type='swap_request_received',
                title=f'Shift Swap Request from {swap_request.requester.username}',
                message=f'{swap_request.requester.username} wants to swap their {swap_request.original_shift_code} shift on {swap_request.original_date} with your {swap_request.swap_shift_code} shift on {swap_request.swap_date}.',
                swap_request_id=swap_request.id,
                account_id=swap_request.account_id,
                team_id=swap_request.team_id
            )
            
            # Notify admins about the request
            admins = self._get_admins_for_approval(swap_request.account_id, swap_request.team_id)
            for admin in admins:
                self._create_notification(
                    recipient_id=admin.id,
                    notification_type='swap_request_pending',
                    title=f'Shift Swap Request Needs Approval',
                    message=f'{swap_request.requester.username} has requested to swap shifts with {swap_request.swap_with.username}. Reason: {swap_request.reason}',
                    swap_request_id=swap_request.id,
                    account_id=swap_request.account_id,
                    team_id=swap_request.team_id
                )
            
            # 📧 EMAIL ENHANCEMENT: Send email notification to admins when swap request is submitted
            try:
                shift_email_service.send_swap_request_submitted_email(swap_request)
                self.logger.info(f"Email notification sent for swap request {swap_request.id}")
            except Exception as email_error:
                self.logger.warning(f"Failed to send swap request email: {email_error}")
                # Don't fail the entire operation if email fails
                
        except Exception as e:
            self.logger.error(f"Error sending swap request notifications: {str(e)}")
    
    def _send_leave_request_notifications(self, leave_request: LeaveRequest):
        """Send notifications for new leave request"""
        try:
            # Notify admins about the request
            admins = self._get_admins_for_approval(leave_request.account_id, leave_request.team_id)
            for admin in admins:
                self._create_notification(
                    recipient_id=admin.id,
                    notification_type='leave_request_pending',
                    title=f'Leave Request Needs Approval',
                    message=f'{leave_request.requester.username} has requested {leave_request.leave_type} leave on {leave_request.leave_date} for {leave_request.shift_code} shift.',
                    leave_request_id=leave_request.id,
                    account_id=leave_request.account_id,
                    team_id=leave_request.team_id
                )
            
            # 📧 EMAIL ENHANCEMENT: Send email notification to admins when leave request is submitted
            try:
                shift_email_service.send_leave_request_submitted_email(leave_request)
                self.logger.info(f"Email notification sent for leave request {leave_request.id}")
            except Exception as email_error:
                self.logger.warning(f"Failed to send leave request email: {email_error}")
                # Don't fail the entire operation if email fails
                
        except Exception as e:
            self.logger.error(f"Error sending leave request notifications: {str(e)}")
    
    def _send_swap_approval_notifications(self, swap_request: ShiftSwapRequest, approved: bool):
        """Send notifications for swap approval/rejection"""
        try:
            status = 'approved' if approved else 'rejected'
            
            # Notify requester
            self._create_notification(
                recipient_id=swap_request.requester_id,
                notification_type=f'swap_request_{status}',
                title=f'Shift Swap Request {status.title()}',
                message=f'Your shift swap request with {swap_request.swap_with.username} has been {status}.',
                swap_request_id=swap_request.id,
                account_id=swap_request.account_id,
                team_id=swap_request.team_id
            )
            
            # Notify swap partner
            self._create_notification(
                recipient_id=swap_request.swap_with_id,
                notification_type=f'swap_request_{status}',
                title=f'Shift Swap Request {status.title()}',
                message=f'The shift swap request from {swap_request.requester.username} has been {status}.',
                swap_request_id=swap_request.id,
                account_id=swap_request.account_id,
                team_id=swap_request.team_id
            )
            
            # 📧 EMAIL ENHANCEMENT: Send email notification to requester about decision
            try:
                shift_email_service.send_swap_decision_email(
                    swap_request, 
                    approved, 
                    swap_request.approval_comments or ''
                )
                self.logger.info(f"Swap decision email sent for request {swap_request.id}")
            except Exception as email_error:
                self.logger.warning(f"Failed to send swap decision email: {email_error}")
            
            # 📧 EMAIL ENHANCEMENT: Send roster update notification to team if approved
            if approved:
                try:
                    shift_email_service.send_roster_update_notification(
                        'swap', 
                        swap_request=swap_request
                    )
                    self.logger.info(f"Roster update notification sent for approved swap {swap_request.id}")
                except Exception as email_error:
                    self.logger.warning(f"Failed to send roster update notification: {email_error}")
                    
        except Exception as e:
            self.logger.error(f"Error sending swap approval notifications: {str(e)}")
    
    def _send_leave_approval_notifications(self, leave_request: LeaveRequest, approved: bool):
        """Send notifications for leave approval/rejection"""
        try:
            status = 'approved' if approved else 'rejected'
            
            # Notify requester
            self._create_notification(
                recipient_id=leave_request.requester_id,
                notification_type=f'leave_request_{status}',
                title=f'Leave Request {status.title()}',
                message=f'Your {leave_request.leave_type} leave request for {leave_request.leave_date} has been {status}.',
                leave_request_id=leave_request.id,
                account_id=leave_request.account_id,
                team_id=leave_request.team_id
            )
            
            # 📧 EMAIL ENHANCEMENT: Send email notification to requester about decision
            try:
                shift_email_service.send_leave_decision_email(
                    leave_request, 
                    approved, 
                    leave_request.approval_comments or ''
                )
                self.logger.info(f"Leave decision email sent for request {leave_request.id}")
            except Exception as email_error:
                self.logger.warning(f"Failed to send leave decision email: {email_error}")
            
            # 📧 EMAIL ENHANCEMENT: Send roster update notification to team if approved
            if approved:
                try:
                    shift_email_service.send_roster_update_notification(
                        'leave', 
                        leave_request=leave_request
                    )
                    self.logger.info(f"Roster update notification sent for approved leave {leave_request.id}")
                except Exception as email_error:
                    self.logger.warning(f"Failed to send roster update notification: {email_error}")
                    
        except Exception as e:
            self.logger.error(f"Error sending leave approval notifications: {str(e)}")
    
    def _get_admins_for_approval(self, account_id: int, team_id: int) -> List[User]:
        """Get list of admins who can approve requests"""
        try:
            # Get super admins, account admins for this account, and team admins for this team
            admins = User.query.filter(
                db.or_(
                    User.role == 'super_admin',
                    db.and_(User.role == 'account_admin', User.account_id == account_id),
                    db.and_(User.role == 'team_admin', User.account_id == account_id, User.team_id == team_id)
                ),
                User.is_active == True
            ).all()
            
            return admins
        except Exception as e:
            self.logger.error(f"Error getting admins for approval: {str(e)}")
            return []
    
    def _create_notification(self, recipient_id: int, notification_type: str, title: str, 
                           message: str, account_id: int, team_id: int,
                           swap_request_id: int = None, leave_request_id: int = None):
        """Create notification record"""
        try:
            notification = SwapLeaveNotification(
                recipient_id=recipient_id,
                notification_type=notification_type,
                title=title,
                message=message,
                swap_request_id=swap_request_id,
                leave_request_id=leave_request_id,
                account_id=account_id,
                team_id=team_id
            )
            db.session.add(notification)
        except Exception as e:
            self.logger.error(f"Error creating notification: {str(e)}")
    
    def _serialize_swap_request(self, request: ShiftSwapRequest) -> Dict:
        """Serialize swap request for API response"""
        return {
            'id': request.id,
            'requester': {
                'id': request.requester.id,
                'username': request.requester.username,
                'full_name': f"{request.requester.first_name} {request.requester.last_name}"
            },
            'swap_with': {
                'id': request.swap_with.id,
                'username': request.swap_with.username,
                'full_name': f"{request.swap_with.first_name} {request.swap_with.last_name}"
            },
            'original_date': request.original_date.isoformat(),
            'original_shift_code': request.original_shift_code,
            'swap_date': request.swap_date.isoformat(),
            'swap_shift_code': request.swap_shift_code,
            'reason': request.reason,
            'status': request.status,
            'created_at': request.created_at.isoformat(),
            'approved_by': request.approved_by.username if request.approved_by else None,
            'approval_comments': request.approval_comments,
            'approved_at': request.approved_at.isoformat() if request.approved_at else None
        }
    
    def _serialize_leave_request(self, request: LeaveRequest) -> Dict:
        """Serialize leave request for API response"""
        return {
            'id': request.id,
            'requester': {
                'id': request.requester.id,
                'username': request.requester.username,
                'full_name': f"{request.requester.first_name} {request.requester.last_name}"
            },
            'leave_type': request.leave_type,
            'leave_date': request.leave_date.isoformat(),
            'shift_code': request.shift_code,
            'reason': request.reason,
            'status': request.status,
            'created_at': request.created_at.isoformat(),
            'approved_by': request.approved_by.username if request.approved_by else None,
            'approval_comments': request.approval_comments,
            'approved_at': request.approved_at.isoformat() if request.approved_at else None,
            'covered_by': request.covered_by.username if request.covered_by else None
        }

# Global service instance
shift_swap_leave_service = ShiftSwapLeaveService()