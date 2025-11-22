from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_required, current_user
from models.models import TeamMember, Account, Team, User, db

team_bp = Blueprint('team', __name__)

@team_bp.route('/team')
@login_required
def team():
    """Display team members - fixed version without is_active filter"""
    
    try:
        # Simple query - join with User but don't filter by team_member.is_active (doesn't exist)
        members = TeamMember.query.join(User, TeamMember.user_id == User.id).all()
        
        # Get basic data for display based on user role
        if current_user.role == 'super_admin':
            accounts = Account.query.filter_by(is_active=True).all()
            teams = Team.query.filter_by(is_active=True).all()
        elif current_user.role == 'account_admin':
            accounts = [Account.query.get(current_user.account_id)] if current_user.account_id else []
            teams = Team.query.filter_by(account_id=current_user.account_id, is_active=True).all()
        else:
            accounts = []
            teams = []
        
        return render_template('team_details.html',
                             members=members,
                             accounts=accounts,
                             teams=teams,
                             selected_account_id=None,
                             selected_team_id=None,
                             show_inactive=False)
                             
    except Exception as e:
        flash(f'Error loading team data: {str(e)}', 'danger')
        return render_template('team_details.html',
                             members=[],
                             accounts=[],
                             teams=[],
                             selected_account_id=None,
                             selected_team_id=None,
                             show_inactive=False)

@team_bp.route('/team/add', methods=['GET', 'POST'])
@login_required
def add_team_member():
    """Add a new team member"""
    
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        account_id = request.form.get('account_id')
        team_id = request.form.get('team_id')
        
        if user_id and account_id and team_id:
            # Check if team member already exists
            existing = TeamMember.query.filter_by(
                user_id=user_id,
                account_id=account_id,
                team_id=team_id
            ).first()
            
            if existing:
                flash('Team member already exists!', 'warning')
            else:
                new_member = TeamMember(
                    user_id=user_id,
                    account_id=account_id,
                    team_id=team_id
                )
                
                db.session.add(new_member)
                db.session.commit()
                flash('Team member added successfully!', 'success')
                
            return redirect(url_for('team.team'))
        else:
            flash('All fields are required!', 'danger')
    
    # Get available data for the form
    if current_user.role == 'super_admin':
        users = User.query.filter_by(is_active=True).all()
        accounts = Account.query.filter_by(is_active=True).all()
        teams = Team.query.filter_by(is_active=True).all()
    elif current_user.role == 'account_admin':
        users = User.query.filter_by(account_id=current_user.account_id, is_active=True).all()
        accounts = [Account.query.get(current_user.account_id)]
        teams = Team.query.filter_by(account_id=current_user.account_id, is_active=True).all()
    else:
        users = []
        accounts = []
        teams = []
    
    return render_template('add_team_member.html',
                         users=users,
                         accounts=accounts,
                         teams=teams)