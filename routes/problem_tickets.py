"""
Problem Tickets Management Routes

This module handles the management of Problem Tickets and their associated PTasks.
Similar to Change Info management with manual entries.
"""

import logging
from datetime import datetime, date
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from models.models import db, ProblemTicket, ProblemTask, TeamMember, Account, Team

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

problem_tickets_bp = Blueprint('problem_tickets', __name__)


@problem_tickets_bp.route('/problem-tickets', methods=['GET'])
@login_required
def problem_tickets_page():
    """Problem Tickets management page"""
    try:
        # Get filter parameters
        status_filter = request.args.get('status', '')
        priority_filter = request.args.get('priority', '')
        app_filter = request.args.get('app', '')
        team_filter = request.args.get('team_id', '')
        
        # Build base query
        query = ProblemTicket.query
        
        # Role-based filtering
        if current_user.role == 'super_admin':
            # Super admin can see all
            pass
        elif current_user.role == 'account_admin':
            query = query.filter(ProblemTicket.account_id == current_user.account_id)
        else:
            # Team admin and users see their team's tickets
            query = query.filter(
                ProblemTicket.account_id == current_user.account_id,
                ProblemTicket.team_id == current_user.team_id
            )
        
        # Apply team filter for admins
        if team_filter and current_user.role in ['super_admin', 'account_admin']:
            query = query.filter(ProblemTicket.team_id == int(team_filter))
        
        # Apply filters
        if status_filter:
            query = query.filter(ProblemTicket.status == status_filter)
        
        if priority_filter:
            query = query.filter(ProblemTicket.priority == priority_filter)
        
        if app_filter:
            query = query.filter(ProblemTicket.app_name.ilike(f'%{app_filter}%'))
        
        # Order by most recent first
        problem_tickets = query.order_by(ProblemTicket.created_at.desc()).all()
        
        # Get team members for dropdowns
        if current_user.role == 'super_admin':
            team_members = TeamMember.query.filter_by(is_active=True).all()
            teams = Team.query.filter_by(is_active=True).all()
        elif current_user.role == 'account_admin':
            team_members = TeamMember.query.filter_by(
                account_id=current_user.account_id,
                is_active=True
            ).all()
            teams = Team.query.filter_by(
                account_id=current_user.account_id,
                is_active=True
            ).all()
        else:
            team_members = TeamMember.query.filter_by(
                team_id=current_user.team_id,
                is_active=True
            ).all()
            teams = [Team.query.get(current_user.team_id)] if current_user.team_id else []
        
        # Get unique app names for filter dropdown
        app_names = db.session.query(ProblemTicket.app_name).distinct().filter(
            ProblemTicket.app_name.isnot(None),
            ProblemTicket.app_name != ''
        ).all()
        app_names = [app[0] for app in app_names if app[0]]
        
        return render_template('problem_tickets.html',
                             problem_tickets=problem_tickets,
                             team_members=team_members,
                             teams=teams,
                             app_names=app_names,
                             status_filter=status_filter,
                             priority_filter=priority_filter,
                             app_filter=app_filter,
                             team_filter=team_filter)
    
    except Exception as e:
        logger.error(f"Error loading problem tickets page: {e}")
        import traceback
        traceback.print_exc()
        flash('Error loading problem tickets page.', 'error')
        return redirect(url_for('dashboard.dashboard'))


@problem_tickets_bp.route('/api/problem-tickets', methods=['GET'])
@login_required
def get_problem_tickets():
    """API endpoint to get problem tickets"""
    try:
        query = ProblemTicket.query
        
        # Role-based filtering
        if current_user.role == 'super_admin':
            pass
        elif current_user.role == 'account_admin':
            query = query.filter(ProblemTicket.account_id == current_user.account_id)
        else:
            query = query.filter(
                ProblemTicket.account_id == current_user.account_id,
                ProblemTicket.team_id == current_user.team_id
            )
        
        tickets = query.order_by(ProblemTicket.created_at.desc()).all()

        # Batch-load task counts to avoid 2N COUNT queries
        from sqlalchemy import func
        ticket_ids = [t.id for t in tickets]
        if ticket_ids:
            _total_counts = dict(db.session.query(ProblemTask.problem_id, func.count(ProblemTask.id))
                .filter(ProblemTask.problem_id.in_(ticket_ids))
                .group_by(ProblemTask.problem_id).all())
            _open_counts = dict(db.session.query(ProblemTask.problem_id, func.count(ProblemTask.id))
                .filter(ProblemTask.problem_id.in_(ticket_ids),
                        ProblemTask.status.in_(['Open', 'In Progress', 'Pending']))
                .group_by(ProblemTask.problem_id).all())
        else:
            _total_counts = {}
            _open_counts = {}

        return jsonify({
            'success': True,
            'tickets': [{
                'id': t.id,
                'problem_number': t.problem_number,
                'title': t.title,
                'description': t.description,
                'app_name': t.app_name,
                'priority': t.priority,
                'status': t.status,
                'root_cause': t.root_cause,
                'workaround': t.workaround,
                'resolution': t.resolution,
                'owner_id': t.owner_id,
                'owner_name': t.owner_name,
                'created_date': t.created_date.isoformat() if t.created_date else None,
                'target_resolution_date': t.target_resolution_date.isoformat() if t.target_resolution_date else None,
                'actual_resolution_date': t.actual_resolution_date.isoformat() if t.actual_resolution_date else None,
                'ptask_count': _total_counts.get(t.id, 0),
                'open_ptask_count': _open_counts.get(t.id, 0),
                'created_at': t.created_at.isoformat() if t.created_at else None
            } for t in tickets]
        })
    except Exception as e:
        logger.error(f"Error getting problem tickets: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@problem_tickets_bp.route('/api/problem-tickets', methods=['POST'])
@login_required
def create_problem_ticket():
    """Create a new problem ticket"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('problem_number'):
            return jsonify({'success': False, 'error': 'Problem number is required'}), 400
        if not data.get('title'):
            return jsonify({'success': False, 'error': 'Title is required'}), 400
        
        # Check for duplicate problem number in same team
        existing = ProblemTicket.query.filter_by(
            team_id=current_user.team_id,
            problem_number=data.get('problem_number')
        ).first()
        
        if existing:
            return jsonify({'success': False, 'error': 'Problem number already exists for this team'}), 400
        
        # Create new ticket
        ticket = ProblemTicket(
            problem_number=data.get('problem_number'),
            title=data.get('title'),
            description=data.get('description'),
            app_name=data.get('app_name'),
            priority=data.get('priority', 'Medium'),
            status=data.get('status', 'Open'),
            root_cause=data.get('root_cause'),
            workaround=data.get('workaround'),
            resolution=data.get('resolution'),
            owner_id=data.get('owner_id') if data.get('owner_id') else None,
            account_id=current_user.account_id,
            team_id=current_user.team_id
        )
        
        # Handle dates
        if data.get('created_date'):
            try:
                ticket.created_date = datetime.fromisoformat(data['created_date'].replace('Z', '+00:00'))
            except:
                ticket.created_date = datetime.now()
        else:
            ticket.created_date = datetime.now()
        
        if data.get('target_resolution_date'):
            try:
                ticket.target_resolution_date = datetime.fromisoformat(data['target_resolution_date'].replace('Z', '+00:00'))
            except:
                pass
        
        if data.get('actual_resolution_date'):
            try:
                ticket.actual_resolution_date = datetime.fromisoformat(data['actual_resolution_date'].replace('Z', '+00:00'))
            except:
                pass
        
        db.session.add(ticket)
        db.session.commit()
        
        logger.info(f"Created problem ticket {ticket.problem_number} by {current_user.username}")
        
        return jsonify({
            'success': True,
            'message': 'Problem ticket created successfully',
            'ticket': {
                'id': ticket.id,
                'problem_number': ticket.problem_number,
                'title': ticket.title,
                'status': ticket.status,
                'priority': ticket.priority
            }
        })
    
    except Exception as e:
        logger.error(f"Error creating problem ticket: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@problem_tickets_bp.route('/api/problem-tickets/<int:ticket_id>', methods=['PUT'])
@login_required
def update_problem_ticket(ticket_id):
    """Update a problem ticket"""
    try:
        ticket = ProblemTicket.query.get_or_404(ticket_id)
        
        # Check permissions
        if current_user.role not in ['super_admin', 'account_admin']:
            if ticket.account_id != current_user.account_id or ticket.team_id != current_user.team_id:
                return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        elif current_user.role == 'account_admin':
            if ticket.account_id != current_user.account_id:
                return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
        data = request.get_json()
        
        # Update fields
        ticket.problem_number = data.get('problem_number', ticket.problem_number)
        ticket.title = data.get('title', ticket.title)
        ticket.description = data.get('description', ticket.description)
        ticket.app_name = data.get('app_name', ticket.app_name)
        ticket.priority = data.get('priority', ticket.priority)
        ticket.status = data.get('status', ticket.status)
        ticket.root_cause = data.get('root_cause', ticket.root_cause)
        ticket.workaround = data.get('workaround', ticket.workaround)
        ticket.resolution = data.get('resolution', ticket.resolution)
        
        if 'owner_id' in data:
            ticket.owner_id = data['owner_id'] if data['owner_id'] else None
        
        # Handle dates
        if 'created_date' in data:
            if data['created_date']:
                try:
                    ticket.created_date = datetime.fromisoformat(data['created_date'].replace('Z', '+00:00'))
                except:
                    pass
            else:
                ticket.created_date = None
        
        if 'target_resolution_date' in data:
            if data['target_resolution_date']:
                try:
                    ticket.target_resolution_date = datetime.fromisoformat(data['target_resolution_date'].replace('Z', '+00:00'))
                except:
                    pass
            else:
                ticket.target_resolution_date = None
        
        if 'actual_resolution_date' in data:
            if data['actual_resolution_date']:
                try:
                    ticket.actual_resolution_date = datetime.fromisoformat(data['actual_resolution_date'].replace('Z', '+00:00'))
                except:
                    pass
            else:
                ticket.actual_resolution_date = None
        
        db.session.commit()
        
        logger.info(f"Updated problem ticket {ticket.problem_number} by {current_user.username}")
        
        return jsonify({
            'success': True,
            'message': 'Problem ticket updated successfully',
            'ticket': {
                'id': ticket.id,
                'problem_number': ticket.problem_number,
                'title': ticket.title,
                'status': ticket.status,
                'owner_name': ticket.owner_name
            }
        })
    
    except Exception as e:
        logger.error(f"Error updating problem ticket: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@problem_tickets_bp.route('/api/problem-tickets/<int:ticket_id>', methods=['DELETE'])
@login_required
def delete_problem_ticket(ticket_id):
    """Delete a problem ticket"""
    try:
        ticket = ProblemTicket.query.get_or_404(ticket_id)
        
        # Check permissions - only super_admin and account_admin can delete
        if current_user.role not in ['super_admin', 'account_admin']:
            return jsonify({'success': False, 'error': 'Only administrators can delete problem tickets'}), 403
        
        if current_user.role == 'account_admin' and ticket.account_id != current_user.account_id:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
        problem_number = ticket.problem_number
        db.session.delete(ticket)
        db.session.commit()
        
        logger.info(f"Deleted problem ticket {problem_number} by {current_user.username}")
        
        return jsonify({
            'success': True,
            'message': f'Problem ticket {problem_number} deleted successfully'
        })
    
    except Exception as e:
        logger.error(f"Error deleting problem ticket: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== PTASK ROUTES ====================

@problem_tickets_bp.route('/api/problem-tickets/<int:ticket_id>/ptasks', methods=['GET'])
@login_required
def get_ptasks(ticket_id):
    """Get all PTasks for a problem ticket"""
    try:
        ticket = ProblemTicket.query.get_or_404(ticket_id)
        
        ptasks = ProblemTask.query.filter_by(problem_id=ticket_id).order_by(ProblemTask.created_at.desc()).all()
        
        return jsonify({
            'success': True,
            'ptasks': [{
                'id': p.id,
                'ptask_number': p.ptask_number,
                'title': p.title,
                'description': p.description,
                'status': p.status,
                'assigned_to_id': p.assigned_to_id,
                'assigned_to_name': p.assigned_to_name,
                'due_date': p.due_date.isoformat() if p.due_date else None,
                'completion_date': p.completion_date.isoformat() if p.completion_date else None,
                'notes': p.notes,
                'created_at': p.created_at.isoformat() if p.created_at else None
            } for p in ptasks]
        })
    
    except Exception as e:
        logger.error(f"Error getting PTasks: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@problem_tickets_bp.route('/api/problem-tickets/<int:ticket_id>/ptasks', methods=['POST'])
@login_required
def create_ptask(ticket_id):
    """Create a new PTask for a problem ticket"""
    try:
        ticket = ProblemTicket.query.get_or_404(ticket_id)
        
        # Check permissions
        if current_user.role not in ['super_admin', 'account_admin']:
            if ticket.account_id != current_user.account_id or ticket.team_id != current_user.team_id:
                return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
        data = request.get_json()
        
        # Validate required fields
        if not data.get('ptask_number'):
            return jsonify({'success': False, 'error': 'PTask number is required'}), 400
        if not data.get('title'):
            return jsonify({'success': False, 'error': 'Title is required'}), 400
        
        # Create PTask
        ptask = ProblemTask(
            ptask_number=data.get('ptask_number'),
            problem_id=ticket_id,
            title=data.get('title'),
            description=data.get('description'),
            status=data.get('status', 'Open'),
            assignee_name=data.get('assigned_to_name', '').strip() if data.get('assigned_to_name') else None,
            notes=data.get('notes')
        )
        
        # Handle dates
        if data.get('due_date'):
            try:
                ptask.due_date = datetime.fromisoformat(data['due_date'].replace('Z', '+00:00'))
            except:
                pass
        
        if data.get('completion_date'):
            try:
                ptask.completion_date = datetime.fromisoformat(data['completion_date'].replace('Z', '+00:00'))
            except:
                pass
        
        db.session.add(ptask)
        db.session.commit()
        
        logger.info(f"Created PTask {ptask.ptask_number} for {ticket.problem_number} by {current_user.username}")
        
        return jsonify({
            'success': True,
            'message': 'PTask created successfully',
            'ptask': {
                'id': ptask.id,
                'ptask_number': ptask.ptask_number,
                'title': ptask.title,
                'status': ptask.status
            }
        })
    
    except Exception as e:
        logger.error(f"Error creating PTask: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@problem_tickets_bp.route('/api/ptasks/<int:ptask_id>', methods=['PUT'])
@login_required
def update_ptask(ptask_id):
    """Update a PTask"""
    try:
        ptask = ProblemTask.query.get_or_404(ptask_id)
        ticket = ptask.problem_ticket
        
        # Check permissions
        if current_user.role not in ['super_admin', 'account_admin']:
            if ticket.account_id != current_user.account_id or ticket.team_id != current_user.team_id:
                return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
        data = request.get_json()
        
        # Update fields
        ptask.ptask_number = data.get('ptask_number', ptask.ptask_number)
        ptask.title = data.get('title', ptask.title)
        ptask.description = data.get('description', ptask.description)
        ptask.status = data.get('status', ptask.status)
        ptask.notes = data.get('notes', ptask.notes)
        
        if 'assigned_to_name' in data:
            ptask.assignee_name = data['assigned_to_name'].strip() if data['assigned_to_name'] else None
        
        # Handle dates
        if 'due_date' in data:
            if data['due_date']:
                try:
                    ptask.due_date = datetime.fromisoformat(data['due_date'].replace('Z', '+00:00'))
                except:
                    pass
            else:
                ptask.due_date = None
        
        if 'completion_date' in data:
            if data['completion_date']:
                try:
                    ptask.completion_date = datetime.fromisoformat(data['completion_date'].replace('Z', '+00:00'))
                except:
                    pass
            else:
                ptask.completion_date = None
        
        db.session.commit()
        
        logger.info(f"Updated PTask {ptask.ptask_number} by {current_user.username}")
        
        return jsonify({
            'success': True,
            'message': 'PTask updated successfully'
        })
    
    except Exception as e:
        logger.error(f"Error updating PTask: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@problem_tickets_bp.route('/api/ptasks/<int:ptask_id>', methods=['DELETE'])
@login_required
def delete_ptask(ptask_id):
    """Delete a PTask"""
    try:
        ptask = ProblemTask.query.get_or_404(ptask_id)
        ticket = ptask.problem_ticket
        
        # Check permissions
        if current_user.role not in ['super_admin', 'account_admin']:
            if ticket.account_id != current_user.account_id or ticket.team_id != current_user.team_id:
                return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
        ptask_number = ptask.ptask_number
        db.session.delete(ptask)
        db.session.commit()
        
        logger.info(f"Deleted PTask {ptask_number} by {current_user.username}")
        
        return jsonify({
            'success': True,
            'message': f'PTask {ptask_number} deleted successfully'
        })
    
    except Exception as e:
        logger.error(f"Error deleting PTask: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


