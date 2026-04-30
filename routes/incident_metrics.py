"""
Incident Metrics Dashboard
Shows charts and analytics for incident response performance
"""

from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from models.models import db, Incident, Shift, Team, Account
from sqlalchemy import func, case
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

incident_metrics_bp = Blueprint('incident_metrics', __name__)


@incident_metrics_bp.route('/admin/incident-metrics')
@login_required
def incident_metrics():
    """Incident metrics dashboard page."""
    if current_user.role != 'super_admin':
        return "Access denied - Super Admin only", 403
    
    # Get all accounts and teams for filters
    accounts = Account.query.filter_by(is_active=True).order_by(Account.name).all()
    teams = Team.query.filter_by(is_active=True).order_by(Team.name).all()
    
    return render_template('admin/incident_metrics.html', accounts=accounts, teams=teams)


def get_filter_params():
    """Extract filter parameters from request."""
    account_id = request.args.get('account_id', type=int)
    team_id = request.args.get('team_id', type=int)
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    
    # Default date range - last 30 days
    if end_date_str:
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    else:
        end_date = datetime.now().date()
    
    if start_date_str:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
    else:
        start_date = end_date - timedelta(days=30)
    
    return account_id, team_id, start_date, end_date


def apply_filters(query, account_id, team_id, start_date, end_date):
    """Apply common filters to query."""
    # Filter by date range
    query = query.filter(Shift.date >= start_date)
    query = query.filter(Shift.date <= end_date)
    
    # Filter by account
    if account_id:
        query = query.filter(Shift.account_id == account_id)
    
    # Filter by team
    if team_id:
        query = query.filter(Shift.team_id == team_id)
    
    return query


@incident_metrics_bp.route('/api/incident-metrics/summary')
@login_required
def get_metrics_summary():
    """Get incident metrics summary."""
    if current_user.role != 'super_admin':
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    try:
        # Get filter parameters
        account_id, team_id, start_date, end_date = get_filter_params()
        
        # Calculate days in range for average
        days_in_range = (end_date - start_date).days + 1
        
        # Base query
        query = Incident.query.join(Shift, Incident.shift_id == Shift.id)
        query = apply_filters(query, account_id, team_id, start_date, end_date)
        
        # Total incidents
        total_incidents = query.count()
        
        # Incidents by status - need fresh queries to avoid filter issues
        base_query = Incident.query.join(Shift, Incident.shift_id == Shift.id)
        base_query = apply_filters(base_query, account_id, team_id, start_date, end_date)
        
        open_incidents = base_query.filter(Incident.status == 'open').count()
        
        base_query = Incident.query.join(Shift, Incident.shift_id == Shift.id)
        base_query = apply_filters(base_query, account_id, team_id, start_date, end_date)
        closed_incidents = base_query.filter(Incident.status == 'closed').count()
        
        base_query = Incident.query.join(Shift, Incident.shift_id == Shift.id)
        base_query = apply_filters(base_query, account_id, team_id, start_date, end_date)
        in_progress = base_query.filter(Incident.status == 'in_progress').count()
        
        # Incidents by priority/severity
        base_query = Incident.query.join(Shift, Incident.shift_id == Shift.id)
        base_query = apply_filters(base_query, account_id, team_id, start_date, end_date)
        critical = base_query.filter(Incident.priority == 'critical').count()
        
        base_query = Incident.query.join(Shift, Incident.shift_id == Shift.id)
        base_query = apply_filters(base_query, account_id, team_id, start_date, end_date)
        high = base_query.filter(Incident.priority == 'high').count()
        
        base_query = Incident.query.join(Shift, Incident.shift_id == Shift.id)
        base_query = apply_filters(base_query, account_id, team_id, start_date, end_date)
        medium = base_query.filter(Incident.priority == 'medium').count()
        
        base_query = Incident.query.join(Shift, Incident.shift_id == Shift.id)
        base_query = apply_filters(base_query, account_id, team_id, start_date, end_date)
        low = base_query.filter(Incident.priority == 'low').count()
        
        # Resolution rate
        resolution_rate = round((closed_incidents / total_incidents * 100), 1) if total_incidents > 0 else 0
        
        # Average incidents per day
        avg_per_day = round(total_incidents / days_in_range, 1) if days_in_range > 0 else 0
        
        return jsonify({
            'success': True,
            'summary': {
                'total_incidents': total_incidents,
                'open_incidents': open_incidents,
                'closed_incidents': closed_incidents,
                'in_progress': in_progress,
                'resolution_rate': resolution_rate,
                'avg_per_day': avg_per_day
            },
            'by_severity': {
                'critical': critical,
                'high': high,
                'medium': medium,
                'low': low
            },
            'by_status': {
                'open': open_incidents,
                'in_progress': in_progress,
                'closed': closed_incidents
            }
        })
    except Exception as e:
        logger.error(f"Error getting metrics summary: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@incident_metrics_bp.route('/api/incident-metrics/trends')
@login_required
def get_metrics_trends():
    """Get incident trends over time."""
    if current_user.role != 'super_admin':
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    try:
        # Get filter parameters
        account_id, team_id, start_date, end_date = get_filter_params()
        
        # Build query
        query = db.session.query(
            Shift.date,
            func.count(Incident.id).label('count')
        ).join(Incident, Incident.shift_id == Shift.id)
        
        # Apply filters
        query = query.filter(Shift.date >= start_date)
        query = query.filter(Shift.date <= end_date)
        
        if account_id:
            query = query.filter(Shift.account_id == account_id)
        if team_id:
            query = query.filter(Shift.team_id == team_id)
        
        query = query.group_by(Shift.date).order_by(Shift.date)
        
        results = query.all()
        
        # Format for chart
        labels = []
        data = []
        for row in results:
            labels.append(row.date.strftime('%m/%d'))
            data.append(row.count)
        
        return jsonify({
            'success': True,
            'labels': labels,
            'data': data
        })
    except Exception as e:
        logger.error(f"Error getting trends: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@incident_metrics_bp.route('/api/incident-metrics/by-team')
@login_required
def get_metrics_by_team():
    """Get incidents grouped by team."""
    if current_user.role != 'super_admin':
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    try:
        # Get filter parameters
        account_id, team_id, start_date, end_date = get_filter_params()
        
        # Build query
        query = db.session.query(
            Team.name,
            func.count(Incident.id).label('count')
        ).join(Shift, Shift.team_id == Team.id
        ).join(Incident, Incident.shift_id == Shift.id)
        
        # Apply filters
        query = query.filter(Shift.date >= start_date)
        query = query.filter(Shift.date <= end_date)
        
        if account_id:
            query = query.filter(Shift.account_id == account_id)
        if team_id:
            query = query.filter(Shift.team_id == team_id)
        
        query = query.group_by(Team.name).order_by(func.count(Incident.id).desc())
        results = query.all()
        
        labels = [r.name for r in results]
        data = [r.count for r in results]
        
        return jsonify({
            'success': True,
            'labels': labels,
            'data': data
        })
    except Exception as e:
        logger.error(f"Error getting by team: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@incident_metrics_bp.route('/api/incident-metrics/teams-by-account/<int:account_id>')
@login_required
def get_teams_by_account(account_id):
    """Get teams for a specific account (for cascading filter)."""
    if current_user.role != 'super_admin':
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    try:
        teams = Team.query.filter_by(account_id=account_id, is_active=True).order_by(Team.name).all()
        return jsonify({
            'success': True,
            'teams': [{'id': t.id, 'name': t.name} for t in teams]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

