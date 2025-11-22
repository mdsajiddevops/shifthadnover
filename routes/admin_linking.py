"""
Admin interface for User-TeamMember linking management
"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from models.models import db, User, TeamMember
from routes.sso_auth import _find_matching_team_member

admin_linking = Blueprint('admin_linking', __name__, url_prefix='/admin')

@admin_linking.route('/user-team-linking')
@login_required
def user_team_linking():
    """Admin interface for managing user-team member links"""
    # Check if user has admin privileges
    if current_user.role not in ['super_admin', 'account_admin']:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard.dashboard'))
    
    # Get unlinked team members
    unlinked_members = TeamMember.query.filter_by(user_id=None).all()
    
    # Get unlinked users (users without team member association)
    linked_user_ids = [tm.user_id for tm in TeamMember.query.filter(TeamMember.user_id.isnot(None)).all()]
    unlinked_users = User.query.filter(~User.id.in_(linked_user_ids)).all()
    
    # Get potential matches for unlinked team members
    potential_matches = []
    for tm in unlinked_members:
        best_match, confidence, reason = _find_matching_team_member(
            tm.email or f"{tm.name.lower().replace(' ', '.')}@company.com",
            tm.name,
            tm.name.lower().replace(' ', '_')
        )
        
        potential_matches.append({
            'team_member': tm,
            'suggested_user': best_match,
            'confidence': confidence,
            'reason': reason
        })
    
    return render_template('admin/user_team_linking.html',
                         unlinked_members=unlinked_members,
                         unlinked_users=unlinked_users,
                         potential_matches=potential_matches)

@admin_linking.route('/api/link-user-team', methods=['POST'])
@login_required
def link_user_team():
    """API endpoint to manually link a user to a team member"""
    if current_user.role not in ['super_admin', 'account_admin']:
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        team_member_id = data.get('team_member_id')
        
        if not user_id or not team_member_id:
            return jsonify({'success': False, 'error': 'Missing user_id or team_member_id'}), 400
        
        # Validate user and team member exist
        user = User.query.get(user_id)
        team_member = TeamMember.query.get(team_member_id)
        
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        if not team_member:
            return jsonify({'success': False, 'error': 'Team member not found'}), 404
        
        # Check if team member is already linked
        if team_member.user_id:
            existing_user = User.query.get(team_member.user_id)
            return jsonify({
                'success': False, 
                'error': f'Team member already linked to user: {existing_user.username if existing_user else "Unknown"}'
            }), 400
        
        # Check if user is already linked to another team member
        existing_link = TeamMember.query.filter_by(user_id=user_id).first()
        if existing_link:
            return jsonify({
                'success': False,
                'error': f'User already linked to team member: {existing_link.name}'
            }), 400
        
        # Perform the linking
        team_member.user_id = user_id
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Successfully linked {user.username} to {team_member.name}'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_linking.route('/api/unlink-user-team', methods=['POST'])
@login_required
def unlink_user_team():
    """API endpoint to unlink a user from a team member"""
    if current_user.role not in ['super_admin', 'account_admin']:
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    try:
        data = request.get_json()
        team_member_id = data.get('team_member_id')
        
        if not team_member_id:
            return jsonify({'success': False, 'error': 'Missing team_member_id'}), 400
        
        team_member = TeamMember.query.get(team_member_id)
        if not team_member:
            return jsonify({'success': False, 'error': 'Team member not found'}), 404
        
        if not team_member.user_id:
            return jsonify({'success': False, 'error': 'Team member is not linked to any user'}), 400
        
        # Get user info for response
        user = User.query.get(team_member.user_id)
        username = user.username if user else "Unknown"
        
        # Unlink
        team_member.user_id = None
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Successfully unlinked {username} from {team_member.name}'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_linking.route('/api/bulk-auto-link', methods=['POST'])
@login_required
def bulk_auto_link():
    """API endpoint to auto-link all high-confidence matches"""
    if current_user.role not in ['super_admin', 'account_admin']:
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    try:
        min_confidence = request.get_json().get('min_confidence', 80)
        
        unlinked_members = TeamMember.query.filter_by(user_id=None).all()
        linked_count = 0
        skipped_count = 0
        errors = []
        
        for tm in unlinked_members:
            try:
                # Find best match for this team member
                best_user, confidence, reason = _find_matching_team_member(
                    tm.email or f"{tm.name.lower().replace(' ', '.')}@company.com",
                    tm.name,
                    tm.name.lower().replace(' ', '_')
                )
                
                if best_user and confidence >= min_confidence:
                    # Check if user is already linked
                    existing_link = TeamMember.query.filter_by(user_id=best_user.id).first()
                    if not existing_link:
                        tm.user_id = best_user.id
                        db.session.add(tm)
                        linked_count += 1
                    else:
                        skipped_count += 1
                        errors.append(f"Skipped {tm.name}: user {best_user.username} already linked")
                else:
                    skipped_count += 1
            
            except Exception as e:
                errors.append(f"Error processing {tm.name}: {str(e)}")
                skipped_count += 1
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'linked_count': linked_count,
            'skipped_count': skipped_count,
            'errors': errors,
            'message': f'Bulk auto-link completed: {linked_count} linked, {skipped_count} skipped'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500