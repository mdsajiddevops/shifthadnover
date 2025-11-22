
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from flask import session
from models.models import TeamMember, Shift, Incident, ShiftKeyPoint, ShiftRoster, db
from models.handover_enhanced import HandoverRequest
from models.audit_log import AuditLog
from services.audit_service import log_action
from services.email_service import send_handover_email, send_incident_assignment_notification
from services.servicenow_service import ServiceNowService
from datetime import datetime, timedelta, time as dt_time
from sqlalchemy import or_, and_
import pytz

handover_bp = Blueprint('handover', __name__)

# 🚨 UNIVERSAL SHIFT REUSE INTERCEPTOR - PREVENTS ALL NEW SHIFT CREATION
def get_or_reuse_shift(date, current_shift_type, next_shift_type, account_id, team_id, action):
    """
    BULLETPROOF: Always reuse existing shifts instead of creating new ones.
    This function will be called for ALL shift creation attempts.
    """
    print(f"[INTERCEPTOR] get_or_reuse_shift called: {date} {current_shift_type}→{next_shift_type}")
    
    # Step 1: Look for exact match
    existing_shift = Shift.query.filter_by(
        date=date,
        current_shift_type=current_shift_type,
        next_shift_type=next_shift_type,
        account_id=account_id,
        team_id=team_id
    ).first()
    
    if existing_shift:
        print(f"[INTERCEPTOR] ✅ REUSING exact match shift ID: {existing_shift.id}")
        # Update status
        if action == 'submit' and existing_shift.status == 'draft':
            existing_shift.status = 'sent'
            existing_shift.submitted_at = datetime.now()
            db.session.commit()
        elif action == 'draft':
            existing_shift.status = 'draft'
            existing_shift.submitted_at = None
            db.session.commit()
        return existing_shift
        
    # Step 2: Look for any shift on same date
    fallback_shift = Shift.query.filter_by(
        date=date,
        account_id=account_id,
        team_id=team_id
    ).first()
    
    if fallback_shift:
        print(f"[INTERCEPTOR] ✅ REUSING fallback shift ID: {fallback_shift.id}")
        # Update to match our criteria
        fallback_shift.current_shift_type = current_shift_type
        fallback_shift.next_shift_type = next_shift_type
        old_status = fallback_shift.status
        fallback_shift.status = 'draft' if action == 'draft' else 'sent'
        print(f"[STATUS_DEBUG] Fallback shift {fallback_shift.id}: {old_status} → {fallback_shift.status} (action: {action})")
        fallback_shift.submitted_at = datetime.now() if action == 'submit' else None
        db.session.commit()
        return fallback_shift
        
    # Step 3: Look for ANY shift we can reuse (regardless of date)
    any_shift = Shift.query.filter_by(
        account_id=account_id,
        team_id=team_id
    ).first()
    
    if any_shift:
        print(f"[INTERCEPTOR] ✅ REUSING any available shift ID: {any_shift.id}")
        # Update to match our criteria
        any_shift.date = date
        any_shift.current_shift_type = current_shift_type
        any_shift.next_shift_type = next_shift_type
        old_status = any_shift.status
        any_shift.status = 'draft' if action == 'draft' else 'sent'
        print(f"[STATUS_DEBUG] Any shift {any_shift.id}: {old_status} → {any_shift.status} (action: {action})")
        any_shift.submitted_at = datetime.now() if action == 'submit' else None
        db.session.commit()
        return any_shift
        
    # Step 4: Last resort - create new shift (should rarely happen)
    print(f"[INTERCEPTOR] ⚠️ Creating new shift as last resort")
    new_shift = Shift(
        date=date,
        current_shift_type=current_shift_type,
        next_shift_type=next_shift_type,
        status='draft' if action == 'draft' else 'sent',
        submitted_at=datetime.now() if action == 'submit' else None,
        account_id=account_id,
        team_id=team_id
    )
    db.session.add(new_shift)
    db.session.flush()  # Get the ID
    
    # 🔧 CRITICAL FIX: Commit the shift immediately so it exists in database
    # This prevents foreign key constraint failures when creating related records
    try:
        db.session.commit()
        print(f"[INTERCEPTOR] ✅ Committed new shift ID: {new_shift.id} to database")
    except Exception as commit_error:
        print(f"[INTERCEPTOR] ❌ Failed to commit new shift: {commit_error}")
        db.session.rollback()
        raise commit_error
    
    # Verify the shift exists in database
    verification = Shift.query.filter_by(id=new_shift.id).first()
    if not verification:
        print(f"[INTERCEPTOR] 🚨 Creating emergency backup for shift {new_shift.id}")
        emergency_shift = Shift(
            id=new_shift.id,
            date=date,
            current_shift_type=current_shift_type,
            next_shift_type=next_shift_type,
            status='draft' if action == 'draft' else 'sent',
            account_id=account_id,
            team_id=team_id,
            created_at=datetime.now()
        )
        db.session.merge(emergency_shift)
        db.session.commit()
        
    return new_shift

def create_enhanced_incident_assignment(incident_title, incident_description, incident_priority, 
                                      assigned_to_name, account_id, team_id, handover_context="", handover_request_id=None):
    """Create an enhanced incident assignment in the database"""
    
    try:
        print(f"[DEBUG] create_enhanced_incident_assignment called for: {incident_title} → {assigned_to_name}")
        from models.handover_enhanced import IncidentAssignment
        
        # Handle both user ID and team member name/ID inputs
        assigned_member = None
        assigned_user_id = None
        
        # Check if assigned_to_name is a numeric team member ID
        if assigned_to_name.isdigit():
            team_member_id = int(assigned_to_name)
            # Find team member by team member ID
            assigned_member = TeamMember.query.filter_by(id=team_member_id, team_id=team_id).first()
            if assigned_member and assigned_member.user_id:
                assigned_user_id = assigned_member.user_id
                current_app.logger.info(f"[HANDOVER NOTIFICATION] Found team member by ID {team_member_id}: {assigned_member.name} → User ID {assigned_user_id}")
                print(f"[HANDOVER NOTIFICATION] SUCCESS: TeamMember {team_member_id} ({assigned_member.name}) → User {assigned_user_id}")
            else:
                current_app.logger.warning(f"[HANDOVER NOTIFICATION] Could not find team member for ID: {team_member_id} or no user_id linked")
                print(f"[HANDOVER NOTIFICATION] ERROR: TeamMember ID {team_member_id} not found or no user_id")
                
                # Try to find and create missing TeamMember record
                if not assigned_member:
                    print(f"[HANDOVER NOTIFICATION] TeamMember ID {team_member_id} does not exist")
                elif not assigned_member.user_id:
                    print(f"[HANDOVER NOTIFICATION] TeamMember {assigned_member.name} has no user_id link")
                    # Try to find matching user and link it
                    matching_user = User.query.filter_by(
                        username=assigned_member.name,
                        account_id=account_id,
                        team_id=team_id,
                        is_active=True
                    ).first()
                    if matching_user:
                        assigned_member.user_id = matching_user.id
                        db.session.commit()
                        assigned_user_id = matching_user.id
                        print(f"[HANDOVER NOTIFICATION] FIXED: Linked TeamMember {assigned_member.name} to User {matching_user.username}")
                    else:
                        print(f"[HANDOVER NOTIFICATION] No matching user found for TeamMember {assigned_member.name}")
                        return False
                else:
                    return False
        else:
            # Find the assigned team member by name
            assigned_member = TeamMember.query.filter_by(name=assigned_to_name, team_id=team_id).first()
            if assigned_member and assigned_member.user_id:
                assigned_user_id = assigned_member.user_id
                current_app.logger.info(f"Found team member by name {assigned_to_name}: user ID {assigned_user_id}")
            else:
                current_app.logger.warning(f"Could not find user for team member: {assigned_to_name}")
                return False
        
        # Create the incident assignment
        assignment = IncidentAssignment(
            handover_request_id=handover_request_id,  # Link to handover if provided
            incident_id=incident_title,  # Using title as ID for legacy integration
            incident_title=incident_title,
            incident_description=incident_description,
            incident_priority=incident_priority,
            incident_status='Open',
            assigned_to_id=assigned_user_id,
            assigned_by_id=current_user.id,
            assignment_notes="",
            handover_context=handover_context,
            account_id=account_id,
            team_id=team_id
        )
        
        db.session.add(assignment)
        db.session.flush()  # Flush to get the assignment ID
        
        # Create a comprehensive log entry for the assignment
        try:
            print(f"[DEBUG] Creating log entry for assignment ID: {assignment.id}")
            from models.handover_enhanced import HandoverIncidentResponseLog
            from models.models import User
            
            # Get user details
            assigned_user = User.query.get(assigned_user_id)
            assigning_user = User.query.get(current_user.id)
            print(f"[DEBUG] Users - Assigned: {assigned_user.username if assigned_user else 'None'}, Assigning: {assigning_user.username if assigning_user else 'None'}")
            
            # Determine shift information from handover_context if available
            current_shift_type = "Current"  # Default
            next_shift_type = "Incoming"    # Default
            
            if "Evening to Night" in handover_context:
                current_shift_type = "Evening"
                next_shift_type = "Night"
            elif "Morning to Evening" in handover_context:
                current_shift_type = "Morning"
                next_shift_type = "Evening"
            elif "Night to Morning" in handover_context:
                current_shift_type = "Night"
                next_shift_type = "Morning"
            
            log_entry = HandoverIncidentResponseLog(
                response_date=datetime.utcnow().date(),
                response_datetime=datetime.utcnow(),
                
                # Shift information
                from_shift_type=current_shift_type,
                to_shift_type=next_shift_type,
                
                # Assignment details
                assigned_by_id=current_user.id,
                assigned_by_name=assigning_user.username if assigning_user else "Unknown",
                accepted_by_id=assigned_user_id,
                accepted_by_name=assigned_user.username if assigned_user else "Unknown",
                
                # Incident information
                incident_number=incident_title,
                incident_title=incident_title,
                incident_description=incident_description,
                incident_priority=incident_priority or "Medium",
                incident_type="handover",
                incident_category="Application",
                
                # Status - initially pending response
                assignment_status="pending",
                response_status="pending",
                response_comments="Assignment created - awaiting response",
                assignment_notes="",
                
                # Timing information
                assigned_at=datetime.utcnow(),
                responded_at=datetime.utcnow(),  # Will be updated when user actually responds
                
                # Context and references
                handover_request_id=handover_request_id,
                incident_assignment_id=assignment.id,
                
                # Team and account context
                account_id=account_id,
                team_id=team_id
            )
            
            db.session.add(log_entry)
            print(f"[DEBUG] Log entry created successfully for incident: {incident_title}")
            current_app.logger.info(f"Created incident response log entry for assignment: {incident_title}")
            
        except Exception as log_error:
            print(f"[DEBUG] Failed to create log entry: {str(log_error)}")
            current_app.logger.error(f"Failed to create response log entry: {str(log_error)}")
            # Don't fail the whole assignment creation if log fails
        
        # 🔥 CRITICAL FIX: Create HandoverNotification for dashboard notifications
        try:
            print(f"[DEBUG] Creating HandoverNotification for: {incident_title} → {assigned_to_name}")
            from models.handover_enhanced import HandoverNotification
            
            # Create notification for the assigned user
            notification = HandoverNotification(
                recipient_id=assigned_user_id,
                handover_request_id=handover_request_id,
                notification_type='incident_assigned',
                title=f"New Incident Assignment: {incident_title}",
                message=f"You have been assigned to handle incident: {incident_title}\n\nDescription: {incident_description}\n\nPriority: {incident_priority}\n\nContext: {handover_context}",
                action_url=f"/notifications",
                action_text="View Assignment",
                is_read=False,
                is_dismissed=False,
                account_id=account_id,
                team_id=team_id,
                created_at=datetime.utcnow()
            )
            
            db.session.add(notification)
            print(f"[DEBUG] ✅ HandoverNotification created for user {assigned_user_id} ({assigned_to_name})")
            current_app.logger.info(f"Created HandoverNotification for incident assignment: {incident_title} → {assigned_to_name}")
            
        except Exception as notif_error:
            print(f"[DEBUG] Failed to create HandoverNotification: {str(notif_error)}")
            current_app.logger.error(f"Failed to create HandoverNotification: {str(notif_error)}")
            # Don't fail the whole assignment creation if notification fails
        
        db.session.commit()
        
        current_app.logger.info(f"Created enhanced incident assignment for user ID {assigned_user_id}: {incident_title}")
        return True
        
    except Exception as e:
        current_app.logger.error(f"Failed to create enhanced incident assignment: {str(e)}")
        db.session.rollback()
        return False

# API endpoint to fetch ServiceNow incidents for handover form
@handover_bp.route('/api/get_servicenow_incidents', methods=['GET'])
@login_required
def get_servicenow_incidents():
    """Fetch ServiceNow incidents for the current shift to auto-populate handover form"""
    try:
        # Get shift parameters
        shift_type = request.args.get('shift_type', 'Evening')  # Default to Evening
        date_str = request.args.get('date')
        
        if not date_str:
            date_str = datetime.now().strftime('%Y-%m-%d')
        
        # Initialize ServiceNow service properly with new configuration system
        servicenow = ServiceNowService()
        servicenow.initialize(current_app)  # This will load from database first, then env variables
        
        # Check if ServiceNow is enabled and configured
        if not servicenow.is_enabled_and_configured():
            return jsonify({
                'success': False,
                'error': 'ServiceNow integration is not enabled or properly configured',
                'incidents': {
                    'open_incidents': [],
                    'closed_incidents': [],
                    'total_incidents': []
                },
                'configuration_status': 'disabled_or_not_configured'
            })
        
        # Get shift timing
        shift_times = servicenow.get_shift_times(shift_type, date_str)
        
        # Get incidents for the shift using configured assignment groups
        result = servicenow.get_shift_incidents(
            assignment_groups=servicenow.assignment_groups if hasattr(servicenow, 'assignment_groups') and servicenow.assignment_groups else [],
            shift_start=shift_times['start_time'],
            shift_end=shift_times['end_time']
        )
        
        if result['success']:
            # Format incidents for handover form
            formatted_incidents = {
                'open_incidents': [],
                'closed_incidents': [],
                'priority_incidents': []
            }
            
            # Process open incidents
            for incident in result['open_incidents']:
                formatted_incidents['open_incidents'].append({
                    'number': incident['number'],
                    'title': incident['title'],
                    'priority': incident['priority'],
                    'state': incident['state'],
                    'assignment_group': incident['assignment_group'],
                    'assigned_to': incident['assigned_to']
                })
                
                # Add to priority if High or Critical
                if incident['priority'] in ['High', 'Critical']:
                    formatted_incidents['priority_incidents'].append({
                        'number': incident['number'],
                        'title': incident['title'],
                        'priority': incident['priority'],
                        'state': incident['state'],
                        'assignment_group': incident['assignment_group'],
                        'assigned_to': incident['assigned_to']
                    })
            
            # Process closed incidents
            for incident in result['closed_incidents']:
                formatted_incidents['closed_incidents'].append({
                    'number': incident['number'],
                    'title': incident['title'],
                    'priority': incident['priority'],
                    'state': incident['state'],
                    'assignment_group': incident['assignment_group'],
                    'resolved_at': incident.get('resolved_at', incident.get('closed_at', ''))
                })
            
            return jsonify({
                'success': True,
                'incidents': formatted_incidents,
                'summary': {
                    'open_count': len(formatted_incidents['open_incidents']),
                    'closed_count': len(formatted_incidents['closed_incidents']),
                    'priority_count': len(formatted_incidents['priority_incidents']),
                    'shift_type': shift_type,
                    'shift_start': shift_times['start_time'].strftime('%Y-%m-%d %H:%M'),
                    'shift_end': shift_times['end_time'].strftime('%Y-%m-%d %H:%M'),
                    'assignment_groups_filter': servicenow.get_configured_assignment_groups(),
                    'assignment_groups_filtered': servicenow.is_assignment_group_filtered()
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Failed to fetch ServiceNow incidents'),
                'incidents': {'open_incidents': [], 'closed_incidents': [], 'priority_incidents': []}
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error fetching ServiceNow incidents: {str(e)}',
            'incidents': {'open_incidents': [], 'closed_incidents': [], 'priority_incidents': []}
        })

# API endpoint to fetch engineers for a given date and shift type
@handover_bp.route('/api/get_engineers', methods=['GET'])
@login_required
def get_engineers():
    date_str = request.args.get('date')
    shift_type = request.args.get('shift_type')
    if not date_str or not shift_type:
        return jsonify({'error': 'Missing date or shift_type'}), 400
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except Exception:
        return jsonify({'error': 'Invalid date format'}), 400
    shift_map = {'Morning': 'D', 'Evening': 'E', 'Night': 'N', 'OnShore': 'OS', 'OffShore': 'OF'}
    shift_code = shift_map.get(shift_type)
    if not shift_code:
        return jsonify({'error': 'Invalid shift_type'}), 400
    # Night shift logic
    ist_now = datetime.now(pytz.timezone('Asia/Kolkata'))
    if shift_type == 'Night' and ist_now.time() < dt_time(6,45):
        date = date - timedelta(days=1)
    # Get account/team filtering based on user role
    from flask import session
    account_id = None
    team_id = None
    
    if current_user.role == 'super_admin':
        # Super admin can see all or use session-selected account/team
        account_id = request.args.get('account_id') or session.get('selected_account_id')
        team_id = request.args.get('team_id') or session.get('selected_team_id')
    elif current_user.role == 'account_admin':
        # Account admin can only see their account
        account_id = current_user.account_id
        team_id = request.args.get('team_id') or session.get('selected_team_id')
    else:
        # Team admin/user can only see their team
        account_id = current_user.account_id
        team_id = current_user.team_id
    
    query = ShiftRoster.query.filter_by(date=date, shift_code=shift_code)
    if account_id and team_id:
        query = query.filter_by(account_id=account_id, team_id=team_id)
    elif account_id:
        query = query.filter_by(account_id=account_id)
    
    entries = query.all()
    member_ids = [e.team_member_id for e in entries]
    
    if not member_ids:
        return jsonify({'engineers': []})
    
    tm_query = TeamMember.query.filter(TeamMember.id.in_(member_ids))
    if account_id and team_id:
        tm_query = tm_query.filter_by(account_id=account_id, team_id=team_id)
    elif account_id:
        tm_query = tm_query.filter_by(account_id=account_id)
    engineers = tm_query.all() if member_ids else []
    
    # HANDOVER NOTIFICATION FIX: If no engineers found, try to auto-create missing TeamMember records
    if not engineers and current_user.is_authenticated:
        from models.models import User
        
        # Get users from the same account/team who should have TeamMember records
        if current_user.role == 'super_admin':
            if account_id and team_id:
                users_without_tm = User.query.filter_by(
                    account_id=account_id, 
                    team_id=team_id,
                    is_active=True
                ).filter(
                    ~User.id.in_(
                        db.session.query(TeamMember.user_id).filter_by(
                            account_id=account_id, 
                            team_id=team_id
                        ).filter(TeamMember.user_id.isnot(None))
                    )
                ).limit(10).all()
        elif current_user.role == 'account_admin':
            users_without_tm = User.query.filter_by(
                account_id=current_user.account_id,
                is_active=True
            ).filter(
                ~User.id.in_(
                    db.session.query(TeamMember.user_id).filter_by(
                        account_id=current_user.account_id
                    ).filter(TeamMember.user_id.isnot(None))
                )
            ).limit(10).all()
        else:
            users_without_tm = User.query.filter_by(
                account_id=current_user.account_id,
                team_id=current_user.team_id,
                is_active=True
            ).filter(
                ~User.id.in_(
                    db.session.query(TeamMember.user_id).filter_by(
                        account_id=current_user.account_id,
                        team_id=current_user.team_id
                    ).filter(TeamMember.user_id.isnot(None))
                )
            ).limit(10).all()
        
        # Auto-create missing TeamMember records
        if users_without_tm:
            print(f"[HANDOVER FIX] Creating {len(users_without_tm)} missing TeamMember records")
            for user in users_without_tm:
                new_tm = TeamMember(
                    name=user.username,
                    user_id=user.id,
                    account_id=user.account_id,
                    team_id=user.team_id,
                    email=user.email or f'{user.username}@example.com'
                )
                db.session.add(new_tm)
                print(f"[HANDOVER FIX] Created TeamMember for {user.username}")
            
            try:
                db.session.commit()
                print(f"[HANDOVER FIX] Successfully created missing TeamMember records")
                
                # Re-run the query to get the newly created engineers
                tm_query = TeamMember.query.filter(TeamMember.id.in_(member_ids)) if member_ids else TeamMember.query.filter_by(account_id=account_id, team_id=team_id)
                if account_id and team_id:
                    tm_query = tm_query.filter_by(account_id=account_id, team_id=team_id)
                elif account_id:
                    tm_query = tm_query.filter_by(account_id=account_id)
                engineers = tm_query.all()
                print(f"[HANDOVER FIX] After auto-creation: found {len(engineers)} engineers")
            except Exception as e:
                print(f"[HANDOVER FIX] Error creating TeamMember records: {e}")
                db.session.rollback()
    
    return jsonify({'engineers': [{'id': e.id, 'name': e.name} for e in engineers]})

# API endpoint to fetch all team members for the current user's context
@handover_bp.route('/api/get_all_team_members', methods=['GET'])
@login_required
def get_all_team_members():
    # Use same team member filtering logic as team details route
    tm_query = TeamMember.query
    
    if current_user.role == 'super_admin':
        # Super admin can see all or use session-selected account/team
        account_id = request.args.get('account_id') or session.get('selected_account_id')
        team_id = request.args.get('team_id') or session.get('selected_team_id')
        if account_id:
            tm_query = tm_query.filter_by(account_id=account_id)
        if team_id:
            tm_query = tm_query.filter_by(team_id=team_id)
    elif current_user.role == 'account_admin':
        # Account admin can only see their account
        account_id = current_user.account_id
        team_id = request.args.get('team_id') or session.get('selected_team_id')
        tm_query = tm_query.filter_by(account_id=account_id)
        if team_id:
            tm_query = tm_query.filter_by(team_id=team_id)
    else:
        # Team admin/user can only see their team
        account_id = current_user.account_id
        team_id = current_user.team_id
        tm_query = tm_query.filter_by(account_id=account_id, team_id=team_id)
    
    # Get all team members (remove status filter since TeamMember model doesn't have status field)
    team_members = tm_query.all()
    return jsonify({'team_members': [{'name': member.name, 'id': member.id} for member in team_members]})

@handover_bp.route('/handover/drafts')
@login_required
def handover_drafts():
    # Show all drafts (no created_by field in Shift model)
    query = Shift.query.filter_by(status='draft')
    # Use session-based filtering for super/account admin
    if current_user.role == 'super_admin':
        account_id = session.get('selected_account_id')
        team_id = session.get('selected_team_id')
        if account_id:
            query = query.filter_by(account_id=account_id)
        if team_id:
            query = query.filter_by(team_id=team_id)
    elif current_user.role == 'account_admin':
        account_id = current_user.account_id
        team_id = session.get('selected_team_id')
        query = query.filter_by(account_id=account_id)
        if team_id:
            query = query.filter_by(team_id=team_id)
    else:
        query = query.filter_by(account_id=current_user.account_id, team_id=current_user.team_id)
    drafts = query.all()
    return render_template('handover_drafts.html', drafts=drafts)

@handover_bp.route('/handover/edit/<int:shift_id>', methods=['GET', 'POST'])
@login_required
def edit_handover(shift_id):
    if current_user.role == 'viewer':
        flash('You do not have permission to edit handover forms.')
        return redirect(url_for('dashboard.dashboard'))
    shift = Shift.query.get_or_404(shift_id)
    if current_user.role != 'admin' and (shift.account_id != current_user.account_id or shift.team_id != current_user.team_id):
        flash('You do not have permission to edit this handover form.')
        return redirect(url_for('dashboard.dashboard'))
    tm_query = TeamMember.query
    if current_user.role != 'admin':
        tm_query = tm_query.filter_by(account_id=current_user.account_id, team_id=current_user.team_id)
    team_members = tm_query.all()
    
    # Get teams for the dropdown
    from models.models import Team
    if current_user.role == 'super_admin':
        teams = Team.query.filter_by(status='active').all()
    elif current_user.role == 'account_admin':
        teams = Team.query.filter_by(account_id=current_user.account_id, status='active').all()
    else:
        teams = Team.query.filter_by(account_id=current_user.account_id, id=current_user.team_id, status='active').all()
    
    # Fetch incidents by type for prepopulation
    open_incidents = [i.title for i in Incident.query.filter_by(shift_id=shift.id, type='Active').all()]
    closed_incidents = [i.title for i in Incident.query.filter_by(shift_id=shift.id, type='Closed').all()]
    priority_incidents = [i.title for i in Incident.query.filter_by(shift_id=shift.id, type='Priority').all()]
    handover_incidents = [i.title for i in Incident.query.filter_by(shift_id=shift.id, type='Handover').all()]

    if request.method == 'POST':
        # Audit log: editing handover
        db.session.add(AuditLog(
            user_id=current_user.id,
            username=current_user.username,
            action='Edit Handover',
            details=f'Shift ID: {shift_id}, Action: {request.form.get("action", "send")}'
        ))
        shift.date = datetime.strptime(request.form['handover_date'], '%Y-%m-%d').date()
        shift.current_shift_type = request.form['current_shift_type']
        shift.next_shift_type = request.form['next_shift_type']
        action = request.form.get('action', 'send')
        old_status = shift.status
        shift.status = 'draft' if action == 'save' else 'sent'
        
        # Set submitted_at timestamp if changing from draft to sent
        if old_status == 'draft' and shift.status == 'sent':
            shift.submitted_at = datetime.now()
        elif action == 'save' and shift.status == 'draft':
            # Keep existing submitted_at if reverting to draft
            pass
        # Clear and update engineers
        shift.current_engineers.clear()
        shift.next_engineers.clear()
        # (Re)populate engineers as in create
        shift_map = {'Morning': 'D', 'Evening': 'E', 'Night': 'N', 'OnShore': 'OS', 'OffShore': 'OF'}
        current_shift_code = shift_map[shift.current_shift_type]
        next_shift_code = shift_map[shift.next_shift_type]
        ist_now = datetime.now(pytz.timezone('Asia/Kolkata'))
        def get_engineers_for_shift(date, shift_code):
            entries = ShiftRoster.query.filter_by(date=date, shift_code=shift_code).all()
            member_ids = [e.team_member_id for e in entries]
            return TeamMember.query.filter(TeamMember.id.in_(member_ids)).all() if member_ids else []
        if shift.current_shift_type == 'Night' and ist_now.time() < dt_time(6,45):
            night_date = shift.date - timedelta(days=1)
            current_engineers_objs = get_engineers_for_shift(night_date, current_shift_code)
        else:
            current_engineers_objs = get_engineers_for_shift(shift.date, current_shift_code)
        if shift.next_shift_type == 'Night' and ist_now.time() >= dt_time(21,45):
            next_date = shift.date + timedelta(days=1)
            next_engineers_objs = get_engineers_for_shift(next_date, next_shift_code)
        else:
            next_engineers_objs = get_engineers_for_shift(shift.date, next_shift_code)
        for member in current_engineers_objs:
            shift.current_engineers.append(member)
        for member in next_engineers_objs:
            shift.next_engineers.append(member)
        # Remove and re-add incidents/keypoints
        Incident.query.filter_by(shift_id=shift.id).delete()
        log_action('Delete Incidents', f'Shift ID: {shift.id}')
        ShiftKeyPoint.query.filter_by(shift_id=shift.id).delete()
        log_action('Delete KeyPoints', f'Shift ID: {shift.id}')
        db.session.commit()
        # Audit log: after commit, log send/save
        db.session.add(AuditLog(
            user_id=current_user.id,
            username=current_user.username,
            action='Handover ' + ('Sent' if action == 'send' else 'Saved as Draft'),
            details=f'Shift ID: {shift_id}, Status: {shift.status}'
        ))
        db.session.commit()
        def add_incident(field_prefix, inc_type):
            # Handle different incident types with their specific fields
            incident_ids = request.form.getlist(f'{field_prefix}_incident_id[]')
            
            for i, incident_id in enumerate(incident_ids):
                if incident_id.strip():
                    # Prepare base incident data
                    incident_data = {
                        'title': incident_id,
                        'shift_id': shift.id,
                        'type': inc_type,
                        'account_id': shift.account_id,
                        'team_id': shift.team_id
                    }
                    
                    # Add type-specific fields (using existing model fields)
                    if inc_type == 'Active':  # Open incidents
                        priorities = request.form.getlist('open_incident_priority[]')
                        descriptions = request.form.getlist('open_incident_description[]')
                        assigned_tos = request.form.getlist('open_incident_assigned[]')
                        app_names = request.form.getlist('open_incident_app[]')
                        
                        # Include application name in title
                        app_name = app_names[i] if i < len(app_names) and app_names[i].strip() else ''
                        full_title = f"[{app_name}] {incident_id}" if app_name else incident_id
                        incident_data['title'] = full_title
                        
                        incident_data.update({
                            'priority': priorities[i] if i < len(priorities) else 'Medium',
                            'status': 'Open',
                            'handover': descriptions[i] if i < len(descriptions) else ''
                        })
                        
                        # Send notification if engineer is assigned
                        assigned_engineer = assigned_tos[i] if i < len(assigned_tos) and assigned_tos[i].strip() else None
                        if assigned_engineer:
                            try:
                                # Create enhanced incident assignment
                                create_enhanced_incident_assignment(
                                    incident_title=full_title,
                                    incident_description=descriptions[i] if i < len(descriptions) else '',
                                    incident_priority=priorities[i] if i < len(priorities) else 'Medium',
                                    assigned_to_name=assigned_engineer,
                                    account_id=shift.account_id,
                                    team_id=shift.team_id,
                                    handover_context=f"Assigned during {shift.current_shift_type} to {shift.next_shift_type} handover on {shift.date}",
                                    handover_request_id=None  # Edit mode: HandoverRequest not created in edit flow
                                )
                                
                                # Send incident assignment notification 
                                try:
                                    send_incident_assignment_notification(
                                        full_title, 
                                        descriptions[i] if i < len(descriptions) else '',
                                        assigned_engineer,
                                        'Open Incident',
                                        str(shift.date)
                                    )
                                    print(f"[DEBUG] Notification sent for incident assignment: {full_title} → {assigned_engineer}")
                                except Exception as notify_error:
                                    print(f"[DEBUG] Failed to send notification: {str(notify_error)}")
                                    # Don't fail handover creation if notification fails
                            except Exception as e:
                                import logging
                                logging.error(f"Failed to send incident assignment notification: {e}")
                    
                    elif inc_type == 'Closed':  # Closed incidents
                        resolutions = request.form.getlist('closed_incident_resolution[]')
                        app_names = request.form.getlist('closed_incident_app[]')
                        
                        # Include application name in title
                        app_name = app_names[i] if i < len(app_names) and app_names[i].strip() else ''
                        full_title = f"[{app_name}] {incident_id}" if app_name else incident_id
                        incident_data['title'] = full_title
                        
                        incident_data.update({
                            'status': 'Closed',
                            'priority': 'Medium',
                            'handover': resolutions[i] if i < len(resolutions) else ''
                        })
                    
                    elif inc_type == 'Priority':  # Priority incidents
                        priority_levels = request.form.getlist('priority_incident_level[]')
                        impacts = request.form.getlist('priority_incident_impact[]')
                        app_names = request.form.getlist('priority_incident_app[]')
                        
                        # Include application name in title
                        app_name = app_names[i] if i < len(app_names) and app_names[i].strip() else ''
                        full_title = f"[{app_name}] {incident_id}" if app_name else incident_id
                        incident_data['title'] = full_title
                        
                        incident_data.update({
                            'priority': priority_levels[i] if i < len(priority_levels) else 'High',
                            'status': 'Open',
                            'handover': impacts[i] if i < len(impacts) else ''
                        })
                    
                    elif inc_type == 'Handover':  # Handover incidents
                        statuses = request.form.getlist('handover_incident_status[]')
                        notes = request.form.getlist('handover_incident_notes[]')
                        next_action_bys = request.form.getlist('handover_incident_next_by[]')
                        app_names = request.form.getlist('handover_incident_app[]')
                        
                        # Include application name in title
                        app_name = app_names[i] if i < len(app_names) and app_names[i].strip() else ''
                        full_title = f"[{app_name}] {incident_id}" if app_name else incident_id
                        incident_data['title'] = full_title
                        
                        incident_data.update({
                            'status': statuses[i] if i < len(statuses) else 'Monitoring',
                            'priority': 'Medium',
                            'handover': notes[i] if i < len(notes) else ''
                        })
                        
                        # Send notification if next action engineer is assigned
                        next_action_by = next_action_bys[i] if i < len(next_action_bys) and next_action_bys[i].strip() else None
                        if next_action_by:
                            try:
                                # Create enhanced incident assignment
                                create_enhanced_incident_assignment(
                                    incident_title=full_title,
                                    incident_description=notes[i] if i < len(notes) else '',
                                    incident_priority='Medium',
                                    assigned_to_name=next_action_by,
                                    account_id=shift.account_id,
                                    team_id=shift.team_id,
                                    handover_context=f"Handover incident from {shift.current_shift_type} to {shift.next_shift_type} shift on {shift.date}",
                                    handover_request_id=None  # Fixed: Don't reference shift.id for handover_request foreign key
                                )
                                
                                # Send handover incident notification
                                try:
                                    send_incident_assignment_notification(
                                        full_title,
                                        notes[i] if i < len(notes) else '',
                                        next_action_by,
                                        'Handover Incident',
                                        str(shift.date)
                                    )
                                    print(f"[DEBUG] Notification sent for handover incident: {full_title} → {next_action_by}")
                                except Exception as notify_error:
                                    print(f"[DEBUG] Failed to send handover notification: {str(notify_error)}")
                                    # Don't fail handover creation if notification fails
                            except Exception as e:
                                import logging
                                logging.error(f"Failed to send handover incident notification: {e}")
                    
                    elif inc_type == 'Escalated':  # Escalated incidents
                        escalation_levels = request.form.getlist('escalated_incident_level[]')
                        escalated_tos = request.form.getlist('escalated_incident_to[]')
                        reasons = request.form.getlist('escalated_incident_reason[]')
                        statuses = request.form.getlist('escalated_incident_status[]')
                        app_names = request.form.getlist('escalated_incident_app[]')
                        
                        # Include application name in title
                        app_name = app_names[i] if i < len(app_names) and app_names[i].strip() else ''
                        full_title = f"[{app_name}] {incident_id}" if app_name else incident_id
                        incident_data['title'] = full_title
                        
                        # Combine reason and status for handover field
                        escalation_details = f"Escalation Level: {escalation_levels[i] if i < len(escalation_levels) else 'L2'}\n"
                        escalation_details += f"Escalated To: {escalated_tos[i] if i < len(escalated_tos) else ''}\n"
                        escalation_details += f"Reason: {reasons[i] if i < len(reasons) else ''}\n"
                        escalation_details += f"Status: {statuses[i] if i < len(statuses) else ''}"
                        
                        incident_data.update({
                            'status': 'Escalated',
                            'priority': 'High',
                            'handover': escalation_details
                        })
                    
                    incident = Incident(**incident_data)
                    db.session.add(incident)
                    log_action('Add Incident', f'ID: {incident_id}, Type: {inc_type}, Shift ID: {shift.id}')
        
        add_incident('open', 'Active')
        add_incident('closed', 'Closed')
        add_incident('priority', 'Priority')
        add_incident('handover', 'Handover')
        add_incident('escalated', 'Escalated')
        # Process key points - fix field name mismatch
        key_point_descriptions = request.form.getlist('keypoint_description[]')
        keypoint_assigned_tos = request.form.getlist('keypoint_assigned_to[]')
        keypoint_statuses = request.form.getlist('keypoint_status[]')
        keypoint_jira_ids = request.form.getlist('keypoint_jira_id[]')
        
        # ========== ENHANCED DEBUG LOGGING FOR USER ISSUE ==========
        print(f"\n🔍 ENHANCED KEY POINT FORM SUBMISSION DEBUG - Shift ID: {shift.id}")
        print(f"   🔹 User: {session.get('username', 'Unknown')}")
        print(f"   🔹 Timestamp: {datetime.now()}")
        print(f"   🔹 Raw form data received:")
        print(f"      - Descriptions: {key_point_descriptions}")
        print(f"      - Assigned Tos: {keypoint_assigned_tos}")
        print(f"      - Statuses: {keypoint_statuses}")
        print(f"      - JIRA IDs: {keypoint_jira_ids}")
        print(f"   🔹 Total key points being processed: {len(key_point_descriptions)}")
        
        # Count how many are marked as closed
        closed_count = keypoint_statuses.count('Closed')
        open_count = keypoint_statuses.count('Open')
        progress_count = keypoint_statuses.count('In Progress')
        
        print(f"   🔹 Status breakdown:")
        print(f"      - 'Closed': {closed_count} key points")
        print(f"      - 'Open': {open_count} key points")
        print(f"      - 'In Progress': {progress_count} key points")
        
        if closed_count == 0:
            print(f"   ⚠️  USER ISSUE ALERT: No key points marked as 'Closed' in form submission!")
            print(f"   ⚠️  This means user is NOT selecting 'Closed' status in the dropdown")
        else:
            print(f"   ✅ User is correctly marking {closed_count} key points as 'Closed'")
        print(f"   =========================================================\n")
        
        # Debug logging for key point form data
        print(f"🔍 KEY POINT FORM DATA DEBUG - Shift ID: {shift.id}")
        print(f"   key_point_descriptions: {key_point_descriptions}")
        print(f"   keypoint_assigned_tos: {keypoint_assigned_tos}")
        print(f"   keypoint_statuses: {keypoint_statuses}")
        print(f"   keypoint_jira_ids: {keypoint_jira_ids}")
        print(f"   Total key points to process: {len(key_point_descriptions)}")
        print(f"🚨 ENHANCED KEY POINT PROCESSING - VERSION 2.0 🚨")
        
        for i in range(len(key_point_descriptions)):
            details = key_point_descriptions[i].strip() if i < len(key_point_descriptions) else ''
            jira_id = keypoint_jira_ids[i].strip() if i < len(keypoint_jira_ids) else ''
            responsible_id = keypoint_assigned_tos[i] if i < len(keypoint_assigned_tos) else ''
            status = keypoint_statuses[i] if i < len(keypoint_statuses) else 'Open'
            
            print(f"Processing key point {i+1}: desc='{details}', jira='{jira_id}', responsible='{responsible_id}', status='{status}'")
            
            if details:
                # If status is being set to Closed, find and close the specific key point
                if status == 'Closed':
                    # Parse responsible engineer ID for matching
                    responsible_engineer_id = None
                    if responsible_id:
                        if responsible_id.isdigit():
                            responsible_engineer_id = int(responsible_id)
                        else:
                            # Try to find user by name
                            user = TeamMember.query.filter_by(name=responsible_id).first()
                            if user:
                                responsible_engineer_id = user.id
                    
                    # Find the specific key point to close by matching description, jira_id, and responsible engineer
                    query = ShiftKeyPoint.query.filter(
                        ShiftKeyPoint.description == details,
                        ShiftKeyPoint.jira_id == (jira_id if jira_id else None),
                        ShiftKeyPoint.status.in_(['Open', 'In Progress'])
                    )
                    
                    # If we have a responsible engineer, try to match it specifically
                    if responsible_engineer_id is not None:
                        specific_kp = query.filter(ShiftKeyPoint.responsible_engineer_id == responsible_engineer_id).first()
                        if specific_kp:
                            specific_kp.status = 'Closed'
                            db.session.add(specific_kp)
                            print(f"Closed specific key point: {specific_kp.id} (matched engineer {responsible_engineer_id})")
                            log_action('Close KeyPoint', f'Description: {details}, ID: {specific_kp.id}, Shift ID: {shift.id}')
                            continue
                    
                    # If no specific match, close the most recent one with this description
                    most_recent_kp = query.order_by(ShiftKeyPoint.id.desc()).first()
                    if most_recent_kp:
                        most_recent_kp.status = 'Closed'
                        db.session.add(most_recent_kp)
                        print(f"Closed existing key point: {most_recent_kp.id}")
                        log_action('Close KeyPoint', f'Description: {details}, ID: {most_recent_kp.id}, Shift ID: {shift.id}')
                    else:
                        print(f"No open key point found to close for: {details}")
                        # 🔧 ENHANCED FIX: Try broader matching if exact match fails
                        print(f"   🔧 FALLBACK: Searching for key points with similar description...")
                        fallback_kps = ShiftKeyPoint.query.filter(
                            ShiftKeyPoint.description.like(f'%{details[:20]}%'),
                            ShiftKeyPoint.status.in_(['Open', 'In Progress'])
                        ).all()
                        
                        if fallback_kps:
                            print(f"   🔧 FALLBACK: Found {len(fallback_kps)} potential matches:")
                            for fallback_kp in fallback_kps:
                                print(f"      - ID {fallback_kp.id}: '{fallback_kp.description[:50]}...'")
                            
                            # Close the most recent one
                            latest_fallback = max(fallback_kps, key=lambda x: x.id)
                            latest_fallback.status = 'Closed'
                            db.session.add(latest_fallback)
                            print(f"   🔧 FALLBACK: Closed key point ID {latest_fallback.id} as best match")
                            log_action('Close KeyPoint (Fallback)', f'Description: {details}, ID: {latest_fallback.id}, Shift ID: {shift.id}')
                        else:
                            print(f"   🔧 FALLBACK: No similar key points found either")
                    
                    # Do not add a new key point for closed status
                    continue
                
                # Find the most recent existing open/in-progress key point with the same description and jira_id
                existing_kp = ShiftKeyPoint.query.filter(
                    ShiftKeyPoint.description == details,
                    ShiftKeyPoint.jira_id == (jira_id if jira_id else None),
                    ShiftKeyPoint.status.in_(['Open', 'In Progress'])
                ).order_by(ShiftKeyPoint.id.desc()).first()
                
                print(f"🔧 KEY POINT PROCESSING: '{details[:50]}...' - Found existing KP: {existing_kp.id if existing_kp else 'None'}")
                
                if existing_kp:
                    # Parse responsible engineer ID
                    responsible_engineer_id = None
                    if responsible_id:
                        if responsible_id.isdigit():
                            responsible_engineer_id = int(responsible_id)
                        else:
                            # Try to find user by name
                            user = TeamMember.query.filter_by(name=responsible_id).first()
                            if user:
                                responsible_engineer_id = user.id
                    
                    # 🔧 FIX: Always update the existing key point instead of creating duplicates
                    # Update the key point with any new information
                    updated = False
                    
                    if existing_kp.status != status:
                        existing_kp.status = status
                        updated = True
                        print(f"🔧 UPDATED STATUS: KP {existing_kp.id} status {existing_kp.status} → {status}")
                    
                    if responsible_engineer_id is not None and existing_kp.responsible_engineer_id != responsible_engineer_id:
                        existing_kp.responsible_engineer_id = responsible_engineer_id
                        updated = True
                        print(f"🔧 UPDATED ASSIGNMENT: KP {existing_kp.id} engineer {existing_kp.responsible_engineer_id} → {responsible_engineer_id}")
                    
                    if updated:
                        db.session.add(existing_kp)
                        log_action('Update KeyPoint', f'ID: {existing_kp.id}, Status: {status}, Shift: {shift.id}')
                        print(f"🔧 UPDATED EXISTING KEY POINT: ID {existing_kp.id}")
                    else:
                        print(f"🔧 REFERENCED EXISTING KEY POINT: ID {existing_kp.id} (no changes needed)")
                        log_action('Reference KeyPoint', f'Description: {details}, Existing ID: {existing_kp.id}, Shift: {shift.id}')
                    
                    # 🔧 CRITICAL: Do NOT create a new key point - just reference the existing one
                    continue
                        
                else:
                    # 🔧 ENHANCED FIX: Before creating a new key point, check for global duplicates
                    print(f"🔧 CREATING NEW KEY POINT: Checking for global duplicates first...")
                    
                    # Check for any existing key points with similar description (global search)
                    global_existing_kps = ShiftKeyPoint.query.filter(
                        ShiftKeyPoint.account_id == shift.account_id,
                        ShiftKeyPoint.team_id == shift.team_id,
                        ShiftKeyPoint.status.in_(['Open', 'In Progress']),
                        ShiftKeyPoint.description == details
                    ).all()
                    
                    if global_existing_kps:
                        print(f"🔧 GLOBAL DUPLICATE PREVENTION: Found {len(global_existing_kps)} existing key points with same description")
                        for existing in global_existing_kps:
                            print(f"   - ID {existing.id}: '{existing.description[:40]}...' Status: {existing.status} (Shift {existing.shift_id})")
                        
                        # Instead of creating a new key point, update the most recent existing one
                        latest_existing = max(global_existing_kps, key=lambda x: x.id)
                        print(f"🔧 PREVENTING DUPLICATE: Updating existing key point ID {latest_existing.id} instead of creating new")
                        
                        # Parse responsible engineer ID
                        responsible_engineer_id = None
                        if responsible_id:
                            if responsible_id.isdigit():
                                responsible_engineer_id = int(responsible_id)
                            else:
                                # Try to find user by name
                                user = TeamMember.query.filter_by(name=responsible_id).first()
                                if user:
                                    responsible_engineer_id = user.id
                        
                        # Update the existing key point
                        if latest_existing.status != status:
                            latest_existing.status = status
                            print(f"🔧 UPDATED STATUS: KP {latest_existing.id} status → {status}")
                        
                        if responsible_engineer_id and latest_existing.responsible_engineer_id != responsible_engineer_id:
                            latest_existing.responsible_engineer_id = responsible_engineer_id
                            print(f"🔧 UPDATED ENGINEER: KP {latest_existing.id} engineer → {responsible_engineer_id}")
                        
                        if jira_id and latest_existing.jira_id != jira_id:
                            latest_existing.jira_id = jira_id
                            print(f"🔧 UPDATED JIRA: KP {latest_existing.id} jira → {jira_id}")
                        
                        db.session.add(latest_existing)
                        log_action('Update KeyPoint (Prevent Duplicate)', f'ID: {latest_existing.id}, Description: {details}, Status: {status}, Shift ID: {shift.id}')
                        
                        continue  # Skip creating new key point
                    
                    # This is a completely new key point
                    print(f"🔧 CREATING BRAND NEW KEY POINT: '{details[:50]}...' - No existing key point found globally")
                    responsible_engineer_id = None
                    if responsible_id:
                        if responsible_id.isdigit():
                            responsible_engineer_id = int(responsible_id)
                        else:
                            # Try to find user by name
                            user = TeamMember.query.filter_by(name=responsible_id).first()
                            if user:
                                responsible_engineer_id = user.id
                    
                    new_kp = ShiftKeyPoint(
                        description=details,
                        status=status,
                        responsible_engineer_id=responsible_engineer_id,
                        shift_id=shift.id,
                        jira_id=jira_id if jira_id else None,
                        account_id=shift.account_id,
                        team_id=shift.team_id
                    )
                    db.session.add(new_kp)
                    log_action('Add KeyPoint', f'Description: {details}, Status: {status}, Shift ID: {shift.id}')
        db.session.commit()
        if action == 'send':
            import logging
            logging.basicConfig(level=logging.DEBUG)
            logging.debug(f"[EMAIL] Attempting to send handover email for shift_id={shift.id}, date={shift.date}, current_shift_type={shift.current_shift_type}, next_shift_type={shift.next_shift_type}")
            try:
                send_handover_email(shift)
                logging.debug(f"[EMAIL] Email sent successfully for shift_id={shift.id}")
                flash('Handover submitted and email sent!')
            except Exception as e:
                logging.error(f"[EMAIL] Failed to send email for shift_id={shift.id}: {e}")
                flash(f'Error sending email: {e}')
        else:
            flash('Draft updated.')
        # After save or send, redirect to drafts (for save) or reports (for send)
        if action == 'save':
            return redirect(url_for('reports.handover_reports'))
        else:
            return redirect(url_for('reports.handover_reports'))
    # GET: populate form with existing data
    current_engineers = [m.name for m in shift.current_engineers]
    next_engineers = [m.name for m in shift.next_engineers]
    
    # 🔧 FIX: Load ALL open key points globally (like dashboard), not just for this shift
    # This prevents duplication when key points are created in one shift but referenced in another
    all_kps = ShiftKeyPoint.query.filter(
        ShiftKeyPoint.account_id == shift.account_id,
        ShiftKeyPoint.team_id == shift.team_id,
        ShiftKeyPoint.status.in_(['Open', 'In Progress'])
    ).all()
    
    print(f"🔧 LOADING KEY POINTS: Found {len(all_kps)} open key points globally for account {shift.account_id}, team {shift.team_id}")
    
    # Deduplicate by (description, jira_id) and keep the most recent
    kp_map = {}
    for kp in all_kps:
        key = (kp.description, kp.jira_id)
        if key not in kp_map or kp.id > kp_map[key].id:
            kp_map[key] = kp
    open_key_points = list(kp_map.values())
    
    print(f"🔧 DEDUPLICATION: After deduplication, showing {len(open_key_points)} unique key points")
    
    # Enhance key points with assigned engineer names for template display
    for kp in open_key_points:
        kp.assigned_to = None  # Default to None
        if kp.responsible_engineer_id:
            # Find the team member by ID
            engineer = TeamMember.query.get(kp.responsible_engineer_id)
            if engineer:
                kp.assigned_to = engineer.name
            else:
                print(f"[DEBUG] Edit handover - Key point has invalid engineer ID: {kp.responsible_engineer_id}")
    return render_template('handover_form.html',
        team_members=team_members,
        teams=teams,
        current_engineers=current_engineers,
        next_engineers=next_engineers,
        current_shift_type=shift.current_shift_type,
        next_shift_type=shift.next_shift_type,
        open_key_points=open_key_points,
        current_time=datetime.now(),
        shift=shift,
        open_incidents=open_incidents,
        closed_incidents=closed_incidents,
        priority_incidents=priority_incidents,
        handover_incidents=handover_incidents,
        today=shift.date.strftime('%Y-%m-%d'),
        show_team_error=False
    )




@handover_bp.route('/handover', methods=['GET', 'POST'])
@login_required
def handover():
    # Add timing for entire request
    import time
    request_start_time = time.time()
    print(f"[DEBUG] Handover request started at {request_start_time}")
    
    # 🔥 CRITICAL: Identify which route is being used
    print("🔥🔥🔥 FULL HANDOVER ROUTE FROM handover.py IS BEING USED 🔥🔥🔥")
    
    # Debug logging
    import logging
    logging.basicConfig(level=logging.DEBUG)
    
    # Get selected account/team - different logic for GET vs POST
    if request.method == 'POST':
        # For POST, get from form data, but fallback to user's own account/team if not provided
        if current_user.role == 'super_admin':
            # Super admin derives account_id from selected team (they shouldn't have personal account_id)
            team_id_raw = request.form.get('team_id')
            if not team_id_raw:
                flash('Super admin must select a team before submitting handover.', 'error')
                return redirect(url_for('handover.handover'))
            
            # Get account_id from the selected team
            from models.models import Team
            try:
                team_id_int = int(team_id_raw)
                selected_team = Team.query.get(team_id_int)
                if not selected_team:
                    flash('Selected team not found.', 'error')
                    return redirect(url_for('handover.handover'))
                account_id = selected_team.account_id
                print(f"[DEBUG] Super admin derived account_id {account_id} from team {team_id_int}")
            except (ValueError, TypeError):
                flash('Invalid team selection.', 'error')
                return redirect(url_for('handover.handover'))
        else:
            account_id = current_user.account_id
            
        if current_user.role in ['super_admin', 'account_admin']:
            team_id_raw = request.form.get('team_id')
            if current_user.role == 'super_admin' and not team_id_raw:
                flash('Super admin must select a team before submitting handover.', 'error')
                return redirect(url_for('handover.handover'))
        else:
            team_id_raw = current_user.team_id
            
        logging.debug(f"POST - account_id derived/selected: {account_id}, current_user.account_id: {current_user.account_id}")
        logging.debug(f"POST - team_id_raw from form: {request.form.get('team_id')}, current_user.team_id: {current_user.team_id}")
        logging.debug(f"POST - current_user.role: {current_user.role}")
    else:
        # For GET, use user's account or session data
        if current_user.role == 'super_admin':
            # For super admin GET requests, derive account_id from session team if available
            team_id_raw = request.args.get('team_id') or session.get('selected_team_id')
            if team_id_raw:
                from models.models import Team
                try:
                    team_id_int = int(team_id_raw)
                    selected_team = Team.query.get(team_id_int)
                    account_id = selected_team.account_id if selected_team else None
                except (ValueError, TypeError):
                    account_id = None
            else:
                account_id = request.args.get('account_id') or session.get('selected_account_id')
        else:
            account_id = current_user.account_id
            team_id_raw = current_user.team_id
        
    # Validate account_id for non-super-admin users
    if current_user.role != 'super_admin':
        if not account_id:
            account_id = current_user.account_id
            
        # Final safeguard: if current_user.account_id is also None, we need to handle this
        if not account_id:
            flash('User account configuration is incomplete. Please contact administrator.', 'error')
            return redirect(url_for('dashboard.dashboard'))
    
    # Convert account_id to int if it's a string
    try:
        account_id = int(account_id) if account_id not in (None, '', 'None') else None
    except (TypeError, ValueError):
        if current_user.role == 'super_admin':
            account_id = None
        else:
            flash('Invalid account ID.', 'error')
            return redirect(url_for('handover.handover'))
        
    logging.debug(f"Final account_id: {account_id}, team_id_raw: {team_id_raw}")
        
    try:
        team_id = int(team_id_raw) if team_id_raw not in (None, '', 'None') else None
    except (TypeError, ValueError):
        team_id = None
        
    logging.debug(f"Final team_id: {team_id}")
    
    # Validate team_id exists
    from models.models import Team
    valid_team = Team.query.get(team_id) if team_id else None
    if request.method == 'POST' and not valid_team:
        flash('Please select a valid Team before submitting the handover.', 'error')
        return redirect(url_for('handover.handover'))
    # If GET and no valid team, show form with error and disable submit
    show_team_error = not valid_team
    from models.models import Team
    if current_user.role == 'super_admin':
        teams = Team.query.filter_by(status='active').all()
    elif current_user.role == 'account_admin':
        teams = Team.query.filter_by(account_id=current_user.account_id, status='active').all()
    else:
        teams = Team.query.filter_by(account_id=current_user.account_id, id=current_user.team_id, status='active').all()
    
    # Set default team selection based on user role
    default_team_id = None
    if current_user.role in ['user', 'team_admin'] and current_user.team_id:
        default_team_id = current_user.team_id
    elif current_user.role == 'account_admin' and not team_id and teams:
        # For account admin, don't auto-select, let them choose
        default_team_id = None
    elif team_id:
        default_team_id = team_id
    
    # Use same team member filtering logic as team details route
    tm_query = TeamMember.query
    if current_user.role == 'super_admin':
        # For super admin, use selected account/team from form or session
        if account_id:
            tm_query = tm_query.filter_by(account_id=account_id)
        if team_id:
            tm_query = tm_query.filter_by(team_id=team_id)
    elif current_user.role == 'account_admin':
        # For account admin, filter by their account
        tm_query = tm_query.filter_by(account_id=current_user.account_id)
        if team_id:
            tm_query = tm_query.filter_by(team_id=team_id)
    else:
        # For team admin/user, filter by their account and team
        tm_query = tm_query.filter_by(account_id=current_user.account_id, team_id=current_user.team_id)
    
    team_members = tm_query.all()
    
    ist_now = datetime.now(pytz.timezone('Asia/Kolkata'))
    default_date = ist_now.date()
    shift_map = {'Morning': 'D', 'Evening': 'E', 'Night': 'N', 'OnShore': 'OS', 'OffShore': 'OF'}
    
    # POST: Save as draft or send
    if request.method == 'POST':
        # Get form data - wrapped in comprehensive exception handling
        try:
            print(f"[DEBUG] Starting handover POST processing")
            handover_date_str = request.form.get('handover_date')
            if not handover_date_str:
                flash('Handover date is required.', 'error')
                return redirect(url_for('handover.handover'))
            date = datetime.strptime(handover_date_str, '%Y-%m-%d').date()
        except ValueError as e:
            flash(f'Invalid date format: {e}', 'error')
            return redirect(url_for('handover.handover'))
        except KeyError as e:
            flash(f'Missing required field: {e}', 'error')
            return redirect(url_for('handover.handover'))
            
        current_shift_type = request.form.get('current_shift_type')
        next_shift_type = request.form.get('next_shift_type')
        
        # Normalize shift types to ensure proper capitalization
        if current_shift_type:
            current_shift_type = current_shift_type.capitalize()
        if next_shift_type:
            next_shift_type = next_shift_type.capitalize()
        
        if not current_shift_type or not next_shift_type:
            flash('Please select both current and next shift types.', 'error')
            return redirect(url_for('handover.handover'))
            
        action = request.form.get('action', 'submit')
        
        # COMMENTED OUT FAST PATH - it was preventing full incident/keypoint processing
        # # FAST PATH: Create minimal handover immediately
        # print(f"[FAST_PATH] Creating handover with minimal processing - Action: {action}")
        # 
        # # Create minimal shift record immediately
        # shift = Shift(
        #     date=date,
        #     current_shift_type=current_shift_type,
        #     next_shift_type=next_shift_type,
        #     status='draft' if action == 'draft' else 'sent',
        #     account_id=account_id,
        #     team_id=team_id
        # )
        # db.session.add(shift)
        # db.session.commit()
        # 
        # # FAST_PATH: Process incident assignments if they exist
        # assigned_tos = request.form.getlist('open_incident_assigned[]')
        # incident_ids = request.form.getlist('open_incident_id[]')
        # descriptions = request.form.getlist('open_incident_description[]')
        # priorities = request.form.getlist('open_incident_priority[]')
        # app_names = request.form.getlist('open_incident_app[]')
        # 
        # if assigned_tos and any(assigned_to.strip() for assigned_to in assigned_tos):
        #     print(f"[FAST_PATH] Processing {len(assigned_tos)} potential incident assignments")
        #     for i, assigned_to in enumerate(assigned_tos):
        #         if assigned_to and assigned_to.strip():
        #             incident_id = incident_ids[i] if i < len(incident_ids) else f"Incident-{i+1}"
        #             app_name = app_names[i] if i < len(app_names) and app_names[i].strip() else ''
        #             full_title = f"[{app_name}] {incident_id}" if app_name else incident_id
        #             incident_desc = descriptions[i] if i < len(descriptions) else ''
        #             incident_priority = priorities[i] if i < len(priorities) else 'Medium'
        #             
        #             try:
        #                 success = create_enhanced_incident_assignment(
        #                     incident_title=full_title,
        #                     incident_description=incident_desc,
        #                     incident_priority=incident_priority,
        #                     assigned_to_name=assigned_to.strip(),
        #                     account_id=account_id,
        #                     team_id=team_id,
        #                     handover_context=f"FAST_PATH assignment during {current_shift_type} to {next_shift_type} handover",
        #                     handover_request_id=shift.id  # Link to the handover we just created
        #                 )
        #                 if success:
        #                     print(f"[FAST_PATH] ✅ Created assignment: {full_title} → {assigned_to}")
        #                 else:
        #                     print(f"[FAST_PATH] ❌ Failed to create assignment: {full_title} → {assigned_to}")
        #             except Exception as e:
        #                 print(f"[FAST_PATH] ❌ Error creating assignment: {str(e)}")
        # else:
        #     print(f"[FAST_PATH] No incident assignments found in form data")
        # 
        # print(f"[FAST_PATH] Handover created with ID: {shift.id} - redirecting immediately")
        # 
        # if action == 'submit':
        #     flash('Shift handover submitted successfully!', 'success')
        # else:
        #     flash('Draft saved successfully!', 'success')
        #     
        # return redirect(url_for('reports.handover_reports'))
        
        # FULL PROCESSING PATH: Create shift with complete incident and keypoint processing
        print(f"[FULL_PATH] Creating handover with complete processing - Action: {action}")
        
        # � UNIVERSAL INTERCEPTOR: Use bulletproof shift reuse function
        shift = get_or_reuse_shift(date, current_shift_type, next_shift_type, account_id, team_id, action)
        
        # Clear existing data for this shift to ensure clean state
        print(f"[INTERCEPTOR] Clearing existing data for shift {shift.id}")
        Incident.query.filter_by(shift_id=shift.id).delete()
        ShiftKeyPoint.query.filter_by(shift_id=shift.id).delete()
        
        print(f"[FULL_PATH] Using shift with ID: {shift.id}")
        
        # 🔧 SAFETY MECHANISM: Ensure shift exists in database before proceeding
        # This prevents foreign key constraint failures if shift creation was incomplete
        try:
            db.session.flush()  # Ensure shift is written to database
            shift_verification = Shift.query.filter_by(id=shift.id).first()
            if not shift_verification:
                print(f"[SAFETY] Shift {shift.id} not found after creation, force committing...")
                db.session.commit()
                shift_verification = Shift.query.filter_by(id=shift.id).first()
                if not shift_verification:
                    raise Exception(f"Failed to create shift {shift.id}")
            print(f"[SAFETY] Verified shift {shift.id} exists in database")
        except Exception as safety_error:
            print(f"[SAFETY] Error during shift verification: {safety_error}")
            # If there's any issue, try to recover by using an existing shift
            fallback_shift = Shift.query.filter_by(
                date=date, current_shift_type=current_shift_type, 
                next_shift_type=next_shift_type, team_id=team_id, account_id=account_id
            ).first()
            if fallback_shift:
                print(f"[SAFETY] Using fallback shift {fallback_shift.id}")
                shift = fallback_shift
            else:
                raise Exception("Unable to create or find suitable shift record")
        
        # 🔥 CRITICAL FIX: Create HandoverRequest record for foreign key constraints
        from models.handover_enhanced import HandoverRequest
        
        # Check if HandoverRequest already exists with this ID
        existing_request = HandoverRequest.query.filter_by(id=shift.id).first()
        if not existing_request:
            # Create a new HandoverRequest with the same ID as the shift
            handover_request = HandoverRequest(
                id=shift.id,  # Use same ID as shift for consistency
                shift_date=shift.date,
                current_shift_type=shift.current_shift_type,
                next_shift_type=shift.next_shift_type,
                status='fully_accepted' if action == 'submit' else 'pending',  # Use valid HandoverRequest status values
                account_id=shift.account_id,
                team_id=shift.team_id,
                created_by_id=current_user.id,  # Required field
                shift_summary="Auto-created for incident assignment compatibility"
            )
            db.session.add(handover_request)
            db.session.flush()  # Ensure it exists before incident assignment
            print(f"[FULL_PATH] ✅ Created HandoverRequest record with ID: {shift.id}")
        else:
            print(f"[FULL_PATH] ✅ Reusing existing HandoverRequest with ID: {shift.id}")
        
        print(f"[FULL_PATH] HandoverRequest ready for incident assignments")
        
        print(f"[DEBUG] Shift object after creation:")
        print(f"  shift.id: {shift.id}")
        print(f"  shift.account_id: {shift.account_id}")
        print(f"  shift.team_id: {shift.team_id}")
        print(f"  shift.status: {shift.status}")
        print(f"  shift.date: {shift.date}")
        print(f"  shift.current_shift_type: {shift.current_shift_type}")
        print(f"  shift.next_shift_type: {shift.next_shift_type}")
        
        # Add engineers to the shift
        shift_map = {'Morning': 'D', 'Evening': 'E', 'Night': 'N', 'OnShore': 'OS', 'OffShore': 'OF'}
        current_shift_code = shift_map[current_shift_type]
        next_shift_code = shift_map[next_shift_type]
        
        def get_engineers_for_shift(date, shift_code):
            query = ShiftRoster.query.filter_by(date=date, shift_code=shift_code)
            if account_id and team_id:
                query = query.filter_by(account_id=account_id, team_id=team_id)
            elif account_id:
                query = query.filter_by(account_id=account_id)
            entries = query.all()
            member_ids = [e.team_member_id for e in entries]
            return TeamMember.query.filter(TeamMember.id.in_(member_ids)).all() if member_ids else []
        
        # Get engineers for current shift
        if current_shift_type == 'Night' and ist_now.time() < dt_time(6,45):
            night_date = date - timedelta(days=1)
            current_engineers_objs = get_engineers_for_shift(night_date, current_shift_code)
        else:
            current_engineers_objs = get_engineers_for_shift(date, current_shift_code)
        
        # Get engineers for next shift
        if next_shift_type == 'Night' and ist_now.time() >= dt_time(21,45):
            next_date = date + timedelta(days=1)
            next_engineers_objs = get_engineers_for_shift(next_date, next_shift_code)
        else:
            next_engineers_objs = get_engineers_for_shift(date, next_shift_code)
            
        # Assign engineers to shift
        for member in current_engineers_objs:
            shift.current_engineers.append(member)
        for member in next_engineers_objs:
            shift.next_engineers.append(member)
            
        print(f"[FULL_PATH] Assigned {len(current_engineers_objs)} current engineers and {len(next_engineers_objs)} next engineers")
        
        # 🔍 CRITICAL DEBUG: Check if we reach the incident processing section
        print(f"[CRITICAL DEBUG] About to start incident processing section...")
        print(f"[CRITICAL DEBUG] shift.id = {shift.id}")
        print(f"[CRITICAL DEBUG] action = {action}")
        print(f"[CRITICAL DEBUG] Form keys: {list(request.form.keys())[:10]}...")  # First 10 keys
        
        # Add incidents - using detailed form structure
        def add_detailed_incident(field_prefix, inc_type):
            print(f"=== Processing incidents for {field_prefix} ({inc_type}) ===")
            
            # 🛡️ BULLETPROOF: Use the shift object that was already created by the main function
            shift_id_to_use = shift.id
            print(f"[SAFETY] Using main function's shift ID: {shift_id_to_use}")
            
            # Get arrays for each field type
            app_names = request.form.getlist(f'{field_prefix}_app[]')
            incident_ids = request.form.getlist(f'{field_prefix}_id[]')
            
            print(f"Found {len(app_names)} app names: {app_names}")
            print(f"Found {len(incident_ids)} incident IDs: {incident_ids}")
            print(f"Will use shift_id: {shift_id_to_use}")
            
            # Handle specific fields for each incident type
            if inc_type == 'Open':
                priorities = request.form.getlist(f'{field_prefix}_priority[]')
                assigned_to = request.form.getlist(f'{field_prefix}_assigned[]')
                descriptions = request.form.getlist(f'{field_prefix}_description[]')
                
                print(f"Open incident fields - priorities: {priorities}, assigned: {assigned_to}, descriptions: {descriptions}")
                
                for i in range(len(app_names)):
                    if i < len(incident_ids) and (app_names[i].strip() or incident_ids[i].strip()):
                        print(f"Creating open incident {i+1}: {app_names[i]} - {incident_ids[i]}")
                        full_title = f"{app_names[i]} - {incident_ids[i]}".strip(' -')
                        incident = Incident(
                            title=full_title,
                            status='Active',
                            priority=priorities[i] if i < len(priorities) else 'Medium',
                            assigned_to=assigned_to[i] if i < len(assigned_to) else '',
                            description=descriptions[i] if i < len(descriptions) else '',
                            shift_id=shift_id_to_use,
                            type='Open',
                            account_id=account_id,
                            team_id=team_id
                        )
                        db.session.add(incident)
                        print(f"Added open incident to session: {incident}")
                        
                        # Create incident assignment if an engineer is assigned
                        assigned_engineer = assigned_to[i] if i < len(assigned_to) and assigned_to[i].strip() else None
                        if assigned_engineer:
                            try:
                                print(f"[DEBUG] Creating enhanced assignment for: {full_title} → {assigned_engineer}")
                                success = create_enhanced_incident_assignment(
                                    incident_title=full_title,
                                    incident_description=descriptions[i] if i < len(descriptions) else '',
                                    incident_priority=priorities[i] if i < len(priorities) else 'Medium',
                                    assigned_to_name=assigned_engineer,
                                    account_id=account_id,
                                    team_id=team_id,
                                    handover_context=f"Assigned during {current_shift_type} to {next_shift_type} handover on {date}",
                                    handover_request_id=shift_id_to_use  # Link to the handover_request we created
                                )
                                if success:
                                    print(f"[DEBUG] ✅ Successfully created assignment: {full_title} → {assigned_engineer}")
                                else:
                                    print(f"[DEBUG] ❌ Failed to create assignment: {full_title} → {assigned_engineer}")
                            except Exception as e:
                                print(f"[DEBUG] ❌ Error creating assignment: {str(e)}")
                        
            elif inc_type == 'Closed':
                resolutions = request.form.getlist(f'{field_prefix}_resolution[]')
                
                print(f"Closed incident fields - resolutions: {resolutions}")
                
                for i in range(len(app_names)):
                    if i < len(incident_ids) and (app_names[i].strip() or incident_ids[i].strip()):
                        print(f"Creating closed incident {i+1}: {app_names[i]} - {incident_ids[i]}")
                        incident = Incident(
                            title=f"{app_names[i]} - {incident_ids[i]}".strip(' -'),
                            status='Closed',
                            priority='Medium',  # Default priority for closed incidents
                            description=resolutions[i] if i < len(resolutions) else '',
                            shift_id=shift_id_to_use,
                            type='Closed',
                            account_id=account_id,
                            team_id=team_id
                        )
                        db.session.add(incident)
                        print(f"Added closed incident to session: {incident}")
                        
            elif inc_type == 'Priority':
                levels = request.form.getlist(f'{field_prefix}_level[]')
                escalated_to = request.form.getlist(f'{field_prefix}_escalated[]')
                impacts = request.form.getlist(f'{field_prefix}_impact[]')
                
                print(f"Priority incident fields - levels: {levels}, escalated: {escalated_to}, impacts: {impacts}")
                
                for i in range(len(app_names)):
                    if i < len(incident_ids) and (app_names[i].strip() or incident_ids[i].strip()):
                        print(f"Creating priority incident {i+1}: {app_names[i]} - {incident_ids[i]}")
                        incident = Incident(
                            title=f"{app_names[i]} - {incident_ids[i]}".strip(' -'),
                            status='Active',
                            priority=levels[i] if i < len(levels) else 'High',
                            escalated_to=escalated_to[i] if i < len(escalated_to) else '',
                            description=impacts[i] if i < len(impacts) else '',
                            shift_id=shift_id_to_use,
                            type='Priority',
                            account_id=account_id,
                            team_id=team_id
                        )
                        db.session.add(incident)
                        print(f"Added priority incident to session: {incident}")
                        
            elif inc_type == 'Handover':
                statuses = request.form.getlist(f'{field_prefix}_status[]')
                next_by = request.form.getlist(f'{field_prefix}_next_by[]')
                notes = request.form.getlist(f'{field_prefix}_notes[]')
                
                print(f"Handover incident fields - statuses: {statuses}, next_by: {next_by}, notes: {notes}")
                
                for i in range(len(app_names)):
                    if i < len(incident_ids) and (app_names[i].strip() or incident_ids[i].strip()):
                        print(f"Creating handover incident {i+1}: {app_names[i]} - {incident_ids[i]}")
                        full_title = f"{app_names[i]} - {incident_ids[i]}".strip(' -')
                        incident = Incident(
                            title=full_title,
                            status=statuses[i] if i < len(statuses) else 'Active',
                            priority='Medium',  # Default priority for handover incidents
                            assigned_to=next_by[i] if i < len(next_by) else '',
                            description=notes[i] if i < len(notes) else '',
                            handover=notes[i] if i < len(notes) else '',
                            shift_id=shift_id_to_use,
                            type='Handover',
                            account_id=account_id,
                            team_id=team_id
                        )
                        db.session.add(incident)
                        print(f"Added handover incident to session: {incident}")
                        
                        # Create incident assignment if next action engineer is assigned
                        next_action_by = next_by[i] if i < len(next_by) and next_by[i].strip() else None
                        if next_action_by:
                            try:
                                print(f"[DEBUG] Creating enhanced assignment for handover: {full_title} → {next_action_by}")
                                success = create_enhanced_incident_assignment(
                                    incident_title=full_title,
                                    incident_description=notes[i] if i < len(notes) else '',
                                    incident_priority='Medium',
                                    assigned_to_name=next_action_by,
                                    account_id=account_id,
                                    team_id=team_id,
                                    handover_context=f"Handover incident from {current_shift_type} to {next_shift_type} shift on {date}",
                                    handover_request_id=shift_id_to_use  # Link to the handover_request we created
                                )
                                if success:
                                    print(f"[DEBUG] ✅ Successfully created handover assignment: {full_title} → {next_action_by}")
                                else:
                                    print(f"[DEBUG] ❌ Failed to create handover assignment: {full_title} → {next_action_by}")
                            except Exception as e:
                                print(f"[DEBUG] ❌ Error creating handover assignment: {str(e)}")
                        
            elif inc_type == 'Escalated':
                escalated_to = request.form.getlist(f'{field_prefix}_to[]')
                
                print(f"Escalated incident fields - escalated_to: {escalated_to}")
                
                for i in range(len(app_names)):
                    if i < len(incident_ids) and (app_names[i].strip() or incident_ids[i].strip()):
                        print(f"Creating escalated incident {i+1}: {app_names[i]} - {incident_ids[i]}")
                        incident = Incident(
                            title=f"{app_names[i]} - {incident_ids[i]}".strip(' -'),
                            status='Escalated',
                            priority='High',  # Default priority for escalated incidents
                            escalated_to=escalated_to[i] if i < len(escalated_to) else '',
                            shift_id=shift_id_to_use,
                            type='Escalated',
                            account_id=account_id,
                            team_id=team_id
                        )
                        db.session.add(incident)
                        print(f"Added escalated incident to session: {incident}")
            
            print(f"=== Finished processing {field_prefix} ({inc_type}) ===")
        
        # Process all incident types
        import time
        incidents_start_time = time.time()
        print("=== PROCESSING INCIDENTS ===")
        add_detailed_incident('open_incident', 'Open')
        add_detailed_incident('closed_incident', 'Closed') 
        add_detailed_incident('priority_incident', 'Priority')
        add_detailed_incident('handover_incident', 'Handover')
        add_detailed_incident('escalated_incident', 'Escalated')
        incidents_time = time.time() - incidents_start_time
        print(f"[DEBUG] Incident processing took {incidents_time:.2f} seconds")
        
        # Check what's in the session before committing
        print("=== DB SESSION BEFORE COMMIT ===")
        print(f"New objects in session: {len(db.session.new)}")
        for obj in db.session.new:
            if hasattr(obj, '__tablename__'):
                print(f"  - {obj.__tablename__}: {obj}")
        print("=== END DB SESSION ===")
        
        # 🔧 CRITICAL FIX: Use no_autoflush to prevent foreign key constraint issues
        # This prevents SQLAlchemy from auto-flushing before the shift is committed
        with db.session.no_autoflush:
            # Add key points
            keypoints_start_time = time.time()
            print("=== PROCESSING KEY POINTS ===")
            key_point_descriptions = request.form.getlist('keypoint_description[]')
            keypoint_assigned_to = request.form.getlist('keypoint_assigned_to[]')
            keypoint_statuses = request.form.getlist('keypoint_status[]')
            keypoint_jira_ids = request.form.getlist('keypoint_jira_id[]')
        
        print(f"Key point form data:")
        print(f"  Descriptions: {key_point_descriptions}")
        print(f"  Assigned to: {keypoint_assigned_to}")
        print(f"  Statuses: {keypoint_statuses}")
        print(f"  JIRA IDs: {keypoint_jira_ids}")
        
        for i in range(len(key_point_descriptions)):
            description = key_point_descriptions[i].strip() if i < len(key_point_descriptions) else ''
            jira_id = keypoint_jira_ids[i].strip() if i < len(keypoint_jira_ids) else ''
            responsible_id = keypoint_assigned_to[i] if i < len(keypoint_assigned_to) else ''
            status = keypoint_statuses[i] if i < len(keypoint_statuses) else 'Open'
            
            print(f"Processing key point {i+1}: desc='{description}', jira='{jira_id}', responsible='{responsible_id}', status='{status}'")
            
            if description:
                # If status is being set to Closed, close the most recent open/in-progress key point with same description and jira_id
                if status == 'Closed':
                    print(f"🔒 CLOSING KEY POINT: Looking for open/in-progress key point with description='{description}', jira_id='{jira_id}'")
                    
                    # 🔧 ENHANCED CLOSURE LOGIC: Handle different JIRA ID formats
                    # Normalize jira_id - treat 'None', '', and actual None the same
                    normalized_jira_id = None if (not jira_id or jira_id == 'None' or jira_id == '') else jira_id
                    
                    # Find the most recent open/in-progress key point to close
                    query = ShiftKeyPoint.query.filter(
                        ShiftKeyPoint.description == description,
                        ShiftKeyPoint.status.in_(['Open', 'In Progress'])
                    )
                    
                    # Handle JIRA ID matching with multiple possible null representations
                    if normalized_jira_id is None:
                        # Look for key points with null, empty, or 'None' jira_id
                        query = query.filter(
                            or_(
                                ShiftKeyPoint.jira_id.is_(None),
                                ShiftKeyPoint.jira_id == '',
                                ShiftKeyPoint.jira_id == 'None'
                            )
                        )
                    else:
                        # Exact JIRA ID match
                        query = query.filter(ShiftKeyPoint.jira_id == normalized_jira_id)
                    
                    most_recent_kp = query.order_by(ShiftKeyPoint.id.desc()).first()
                    
                    if most_recent_kp:
                        print(f"🔒 FOUND KEY POINT TO CLOSE: ID={most_recent_kp.id}, current_status='{most_recent_kp.status}', description='{most_recent_kp.description[:50]}'")
                        most_recent_kp.status = 'Closed'
                        db.session.add(most_recent_kp)
                        print(f"🔒 SUCCESSFULLY CLOSED KEY POINT: {most_recent_kp.id} - Status changed to 'Closed'")
                        log_action('Close KeyPoint', f'ID: {most_recent_kp.id}, Description: {description}, Shift: {shift.id}')
                    else:
                        print(f"🔒 NO OPEN KEY POINT FOUND to close with description='{description}', jira_id='{jira_id}'")
                        
                        # 🔧 FALLBACK: Try broader matching if exact match fails
                        print(f"🔒 FALLBACK: Searching for key points with similar description...")
                        fallback_kps = ShiftKeyPoint.query.filter(
                            ShiftKeyPoint.description.like(f'%{description[:20]}%'),
                            ShiftKeyPoint.status.in_(['Open', 'In Progress'])
                        ).all()
                        
                        if fallback_kps:
                            print(f"🔒 FALLBACK: Found {len(fallback_kps)} potential matches:")
                            for fallback_kp in fallback_kps:
                                print(f"      - ID {fallback_kp.id}: '{fallback_kp.description[:50]}...' (JIRA: {fallback_kp.jira_id})")
                            
                            # Close the most recent one
                            latest_fallback = max(fallback_kps, key=lambda x: x.id)
                            latest_fallback.status = 'Closed'
                            db.session.add(latest_fallback)
                            print(f"🔒 FALLBACK: Closed key point ID {latest_fallback.id} as best match")
                            log_action('Close KeyPoint (Fallback)', f'ID: {latest_fallback.id}, Description: {description}, Shift: {shift.id}')
                        else:
                            print(f"🔒 FALLBACK: No similar key points found either")
                    
                    # 🔧 CRITICAL FIX: Always create new key points regardless of status
                    # The 'Closed' status indicates the task is completed, but we still need to record it
                    # The old logic incorrectly skipped creating new 'Closed' key points
                    print(f"🔒 PROCEEDING TO CREATE NEW 'Closed' KEY POINT: '{description}'")
                    # Continue to the creation logic below instead of skipping
                
                # 🚨 FIXED: Each handover should have its own key points
                # Only reference existing key points for the SAME handover (editing scenario)
                # or when explicitly carrying forward from previous shift
                
                # 🔧 NORMALIZE JIRA ID for consistent checking
                normalized_jira_id = None if (not jira_id or jira_id == 'None' or jira_id == '') else jira_id
                
                existing_kp = ShiftKeyPoint.query.filter(
                    ShiftKeyPoint.description == description,
                    ShiftKeyPoint.jira_id == normalized_jira_id,
                    ShiftKeyPoint.shift_id == shift.id  # 🔧 FIXED: Only look within the same handover
                ).first()
                
                if existing_kp:
                    # This is an edit of an existing key point in the same handover
                    if existing_kp.status != status:
                        existing_kp.status = status
                        db.session.add(existing_kp)
                        print(f"Updated existing key point {existing_kp.id} status from {existing_kp.status} to {status}")
                    else:
                        print(f"No changes for key point: '{description}', keeping existing ID {existing_kp.id}")
                        
                else:
                    # This is a completely new key point for this handover
                    responsible_engineer_id = None
                    if responsible_id:
                        if responsible_id.isdigit():
                            responsible_engineer_id = int(responsible_id)
                        else:
                            # Try to find user by name
                            user = TeamMember.query.filter_by(name=responsible_id).first()
                            if user:
                                responsible_engineer_id = user.id
                    
                    # 🔧 NORMALIZE JIRA ID for consistent storage
                    normalized_jira_id = None if (not jira_id or jira_id == 'None' or jira_id == '') else jira_id
                    
                    # 🔧 AUTOFLUSH FIX: Use no_autoflush context to prevent premature session flush
                    # 🛡️ BULLETPROOF SAFETY: Use the shift object that was already created by main function
                    try:
                        shift_id_to_use = shift.id
                        print(f"[SAFETY] Using main function's shift ID {shift_id_to_use} for key point")
                        
                        # Create key point with guaranteed existing shift ID
                        new_kp = ShiftKeyPoint(
                            description=description,
                            status=status,
                            responsible_engineer_id=responsible_engineer_id,
                            shift_id=shift_id_to_use,
                            jira_id=normalized_jira_id,
                            account_id=account_id,
                            team_id=team_id
                        )
                        db.session.add(new_kp)
                        print(f"Created new key point with shift ID {shift_id_to_use}: {new_kp}")
                        # Defer audit logging until after commit to avoid autoflush issues
                    
                    except Exception as shift_error:
                        print(f"[EMERGENCY] Error creating key point, attempting recovery: {shift_error}")
                        # If all else fails, use the latest available shift
                        latest_shift = Shift.query.order_by(Shift.id.desc()).first()
                        if latest_shift:
                            print(f"[EMERGENCY] Using latest available shift {latest_shift.id}")
                            with db.session.no_autoflush:
                                new_kp = ShiftKeyPoint(
                                    description=description,
                                    status=status,
                                    responsible_engineer_id=responsible_engineer_id,
                                    shift_id=latest_shift.id,
                                    jira_id=normalized_jira_id,
                                    account_id=account_id,
                                    team_id=team_id
                                )
                                db.session.add(new_kp)
                                print(f"[EMERGENCY] Created key point with fallback shift {latest_shift.id}")
                        else:
                            print(f"[EMERGENCY] No shifts available at all! Skipping key point creation.")
                            continue
                    
                    # Log action outside of no_autoflush context, and only after session is stable
                    try:
                        log_action('Add KeyPoint', f'Description: {description}, Status: {status}, Shift: {shift.id}')
                    except Exception as audit_error:
                        print(f"[WARNING] Audit logging failed but continuing: {audit_error}")
                        # Don't let audit failures break the handover process
        
            keypoints_time = time.time() - keypoints_start_time
            print(f"[DEBUG] Key points processing took {keypoints_time:.2f} seconds")
            print("=== FINISHED PROCESSING KEY POINTS ===")
            # End of no_autoflush context - now we can commit everything safely
        
        # Add timing debug
        import time
        start_commit_time = time.time()
        print(f"[DEBUG] Starting database commit at {start_commit_time}")
        
        db.session.commit()
        
        # Verify the handover was saved correctly
        print(f"[DEBUG] After commit - verifying shift creation:")
        saved_shift = Shift.query.get(shift.id)
        if saved_shift:
            print(f"✅ Shift {saved_shift.id} successfully saved to database")
            print(f"   Date: {saved_shift.date}")
            print(f"   Type: {saved_shift.current_shift_type} → {saved_shift.next_shift_type}")
            print(f"   Status: {saved_shift.status}")
            print(f"   Account ID: {saved_shift.account_id}")
            print(f"   Team ID: {saved_shift.team_id}")
            
            # Check if it would be visible in reports
            all_shifts_count = Shift.query.count()
            filtered_shifts_count = Shift.query.filter_by(account_id=saved_shift.account_id, team_id=saved_shift.team_id).count()
            print(f"   Total shifts in DB: {all_shifts_count}")
            print(f"   Shifts with same account/team: {filtered_shifts_count}")
        else:
            print(f"❌ ERROR: Shift {shift.id} not found after commit!")
        
        # Create audit log entry for handover creation/submission
        audit_action = 'Create Handover' if action == 'submit' else 'Save Handover Draft'
        audit_details = f'Shift: {current_shift_type}, Date: {date}, Status: {shift.status}, Team: {team_id}, Account: {account_id}'
        
        # Add audit log entry with proper user information
        db.session.add(AuditLog(
            user_id=current_user.id,
            username=current_user.username,
            action=audit_action,
            details=audit_details
        ))
        db.session.commit()
        
        # 🔍 VERIFY KEY POINT CLOSURES AFTER COMMIT
        print("🔍 VERIFYING KEY POINT STATUSES AFTER COMMIT:")
        all_kps = ShiftKeyPoint.query.all()
        closed_kps = [kp for kp in all_kps if kp.status == 'Closed']
        open_kps = [kp for kp in all_kps if kp.status in ['Open', 'In Progress']]
        print(f"🔍 Total key points: {len(all_kps)}")
        print(f"🔍 Closed key points: {len(closed_kps)}")
        print(f"🔍 Open/In Progress key points: {len(open_kps)}")
        for kp in open_kps[-3:]:  # Show last 3 open key points
            print(f"🔍   OPEN KP {kp.id}: '{kp.description[:50]}...' status={kp.status}")
        
        commit_time = time.time() - start_commit_time
        print(f"[DEBUG] Database commit took {commit_time:.2f} seconds")
        
        if action == 'submit':
            import logging
            email_start_time = time.time()
            logging.basicConfig(level=logging.DEBUG)
            logging.debug(f"[EMAIL] Attempting to send handover email for shift_id={shift.id}, date={shift.date}, current_shift_type={shift.current_shift_type}, next_shift_type={shift.next_shift_type}")
            
            # 🔧 Process incident assignment notifications (after commit, isolated from main transaction)
            try:
                from services.notification_service_fix import notification_fix
                from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
                print(f"[NOTIFICATION] Starting notification processing for shift {shift.id}")
                
                # Capture the Flask app context and request data for use in threads
                app_context = current_app._get_current_object()
                form_data = dict(request.form)  # Capture form data outside thread
                
                def process_notifications_with_timeout():
                    """Process notifications in a separate thread with Flask app context"""
                    try:
                        with app_context.app_context():
                            # Create a mock request-like object for the notification service
                            return notification_fix.process_handover_with_notifications(shift, form_data)
                    except Exception as e:
                        print(f"[NOTIFICATION] Thread error: {e}")
                        return {'notifications_sent': 0, 'logs_created': 0, 'errors': [str(e)]}
                
                # Use thread pool with timeout for notification processing
                try:
                    with ThreadPoolExecutor(max_workers=1) as executor:
                        future = executor.submit(process_notifications_with_timeout)
                        notification_result = future.result(timeout=30)  # 30 second timeout
                        
                    print(f"[NOTIFICATION] Processed notifications: {notification_result['notifications_sent']} sent, {notification_result['logs_created']} logs created")
                    if notification_result['errors']:
                        print(f"[NOTIFICATION] Errors: {notification_result['errors']}")
                    else:
                        print(f"[NOTIFICATION] All notifications processed successfully")
                        
                except (FutureTimeoutError, Exception) as timeout_error:
                    print(f"[NOTIFICATION] Timeout/error processing notifications: {str(timeout_error)}")
                    logging.error(f"[NOTIFICATION] Failed to process notifications for shift_id={shift.id}: {timeout_error}")
                    # Continue with email processing even if notifications fail
                    print(f"[NOTIFICATION] Continuing with email processing despite notification error")
                    
            except Exception as notify_error:
                print(f"[NOTIFICATION] Error processing notifications: {str(notify_error)}")
                logging.error(f"[NOTIFICATION] Failed to process notifications for shift_id={shift.id}: {notify_error}")
                # Continue with email processing even if notifications fail
                print(f"[NOTIFICATION] Continuing with email processing despite notification error")
            
            try:
                # Check if session is in a valid state before sending email
                if db.session.is_active:
                    try:
                        # Test session with a simple query
                        db.session.execute(db.text("SELECT 1"))
                    except Exception as session_error:
                        print(f"[DEBUG] Session error detected, rolling back: {session_error}")
                        db.session.rollback()
                
                # Send handover email with timeout protection
                from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
                
                # Capture the Flask app context for use in threads
                app_context = current_app._get_current_object()
                
                def send_email_with_timeout():
                    """Send email in a separate thread with Flask app context"""
                    try:
                        with app_context.app_context():
                            send_handover_email(shift)
                        return True
                    except Exception as e:
                        print(f"[EMAIL] Error sending email: {e}")
                        return False
                
                # Use thread pool with timeout for email sending
                try:
                    with ThreadPoolExecutor(max_workers=1) as executor:
                        future = executor.submit(send_email_with_timeout)
                        email_success = future.result(timeout=45)  # 45 second timeout
                        
                    email_time = time.time() - email_start_time
                    print(f"[DEBUG] Email process took {email_time:.2f} seconds")
                    logging.debug(f"[EMAIL] Email process completed for shift_id={shift.id}")
                    flash('Shift handover submitted successfully!', 'success')
                except (FutureTimeoutError, Exception) as timeout_error:
                    email_time = time.time() - email_start_time
                    print(f"[DEBUG] Email timeout/error after {email_time:.2f} seconds: {timeout_error}")
                    flash('Shift handover submitted successfully! (Email may be delayed)', 'success')
            except Exception as e:
                email_time = time.time() - email_start_time
                print(f"[DEBUG] Email error after {email_time:.2f} seconds: {e}")
                logging.error(f"[EMAIL] Failed to send email for shift_id={shift.id}: {e}")
                
                # DO NOT ROLLBACK AFTER COMMIT - this was causing the silent failure
                # The handover data has already been committed successfully
                print(f"[DEBUG] Email/notification failed but handover data was saved successfully")
                
                # Check if it's a network/timeout issue (common in local development)
                error_str = str(e).lower()
                if any(keyword in error_str for keyword in ['timed out', 'connection', 'network', 'getaddrinfo', 'smtp']):
                    flash('✅ Handover submitted successfully! (Email notification temporarily unavailable - this is normal in local development)', 'success')
                else:
                    flash(f'✅ Handover submitted successfully! Note: Email notification failed - {e}', 'warning')
        else:
            flash('Draft saved.', 'success')
            
        total_time = time.time() - start_commit_time
        print(f"[DEBUG] Total processing time after database commit: {total_time:.2f} seconds")
        print(f"[REDIRECT] About to redirect to handover reports...")
        return redirect(url_for('reports.handover_reports'))
    
    # GET: render form with defaults
    # Determine current and next shift based on time (consistent with dashboard)
    hour = ist_now.hour
    minute = ist_now.minute
    if dt_time(6,30) <= ist_now.time() < dt_time(15,30):
        current_shift_type = 'Morning'
        next_shift_type = 'Evening'
    elif dt_time(14,45) <= ist_now.time() < dt_time(23,45):
        current_shift_type = 'Evening'
        next_shift_type = 'Night'
    else:
        current_shift_type = 'Night'
        next_shift_type = 'Morning'
    
    # 🔧 FIX: Adjust handover date for Night → Morning transition
    # When Night shift hands over to Morning shift, the handover date should be 
    # the previous day (when the night shift started), not the current date
    handover_date = default_date
    if current_shift_type == 'Night' and next_shift_type == 'Morning':
        handover_date = default_date - timedelta(days=1)
        print(f"[DEBUG] Night→Morning handover: Adjusted date from {default_date} to {handover_date}")
    
    def get_engineers_for_shift(date, shift_code):
        entries = ShiftRoster.query.filter_by(date=date, shift_code=shift_code).all()
        member_ids = [e.team_member_id for e in entries]
        return TeamMember.query.filter(TeamMember.id.in_(member_ids)).all() if member_ids else []
    if current_shift_type == 'Night' and ist_now.time() < dt_time(6,45):
        night_date = default_date - timedelta(days=1)
        current_engineers_objs = get_engineers_for_shift(night_date, shift_map[current_shift_type])
    else:
        current_engineers_objs = get_engineers_for_shift(default_date, shift_map[current_shift_type])
    if next_shift_type == 'Night' and ist_now.time() >= dt_time(21,45):
        next_date = default_date + timedelta(days=1)
        next_engineers_objs = get_engineers_for_shift(next_date, shift_map[next_shift_type])
    else:
        next_engineers_objs = get_engineers_for_shift(default_date, shift_map[next_shift_type])
    current_engineers = [m.name for m in current_engineers_objs]
    next_engineers = [m.name for m in next_engineers_objs]
    # 🔧 FIX: Load ALL open key points globally for pre-population (like dashboard)
    # Don't filter by specific shifts - key points should persist until closed
    print(f"[DEBUG] Loading all open key points globally for account {current_user.account_id}, team {current_user.team_id}")
    
    all_prev_kps = ShiftKeyPoint.query.filter(
        ShiftKeyPoint.account_id == current_user.account_id,
        ShiftKeyPoint.team_id == current_user.team_id,
        ShiftKeyPoint.status.in_(['Open', 'In Progress'])
    ).all()
    
    print(f"[DEBUG] Found {len(all_prev_kps)} total open/in-progress key points globally")
    
    # Deduplicate: keep only the latest (by id) for each (description, jira_id) pair
    kp_map = {}
    for kp in all_prev_kps:
        if kp.status == 'Closed':
            continue
        key = (kp.description, kp.jira_id)
        if key not in kp_map or kp.id > kp_map[key].id:
            kp_map[key] = kp
    open_key_points = list(kp_map.values())
    
    # Enhance key points with assigned engineer names for template display
    for kp in open_key_points:
        kp.assigned_to = None  # Default to None
        if kp.responsible_engineer_id:
            # Find the team member by ID
            engineer = TeamMember.query.get(kp.responsible_engineer_id)
            if engineer:
                kp.assigned_to = engineer.name
                print(f"[DEBUG] Key point '{kp.description[:30]}...' assigned to: {engineer.name}")
            else:
                print(f"[DEBUG] Key point '{kp.description[:30]}...' has invalid engineer ID: {kp.responsible_engineer_id}")
        else:
            print(f"[DEBUG] Key point '{kp.description[:30]}...' has no assigned engineer")
    
    # Initialize ServiceNow service to get assignment group configuration for template
    # QUICK FIX: Skip ServiceNow initialization for local development to avoid delays
    try:
        servicenow = ServiceNowService()
        servicenow.initialize(current_app)
        assignment_groups_filter = servicenow.get_configured_assignment_groups()
        assignment_groups_filtered = servicenow.is_assignment_group_filtered()
    except Exception as e:
        current_app.logger.info(f"[LOCAL_DEV] Skipping ServiceNow initialization: {e}")
        assignment_groups_filter = []
        assignment_groups_filtered = False
    
    # Always show at least one blank row for new key point entry in the form
    return render_template('handover_form.html',
        team_members=team_members,
        teams=teams,
        default_team_id=default_team_id,
        current_engineers=current_engineers,
        next_engineers=next_engineers,
        current_shift_type=current_shift_type,
        next_shift_type=next_shift_type,
        open_key_points=open_key_points,
        current_time=datetime.now(),
        shift=None,
        open_incidents=[],
        closed_incidents=[],
        priority_incidents=[],
        handover_incidents=[],
        today=handover_date.strftime('%Y-%m-%d'),  # Use adjusted handover_date instead of default_date
        show_team_error=show_team_error,
        # ServiceNow configuration for template
        assignment_groups_filter=assignment_groups_filter,
        assignment_groups_filtered=assignment_groups_filtered
    )

