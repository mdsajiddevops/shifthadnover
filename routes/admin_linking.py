"""
Admin interface for User-TeamMember linking management
"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from models.models import db, User, TeamMember
from difflib import SequenceMatcher
import re

admin_linking = Blueprint('admin_linking', __name__, url_prefix='/admin')


def _find_matching_user_for_team_member(team_member):
    """
    Find the best matching User for a TeamMember based on email/name.
    Returns: (user, confidence_score, match_reason)
    """
    best_match = None
    best_score = 0
    best_reasons = []
    
    # Get all users that are not already linked to a team member
    linked_user_ids = [tm.user_id for tm in TeamMember.query.filter(TeamMember.user_id.isnot(None)).all()]
    available_users = User.query.filter(~User.id.in_(linked_user_ids) if linked_user_ids else True).all()
    
    tm_email = (team_member.email or '').lower().strip()
    tm_name = (team_member.name or '').lower().strip()
    
    for user in available_users:
        score = 0
        reasons = []
        
        user_email = (user.email or '').lower().strip()
        user_username = (user.username or '').lower().strip()
        user_fullname = f"{user.first_name or ''} {user.last_name or ''}".lower().strip()
        
        # 1. Exact email match (highest priority)
        if tm_email and user_email and tm_email == user_email:
            score = 100
            reasons.append("exact email match")
        
        # 2. Email username part match
        elif tm_email and user_email:
            tm_email_user = tm_email.split('@')[0] if '@' in tm_email else tm_email
            user_email_user = user_email.split('@')[0] if '@' in user_email else user_email
            
            if tm_email_user == user_email_user:
                score = max(score, 95)
                reasons.append("email username match")
        
        # 3. Name similarity
        if tm_name and user_fullname:
            name_ratio = SequenceMatcher(None, tm_name, user_fullname).ratio() * 100
            if name_ratio >= 90:
                score = max(score, 90)
                reasons.append(f"name similarity: {int(name_ratio)}%")
            elif name_ratio >= 70:
                score = max(score, 75)
                reasons.append(f"name similarity: {int(name_ratio)}%")
        
        # 4. Username pattern match
        if tm_name and user_username:
            # Clean both for comparison
            clean_tm = re.sub(r'[^a-zA-Z0-9]', '', tm_name)
            clean_user = re.sub(r'[^a-zA-Z0-9]', '', user_username)
            
            username_ratio = SequenceMatcher(None, clean_tm, clean_user).ratio() * 100
            if username_ratio >= 80:
                score = max(score, 85)
                reasons.append(f"username pattern match: {int(username_ratio)}%")
        
        # Update best match if this is better
        if score > best_score:
            best_score = score
            best_match = user
            best_reasons = reasons
    
    return best_match, best_score, "; ".join(best_reasons) if best_reasons else "No match found"


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
    if linked_user_ids:
        unlinked_users = User.query.filter(~User.id.in_(linked_user_ids)).all()
    else:
        unlinked_users = User.query.all()
    
    # Get potential matches for unlinked team members
    potential_matches = []
    for tm in unlinked_members:
        best_match, confidence, reason = _find_matching_user_for_team_member(tm)
        
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
        data = request.get_json() or {}
        min_confidence = data.get('min_confidence', 80)
        
        unlinked_members = TeamMember.query.filter_by(user_id=None).all()
        linked_count = 0
        skipped_count = 0
        errors = []
        
        for tm in unlinked_members:
            try:
                # Find best matching User for this TeamMember
                best_user, confidence, reason = _find_matching_user_for_team_member(tm)
                
                if best_user and confidence >= min_confidence:
                    # Verify user exists and is not already linked
                    user = User.query.get(best_user.id)
                    if not user:
                        errors.append(f"Skipped {tm.name}: user not found in database")
                        skipped_count += 1
                        continue
                    
                    # Check if user is already linked to another team member
                    existing_link = TeamMember.query.filter_by(user_id=user.id).first()
                    if not existing_link:
                        tm.user_id = user.id
                        db.session.add(tm)
                        linked_count += 1
                    else:
                        skipped_count += 1
                        errors.append(f"Skipped {tm.name}: user {user.username} already linked to {existing_link.name}")
                else:
                    skipped_count += 1
                    if confidence > 0:
                        errors.append(f"Skipped {tm.name}: confidence {confidence}% below threshold {min_confidence}%")
            
            except Exception as e:
                errors.append(f"Error processing {tm.name}: {str(e)}")
                skipped_count += 1
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'linked_count': linked_count,
            'skipped_count': skipped_count,
            'errors': errors[:20],  # Limit errors to prevent huge response
            'message': f'Bulk auto-link completed: {linked_count} linked, {skipped_count} skipped'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500