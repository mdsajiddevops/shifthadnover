"""
Utility route to reset user session to primary team
"""

from flask import Blueprint, request, redirect, url_for, session, flash
from flask_login import login_required
from services.team_access_service import TeamAccessService

team_utils_bp = Blueprint('team_utils', __name__)

@team_utils_bp.route('/reset-to-primary-team', methods=['POST'])
@login_required  
def reset_to_primary_team():
    """Reset session to user's primary team"""
    primary_team_id = TeamAccessService.reset_to_primary_team()
    
    if primary_team_id:
        flash('Team selection reset to your primary team.', 'success')
    else:
        flash('No primary team found.', 'warning')
    
    # Redirect back to the referring page or dashboard
    return redirect(request.referrer or url_for('dashboard.dashboard'))

@team_utils_bp.route('/set-primary-team/<int:team_id>', methods=['POST'])
@login_required
def set_primary_team(team_id):
    """Set a team as the user's primary team (if they have access)"""
    from flask_login import current_user
    from models.models import UserTeamMembership, db
    
    # Validate user has access to this team
    user_team_ids = TeamAccessService.get_user_team_ids()
    if team_id not in user_team_ids:
        flash('You do not have access to that team.', 'error')
        return redirect(request.referrer or url_for('dashboard.dashboard'))
    
    try:
        # Clear any existing primary team designations for this user
        UserTeamMembership.query.filter_by(
            user_id=current_user.id,
            is_primary=True
        ).update({'is_primary': False})
        
        # Set the new primary team
        membership = UserTeamMembership.query.filter_by(
            user_id=current_user.id,
            team_id=team_id,
            is_active=True
        ).first()
        
        if membership:
            membership.is_primary = True
            db.session.commit()
            
            # Update session to use the new primary team
            session['selected_team_id'] = team_id
            
            flash(f'Team "{membership.team.name}" is now your primary team.', 'success')
        else:
            flash('Team membership not found.', 'error')
            
    except Exception as e:
        db.session.rollback()
        flash(f'Error setting primary team: {str(e)}', 'error')
    
    return redirect(request.referrer or url_for('dashboard.dashboard'))