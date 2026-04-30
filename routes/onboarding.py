"""
User Onboarding Routes
Handles first-time user setup with account and team selection
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, session
from flask_login import login_required, current_user
from models.models import db, Account, Team, User
from datetime import datetime
import logging

onboarding_bp = Blueprint('onboarding', __name__, url_prefix='/onboarding')
logger = logging.getLogger(__name__)

@onboarding_bp.route('/')
@login_required
def index():
    """Onboarding page for first-time users"""
    # Check if user needs onboarding
    if not current_user.needs_onboarding:
        logger.info(f"User {current_user.username} already completed onboarding, redirecting to dashboard")
        return redirect(url_for('dashboard.dashboard'))
    
    # Super admins should never reach this page
    if current_user.role == 'super_admin':
        logger.warning(f"Super admin {current_user.username} reached onboarding page, redirecting to dashboard")
        return redirect(url_for('dashboard.dashboard'))
    
    # Clear any existing flash messages to avoid confusion
    session.pop('_flashes', None)
    
    # Get available accounts and teams
    accounts = Account.query.filter_by(is_active=True).order_by(Account.name).all()
    
    return render_template('onboarding/welcome.html',
                         accounts=accounts,
                         user=current_user)

@onboarding_bp.route('/api/teams/<int:account_id>')
@login_required
def get_teams_for_account(account_id):
    """API endpoint to get teams for a specific account"""
    try:
        teams = Team.query.filter_by(account_id=account_id, is_active=True).order_by(Team.name).all()
        teams_data = [{'id': team.id, 'name': team.name} for team in teams]
        return jsonify({'success': True, 'teams': teams_data})
    except Exception as e:
        logger.error(f"Error fetching teams for account {account_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@onboarding_bp.route('/complete', methods=['POST'])
@login_required
def complete_onboarding():
    """Complete the onboarding process"""
    try:
        data = request.get_json()
        account_id = data.get('account_id')
        team_id = data.get('team_id')
        
        # Validate inputs
        if not account_id or not team_id:
            return jsonify({'success': False, 'error': 'Account and team selection are required'}), 400
        
        # Verify account exists and is active
        account = Account.query.filter_by(id=account_id, is_active=True).first()
        if not account:
            return jsonify({'success': False, 'error': 'Invalid account selected'}), 400
        
        # Verify team exists, is active, and belongs to selected account
        team = Team.query.filter_by(id=team_id, account_id=account_id, is_active=True).first()
        if not team:
            return jsonify({'success': False, 'error': 'Invalid team selected for this account'}), 400
        
        # Complete onboarding for current user
        current_user.complete_onboarding(account_id, team_id)
        
        logger.info(f"User {current_user.username} completed onboarding: Account={account.name}, Team={team.name}")
        
        return jsonify({
            'success': True,
            'message': f'Welcome to {account.name} - {team.name}!',
            'redirect_url': url_for('dashboard.dashboard', onboarding_complete='true')
        })
        
    except Exception as e:
        logger.error(f"Error completing onboarding for user {current_user.username}: {e}")
        return jsonify({'success': False, 'error': 'An error occurred during onboarding'}), 500

@onboarding_bp.route('/skip')
@login_required  
def skip_onboarding():
    """Skip onboarding (for testing purposes - can be removed in production)"""
    if current_user.role == 'super_admin':
        return redirect(url_for('dashboard.dashboard'))
    
    # For non-admin users, redirect back to onboarding
    flash('Account and team selection is required to proceed', 'warning')
    return redirect(url_for('onboarding.index'))