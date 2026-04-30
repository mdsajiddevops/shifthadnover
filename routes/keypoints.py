from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_required, current_user
from models.models import ShiftKeyPoint, ShiftKeyPointUpdate, db
from sqlalchemy import func
from datetime import date
import logging
logger = logging.getLogger(__name__)

keypoints_bp = Blueprint('keypoints', __name__)

# Valid status options
VALID_STATUSES = [
    'Open', 'In Progress', 'Pending with Another Team', 'On Hold', 
    'Under Review', 'Escalated', 'Waiting for Approval', 'Closed'
]

# 🔧 NEW: Edit key point description/title route
@keypoints_bp.route('/keypoints/edit/<int:key_point_id>', methods=['GET', 'POST'])
@login_required
def edit_keypoint(key_point_id):
    """Edit key point description - also updates all duplicates with same description"""
    key_point = ShiftKeyPoint.query.get_or_404(key_point_id)
    
    if request.method == 'POST':
        new_description = request.form.get('description', '').strip()
        
        if not new_description:
            flash('Description is required.', 'danger')
            return redirect(url_for('keypoints.keypoints'))
        
        old_description = key_point.description
        
        # Check if description actually changed
        if new_description.lower() == old_description.lower():
            flash('No changes detected.', 'info')
            return redirect(url_for('keypoints.keypoints'))
        
        # 🔧 FIX: Update ALL key points with the same description (case-insensitive)
        # This ensures consistency across all carried-forward duplicates
        duplicates_updated = 0
        all_duplicates = ShiftKeyPoint.query.filter(
            func.lower(ShiftKeyPoint.description) == old_description.lower(),
            ShiftKeyPoint.account_id == key_point.account_id,
            ShiftKeyPoint.team_id == key_point.team_id
        ).all()
        
        for dup_kp in all_duplicates:
            dup_kp.description = new_description
            db.session.add(dup_kp)
            duplicates_updated += 1
            logger.debug(f"🔧 KEYPOINTS: Updated key point ID {dup_kp.id} description from '{old_description[:30]}...' to '{new_description[:30]}...'")
        
        # Add an update entry to track the change
        status_update = ShiftKeyPointUpdate(
            key_point_id=key_point_id,
            update_text=f"Title updated from '{old_description}' to '{new_description}' by {current_user.username}",
            update_date=date.today(),
            updated_by=current_user.username
        )
        db.session.add(status_update)
        db.session.commit()
        
        flash(f'Key point title updated! {duplicates_updated} entries updated across all shifts.', 'success')
        return redirect(url_for('keypoints.keypoints'))
    
    # GET request - return JSON for modal
    return jsonify({
        'id': key_point.id,
        'description': key_point.description,
        'status': key_point.status
    })

@keypoints_bp.route('/keypoints/update/edit/<int:update_id>', methods=['GET', 'POST'])
@login_required
def edit_keypoint_update(update_id):
    update = ShiftKeyPointUpdate.query.get_or_404(update_id)
    if request.method == 'POST':
        update_text = request.form.get('update_text')
        update_date = request.form.get('update_date')
        if update_text:
            update.update_text = update_text
            if update_date:
                update.update_date = date.fromisoformat(update_date)
            db.session.commit()
            flash('Update edited!', 'success')
            return redirect(url_for('keypoints.keypoints'))
        else:
            flash('Update text required.', 'danger')
    return render_template('edit_keypoint_update.html', update=update)

@keypoints_bp.route('/keypoints/update/delete/<int:update_id>', methods=['POST'])
@login_required
def delete_keypoint_update(update_id):
    update = ShiftKeyPointUpdate.query.get_or_404(update_id)
    db.session.delete(update)
    db.session.commit()
    flash('Update deleted!', 'success')
    return redirect(url_for('keypoints.keypoints'))

# Enhanced STATUS UPDATE ROUTE with additional status options
@keypoints_bp.route('/keypoints/status/<int:key_point_id>', methods=['POST'])
@login_required
def update_keypoint_status(key_point_id):
    key_point = ShiftKeyPoint.query.get_or_404(key_point_id)
    new_status = request.form.get('new_status')
    
    if new_status in VALID_STATUSES:
        old_status = key_point.status
        key_point.status = new_status
        
        # Enhanced status change messages
        status_messages = {
            'Open': 'Task is now ready to be worked on',
            'In Progress': 'Task is now being actively worked on',
            'Pending with Another Team': 'Task is now waiting for another team',
            'On Hold': 'Task is now temporarily paused or blocked',
            'Under Review': 'Task is now being reviewed or validated',
            'Escalated': 'Task has been escalated to higher level',
            'Waiting for Approval': 'Task is now waiting for approval',
            'Closed': 'Task has been completed successfully'
        }
        
        # 🔧 FIX: When closing a key point, also close ALL duplicate entries with same description (CASE-INSENSITIVE)
        # This ensures older carried-forward entries are also marked as closed
        closed_duplicates = 0
        if new_status == 'Closed':
            duplicate_kps = ShiftKeyPoint.query.filter(
                func.lower(ShiftKeyPoint.description) == key_point.description.lower(),
                ShiftKeyPoint.account_id == key_point.account_id,
                ShiftKeyPoint.team_id == key_point.team_id,
                ShiftKeyPoint.status.in_(['Open', 'In Progress']),
                ShiftKeyPoint.id != key_point.id  # Exclude the current one
            ).all()
            
            for dup_kp in duplicate_kps:
                dup_kp.status = 'Closed'
                db.session.add(dup_kp)
                closed_duplicates += 1
                logger.debug(f"🔧 KEYPOINTS: Auto-closed duplicate key point ID {dup_kp.id} (shift_id={dup_kp.shift_id})")
        
        # Add an automatic update entry for status change with enhanced message
        status_update = ShiftKeyPointUpdate(
            key_point_id=key_point_id,
            update_text=f"Status changed from '{old_status}' to '{new_status}' by {current_user.username}. {status_messages.get(new_status, '')}",
            update_date=date.today(),
            updated_by=current_user.username
        )
        
        db.session.add(status_update)
        db.session.commit()
        
        if closed_duplicates > 0:
            flash(f'Key point status updated to "{new_status}"! Also closed {closed_duplicates} duplicate entries. {status_messages.get(new_status, "")}', 'success')
        else:
            flash(f'Key point status updated to "{new_status}"! {status_messages.get(new_status, "")}', 'success')
    else:
        flash('Invalid status value.', 'danger')
    
    # Preserve filter parameters when redirecting back
    filter_params = {}
    if request.form.get('filter_status'):
        filter_params['status'] = request.form.get('filter_status')
    if request.form.get('filter_date'):
        filter_params['date'] = request.form.get('filter_date')
    if request.form.get('filter_team_id'):
        filter_params['team_id'] = request.form.get('filter_team_id')
    
    return redirect(url_for('keypoints.keypoints', **filter_params))

@keypoints_bp.route('/keypoints', methods=['GET', 'POST'])
@login_required
def keypoints():
    from models.models import Account, Team
    from services.team_access_service import TeamAccessService
    
    status_filter = request.args.get('status', 'all')
    date_filter = request.args.get('date')
    account_id = None
    team_id = None
    accounts = []
    teams = []
    
    # Initialize variables that will be used later
    filter_account_id = None
    filter_team_id = None
    selected_team_id = None
    selected_account_id = None
    team_filter_context = None

    if current_user.role == 'super_admin':
        accounts = Account.query.filter_by(is_active=True).all()
        account_id = request.args.get('account_id') or session.get('selected_account_id')
        selected_team_id = request.args.get('team_id') or session.get('selected_team_id')
        teams = Team.query.filter_by(is_active=True)
        if account_id:
            teams = teams.filter_by(account_id=account_id)
        teams = teams.all()
        filter_account_id = account_id
        filter_team_id = int(selected_team_id) if selected_team_id else None
        selected_account_id = account_id
        # Create team_filter_context for template
        team_filter_context = {
            'user_teams': teams,
            'show_team_filter': len(teams) > 1,
            'selected_team_id': filter_team_id
        }
    elif current_user.role == 'account_admin':
        account_id = current_user.account_id
        filter_account_id = account_id
        selected_account_id = account_id
        accounts = [Account.query.get(account_id)] if account_id else []
        teams = Team.query.filter_by(account_id=account_id, is_active=True).all()
        selected_team_id = request.args.get('team_id') or session.get('selected_team_id')
        filter_team_id = int(selected_team_id) if selected_team_id else None
        # Create team_filter_context for template
        team_filter_context = {
            'user_teams': teams,
            'show_team_filter': len(teams) > 1,
            'selected_team_id': filter_team_id
        }
    else:
        # Regular users and team admins: Use team access service (SAME AS DASHBOARD)
        filter_account_id = current_user.account_id
        accounts = [Account.query.get(filter_account_id)] if filter_account_id else []
        
        # Get team filter context using team access service (SAME AS DASHBOARD)
        url_team_id = request.args.get('team_id', type=int)
        team_filter_context = TeamAccessService.get_team_filter_context(url_team_id=url_team_id)
        
        teams = team_filter_context['user_teams']
        selected_account_id = filter_account_id
        
        # Check for team_id in request args FIRST (from form submission), then fall back to session
        selected_team_id = request.args.get('team_id')
        if selected_team_id:
            selected_team_id = int(selected_team_id)
            # Update the team_filter_context with the selected team
            team_filter_context['selected_team_id'] = selected_team_id
        else:
            selected_team_id = team_filter_context['selected_team_id']
        
        # Set filter team ID - None means show all user's teams (SAME AS DASHBOARD)
        filter_team_id = selected_team_id
        
    # Set template variables
    team_id = filter_team_id  # For template compatibility
    
    # Build query with proper filtering like dashboard
    query = ShiftKeyPoint.query
    
    if filter_account_id:
        query = query.filter_by(account_id=filter_account_id)
        
    # Apply team filtering based on role and selection (SAME AS DASHBOARD)
    if filter_team_id:
        # Specific team selected
        query = query.filter_by(team_id=filter_team_id)
    elif current_user.role not in ['super_admin', 'account_admin']:
        # Regular users: filter by their accessible teams (SAME AS DASHBOARD)
        if team_filter_context and team_filter_context['show_team_filter']:
            user_team_ids = [team.id for team in team_filter_context['user_teams']]
            query = query.filter(ShiftKeyPoint.team_id.in_(user_team_ids))
        elif current_user.team_id:
            query = query.filter_by(team_id=current_user.team_id)
    # NOTE: Do NOT apply status filter here - we need to check all statuses for proper filtering
    # The status filtering will be done after we exclude key points that have been closed
    
    # Get all key points (before status filtering) to properly handle closed status
    all_key_points = query.all()
    
    # 🔧 FIX: For each key point, check if there's a NEWER version with "Closed" status
    # If so, exclude this key point from results (it has been resolved)
    filtered_key_points = []
    for kp in all_key_points:
        # Skip if already Closed and we're filtering for Open/In Progress
        if status_filter != 'all' and kp.status != status_filter:
            continue
            
        # Check if this key point has been closed in a newer entry (CASE-INSENSITIVE matching)
        newer_closed = ShiftKeyPoint.query.filter(
            func.lower(ShiftKeyPoint.description) == kp.description.lower(),
            ShiftKeyPoint.status == 'Closed',
            ShiftKeyPoint.id > kp.id,
            ShiftKeyPoint.account_id == kp.account_id,
            ShiftKeyPoint.team_id == kp.team_id
        ).first()
        
        if newer_closed:
            logger.debug(f"🔧 KEYPOINTS: Excluding key point ID {kp.id} - found newer closed version ID {newer_closed.id}")
            continue
            
        filtered_key_points.append(kp)
    
    # Deduplicate key points by description, keeping the most recent one
    kp_map = {}
    for kp in filtered_key_points:
        key = kp.description.strip().lower() if kp.description else ''
        if key not in kp_map or kp.id > kp_map[key].id:
            kp_map[key] = kp
    
    key_points = list(kp_map.values())
    logger.debug(f"🔧 KEYPOINTS: Deduplication reduced {len(all_key_points)} to {len(key_points)} unique key points (after filtering closed)")
    
    # Populate submitted_by_name and original_created_date for key points
    from models.handover_enhanced import HandoverRequest
    from models.models import User, Shift
    
    for kp in key_points:
        kp.submitted_by_name = None  # Default
        kp.original_created_date = None  # The earliest date this key point was created
        
        # 🔧 FIX: Find the OLDEST shift date for key points with the same description
        # This handles carried-forward key points correctly
        try:
            oldest_kp = ShiftKeyPoint.query.filter_by(
                description=kp.description,
                account_id=kp.account_id,
                team_id=kp.team_id
            ).join(Shift).order_by(Shift.date.asc()).first()
            
            if oldest_kp and oldest_kp.shift and oldest_kp.shift.date:
                kp.original_created_date = oldest_kp.shift.date
                logger.debug(f"🔧 KEYPOINTS: KP {kp.id} original date: {kp.original_created_date}")
        except Exception as e:
            logger.debug(f"🔧 KEYPOINTS: Error finding original date for KP {kp.id}: {e}")
        
        if not kp.created_by and kp.shift_id:
            try:
                # Find the HandoverRequest for this shift to get the submitter
                shift = Shift.query.get(kp.shift_id)
                if shift:
                    handover_req = HandoverRequest.query.filter_by(
                        shift_date=shift.date,
                        current_shift_type=shift.current_shift_type,
                        account_id=shift.account_id,
                        team_id=shift.team_id
                    ).first()
                    if handover_req and handover_req.created_by_id:
                        user = User.query.get(handover_req.created_by_id)
                        if user:
                            kp.submitted_by_name = user.display_name or user.username
            except Exception as e:
                logger.debug(f"🔧 KEYPOINTS: Error getting submitter for KP {kp.id}: {e}")
    
    updates_by_kp = {}
    for kp in key_points:
        updates_query = ShiftKeyPointUpdate.query.filter_by(key_point_id=kp.id)
        if date_filter:
            updates_query = updates_query.filter_by(update_date=date.fromisoformat(date_filter))
        updates_by_kp[kp.id] = updates_query.order_by(ShiftKeyPointUpdate.update_date.desc()).all()
    
    return render_template('keypoints_updates.html', 
                         key_points=key_points, 
                         updates_by_kp=updates_by_kp, 
                         status_filter=status_filter, 
                         date_filter=date_filter, 
                         accounts=accounts, 
                         teams=teams, 
                         selected_account_id=filter_account_id, 
                         selected_team_id=selected_team_id,
                         team_filter_context=team_filter_context,
                         date=date)

@keypoints_bp.route('/keypoints/update/<int:key_point_id>', methods=['POST'])
@login_required
def add_keypoint_update(key_point_id):
    update_text = request.form.get('update_text')
    update_date = request.form.get('update_date') or date.today().isoformat()
    if update_text:
        update = ShiftKeyPointUpdate(
            key_point_id=key_point_id,
            update_text=update_text,
            update_date=date.fromisoformat(update_date),
            updated_by=current_user.username
        )
        db.session.add(update)
        db.session.commit()
        flash('Update added!', 'success')
    else:
        flash('Update text required.', 'danger')
    
    # Preserve filter parameters when redirecting back
    filter_params = {}
    if request.form.get('filter_status'):
        filter_params['status'] = request.form.get('filter_status')
    if request.form.get('filter_date'):
        filter_params['date'] = request.form.get('filter_date')
    if request.form.get('filter_team_id'):
        filter_params['team_id'] = request.form.get('filter_team_id')
    
    return redirect(url_for('keypoints.keypoints', **filter_params))
