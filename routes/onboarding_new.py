from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_required, current_user
from models.models import Account, Team, User, db

onboarding_bp = Blueprint('onboarding', __name__)

@onboarding_bp.route('/onboarding')
@login_required
def onboarding():
    """Show onboarding page for new users"""
    
    # Check if user already has account and team assigned
    if current_user.account_id and current_user.team_id:
        flash('You have already completed onboarding!', 'info')
        return redirect(url_for('main.dashboard'))
    
    # Get available accounts and teams
    accounts = Account.query.filter_by(is_active=True).all()
    teams = Team.query.filter_by(is_active=True).all()
    
    return render_template('onboarding.html', 
                         accounts=accounts, 
                         teams=teams,
                         user=current_user)

@onboarding_bp.route('/onboarding/complete', methods=['POST'])
@login_required
def complete_onboarding():
    """Complete user onboarding with selected account and team"""
    
    account_id = request.form.get('account_id')
    team_id = request.form.get('team_id')
    
    if not account_id or not team_id:
        flash('Please select both an account and a team.', 'danger')
        return redirect(url_for('onboarding.onboarding'))
    
    # Validate account and team exist
    account = Account.query.get(account_id)
    team = Team.query.get(team_id)
    
    if not account or not team:
        flash('Invalid account or team selection.', 'danger')
        return redirect(url_for('onboarding.onboarding'))
    
    # Validate team belongs to account
    if team.account_id != int(account_id):
        flash('Selected team does not belong to the selected account.', 'danger')
        return redirect(url_for('onboarding.onboarding'))
    
    # Update user with selections
    current_user.account_id = account_id
    current_user.team_id = team_id
    current_user.role = 'user'  # Default role for new users
    
    try:
        db.session.commit()
        flash(f'Welcome! You have been assigned to {account.name} - {team.name}', 'success')
        return redirect(url_for('main.dashboard'))
    except Exception as e:
        db.session.rollback()
        flash(f'Error completing onboarding: {str(e)}', 'danger')
        return redirect(url_for('onboarding.onboarding'))

@onboarding_bp.route('/onboarding/skip')
@login_required
def skip_onboarding():
    """Skip onboarding and assign to default team"""
    
    # Find TechCorp account and Operations team as fallback
    techcorp_account = Account.query.filter_by(name='TechCorp', is_active=True).first()
    if techcorp_account:
        operations_team = Team.query.filter_by(
            account_id=techcorp_account.id, 
            name='Operations', 
            is_active=True
        ).first()
        
        if operations_team:
            current_user.account_id = techcorp_account.id
            current_user.team_id = operations_team.id
            current_user.role = 'user'
            
            try:
                db.session.commit()
                flash('You have been assigned to the default team. You can change this later in your profile.', 'info')
                return redirect(url_for('main.dashboard'))
            except Exception as e:
                db.session.rollback()
                flash(f'Error assigning default team: {str(e)}', 'danger')
    
    flash('Unable to complete onboarding. Please contact support.', 'danger')
    return redirect(url_for('onboarding.onboarding'))
