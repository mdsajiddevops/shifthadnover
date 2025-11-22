"""
Handover Audit Service
Comprehensive audit logging and reporting for handover operations
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy import and_, or_, func, text
from models.models import db, IncidentHandoverAction, HandoverNotification, Incident, TeamMember
import logging

logger = logging.getLogger(__name__)

class HandoverAuditService:
    """Service for auditing and reporting handover operations"""
    
    def log_handover_action(
        self,
        incident_id: int,
        action_type: str,
        performed_by_id: int,
        details: Optional[Dict[str, Any]] = None,
        notes: Optional[str] = None
    ) -> IncidentHandoverAction:
        """
        Log a handover action for audit purposes
        
        Args:
            incident_id: ID of the incident
            action_type: Type of action (initiated, accepted, rejected, escalated)
            performed_by_id: ID of the user performing the action
            details: Additional details about the action
            notes: User notes for the action
            
        Returns:
            IncidentHandoverAction: The created audit record
        """
        try:
            audit_record = IncidentHandoverAction(
                incident_id=incident_id,
                action_type=action_type,
                performed_by_id=performed_by_id,
                action_timestamp=datetime.utcnow(),
                details=details or {},
                notes=notes
            )
            
            db.session.add(audit_record)
            db.session.commit()
            
            logger.info(f"Audit logged: {action_type} for incident {incident_id} by user {performed_by_id}")
            return audit_record
            
        except Exception as e:
            logger.error(f"Failed to log handover action: {str(e)}")
            db.session.rollback()
            raise

    def get_handover_efficiency_report(
        self,
        start_date: datetime,
        end_date: datetime,
        account_id: Optional[int] = None,
        team_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate handover efficiency report for specified date range
        
        Args:
            start_date: Start date for the report
            end_date: End date for the report
            account_id: Optional account filter
            team_id: Optional team filter
            
        Returns:
            Dict containing efficiency metrics and trends
        """
        try:
            # Base query for handover actions in date range
            base_query = db.session.query(IncidentHandoverAction).filter(
                IncidentHandoverAction.action_timestamp.between(start_date, end_date)
            )
            
            # Apply account/team filters
            if account_id or team_id:
                base_query = base_query.join(Incident, IncidentHandoverAction.incident_id == Incident.id)
                if account_id:
                    base_query = base_query.filter(Incident.account_id == account_id)
                if team_id:
                    base_query = base_query.filter(Incident.team_id == team_id)
            
            # Calculate basic metrics
            total_initiated = base_query.filter(IncidentHandoverAction.action_type == 'initiated').count()
            total_accepted = base_query.filter(IncidentHandoverAction.action_type == 'accepted').count()
            total_rejected = base_query.filter(IncidentHandoverAction.action_type == 'rejected').count()
            
            # Calculate efficiency rates
            acceptance_rate = (total_accepted / total_initiated * 100) if total_initiated > 0 else 0
            rejection_rate = (total_rejected / total_initiated * 100) if total_initiated > 0 else 0
            
            # Average response time for accepted handovers
            accepted_handovers = db.session.query(
                IncidentHandoverAction.incident_id,
                func.min(IncidentHandoverAction.action_timestamp).label('initiated_at'),
                func.max(IncidentHandoverAction.action_timestamp).label('accepted_at')
            ).filter(
                IncidentHandoverAction.action_timestamp.between(start_date, end_date),
                IncidentHandoverAction.action_type.in_(['initiated', 'accepted'])
            ).group_by(IncidentHandoverAction.incident_id).having(
                func.count(IncidentHandoverAction.id) >= 2
            ).all()
            
            response_times = []
            for handover in accepted_handovers:
                if handover.accepted_at and handover.initiated_at:
                    response_time = (handover.accepted_at - handover.initiated_at).total_seconds() / 60  # minutes
                    response_times.append(response_time)
            
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0
            
            # Daily trends
            daily_trends = self._get_daily_handover_trends(start_date, end_date, account_id, team_id)
            
            # Top rejection reasons
            rejection_reasons = self._get_top_rejection_reasons(start_date, end_date, account_id, team_id)
            
            return {
                'period': {
                    'start_date': start_date.strftime('%Y-%m-%d'),
                    'end_date': end_date.strftime('%Y-%m-%d'),
                    'days': (end_date - start_date).days + 1
                },
                'overview': {
                    'total_initiated': total_initiated,
                    'total_accepted': total_accepted,
                    'total_rejected': total_rejected,
                    'acceptance_rate': round(acceptance_rate, 2),
                    'rejection_rate': round(rejection_rate, 2),
                    'avg_response_time_minutes': round(avg_response_time, 2)
                },
                'daily_trends': daily_trends,
                'rejection_reasons': rejection_reasons,
                'performance_grade': self._calculate_performance_grade(acceptance_rate, avg_response_time)
            }
            
        except Exception as e:
            logger.error(f"Failed to generate efficiency report: {str(e)}")
            raise

    def get_engineer_handover_summary(
        self,
        engineer_id: int,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get handover summary for a specific engineer
        
        Args:
            engineer_id: ID of the engineer
            days: Number of days to look back
            
        Returns:
            Dict containing engineer's handover statistics
        """
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            # Actions performed by this engineer
            actions_performed = db.session.query(IncidentHandoverAction).filter(
                IncidentHandoverAction.performed_by_id == engineer_id,
                IncidentHandoverAction.action_timestamp.between(start_date, end_date)
            ).all()
            
            # Actions on incidents assigned to this engineer
            actions_received = db.session.query(IncidentHandoverAction).join(
                Incident, IncidentHandoverAction.incident_id == Incident.id
            ).filter(
                Incident.handover_assigned_to == engineer_id,
                IncidentHandoverAction.action_timestamp.between(start_date, end_date)
            ).all()
            
            # Calculate statistics
            accepted_count = len([a for a in actions_performed if a.action_type == 'accepted'])
            rejected_count = len([a for a in actions_performed if a.action_type == 'rejected'])
            
            received_count = len([a for a in actions_received if a.action_type == 'initiated'])
            
            # Calculate response times
            response_times = []
            for action in actions_performed:
                if action.action_type in ['accepted', 'rejected']:
                    # Find the corresponding initiated action
                    initiated_action = next((a for a in actions_received 
                                           if a.incident_id == action.incident_id and a.action_type == 'initiated'), None)
                    if initiated_action:
                        response_time = (action.action_timestamp - initiated_action.action_timestamp).total_seconds() / 60
                        response_times.append(response_time)
            
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0
            
            return {
                'engineer_id': engineer_id,
                'period_days': days,
                'handovers_received': received_count,
                'handovers_accepted': accepted_count,
                'handovers_rejected': rejected_count,
                'acceptance_rate': round((accepted_count / received_count * 100) if received_count > 0 else 0, 2),
                'avg_response_time_minutes': round(avg_response_time, 2),
                'total_actions': len(actions_performed)
            }
            
        except Exception as e:
            logger.error(f"Failed to get engineer handover summary: {str(e)}")
            raise

    def _get_daily_handover_trends(
        self,
        start_date: datetime,
        end_date: datetime,
        account_id: Optional[int] = None,
        team_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get daily handover trends for the specified period"""
        try:
            # Group actions by date
            query = db.session.query(
                func.date(IncidentHandoverAction.action_timestamp).label('date'),
                IncidentHandoverAction.action_type,
                func.count(IncidentHandoverAction.id).label('count')
            ).filter(
                IncidentHandoverAction.action_timestamp.between(start_date, end_date)
            )
            
            if account_id or team_id:
                query = query.join(Incident, IncidentHandoverAction.incident_id == Incident.id)
                if account_id:
                    query = query.filter(Incident.account_id == account_id)
                if team_id:
                    query = query.filter(Incident.team_id == team_id)
            
            results = query.group_by(
                func.date(IncidentHandoverAction.action_timestamp),
                IncidentHandoverAction.action_type
            ).all()
            
            # Organize by date
            trends = {}
            for result in results:
                date_str = result.date.strftime('%Y-%m-%d')
                if date_str not in trends:
                    trends[date_str] = {'initiated': 0, 'accepted': 0, 'rejected': 0}
                trends[date_str][result.action_type] = result.count
            
            # Convert to list format
            return [
                {
                    'date': date,
                    'initiated': data['initiated'],
                    'accepted': data['accepted'],
                    'rejected': data['rejected'],
                    'acceptance_rate': round((data['accepted'] / data['initiated'] * 100) if data['initiated'] > 0 else 0, 2)
                }
                for date, data in sorted(trends.items())
            ]
            
        except Exception as e:
            logger.error(f"Failed to get daily trends: {str(e)}")
            return []

    def _get_top_rejection_reasons(
        self,
        start_date: datetime,
        end_date: datetime,
        account_id: Optional[int] = None,
        team_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get top rejection reasons for the specified period"""
        try:
            query = db.session.query(IncidentHandoverAction).filter(
                IncidentHandoverAction.action_type == 'rejected',
                IncidentHandoverAction.action_timestamp.between(start_date, end_date),
                IncidentHandoverAction.notes.isnot(None)
            )
            
            if account_id or team_id:
                query = query.join(Incident, IncidentHandoverAction.incident_id == Incident.id)
                if account_id:
                    query = query.filter(Incident.account_id == account_id)
                if team_id:
                    query = query.filter(Incident.team_id == team_id)
            
            rejections = query.all()
            
            # Count rejection reasons
            reason_counts = {}
            for rejection in rejections:
                reason = rejection.notes.lower().strip()
                # Categorize common reasons
                if 'not relevant' in reason or 'irrelevant' in reason:
                    category = 'Not Relevant'
                elif 'insufficient information' in reason or 'incomplete' in reason:
                    category = 'Insufficient Information'
                elif 'already resolved' in reason or 'duplicate' in reason:
                    category = 'Already Resolved'
                elif 'wrong assignee' in reason or 'wrong team' in reason:
                    category = 'Wrong Assignment'
                else:
                    category = 'Other'
                
                reason_counts[category] = reason_counts.get(category, 0) + 1
            
            # Sort by count
            sorted_reasons = sorted(reason_counts.items(), key=lambda x: x[1], reverse=True)
            
            total_rejections = sum(reason_counts.values())
            
            return [
                {
                    'reason': reason,
                    'count': count,
                    'percentage': round((count / total_rejections * 100) if total_rejections > 0 else 0, 2)
                }
                for reason, count in sorted_reasons[:5]  # Top 5 reasons
            ]
            
        except Exception as e:
            logger.error(f"Failed to get rejection reasons: {str(e)}")
            return []

    def _calculate_performance_grade(self, acceptance_rate: float, avg_response_time: float) -> str:
        """Calculate performance grade based on acceptance rate and response time"""
        # Grade based on acceptance rate (70%) and response time (30%)
        acceptance_score = min(acceptance_rate, 100) / 100  # Normalize to 0-1
        
        # Response time score (better performance = lower time)
        # Assume 30 minutes or less is excellent, 60 minutes is acceptable
        response_score = max(0, min(1, (60 - avg_response_time) / 60)) if avg_response_time > 0 else 1
        
        overall_score = (acceptance_score * 0.7) + (response_score * 0.3)
        
        if overall_score >= 0.9:
            return 'A+'
        elif overall_score >= 0.8:
            return 'A'
        elif overall_score >= 0.7:
            return 'B+'
        elif overall_score >= 0.6:
            return 'B'
        elif overall_score >= 0.5:
            return 'C'
        else:
            return 'D'

    def export_handover_audit_log(
        self,
        start_date: datetime,
        end_date: datetime,
        account_id: Optional[int] = None,
        team_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Export complete handover audit log for the specified period
        
        Returns:
            List of audit records with detailed information
        """
        try:
            query = db.session.query(IncidentHandoverAction).filter(
                IncidentHandoverAction.action_timestamp.between(start_date, end_date)
            )
            
            if account_id or team_id:
                query = query.join(Incident, IncidentHandoverAction.incident_id == Incident.id)
                if account_id:
                    query = query.filter(Incident.account_id == account_id)
                if team_id:
                    query = query.filter(Incident.team_id == team_id)
            
            actions = query.order_by(IncidentHandoverAction.action_timestamp.desc()).all()
            
            audit_log = []
            for action in actions:
                # Get related information
                incident = db.session.query(Incident).get(action.incident_id)
                performer = db.session.query(TeamMember).get(action.performed_by_id)
                
                audit_log.append({
                    'timestamp': action.action_timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    'action_type': action.action_type,
                    'incident_id': action.incident_id,
                    'incident_title': incident.title if incident else 'Unknown',
                    'incident_priority': incident.priority if incident else 'Unknown',
                    'performed_by': performer.name if performer else 'Unknown',
                    'notes': action.notes,
                    'details': action.details
                })
            
            return audit_log
            
        except Exception as e:
            logger.error(f"Failed to export audit log: {str(e)}")
            raise