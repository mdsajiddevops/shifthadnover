
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from flask import session
from models.models import TeamMember, Shift, Incident, ShiftKeyPoint, ShiftRoster, ShiftChangeInfo, ShiftKBUpdate, db
from sqlalchemy import or_
from models.handover_enhanced import HandoverRequest
from models.audit_log import AuditLog
from services.audit_service import log_action
from services.email_service import send_handover_email, send_incident_assignment_notification
from services.servicenow_service import ServiceNowService
from services.team_access_service import TeamAccessService
from datetime import datetime, timedelta, time as dt_time
from sqlalchemy import or_, and_
import pytz

handover_bp = Blueprint('handover', __name__)

def create_new_shift(date, current_shift_type, next_shift_type, account_id, team_id, action, additional_notes=None):
    """
    Creates a new shift record for each handover submission.
    This prevents overriding existing shifts and maintains proper data integrity.
    """
    print(f"[NEW_SHIFT] Creating new shift: {date} {current_shift_type}→{next_shift_type} (action: '{action}')")
    print(f"[NEW_SHIFT] Action type: {type(action)}, Will set status to: {'draft' if action == 'draft' else 'sent'}")
    
    # Always create a new shift for each handover submission
    new_shift = Shift(
        date=date,
        current_shift_type=current_shift_type,
        next_shift_type=next_shift_type,
        status='draft' if action == 'draft' else 'sent',
        submitted_at=datetime.now() if action == 'submit' else None,
        account_id=account_id,
        team_id=team_id,
        created_at=datetime.now(),
        additional_notes=additional_notes
    )
    
    db.session.add(new_shift)
    
    # Commit immediately to get the ID and ensure it exists
    try:
        db.session.commit()
        print(f"[NEW_SHIFT] ✅ Created new shift ID: {new_shift.id} with status: {new_shift.status}")
    except Exception as commit_error:
        print(f"[NEW_SHIFT] ❌ Failed to commit new shift: {commit_error}")
        db.session.rollback()
        raise commit_error
    
    return new_shift

def create_enhanced_incident_assignment(incident_title, incident_description, incident_priority, 
                                      assigned_to_name, account_id, team_id, handover_context="", handover_request_id=None):
    """Create an enhanced incident assignment in the database"""
    
    try:
        print(f"[DEBUG] create_enhanced_incident_assignment called for: {incident_title} → {assigned_to_name}")
        from models.handover_enhanced import IncidentAssignment
        from models.models import User  # Move User import to top to fix scope issue
        
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
                        # Use flush instead of commit to avoid losing pending incidents
                        db.session.flush()
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
        
        # DON'T COMMIT HERE - let the main handover creation handle the final commit
        # This was causing session corruption and losing pending incidents
        db.session.flush()  # Just flush to get IDs
        
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
    current_shift_type = request.args.get('current_shift_type')  # New parameter
    is_next_shift = request.args.get('is_next_shift', 'false').lower() == 'true'  # New parameter
    
    if not date_str or not shift_type:
        return jsonify({'error': 'Missing date or shift_type'}), 400
    try:
        handover_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except Exception:
        return jsonify({'error': 'Invalid date format'}), 400
    
    shift_map = {'Morning': 'D', 'Evening': 'E', 'Night': 'N', 'OnShore': 'OS', 'OffShore': 'OF'}
    shift_code = shift_map.get(shift_type)
    if not shift_code:
        return jsonify({'error': 'Invalid shift_type'}), 400
    
    # Calculate the correct date for engineer lookup based on shift transition logic
    lookup_date = handover_date
    
    # If this is the next shift and we're transitioning from Night to Morning,
    # Morning engineers should be from the next day
    if is_next_shift and current_shift_type == 'Night' and shift_type == 'Morning':
        lookup_date = handover_date + timedelta(days=1)
        print(f"[SHIFT FIX] Night->Morning transition: Looking up Morning engineers for {lookup_date} instead of {handover_date}")
    
    # Use the calculated lookup_date for roster query
    date = lookup_date
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
    print(f"🔧 API_TEAM_MEMBERS: User role: {current_user.role}")
    print(f"🔧 API_TEAM_MEMBERS: User account: {current_user.account_id}")
    print(f"🔧 API_TEAM_MEMBERS: User team: {current_user.team_id}")
    
    # Use same team member filtering logic as team details route
    tm_query = TeamMember.query
    
    if current_user.role == 'super_admin':
        # Super admin can see all or use session-selected account/team
        account_id = request.args.get('account_id') or session.get('selected_account_id')
        team_id = request.args.get('team_id') or session.get('selected_team_id')
        print(f"🔧 API_TEAM_MEMBERS: Super admin - account_id: {account_id}, team_id: {team_id}")
        if account_id:
            tm_query = tm_query.filter_by(account_id=account_id)
        if team_id:
            tm_query = tm_query.filter_by(team_id=team_id)
    elif current_user.role == 'account_admin':
        # Account admin can only see their account
        account_id = current_user.account_id
        team_id = request.args.get('team_id') or session.get('selected_team_id')
        print(f"🔧 API_TEAM_MEMBERS: Account admin - account_id: {account_id}, team_id: {team_id}")
        tm_query = tm_query.filter_by(account_id=account_id)
        if team_id:
            tm_query = tm_query.filter_by(team_id=team_id)
    else:
        # Team admin/user can only see their team
        account_id = current_user.account_id
        team_id = current_user.team_id
        print(f"🔧 API_TEAM_MEMBERS: Team user - account_id: {account_id}, team_id: {team_id}")
        tm_query = tm_query.filter_by(account_id=account_id, team_id=team_id)
    
    # Get all team members (remove status filter since TeamMember model doesn't have status field)
    team_members = tm_query.all()
    print(f"🔧 API_TEAM_MEMBERS: Found {len(team_members)} team members")
    for i, member in enumerate(team_members[:5]):  # Show first 5
        print(f"🔧 API_TEAM_MEMBERS:   Member {i+1}: {member.name} (ID: {member.id}, Team: {member.team_id})")
    
    response_data = {'team_members': [{'name': member.name, 'id': member.id} for member in team_members]}
    print(f"🔧 API_TEAM_MEMBERS: Returning {len(response_data['team_members'])} team members")
    return jsonify(response_data)

@handover_bp.route('/api/debug_team_members')
@login_required  
def debug_team_members():
    """Debug endpoint to check team members data"""
    try:
        # Direct query without filtering
        all_members = TeamMember.query.all()
        print(f"🔍 DEBUG: Total team members in database: {len(all_members)}")
        
        # User's team members
        user_members = TeamMember.query.filter_by(account_id=current_user.account_id, team_id=current_user.team_id).all()
        print(f"🔍 DEBUG: User's team members: {len(user_members)}")
        
        return jsonify({
            'total_members': len(all_members), 
            'user_members': len(user_members),
            'user_role': current_user.role,
            'user_account': current_user.account_id,
            'user_team': current_user.team_id,
            'sample_members': [{'name': m.name, 'id': m.id, 'team_id': m.team_id} for m in all_members[:5]]
        })
    except Exception as e:
        print(f"🔍 DEBUG: Error: {e}")
        return jsonify({'error': str(e)})

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
    
    # Permission check: super_admin can edit any handover, others need account/team access
    # Special case: Team-based access for draft handovers
    if shift.status == 'draft':
        # For drafts, allow same team members to collaborate
        if current_user.role == 'super_admin':
            pass  # Super admin can edit any draft
        elif shift.account_id != current_user.account_id:
            flash('You do not have permission to edit this handover form.')
            return redirect(url_for('dashboard.dashboard'))
        elif not current_user.is_member_of_team(shift.team_id, account_id=current_user.account_id):
            flash('You do not have permission to edit this handover form.')
            return redirect(url_for('dashboard.dashboard'))
        # If we reach here, user is in same account and same team - allow editing
    elif current_user.role != 'super_admin':
        # Check account access
        if shift.account_id != current_user.account_id:
            flash('You do not have permission to edit this handover form.')
            return redirect(url_for('dashboard.dashboard'))
        
        # Check team access - user must belong to the handover's team
        if not current_user.is_member_of_team(shift.team_id, account_id=current_user.account_id):
            flash('You do not have permission to edit this handover form.')
            return redirect(url_for('dashboard.dashboard'))
    # 🔧 CRITICAL FIX: For edit mode, include team members from the handover's team
    print(f"🔧 EDIT_HANDOVER: User role: {current_user.role}")
    print(f"🔧 EDIT_HANDOVER: User account: {current_user.account_id}")
    print(f"🔧 EDIT_HANDOVER: Handover team: {shift.team_id}")
    print(f"🔧 EDIT_HANDOVER: Handover account: {shift.account_id}")
    
    tm_query = TeamMember.query
    if current_user.role not in ['super_admin', 'admin']:
        # Use TeamAccessService for proper team filtering
        user_team_ids = TeamAccessService.get_user_team_ids()
        print(f"🔧 EDIT_HANDOVER: User team IDs: {user_team_ids}")
        
        # CRITICAL FIX: Always include the handover's team for edit mode
        if shift.team_id not in user_team_ids:
            user_team_ids.append(shift.team_id)
            print(f"🔧 EDIT_HANDOVER: Added handover team {shift.team_id} to accessible teams")
        
        if user_team_ids:
            account_id = TeamAccessService.get_effective_account_id()
            tm_query = tm_query.filter(
                TeamMember.account_id == account_id,
                TeamMember.team_id.in_(user_team_ids)
            )
        else:
            tm_query = tm_query.filter(False)  # No teams = no members
    team_members = tm_query.all()
    print(f"🔧 EDIT_HANDOVER: Found {len(team_members)} team members")
    for i, member in enumerate(team_members[:5]):  # Show first 5
        print(f"🔧 EDIT_HANDOVER:   Member {i+1}: {member.name} (ID: {member.id}, Team: {member.team_id})")
    
    # Get teams for the dropdown
    from models.models import Team
    if current_user.role == 'super_admin':
        teams = Team.query.filter_by(status='active').all()
    elif current_user.role == 'account_admin':
        teams = Team.query.filter_by(account_id=current_user.account_id, status='active').all()
    else:
        # Regular users: get all their teams for dropdown using TeamAccessService
        team_ids = TeamAccessService.get_user_team_ids()
        
        # Include the handover's team if not already in user teams
        if shift.team_id not in team_ids:
            team_ids.append(shift.team_id)
            
        account_id = TeamAccessService.get_effective_account_id()
        teams = Team.query.filter(
            Team.account_id == account_id,
            Team.id.in_(team_ids),
            Team.status == 'active'
        ).all() if team_ids else []
    
    # Set default team selection for edit mode - use the shift's team
    default_team_id = shift.team_id
    
    # Fetch incidents by type for prepopulation - FIXED: Return full incident objects for edit form
    def serialize_incident(incident):
        """Convert incident object to dictionary for template"""
        # Extract app name from title if it exists
        title = incident.title
        app_name = ""
        incident_id = ""
        
        # Handle format: [AppName] IncidentID
        if title.startswith('[') and ']' in title:
            end_bracket = title.index(']')
            app_name = title[1:end_bracket]
            incident_id = title[end_bracket+1:].strip()
        # Handle format: AppName - IncidentID or AppNameNumber - IncidentID
        elif ' - ' in title:
            parts = title.split(' - ', 1)
            app_name = parts[0].strip()
            incident_id = parts[1].strip()
        # Handle single title without separation
        else:
            app_name = ""
            incident_id = title
        
        # The assigned_to field might be stored as an ID or name, need to handle both
        assigned_to_value = getattr(incident, 'assigned_to', '')
        assigned_to_name = assigned_to_value
        
        # If assigned_to looks like an ID (numeric), convert to name
        if assigned_to_value and str(assigned_to_value).isdigit():
            try:
                # TeamMember is already imported at the top of the file
                engineer = TeamMember.query.get(int(assigned_to_value))
                if engineer:
                    assigned_to_name = engineer.name
                    print(f"🔧 SERIALIZE: Converted ID {assigned_to_value} to name '{assigned_to_name}'")
                else:
                    print(f"🔧 SERIALIZE: ID {assigned_to_value} not found, using as-is")
                    assigned_to_name = assigned_to_value
            except Exception as e:
                print(f"🔧 SERIALIZE: Error converting ID {assigned_to_value}: {e}")
                assigned_to_name = assigned_to_value
        
        # 🔧 DEBUG: Log assignment data during serialization
        if assigned_to_name:
            print(f"🔧 SERIALIZE: Incident '{incident.title}' final assignment: '{assigned_to_name}'") 
        else:
            print(f"🔧 SERIALIZE: Incident '{incident.title}' has NO assignment")
        
        # Create the incident dictionary with all available fields
        # 🔧 FIX: Check both handover and description fields for description content
        description_content = getattr(incident, 'handover', '') or getattr(incident, 'description', '')
        
        # 🔧 ENHANCED FIX: Handle all incident types with proper field mapping
        incident_status = getattr(incident, 'status', '')
        incident_type = getattr(incident, 'type', '')
        
        # Initialize default values
        resolution_content = ''
        impact_content = ''
        notes_content = ''
        escalated_to_content = ''
        next_action_by_content = ''
        
        if incident_type == 'Closed':
            # Closed incidents: resolution stored in handover field
            resolution_content = description_content
        elif incident_type == 'Priority':
            # Priority incidents: impact stored in handover field  
            impact_content = description_content
            # ✅ FIX: Map escalated_to field for Priority incidents
            escalated_to_content = getattr(incident, 'escalated_to', '') or ''
        elif incident_type == 'Handover':
            # Handover incidents: notes stored in handover field, next_action_by stored in assigned_to field
            notes_content = description_content
            # ✅ FIX: Get next_action_by from assigned_to field (this is where we store it)
            next_action_by_content = assigned_to_name  # assigned_to already contains the name
        elif incident_type == 'Escalated':
            # ✅ FIX: Map Escalated incident fields properly from database
            escalated_to_content = getattr(incident, 'escalated_to', '') or ''
            escalation_reason = getattr(incident, 'description', '') or ''  # Stored in description field
            current_status = getattr(incident, 'status', '') or ''  # Stored in status field
            
            # Use escalation_reason for notes if available
            if escalation_reason:
                notes_content = escalation_reason
        elif incident_type == 'Open':
            # Open incidents: description in handover field (already handled correctly)
            pass
        
        result = {
            'id': incident_id,
            'title': title,
            'app_name': app_name,
            'priority': getattr(incident, 'priority', 'Medium'),
            'description': description_content,  # Use handover field primarily, fallback to description
            'assigned_to': assigned_to_name,
            'status': incident_status,
            'resolution': resolution_content,  # For closed incidents
            'escalated_to': escalated_to_content,  # For escalated incidents
            'impact': impact_content,  # For priority incidents
            'next_action_by': next_action_by_content,  # For handover incidents
            'notes': notes_content  # For handover incidents
        }
        
        # ✅ FIX: Add additional fields for Escalated incidents
        if incident_type == 'Escalated':
            result['escalation_reason'] = getattr(incident, 'description', '') or ''  # Stored in description field
            result['current_status'] = getattr(incident, 'status', '') or ''  # Stored in status field
        
        # 🔧 DEBUG: Log each serialized incident
        print(f"[SERIALIZE_DEBUG] Incident {incident.id}: {result}")
        
        return result
    
    # Get full incident objects for each type - FIXED: Use correct type values from database
    open_incidents_raw = Incident.query.filter_by(shift_id=shift.id, type='Open').all()
    closed_incidents_raw = Incident.query.filter_by(shift_id=shift.id, type='Closed').all()
    priority_incidents_raw = Incident.query.filter_by(shift_id=shift.id, type='Priority').all()
    handover_incidents_raw = Incident.query.filter_by(shift_id=shift.id, type='Handover').all()
    escalated_incidents_raw = Incident.query.filter_by(shift_id=shift.id, type='Escalated').all()
    
    # Convert to dictionaries for the template
    open_incidents = [serialize_incident(i) for i in open_incidents_raw]
    closed_incidents = [serialize_incident(i) for i in closed_incidents_raw]
    priority_incidents = [serialize_incident(i) for i in priority_incidents_raw]
    handover_incidents = [serialize_incident(i) for i in handover_incidents_raw]
    escalated_incidents = [serialize_incident(i) for i in escalated_incidents_raw]

    if request.method == 'POST':
        # 🚨 IMMEDIATE DEBUG: Catch POST request entry
        print(f"\n🚨🚨🚨 EDIT HANDOVER POST REQUEST RECEIVED 🚨🚨🚨")
        print(f"   Shift ID: {shift_id}")
        print(f"   User: {current_user.username}")
        print(f"   Action: {request.form.get('action', 'UNKNOWN')}")
        print(f"   Form fields count: {len(request.form)}")
        print(f"   First 5 form keys: {list(request.form.keys())[:5]}")
        
        # Audit log: editing handover
        db.session.add(AuditLog(
            user_id=current_user.id,
            username=current_user.username,
            action='Edit Handover',
            details=f'Shift ID: {shift_id}, Action: {request.form.get("action", "send")}'
        ))
        
        # COMPREHENSIVE FORM SUBMISSION DEBUGGING - Log form data reception
        current_app.logger.info(f"=== EDIT HANDOVER FORM SUBMISSION DEBUG (Shift {shift_id}) ===")
        current_app.logger.info(f"User: {current_user.username}, Action: {request.form.get('action', 'send')}")
        
        # Log all form keys to verify data reception
        form_keys = list(request.form.keys())
        current_app.logger.info(f"Total form fields received: {len(form_keys)}")
        current_app.logger.info(f"All form keys: {form_keys}")
        
        # Specifically check key points data
        key_point_fields = [key for key in form_keys if key.startswith('key_point_')]
        current_app.logger.info(f"Key point fields received: {len(key_point_fields)}")
        current_app.logger.info(f"Key point field names: {key_point_fields}")
        
        # Log key points data structure
        for field in key_point_fields:
            value = request.form.get(field, '')
            current_app.logger.info(f"Form field '{field}': '{value}' (length: {len(str(value))})")
        
        # Check for array-like structures
        if any('[' in key for key in key_point_fields):
            current_app.logger.info("DETECTED: Array-style key point field names")
            # Group by array index
            array_indices = set()
            for field in key_point_fields:
                if '[' in field and ']' in field:
                    try:
                        index = field.split('[')[1].split(']')[0]
                        array_indices.add(index)
                    except:
                        pass
            current_app.logger.info(f"Key point array indices found: {sorted(array_indices)}")
            
            # Log each key point object
            for index in sorted(array_indices):
                current_app.logger.info(f"--- Key Point {index} ---")
                for field in key_point_fields:
                    if f'[{index}]' in field:
                        value = request.form.get(field, '')
                        current_app.logger.info(f"  {field}: '{value}'")
        
        current_app.logger.info("=== END FORM SUBMISSION DEBUG ===")
        
        shift.date = datetime.strptime(request.form['handover_date'], '%Y-%m-%d').date()
        shift.current_shift_type = request.form['current_shift_type']
        shift.next_shift_type = request.form['next_shift_type']
        shift.additional_notes = request.form.get('additional_notes', '')
        action = request.form.get('action', 'send')
        old_status = shift.status
        
        # 🔧 CRITICAL FIX: Prevent converting draft to submission if another submission already exists
        if action not in ['save', 'draft'] and old_status == 'draft':  # Converting draft to submission
            existing_submission = Shift.query.filter_by(
                date=shift.date,
                current_shift_type=shift.current_shift_type,
                next_shift_type=shift.next_shift_type,
                account_id=shift.account_id,
                team_id=shift.team_id,
                status='sent'
            ).filter(Shift.id != shift.id).first()  # Exclude current shift being edited
            
            if existing_submission:
                print(f"[EDIT_DUPLICATE_CHECK] Found existing submission: ID={existing_submission.id}")
                flash('❌ Cannot submit this draft! A handover for this shift has already been submitted. '
                      'Please check the Reports section to view the submitted handover.', 'error')
                return redirect(url_for('handover.edit_handover', shift_id=shift_id))
            else:
                print(f"[EDIT_DUPLICATE_CHECK] ✅ No existing submission found, can convert draft to submission")
        
        shift.status = 'draft' if action in ['save', 'draft'] else 'sent'
        
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
        # Get engineers for current shift (always use the shift date)
        current_engineers_objs = get_engineers_for_shift(shift.date, current_shift_code)
        print(f"[SHIFT EDIT FIX] Current shift ({shift.current_shift_type}) engineers from date: {shift.date}")
        
        # Get engineers for next shift
        # For Night->Morning transitions, Morning engineers should come from next day
        if shift.current_shift_type == 'Night' and shift.next_shift_type == 'Morning':
            next_date = shift.date + timedelta(days=1)
            next_engineers_objs = get_engineers_for_shift(next_date, next_shift_code)
            print(f"[SHIFT EDIT FIX] Night->Morning transition: Next shift ({shift.next_shift_type}) engineers from date: {next_date}")
        else:
            next_engineers_objs = get_engineers_for_shift(shift.date, next_shift_code)
            print(f"[SHIFT EDIT FIX] Regular transition: Next shift ({shift.next_shift_type}) engineers from date: {shift.date}")
        for member in current_engineers_objs:
            shift.current_engineers.append(member)
        for member in next_engineers_objs:
            shift.next_engineers.append(member)
        # 🔧 CRITICAL FIX: Only clear and rebuild data if no existing incidents
        # This prevents duplication in edit mode
        existing_incidents = Incident.query.filter_by(shift_id=shift.id).all()
        existing_keypoints = ShiftKeyPoint.query.filter_by(shift_id=shift.id).all()
        
        print(f"🔧 EDIT MODE: Found {len(existing_incidents)} existing incidents, {len(existing_keypoints)} existing key points")
        
        # 🔧 FIXED LOGIC: Only recreate if this is the FIRST edit (no existing data)
        # Or if explicitly requested to reset (add a flag later if needed)
        should_recreate = len(existing_incidents) == 0 and len(existing_keypoints) == 0
        
        if should_recreate:
            print(f"🔧 EDIT MODE: No existing data found - will create from form")
        else:
            print(f"🔧 EDIT MODE: Existing data found - will update shift properties only, not recreate incidents/keypoints")
            # Just update shift properties, don't recreate incidents/keypoints to prevent duplication
            # The incident/keypoint processing will be skipped below
        # Audit log: defer until final commit
        audit_log = AuditLog(
            user_id=current_user.id,
            username=current_user.username,
            action='Handover ' + ('Sent' if action == 'send' else 'Saved as Draft'),
            details=f'Shift ID: {shift_id}, Status: {shift.status}'
        )
        # Don't commit yet - this was causing session loss during incident processing
        
        def add_incident(field_prefix, inc_type):
            # Handle different incident types with their specific fields
            incident_ids = request.form.getlist(f'{field_prefix}_incident_id[]')
            
            print(f"\n🔧 PROCESSING {inc_type} INCIDENTS:")
            print(f"   Found {len(incident_ids)} incident IDs for type '{inc_type}'")
            print(f"   🔍 DEBUG: Raw incident_ids = {incident_ids}")
            print(f"   🔍 DEBUG: Field prefix = '{field_prefix}'")
            print(f"   🔍 DEBUG: All form fields with '{field_prefix}': {[k for k in request.form.keys() if field_prefix in k]}")
            
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
                    if inc_type == 'Open':  # Open incidents
                        priorities = request.form.getlist('open_incident_priority[]')
                        descriptions = request.form.getlist('open_incident_description[]')
                        assigned_tos = request.form.getlist('open_incident_assigned[]')
                        app_names = request.form.getlist('open_incident_app[]')
                        
                        print(f"   🔧 OPEN INCIDENT {i+1}: assigned_to form data = '{assigned_tos[i] if i < len(assigned_tos) else 'MISSING'}'")
                        
                        # Include application name in title
                        app_name = app_names[i] if i < len(app_names) and app_names[i].strip() else ''
                        full_title = f"[{app_name}] {incident_id}" if app_name else incident_id
                        incident_data['title'] = full_title
                        
                        # Send notification if engineer is assigned
                        assigned_engineer = assigned_tos[i] if i < len(assigned_tos) and assigned_tos[i].strip() else None
                        
                        incident_data.update({
                            'priority': priorities[i] if i < len(priorities) else 'Medium',
                            'status': 'Open',
                            'handover': descriptions[i] if i < len(descriptions) else '',
                            'assigned_to': assigned_engineer  # 🔧 FIX: Store assigned engineer name
                        })
                        if assigned_engineer:
                            try:
                                print(f"🔍 ASSIGNMENT DEBUG: About to create assignment for {assigned_engineer}")
                                print(f"🔍   Session state before assignment: {len(db.session.new)} new objects")
                                
                                # Create enhanced incident assignment
                                # Create or get HandoverRequest for edit mode
                                handover_request = HandoverRequest.query.filter_by(shift_id=shift.id).first()
                                if not handover_request:
                                    handover_request = HandoverRequest(
                                        shift_id=shift.id,
                                        account_id=shift.account_id,
                                        team_id=shift.team_id,
                                        created_at=datetime.now()
                                    )
                                    db.session.add(handover_request)
                                    print(f"🔍   Added HandoverRequest to session")
                                    db.session.flush()  # Get ID without full commit
                                    print(f"🔍   Session after handover request flush: {len(db.session.new)} new objects")
                                
                                # Don't let assignment errors affect the main incident creation
                                assignment_result = create_enhanced_incident_assignment(
                                    incident_title=full_title,
                                    incident_description=descriptions[i] if i < len(descriptions) else '',
                                    incident_priority=priorities[i] if i < len(priorities) else 'Medium',
                                    assigned_to_name=assigned_engineer,
                                    account_id=shift.account_id,
                                    team_id=shift.team_id,
                                    handover_context=f"Assigned during {shift.current_shift_type} to {shift.next_shift_type} handover on {shift.date}",
                                    handover_request_id=handover_request.id
                                )
                                
                                print(f"🔍   Session after assignment creation: {len(db.session.new)} new objects")
                                print(f"🔍   Assignment result: {assignment_result}")
                                
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
                                print(f"🚨 ASSIGNMENT ERROR: {e}")
                                print(f"🔍   Session after assignment error: {len(db.session.new)} new objects")
                                import logging
                                logging.error(f"Failed to send incident assignment notification: {e}")
                                # Continue processing - don't let assignment failures stop incident creation
                    
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
                        
                        # Send notification if next action engineer is assigned
                        next_action_by = next_action_bys[i] if i < len(next_action_bys) and next_action_bys[i].strip() else None
                        
                        incident_data.update({
                            'status': statuses[i] if i < len(statuses) else 'Monitoring',
                            'priority': 'Medium',
                            'handover': notes[i] if i < len(notes) else '',
                            'assigned_to': next_action_by  # Store "next action by" in assigned_to field
                        })
                        if next_action_by:
                            try:
                                # Create or get HandoverRequest for edit mode
                                handover_request = HandoverRequest.query.filter_by(shift_id=shift.id).first()
                                if not handover_request:
                                    handover_request = HandoverRequest(
                                        shift_id=shift.id,
                                        account_id=shift.account_id,
                                        team_id=shift.team_id,
                                        created_at=datetime.now()
                                    )
                                    db.session.add(handover_request)
                                    db.session.flush()  # Get ID without full commit
                                
                                # Create enhanced incident assignment
                                create_enhanced_incident_assignment(
                                    incident_title=full_title,
                                    incident_description=notes[i] if i < len(notes) else '',
                                    incident_priority='Medium',
                                    assigned_to_name=next_action_by,
                                    account_id=shift.account_id,
                                    team_id=shift.team_id,
                                    handover_context=f"Handover incident from {shift.current_shift_type} to {shift.next_shift_type} shift on {shift.date}",
                                    handover_request_id=handover_request.id
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
                        
                        escalated_to_person = escalated_tos[i] if i < len(escalated_tos) and escalated_tos[i].strip() else None
                        
                        incident_data.update({
                            'status': 'Escalated',
                            'priority': 'High',
                            'handover': escalation_details,
                            'assigned_to': escalated_to_person,  # Store escalated to person
                            'escalated_to': escalated_tos[i] if i < len(escalated_tos) else '',  # Store in escalated_to field (exists in DB)
                            'description': reasons[i] if i < len(reasons) else '',  # Store escalation reason in description field
                            'status': (statuses[i] if i < len(statuses) else 'Escalated')[:16]  # Store current status, truncated to 16 chars
                        })
                    
                    incident = Incident(**incident_data)
                    db.session.add(incident)
                    print(f"🔍 DETAILED SESSION DEBUG: Just added {inc_type} incident to session")
                    print(f"🔍   Incident object: {incident}")
                    print(f"🔍   Session.new count: {len(db.session.new)}")
                    print(f"🔍   All new objects: {list(db.session.new)}")
                    log_action('Add Incident', f'ID: {incident_id}, Type: {inc_type}, Shift ID: {shift.id}')
        
        # 🚨 CRITICAL FIX: ALWAYS process ALL incident types from form data
        # Delete all existing incidents first to ensure clean state
        print(f"🔧 UNIVERSAL MODE: Syncing ALL incidents with form data")
        print(f"   Deleting {len(existing_incidents)} existing incidents")
        for incident in existing_incidents:
            db.session.delete(incident)
        
        # Now create ALL incident types from current form data
        print(f"   Creating ALL incident types from form data")
        add_incident('open', 'Open')
        add_incident('closed', 'Closed')
        add_incident('priority', 'Priority')
        add_incident('handover', 'Handover')
        add_incident('escalated', 'Escalated')
        # 🔧 CRITICAL FIX: Always process keypoints in edit mode (they should be updated)
        # Process key points - fix field name mismatch
        key_point_descriptions = request.form.getlist('keypoint_description[]')
        keypoint_assigned_tos = request.form.getlist('keypoint_assigned_to[]')
        keypoint_statuses = request.form.getlist('keypoint_status[]')
        keypoint_jira_ids = request.form.getlist('keypoint_jira_id[]')
        
        # 🆕 NEW: Extract Change Info data
        change_app_names = request.form.getlist('change_application_name[]')
        change_numbers = request.form.getlist('change_number[]')
        change_descriptions = request.form.getlist('change_description[]')
        change_datetimes = request.form.getlist('change_datetime[]')
        change_responsible_persons = request.form.getlist('change_responsible_engineer[]')
        change_statuses = request.form.getlist('change_status[]')  # 🆕 NEW: Status field
        
        # 🆕 NEW: Extract KB Updates data
        kb_app_names = request.form.getlist('kb_application_name[]')
        kb_numbers = request.form.getlist('kb_number[]')
        kb_descriptions = request.form.getlist('kb_description[]')
        kb_responsible_persons = request.form.getlist('kb_responsible_person[]')
        kb_statuses = request.form.getlist('kb_status[]')
        
        # 🐛 DEBUG: Log all form data for Change Info and KB Updates
        print("\n🐛🐛🐛 COMPREHENSIVE FORM SUBMISSION DEBUG 🐛🐛🐛")
        print(f"   Total form fields: {len(request.form)}")
        print(f"   Action: {action}")
        print(f"   Shift: {shift.current_shift_type} → {shift.next_shift_type} on {shift.date}")
        
        # Log all form field names for debugging
        change_related_fields = [k for k in request.form.keys() if 'change' in k.lower()]
        kb_related_fields = [k for k in request.form.keys() if 'kb' in k.lower()]
        incident_related_fields = [k for k in request.form.keys() if 'incident' in k.lower()]
        
        print(f"🔧 CHANGE RELATED FORM FIELDS ({len(change_related_fields)}):")
        for field in change_related_fields:
            values = request.form.getlist(field)
            print(f"   {field}: {values}")
            
        print(f"📚 KB RELATED FORM FIELDS ({len(kb_related_fields)}):")
        for field in kb_related_fields:
            values = request.form.getlist(field)
            print(f"   {field}: {values}")
            
        print(f"🚨 INCIDENT RELATED FORM FIELDS ({len(incident_related_fields)}):")
        for field in incident_related_fields:
            values = request.form.getlist(field)
            print(f"   {field}: {values}")
            
        print(f"🔧 PARSED CHANGE INFO DATA:")
        print(f"   App names ({len(change_app_names)}): {change_app_names}")
        print(f"   Numbers ({len(change_numbers)}): {change_numbers}")
        print(f"   Descriptions ({len(change_descriptions)}): {change_descriptions}")
        print(f"   DateTimes ({len(change_datetimes)}): {change_datetimes}")
        print(f"   Engineers ({len(change_responsible_persons)}): {change_responsible_persons}")
        print(f"   Statuses ({len(change_statuses)}): {change_statuses}")  # 🆕 NEW: Log statuses
        print(f"📚 PARSED KB UPDATES DATA:")
        print(f"   App names ({len(kb_app_names)}): {kb_app_names}")
        print(f"   Numbers ({len(kb_numbers)}): {kb_numbers}")
        print(f"   Descriptions ({len(kb_descriptions)}): {kb_descriptions}")
        print(f"   Persons ({len(kb_responsible_persons)}): {kb_responsible_persons}")
        print(f"   Statuses ({len(kb_statuses)}): {kb_statuses}")
        change_kb_fields = {k: v for k, v in request.form.items() if 'change' in k.lower() or 'kb' in k.lower()}
        print(f"🔍 ALL CHANGE/KB FORM FIELDS: {change_kb_fields}")
        
        # 🔧 CRITICAL FIX: Don't clear existing keypoints in edit mode - let enhanced processing handle updates
        # The enhanced processing logic will update/reuse existing key points properly without deletion
        existing_keypoints = ShiftKeyPoint.query.filter_by(shift_id=shift.id).all()
        print(f"🔧 EDIT MODE: PRESERVING {len(existing_keypoints)} existing keypoints - enhanced processing will handle updates")
        print(f"🔧 This prevents key point loss during submission - enhanced logic manages duplicates and updates")
        
        # 🔧 CRITICAL DEBUG: Log all form data to diagnose missing key points
        print(f"\n🔧 EDIT MODE FORM DATA ANALYSIS:")
        print(f"   Total form fields: {len(request.form)}")
        print(f"   Key point descriptions received: {len(key_point_descriptions)} items")
        print(f"   Key point assigned_tos received: {len(keypoint_assigned_tos)} items")
        print(f"   Key point statuses received: {len(keypoint_statuses)} items")
        print(f"   Key point JIRA IDs received: {len(keypoint_jira_ids)} items")
        
        # Show first few for debugging
        for i in range(min(5, len(key_point_descriptions))):
            desc = key_point_descriptions[i] if i < len(key_point_descriptions) else 'MISSING'
            assigned = keypoint_assigned_tos[i] if i < len(keypoint_assigned_tos) else 'MISSING'
            status = keypoint_statuses[i] if i < len(keypoint_statuses) else 'MISSING'
            jira = keypoint_jira_ids[i] if i < len(keypoint_jira_ids) else 'MISSING'
            print(f"   KP {i+1}: desc='{desc[:30]}...' assigned='{assigned}' status='{status}' jira='{jira}'")
        
        if len(key_point_descriptions) == 0:
            print(f"   ⚠️  CRITICAL: NO KEY POINTS RECEIVED FROM FORM!")
            print(f"   This will cause all key points to be deleted!")
        
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
        
        # Log the complete form data for diagnosis
        print(f"   🔹 ALL FORM DATA:")
        for key, values in request.form.lists():
            if 'keypoint' in key or 'incident' in key:
                print(f"      - {key}: {values}")
        
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
        
        # 🔧 RESTORED: Key point processing for edit mode - this was completely missing!
        print(f"🔧 PROCESSING KEY POINTS FOR EDIT MODE - Total: {len(key_point_descriptions)}")
        
        # First, get all existing key points for this shift
        existing_keypoints = ShiftKeyPoint.query.filter_by(shift_id=shift.id).all()
        print(f"🔧 Found {len(existing_keypoints)} existing key points for shift {shift.id}")
        
        # JIRA ID mapping removed - use description-based matching only
        print(f"🔧 Existing key points: {len(existing_keypoints)} total (description-based matching only)")
        
        # Track which existing key points are updated so we don't delete them
        updated_keypoint_ids = set()
        
        # Process each key point from the form
        for i in range(len(key_point_descriptions)):
            if i < len(key_point_descriptions):
                description = key_point_descriptions[i].strip()
                assigned_to = keypoint_assigned_tos[i] if i < len(keypoint_assigned_tos) else ''
                status = keypoint_statuses[i] if i < len(keypoint_statuses) else 'Open'
                # JIRA ID removed to eliminate duplication issues
                
                if not description:  # Skip empty descriptions
                    continue
                
                print(f"🔧 Processing KP {i+1}: '{description[:40]}...' status='{status}'")
                
                # Find existing key point by description only (no JIRA ID)
                existing_kp = None
                for kp in existing_keypoints:
                    if kp.id not in updated_keypoint_ids and kp.description.strip() == description:
                        existing_kp = kp
                        print(f"🔧 Found existing KP by description: {existing_kp.id}")
                        break
                
                # Get responsible engineer ID
                print(f"🔧 DEBUG [EDIT MODE] assigned_to value: '{assigned_to}' (type: {type(assigned_to)})")
                responsible_engineer_id = None
                if assigned_to:
                    if str(assigned_to).isdigit():
                        responsible_engineer_id = int(assigned_to)
                        print(f"🔧 DEBUG [EDIT MODE]: Converted assigned_to to integer: {responsible_engineer_id}")
                    else:
                        user = TeamMember.query.filter_by(name=assigned_to).first()
                        if user:
                            responsible_engineer_id = user.id
                            print(f"🔧 DEBUG [EDIT MODE]: Found user by name '{assigned_to}' -> ID: {responsible_engineer_id}")
                        else:
                            print(f"🔧 DEBUG [EDIT MODE]: Could not find user by name '{assigned_to}'")
                else:
                    print(f"🔧 DEBUG [EDIT MODE]: assigned_to is empty/None, no assignment")
                
                if existing_kp:
                    # Update existing key point
                    existing_kp.description = description
                    existing_kp.status = status
                    existing_kp.responsible_engineer_id = responsible_engineer_id
                    updated_keypoint_ids.add(existing_kp.id)
                    print(f"🔧 Updated existing key point {existing_kp.id}")
                else:
                    # Create new key point
                    new_kp = ShiftKeyPoint(
                        description=description,
                        status=status,
                        responsible_engineer_id=responsible_engineer_id,
                        shift_id=shift.id,
                        jira_id=None,  # JIRA ID removed to prevent duplicates
                        account_id=shift.account_id,
                        team_id=shift.team_id,
                        created_by_id=current_user.id  # Track who created the key point
                    )
                    db.session.add(new_kp)
                    print(f"🔧 Created new key point for shift {shift.id} by user {current_user.id}")
        
        # Remove key points that weren't updated (they were deleted from form)
        keypoints_to_delete = [kp for kp in existing_keypoints if kp.id not in updated_keypoint_ids]
        for kp in keypoints_to_delete:
            print(f"🔧 Deleting removed key point {kp.id}: '{kp.description[:40]}...'")
            db.session.delete(kp)
        
        print(f"🔧 KEY POINT PROCESSING COMPLETE: Updated {len(updated_keypoint_ids)}, Deleted {len(keypoints_to_delete)}")
        
        # 🔧 Process Change Info entries
        print(f"🔍 CHANGE INFO PROCESSING - Total entries: {len(change_app_names)}")
        
        # Get existing Change Info records for this shift
        existing_change_infos = ShiftChangeInfo.query.filter_by(shift_id=shift.id).all()
        print(f"🔧 Found {len(existing_change_infos)} existing change info records for shift {shift.id}")
        
        # Track which existing records are updated
        updated_change_info_ids = set()
        
        # 🐛 DEBUG: Log processing start
        print(f"\n🔧 STARTING CHANGE INFO PROCESSING: {len(change_app_names)} entries")
        
        # Process each Change Info entry from the form
        for i in range(len(change_app_names)):
            app_name = change_app_names[i].strip() if i < len(change_app_names) else ''
            change_number = change_numbers[i].strip() if i < len(change_numbers) else ''
            description = change_descriptions[i].strip() if i < len(change_descriptions) else ''
            datetime_str = change_datetimes[i].strip() if i < len(change_datetimes) else ''
            responsible_person = change_responsible_persons[i].strip() if i < len(change_responsible_persons) else ''
            
            if not app_name and not change_number and not description and not datetime_str and not responsible_person:  # Skip completely empty entries
                continue
                
            print(f"🔧 Processing Change Info {i+1}: App={app_name}, Change#{change_number}")
            
            # Parse datetime if provided
            change_datetime = None
            if datetime_str:
                try:
                    change_datetime = datetime.strptime(datetime_str, '%Y-%m-%dT%H:%M')
                except ValueError:
                    print(f"⚠️ Invalid datetime format for change {change_number}: {datetime_str}")
            
            # Get responsible engineer ID
            responsible_engineer_id = None
            if responsible_person:
                if responsible_person.isdigit():
                    responsible_engineer_id = int(responsible_person)
                else:
                    user = TeamMember.query.filter_by(name=responsible_person).first()
                    if user:
                        responsible_engineer_id = user.id
            
            # Find existing record by unique constraint (shift_id + change_number)
            existing_record = None
            for record in existing_change_infos:
                if record.id not in updated_change_info_ids and record.change_number == change_number:
                    existing_record = record
                    print(f"🔧 Found existing Change Info by change_number: {existing_record.id}")
                    break
            
            if existing_record:
                # Update existing record
                existing_record.app_name = app_name
                existing_record.description = description
                existing_record.change_datetime = change_datetime
                existing_record.responsible_engineer_id = responsible_engineer_id
                updated_change_info_ids.add(existing_record.id)
                print(f"🔧 Updated existing Change Info {existing_record.id}")
            else:
                # Create new record
                new_record = ShiftChangeInfo(
                    shift_id=shift.id,
                    app_name=app_name,
                    change_number=change_number,
                    description=description,
                    change_datetime=change_datetime,
                    responsible_engineer_id=responsible_engineer_id,
                    account_id=shift.account_id,
                    team_id=shift.team_id
                )
                db.session.add(new_record)
                print(f"🔧 Created new Change Info for shift {shift.id}")
        
        # Remove Change Info records that weren't updated (deleted from form)
        change_infos_to_delete = [record for record in existing_change_infos if record.id not in updated_change_info_ids]
        for record in change_infos_to_delete:
            print(f"🔧 Deleting removed Change Info {record.id}: {record.app_name} - {record.change_number}")
            db.session.delete(record)
        
        print(f"🔧 CHANGE INFO PROCESSING COMPLETE: Updated {len(updated_change_info_ids)}, Deleted {len(change_infos_to_delete)}")
        
        # 🔧 Process KB Update entries
        print(f"🔍 KB UPDATE PROCESSING - Total entries: {len(kb_app_names)}")
        
        # Get existing KB Update records for this shift
        existing_kb_updates = ShiftKBUpdate.query.filter_by(shift_id=shift.id).all()
        print(f"🔧 Found {len(existing_kb_updates)} existing KB update records for shift {shift.id}")
        
        # Track which existing records are updated
        updated_kb_update_ids = set()
        
        # 🐛 DEBUG: Log processing start
        print(f"\n📚 STARTING KB UPDATES PROCESSING: {len(kb_app_names)} entries")
        
        # Process each KB Update entry from the form
        for i in range(len(kb_app_names)):
            app_name = kb_app_names[i].strip() if i < len(kb_app_names) else ''
            kb_number = kb_numbers[i].strip() if i < len(kb_numbers) else ''
            description = kb_descriptions[i].strip() if i < len(kb_descriptions) else ''
            responsible_person = kb_responsible_persons[i].strip() if i < len(kb_responsible_persons) else ''
            status = kb_statuses[i].strip() if i < len(kb_statuses) else ''
            
            if not app_name and not kb_number and not description and not responsible_person and not status:  # Skip completely empty entries
                continue
                
            print(f"🔧 Processing KB Update {i+1}: App={app_name}, KB#{kb_number}")
            
            # Get responsible engineer ID
            responsible_engineer_id = None
            if responsible_person:
                if responsible_person.isdigit():
                    responsible_engineer_id = int(responsible_person)
                else:
                    user = TeamMember.query.filter_by(name=responsible_person).first()
                    if user:
                        responsible_engineer_id = user.id
            
            # Find existing record by unique constraint (shift_id + kb_number)
            existing_record = None
            for record in existing_kb_updates:
                if record.id not in updated_kb_update_ids and record.kb_number == kb_number:
                    existing_record = record
                    print(f"🔧 Found existing KB Update by kb_number: {existing_record.id}")
                    break
            
            if existing_record:
                # Update existing record
                existing_record.app_name = app_name
                existing_record.description = description
                existing_record.responsible_engineer_id = responsible_engineer_id
                existing_record.status = status
                updated_kb_update_ids.add(existing_record.id)
                print(f"🔧 Updated existing KB Update {existing_record.id}")
            else:
                # Create new record
                new_record = ShiftKBUpdate(
                    shift_id=shift.id,
                    app_name=app_name,
                    kb_number=kb_number,
                    description=description,
                    responsible_engineer_id=responsible_engineer_id,
                    status=status,
                    account_id=shift.account_id,
                    team_id=shift.team_id
                )
                db.session.add(new_record)
                print(f"🔧 Created new KB Update for shift {shift.id}")
        
        # Remove KB Update records that weren't updated (deleted from form)
        kb_updates_to_delete = [record for record in existing_kb_updates if record.id not in updated_kb_update_ids]
        for record in kb_updates_to_delete:
            print(f"🔧 Deleting removed KB Update {record.id}: {record.app_name} - {record.kb_number}")
            db.session.delete(record)
        
        print(f"🔧 KB UPDATE PROCESSING COMPLETE: Updated {len(updated_kb_update_ids)}, Deleted {len(kb_updates_to_delete)}")
        
        db.session.commit()
        
        # 🔥🔥🔥 FINAL DATABASE STATE VERIFICATION 🔥🔥🔥
        print(f"\n🎯🎯🎯 FINAL VERIFICATION: DATA SAVED TO DATABASE 🎯🎯🎯")
        print(f"   Shift ID: {shift.id}")
        print(f"   Date: {shift.date}")
        print(f"   Shift: {shift.current_shift_type} → {shift.next_shift_type}")
        print(f"   Status: {shift.status}")
        
        # Verify incidents were saved
        final_incidents = Incident.query.filter_by(shift_id=shift.id).all()
        print(f"   ✅ Incidents saved: {len(final_incidents)}")
        for i, inc in enumerate(final_incidents, 1):
            print(f"      {i}. {inc.title} ({inc.type}) - Priority: {inc.priority}")
        
        # Verify change_infos were saved
        final_change_infos = ShiftChangeInfo.query.filter_by(shift_id=shift.id).all()
        print(f"   ✅ Change Infos saved: {len(final_change_infos)}")
        for i, ci in enumerate(final_change_infos, 1):
            print(f"      {i}. {ci.app_name} - {ci.change_number}: {ci.description}")
        
        # Verify kb_updates were saved
        final_kb_updates = ShiftKBUpdate.query.filter_by(shift_id=shift.id).all()
        print(f"   ✅ KB Updates saved: {len(final_kb_updates)}")
        for i, kb in enumerate(final_kb_updates, 1):
            print(f"      {i}. {kb.app_name} - {kb.kb_number}: {kb.description}")
        
        # Verify key points were saved
        final_key_points = ShiftKeyPoint.query.filter_by(shift_id=shift.id).all()
        print(f"   ✅ Key Points saved: {len(final_key_points)}")
        for i, kp in enumerate(final_key_points, 1):
            print(f"      {i}. {kp.description[:50]}... Status: {kp.status}")
        
        print(f"🎯🎯🎯 END FINAL VERIFICATION 🎯🎯🎯\n")
        
        if action in ['send', 'submit']:
            import logging
            import threading
            import time
            logging.basicConfig(level=logging.DEBUG)
            print(f"[EMAIL_DEBUG] 📧 Attempting to send handover email for shift_id={shift.id}")
            print(f"[EMAIL_DEBUG] 📧 Action: {action}, Date: {shift.date}, Type: {shift.current_shift_type}→{shift.next_shift_type}")
            logging.debug(f"[EMAIL] Attempting to send handover email for shift_id={shift.id}, date={shift.date}, current_shift_type={shift.current_shift_type}, next_shift_type={shift.next_shift_type}")
            
            # Use threading to prevent UI blocking with timeout
            email_success = [False]  # Use list for mutable reference
            email_error = [None]
            
            def send_email_thread():
                try:
                    send_handover_email(shift)
                    email_success[0] = True
                    print(f"[EMAIL_DEBUG] ✅ Email sent successfully for shift_id={shift.id}")
                    logging.debug(f"[EMAIL] Email sent successfully for shift_id={shift.id}")
                except Exception as e:
                    email_error[0] = str(e)
                    print(f"[EMAIL_DEBUG] ❌ Failed to send email for shift_id={shift.id}: {e}")
                    logging.error(f"[EMAIL] Failed to send email for shift_id={shift.id}: {e}")
            
            # Start email sending in background thread
            email_thread = threading.Thread(target=send_email_thread)
            email_thread.daemon = True
            email_thread.start()
            
            # Wait for email with 8-second timeout
            email_thread.join(timeout=8.0)
            
            if email_thread.is_alive():
                print(f"[EMAIL_DEBUG] ⏰ Email sending timed out after 8 seconds for shift_id={shift.id}")
                flash('Handover submitted successfully! Email delivery in progress...')
            elif email_success[0]:
                flash('Handover submitted and email sent successfully!')
            elif email_error[0]:
                flash(f'Handover submitted successfully! Email delivery failed: {email_error[0][:100]}')
            else:
                flash('Handover submitted successfully! Email status unknown.')
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
    
    # 🔧 EDIT MODE FIX: Load appropriate key points based on handover state
    if shift_id:  # Edit mode
        if shift.status == 'draft':
            # DRAFT EDIT: Show all relevant key points (like new handover creation)
            # Include both direct key points AND active ones from same team
            direct_kps = ShiftKeyPoint.query.filter(ShiftKeyPoint.shift_id == shift.id).all()
            active_kps = ShiftKeyPoint.query.filter(
                ShiftKeyPoint.account_id == shift.account_id,
                ShiftKeyPoint.team_id == shift.team_id,
                ShiftKeyPoint.status.in_(['Open', 'In Progress']),
                ShiftKeyPoint.shift_id != shift.id  # Don't include current shift to avoid duplicates
            ).all()
            all_kps = direct_kps + active_kps
            print(f"🔧 EDIT DRAFT: Found {len(direct_kps)} direct + {len(active_kps)} active = {len(all_kps)} total key points")
        else:
            # SENT HANDOVER EDIT: Only show direct key points from this shift
            all_kps = ShiftKeyPoint.query.filter(ShiftKeyPoint.shift_id == shift.id).all()
            print(f"🔧 EDIT SENT: Found {len(all_kps)} key points for shift {shift.id} (ONLY from this shift)")
        
        print(f"🔧 EDIT MODE: Key points loaded:")
        for kp in all_kps:
            print(f"   - ID {kp.id}: '{kp.description[:40]}...' status={kp.status} shift_id={kp.shift_id}")
    else:  # New handover mode - load UNIQUE recent open key points with smart deduplication        
        # Get recent key points from last 7 days to avoid very old duplicates
        recent_date = datetime.now().date() - timedelta(days=7)
        recent_shifts = Shift.query.filter(
            Shift.date >= recent_date,
            Shift.account_id == shift.account_id,
            Shift.team_id == shift.team_id
        ).all()
        recent_shift_ids = [s.id for s in recent_shifts] if recent_shifts else []
        
        if recent_shift_ids:
            raw_kps = ShiftKeyPoint.query.filter(
                ShiftKeyPoint.account_id == shift.account_id,
                ShiftKeyPoint.team_id == shift.team_id,
                ShiftKeyPoint.status.in_(['Open', 'In Progress']),
                ShiftKeyPoint.shift_id.in_(recent_shift_ids)  # Only from recent shifts
            ).order_by(ShiftKeyPoint.id.desc()).all()
            
            # Deduplicate by description - keep most recent version of each unique description
            kp_map = {}
            for kp in raw_kps:
                desc_key = kp.description.strip().lower() if kp.description else ''
                if desc_key and (desc_key not in kp_map or kp.id > kp_map[desc_key].id):
                    kp_map[desc_key] = kp
            
            all_kps = list(kp_map.values())[:8]  # Limit to 8 unique key points
            print(f"🔧 NEW HANDOVER: Deduplicated {len(raw_kps)} raw key points to {len(all_kps)} unique ones from last 7 days")
        else:
            all_kps = []
            print(f"🔧 NEW HANDOVER: No recent shifts found for deduplication, starting with empty key points")
    
    # 🔧 DEDUPLICATION LOGIC: Handle edit mode vs new handover differently
    if shift_id and shift.status != 'draft':
        # SENT HANDOVER EDIT: Show actual key points from this shift without deduplication
        open_key_points = all_kps
        print(f"🔧 EDIT SENT: Showing {len(open_key_points)} actual key points from shift {shift.id}")
    else:
        # DRAFT EDIT or NEW HANDOVER: Deduplicate to avoid showing same key point multiple times
        kp_map = {}
        for kp in all_kps:
            key = (kp.description, kp.jira_id)
            if key not in kp_map or kp.id > kp_map[key].id:
                kp_map[key] = kp
        open_key_points = list(kp_map.values())
        print(f"🔧 NEW HANDOVER: After deduplication, showing {len(open_key_points)} unique key points")
    
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
    
    # 🔧 Load existing Change Info and KB Updates for edit mode
    def serialize_change_info(change_info):
        """Convert Change Info object to dictionary for template"""
        # Get responsible engineer name and ID
        assigned_to_name = ''
        responsible_engineer_id = change_info.responsible_engineer_id
        if change_info.responsible_engineer_id:
            engineer = TeamMember.query.get(change_info.responsible_engineer_id)
            if engineer:
                assigned_to_name = engineer.name
        
        # Format datetime for HTML input
        datetime_str = ''
        if change_info.change_datetime:
            datetime_str = change_info.change_datetime.strftime('%Y-%m-%dT%H:%M')
        
        return {
            'app_name': change_info.app_name,
            'change_number': change_info.change_number,
            'description': change_info.description,
            'change_datetime': datetime_str,
            'responsible_person': assigned_to_name,
            'responsible_engineer_id': responsible_engineer_id,  # Add ID for dropdown
            'status': change_info.status
        }
    
    def serialize_kb_update(kb_update):
        """Convert KB Update object to dictionary for template"""
        # Get responsible engineer name and ID
        assigned_to_name = ''
        responsible_engineer_id = kb_update.responsible_engineer_id
        if kb_update.responsible_engineer_id:
            engineer = TeamMember.query.get(kb_update.responsible_engineer_id)
            if engineer:
                assigned_to_name = engineer.name
        
        return {
            'app_name': kb_update.app_name,
            'kb_number': kb_update.kb_number,
            'description': kb_update.description,
            'responsible_person': assigned_to_name,
            'responsible_engineer_id': responsible_engineer_id,  # Add ID for dropdown
            'status': kb_update.status
        }
    
    # Get existing Change Info and KB Updates
    change_infos_raw = ShiftChangeInfo.query.filter_by(shift_id=shift.id).all()
    kb_updates_raw = ShiftKBUpdate.query.filter_by(shift_id=shift.id).all()
    
    # Convert to dictionaries for the template
    change_infos = [serialize_change_info(ci) for ci in change_infos_raw]
    kb_updates = [serialize_kb_update(kb) for kb in kb_updates_raw]

    # 🔧 DEBUG: Log edit mode data being sent to template
    print(f"[EDIT_DEBUG] 📋 Edit mode for shift {shift.id} - passing data to template:")
    print(f"[EDIT_DEBUG]   Open incidents: {len(open_incidents)} items")
    if open_incidents:
        print(f"[EDIT_DEBUG]     First open incident: {open_incidents[0]}")
    print(f"[EDIT_DEBUG]   Closed incidents: {len(closed_incidents)} items") 
    print(f"[EDIT_DEBUG]   Priority incidents: {len(priority_incidents)} items")
    print(f"[EDIT_DEBUG]   Handover incidents: {len(handover_incidents)} items")
    print(f"[EDIT_DEBUG]   Escalated incidents: {len(escalated_incidents)} items")
    print(f"[EDIT_DEBUG]   Key points: {len(open_key_points)} items")
    for i, kp in enumerate(open_key_points):
        print(f"[EDIT_DEBUG]     KP {i+1}: ID {kp.id}, '{kp.description[:30]}...', status={kp.status}, engineer_id={kp.responsible_engineer_id}")
    print(f"[EDIT_DEBUG]   Change infos: {len(change_infos)} items")
    print(f"[EDIT_DEBUG]   KB updates: {len(kb_updates)} items")
    print(f"[EDIT_DEBUG]   is_edit_mode flag: True")
    
    return render_template('handover_form.html',
        team_members=team_members,
        teams=teams,
        default_team_id=default_team_id,
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
        escalated_incidents=escalated_incidents,
        change_infos=change_infos,
        kb_updates=kb_updates,
        today=shift.date.strftime('%Y-%m-%d'),
        show_team_error=False,
        is_edit_mode=True  # Flag to indicate this is edit mode
    )


@handover_bp.route('/api/team-members/<int:team_id>', methods=['GET'])
@login_required
def get_team_members_api(team_id):
    """API endpoint to fetch team members for a specific team"""
    try:
        # Verify user has access to this team
        if current_user.role == 'super_admin':
            # Super admin can access any team
            pass
        elif current_user.role == 'account_admin':
            # Account admin can access teams in their account
            team = Team.query.get(team_id)
            if not team or team.account_id != current_user.account_id:
                return jsonify({'error': 'Access denied'}), 403
        else:
            # Regular users can only access their assigned teams
            user_team_ids = TeamAccessService.get_user_team_ids()
            if team_id not in user_team_ids:
                print(f"❌ Access denied: team_id {team_id} not in user's teams {user_team_ids}")
                return jsonify({'error': 'Access denied'}), 403
        
        # Fetch team members
        team_members = TeamMember.query.filter_by(team_id=team_id).all()
        
        # Format response
        members_data = [
            {
                'id': member.id,
                'name': member.name,
                'user_id': member.user_id
            }
            for member in team_members
        ]
        
        return jsonify({
            'success': True,
            'members': members_data,
            'team_id': team_id
        })
        
    except Exception as e:
        print(f"❌ Error fetching team members: {e}")
        return jsonify({'error': str(e)}), 500


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
    
    # Import required models at function level to avoid scoping issues
    from models.models import ShiftChangeInfo, ShiftKBUpdate
    
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
        # Regular users: Use TeamAccessService to get ALL their teams (for multi-team support)
        team_filter_context = TeamAccessService.get_team_filter_context()
        teams = team_filter_context['user_teams']
        
        print(f"[HANDOVER-CREATE] User {current_user.username} teams: {[t.name for t in teams]} (count: {len(teams)})")
    
    # Set default team selection based on user role - Enhanced with Primary Team support
    default_team_id = None
    if current_user.role in ['user', 'team_admin']:
        # Check if specific team was requested
        selected_team_id = request.args.get('team_id')
        if selected_team_id:
            default_team_id = int(selected_team_id)
        elif len(teams) > 1:
            # For multi-team users, prefer primary team, then session, then first team
            primary_team_id = TeamAccessService.get_primary_team_id(account_id=account_id)
            if primary_team_id and any(t.id == primary_team_id for t in teams):
                default_team_id = primary_team_id
                print(f"[HANDOVER-CREATE] Using primary team {primary_team_id} for user {current_user.username}")
            else:
                session_team_id = session.get('filter_team_id')
                if session_team_id and any(t.id == int(session_team_id) for t in teams):
                    default_team_id = int(session_team_id)
                else:
                    default_team_id = teams[0].id
                    print(f"[HANDOVER-CREATE] No primary team found, using first team {default_team_id}")
        elif teams:
            # Single team user - use their only team
            default_team_id = teams[0].id
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
        print(f"[DEBUG_ACTION] Action received from form: '{action}' (default: 'submit')")
        print(f"[DEBUG_ACTION] All form keys: {list(request.form.keys())}")  # All keys
        
        # 🚨 CRITICAL DEBUG: Log all incoming form data
        print(f"\n🔍🔍🔍 COMPREHENSIVE FORM DATA DEBUG 🔍🔍🔍")
        print(f"Request method: {request.method}")
        print(f"Action: {action}")
        print(f"Form keys: {list(request.form.keys())}")
        print(f"Total form fields: {len(request.form)}")
        
        # Log incident-related fields
        incident_fields = [k for k in request.form.keys() if 'incident' in k]
        print(f"🚨 INCIDENT FIELDS ({len(incident_fields)}):")
        for field in incident_fields[:10]:  # Limit to first 10 for readability
            values = request.form.getlist(field)
            print(f"   {field}: {values}")
        
        # Log change-related fields  
        change_fields = [k for k in request.form.keys() if 'change' in k]
        print(f"🔧 CHANGE FIELDS ({len(change_fields)}):")
        for field in change_fields:
            values = request.form.getlist(field)
            print(f"   {field}: {values}")
            
        # Log KB-related fields
        kb_fields = [k for k in request.form.keys() if 'kb' in k]
        print(f"📚 KB FIELDS ({len(kb_fields)}):")
        for field in kb_fields:
            values = request.form.getlist(field)
            print(f"   {field}: {values}")
            
        # Log keypoint-related fields
        kp_fields = [k for k in request.form.keys() if 'keypoint' in k]
        print(f"🎯 KEYPOINT FIELDS ({len(kp_fields)}):")
        for field in kp_fields:
            values = request.form.getlist(field)
            print(f"   {field}: {values}")
        print(f"🔍🔍🔍 END FORM DATA DEBUG 🔍🔍🔍\n")
        
        print(f"🔥 KEYPOINT FORM DEBUG: Checking for keypoint fields:")
        keypoint_fields = [key for key in request.form.keys() if 'keypoint' in key.lower()]
        print(f"🔥 Found keypoint-related fields: {keypoint_fields}")
        for field in keypoint_fields:
            print(f"🔥   {field}: {request.form.getlist(field)}")
        
        # 🔧 CRITICAL FIX: Prevent multiple handover submissions for the same shift
        if action == 'submit':  # Only check for actual submissions, not drafts
            existing_handover = Shift.query.filter_by(
                date=date,
                current_shift_type=current_shift_type,
                next_shift_type=next_shift_type,
                account_id=account_id,
                team_id=team_id,
                status='sent'  # Only check for already submitted handovers
            ).first()
            
            if existing_handover:
                print(f"[DUPLICATE_CHECK] Found existing submitted handover: ID={existing_handover.id}")
                flash('❌ This shift handover has already been submitted! You cannot submit the same shift handover twice. '
                      'Please check the Reports section to view your submitted handover.', 'error')
                return redirect(url_for('handover.handover'))
            else:
                print(f"[DUPLICATE_CHECK] ✅ No existing submitted handover found for {current_shift_type}→{next_shift_type} on {date}")
        
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
        
        # ✅ FIXED: Create new shift for each handover to prevent overriding existing data
        additional_notes = request.form.get('additional_notes', '')
        shift = create_new_shift(date, current_shift_type, next_shift_type, account_id, team_id, action, additional_notes)
        
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
        
        # Get engineers for current shift (always use the handover date)
        current_engineers_objs = get_engineers_for_shift(date, current_shift_code)
        print(f"[SHIFT FIX] Current shift ({current_shift_type}) engineers from date: {date}")
        
        # Get engineers for next shift
        # For Night->Morning transitions, Morning engineers should come from next day
        if current_shift_type == 'Night' and next_shift_type == 'Morning':
            next_date = date + timedelta(days=1)
            next_engineers_objs = get_engineers_for_shift(next_date, next_shift_code)
            print(f"[SHIFT FIX] Night->Morning transition: Next shift ({next_shift_type}) engineers from date: {next_date}")
        else:
            next_engineers_objs = get_engineers_for_shift(date, next_shift_code)
            print(f"[SHIFT FIX] Regular transition: Next shift ({next_shift_type}) engineers from date: {date}")
            
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
                        print(f"🔍 SESSION DEBUG: Session now has {len(db.session.new)} new objects")
                        
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
                        print(f"🔍 SESSION DEBUG: Session now has {len(db.session.new)} new objects")
                        
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
                        print(f"🔍 SESSION DEBUG: Session now has {len(db.session.new)} new objects")
                        
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
                            assigned_to=next_by[i] if i < len(next_by) else '',  # Store "next action by" in assigned_to
                            description=notes[i] if i < len(notes) else '',
                            handover=notes[i] if i < len(notes) else '',  # Store notes in handover field
                            shift_id=shift_id_to_use,
                            type='Handover',
                            account_id=account_id,
                            team_id=team_id
                        )
                        db.session.add(incident)
                        print(f"Added handover incident to session: {incident}")
                        print(f"🔍 SESSION DEBUG: Session now has {len(db.session.new)} new objects")
                        
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
                escalation_reasons = request.form.getlist(f'{field_prefix}_reason[]')
                current_statuses = request.form.getlist(f'{field_prefix}_status[]')
                
                print(f"Escalated incident fields - escalated_to: {escalated_to}, escalation_reasons: {escalation_reasons}, current_statuses: {current_statuses}")
                
                for i in range(len(app_names)):
                    if i < len(incident_ids) and (app_names[i].strip() or incident_ids[i].strip()):
                        print(f"Creating escalated incident {i+1}: {app_names[i]} - {incident_ids[i]}")
                        # Truncate status to fit database column (VARCHAR(16))
                        status_value = current_statuses[i] if i < len(current_statuses) else 'Escalated'
                        status_truncated = status_value[:16] if status_value else 'Escalated'
                        
                        incident = Incident(
                            title=f"{app_names[i]} - {incident_ids[i]}".strip(' -'),
                            status=status_truncated,  # Truncated to 16 characters
                            priority='High',  # Default priority for escalated incidents
                            escalated_to=escalated_to[i] if i < len(escalated_to) else '',  # This field exists
                            description=escalation_reasons[i] if i < len(escalation_reasons) else '',  # Store escalation reason in description
                            shift_id=shift_id_to_use,
                            type='Escalated',
                            account_id=account_id,
                            team_id=team_id
                        )
                        db.session.add(incident)
                        print(f"Added escalated incident to session: {incident}")
                        print(f"🔍 SESSION DEBUG: Session now has {len(db.session.new)} new objects")
            
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
        
        # 🚨 CRITICAL FIX: Flush incidents to database immediately after processing
        print("🚨 FLOW DEBUG: Flushing incidents to database to prevent loss")
        try:
            db.session.flush()  # Force incidents to be written to database
            print(f"✅ Successfully flushed incidents to database")
            print(f"🔍 SESSION DEBUG AFTER FLUSH: Session now has {len(db.session.new)} new objects")
        except Exception as e:
            print(f"❌ Error flushing incidents: {e}")
        
        # 🚨 CRITICAL FIX: Process Change Info and KB Updates RIGHT AFTER incidents
        print("🚨 FLOW DEBUG: Starting Change/KB processing immediately after incidents")
        print("=== PROCESSING CHANGE INFO ===")
        change_app_names = request.form.getlist('change_application_name[]')
        change_numbers = request.form.getlist('change_number[]')
        change_descriptions = request.form.getlist('change_description[]')
        change_datetimes = request.form.getlist('change_datetime[]')
        change_engineers = request.form.getlist('change_responsible_engineer[]')
        change_statuses = request.form.getlist('change_status[]')
        
        print(f"Found {len(change_app_names)} change info entries to process")
        for i in range(len(change_app_names)):
            if i < len(change_numbers) and change_numbers[i].strip():
                app_name = change_app_names[i] if i < len(change_app_names) else ''
                change_number = change_numbers[i] if i < len(change_numbers) else ''
                description = change_descriptions[i] if i < len(change_descriptions) else ''
                datetime_str = change_datetimes[i] if i < len(change_datetimes) else ''
                engineer_id = change_engineers[i] if i < len(change_engineers) else ''
                status = change_statuses[i] if i < len(change_statuses) else 'New'
                
                print(f"Creating Change Info {i+1}: {app_name} - {change_number}")
                
                # Convert datetime string to datetime object
                change_datetime = None
                if datetime_str:
                    try:
                        change_datetime = datetime.strptime(datetime_str, '%Y-%m-%dT%H:%M')
                    except ValueError:
                        print(f"Warning: Invalid datetime format for change {change_number}: {datetime_str}")
                
                # Convert engineer_id to integer
                responsible_engineer_id = None
                if engineer_id and engineer_id.isdigit():
                    responsible_engineer_id = int(engineer_id)
                
                change_info = ShiftChangeInfo(
                    shift_id=shift.id,
                    app_name=app_name,
                    change_number=change_number,
                    description=description,
                    change_datetime=change_datetime,
                    responsible_engineer_id=responsible_engineer_id,
                    status=status,
                    account_id=shift.account_id,
                    team_id=shift.team_id
                )
                db.session.add(change_info)
                print(f"✅ Added Change Info: {app_name} - {change_number}")
        
        print("=== PROCESSING KB UPDATES ===")
        kb_app_names = request.form.getlist('kb_application_name[]')
        kb_numbers = request.form.getlist('kb_number[]')
        kb_descriptions = request.form.getlist('kb_description[]')
        kb_persons = request.form.getlist('kb_responsible_person[]')
        kb_statuses = request.form.getlist('kb_status[]')
        
        print(f"Found {len(kb_app_names)} KB update entries to process")
        for i in range(len(kb_app_names)):
            # 🔧 FIX: Allow KB updates even without KB number - check if any field has content
            app_name = kb_app_names[i].strip() if i < len(kb_app_names) else ''
            kb_number = kb_numbers[i].strip() if i < len(kb_numbers) else ''
            kb_desc = kb_descriptions[i].strip() if i < len(kb_descriptions) else ''
            
            # Save if app_name OR kb_number OR description is provided
            if app_name or kb_number or kb_desc:
                description = kb_desc
                person_id = kb_persons[i] if i < len(kb_persons) else ''
                status = kb_statuses[i].strip() if i < len(kb_statuses) and kb_statuses[i] else 'New'
                
                print(f"Creating KB Update {i+1}: {app_name} - {kb_number} - {description[:30]}...")
                
                # Convert person_id to integer
                responsible_person_id = None
                if person_id and person_id.isdigit():
                    responsible_person_id = int(person_id)
                
                kb_update = ShiftKBUpdate(
                    shift_id=shift.id,
                    app_name=app_name,
                    kb_number=kb_number,
                    description=description,
                    responsible_engineer_id=responsible_person_id,
                    status=status,
                    account_id=shift.account_id,
                    team_id=shift.team_id
                )
                db.session.add(kb_update)
                print(f"✅ Added KB Update: {app_name} - {kb_number}")
        
        print("=== FINISHED PROCESSING CHANGE INFO AND KB UPDATES ===")
        
        # Check what's in the session before committing
        print("=== DB SESSION AFTER CHANGE/KB PROCESSING ===")
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
        
        print(f"🚨🚨🚨 KEY POINT FORM DATA DEBUG 🚨🚨🚨")
        print(f"  Total descriptions: {len(key_point_descriptions)}")
        print(f"  Total assigned_to: {len(keypoint_assigned_to)}")
        print(f"  Descriptions: {key_point_descriptions}")
        print(f"  Assigned to (RAW): {keypoint_assigned_to}")
        for idx, assigned in enumerate(keypoint_assigned_to):
            print(f"    assigned_to[{idx}] = '{assigned}' (type: {type(assigned)}, len: {len(assigned) if assigned else 0})")
        print(f"  Statuses: {keypoint_statuses}")
        print(f"  JIRA IDs: {keypoint_jira_ids}")
        print(f"🚨🚨🚨 END KEY POINT FORM DATA 🚨🚨🚨")
        
        print(f"🔍 DUPLICATION PREVENTION: Processing {len(key_point_descriptions)} key points from form")
        for i in range(len(key_point_descriptions)):
            description = key_point_descriptions[i].strip() if i < len(key_point_descriptions) else ''
            jira_id = keypoint_jira_ids[i].strip() if i < len(keypoint_jira_ids) else ''
            responsible_id = keypoint_assigned_to[i] if i < len(keypoint_assigned_to) else ''
            status = keypoint_statuses[i] if i < len(keypoint_statuses) else 'Open'
            
            print(f"\n🔍 Processing key point {i+1}/{len(key_point_descriptions)}:")
            print(f"   Description: '{description[:50]}{'...' if len(description) > 50 else ''}'")
            print(f"   JIRA ID: '{jira_id}'")
            print(f"   Responsible: '{responsible_id}'")
            print(f"   Status: '{status}'")
            
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
                        
                        # 🔧 CRITICAL FIX: Do NOT create a new 'Closed' key point - just update existing one
                        print(f"🔒 SKIPPING NEW KEY POINT CREATION - Updated existing key point to 'Closed' status")
                        continue  # Skip to next key point without creating duplicate
                    else:
                        print(f"🔒 NO OPEN KEY POINT FOUND to close with description='{description}', jira_id='{jira_id}'")
                        print(f"🔒 CREATING NEW 'Closed' KEY POINT since no existing one found to close")
                        # Will proceed to create new closed key point below
                
                # 🔧 FIXED DUPLICATION ISSUE: Check for existing key points across all shifts
                # to prevent creating duplicates when the same key points are carried forward
                
                # 🔧 NORMALIZE JIRA ID for consistent checking
                normalized_jira_id = None if (not jira_id or jira_id == 'None' or jira_id == '') else jira_id
                
                # First check if we're editing an existing key point in the current handover
                # Handle None JIRA ID matching properly for same shift
                if normalized_jira_id is None:
                    same_shift_jira_filter = or_(
                        ShiftKeyPoint.jira_id.is_(None),
                        ShiftKeyPoint.jira_id == '',
                        ShiftKeyPoint.jira_id == 'None'
                    )
                else:
                    same_shift_jira_filter = ShiftKeyPoint.jira_id == normalized_jira_id
                
                existing_kp_same_shift = ShiftKeyPoint.query.filter(
                    ShiftKeyPoint.description == description,
                    same_shift_jira_filter,
                    ShiftKeyPoint.shift_id == shift.id  # Same handover
                ).first()
                
                if existing_kp_same_shift:
                    # This is an edit of an existing key point in the same handover
                    if existing_kp_same_shift.status != status:
                        existing_kp_same_shift.status = status
                        db.session.add(existing_kp_same_shift)
                        print(f"Updated existing key point {existing_kp_same_shift.id} status from {existing_kp_same_shift.status} to {status}")
                    else:
                        print(f"No changes for key point: '{description}', keeping existing ID {existing_kp_same_shift.id}")
                    continue  # Skip to next key point
                
                # 🔧 NORMALIZE JIRA ID for consistent checking
                normalized_jira_id = None if (not jira_id or jira_id == 'None' or jira_id == '') else jira_id
                
                # Check for existing open/in-progress key points from other shifts to prevent duplication
                # Handle None JIRA ID matching properly
                if normalized_jira_id is None:
                    jira_filter = or_(
                        ShiftKeyPoint.jira_id.is_(None),
                        ShiftKeyPoint.jira_id == '',
                        ShiftKeyPoint.jira_id == 'None'
                    )
                else:
                    jira_filter = ShiftKeyPoint.jira_id == normalized_jira_id
                
                # 🔧 FIX: Always create a new key point for each handover, even if carried forward
                # This ensures each handover report shows exactly what was submitted
                existing_kp_other_shift = ShiftKeyPoint.query.filter(
                    ShiftKeyPoint.description == description,
                    jira_filter,
                    ShiftKeyPoint.status.in_(['Open', 'In Progress']),
                    ShiftKeyPoint.account_id == account_id,
                    ShiftKeyPoint.team_id == team_id,
                    ShiftKeyPoint.shift_id != shift.id  # Different handover
                ).order_by(ShiftKeyPoint.id.desc()).first()  # Get the most recent one
                
                if existing_kp_other_shift:
                    # Found existing open/in-progress key point from another shift
                    # 🔧 NEW BEHAVIOR: Create a copy for this shift instead of updating the old one
                    # This ensures each handover report shows exactly what was submitted
                    print(f"📋 CARRYFORWARD KEY POINT from shift {existing_kp_other_shift.shift_id}: '{description[:50]}...' (ID: {existing_kp_other_shift.id})")
                    
                    # If status is being changed to Closed, also close the original
                    if status == 'Closed' and existing_kp_other_shift.status != 'Closed':
                        print(f"🔒 Also closing original key point ID {existing_kp_other_shift.id}")
                        existing_kp_other_shift.status = 'Closed'
                        db.session.add(existing_kp_other_shift)
                    
                    # Create a new copy for this shift - DON'T skip, fall through to create new
                
                # No existing key point found, create a new one
                print(f"🆕 CREATING NEW KEY POINT: '{description[:50]}...' with status '{status}'")
                print(f"🔧 DEBUG responsible_id value: '{responsible_id}' (type: {type(responsible_id)})")
                responsible_engineer_id = None
                if responsible_id:
                    if str(responsible_id).isdigit():
                        responsible_engineer_id = int(responsible_id)
                        print(f"🔧 DEBUG: Converted responsible_id to integer: {responsible_engineer_id}")
                    else:
                        user = TeamMember.query.filter_by(name=responsible_id).first()
                        if user:
                            responsible_engineer_id = user.id
                            print(f"🔧 DEBUG: Found user by name '{responsible_id}' -> ID: {responsible_engineer_id}")
                        else:
                            print(f"🔧 DEBUG: Could not find user by name '{responsible_id}'")
                else:
                    print(f"🔧 DEBUG: responsible_id is empty/None, no assignment")
                
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
                        team_id=team_id,
                        created_by_id=current_user.id  # Track who created the key point
                    )
                    db.session.add(new_kp)
                    print(f"🆕 SUCCESSFULLY CREATED NEW KEY POINT: ID will be assigned after commit, shift_id={shift_id_to_use}, created_by={current_user.id}")
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
                                team_id=team_id,
                                created_by_id=current_user.id  # Track who created the key point
                            )
                            db.session.add(new_kp)
                            print(f"[EMERGENCY] Created key point with fallback shift {latest_shift.id}, created_by={current_user.id}")
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
        
        # Add the deferred audit log from incident processing
        if 'audit_log' in locals():
            db.session.add(audit_log)
        
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
            
            # 🔧 NOTIFICATION PROCESSING COMPLETELY DISABLED
            print(f"[NOTIFICATION] ⚠️ NOTIFICATION SERVICE DISABLED - Skipping notification processing for shift {shift.id}")
            print(f"[NOTIFICATION] ✅ Handover data saved successfully - proceeding directly to email processing")
            
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
                print(f"[DEBUG] 📧 About to send handover email for shift_id={shift.id}")
                from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
                
                # Capture the Flask app context for use in threads
                app_context = current_app._get_current_object()
                
                def send_email_with_timeout():
                    """Send email in a separate thread with Flask app context"""
                    try:
                        print(f"[EMAIL] 🚀 Starting email sending for shift_id={shift.id}")
                        with app_context.app_context():
                            send_handover_email(shift)
                        print(f"[EMAIL] ✅ Email sending completed successfully for shift_id={shift.id}")
                        return True
                    except Exception as e:
                        print(f"[EMAIL] ❌ Error sending email: {e}")
                        import traceback
                        print(f"[EMAIL] 🔍 Full error traceback:")
                        traceback.print_exc()
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
        
        # 🚨 TEMPORARY DEBUG: Show results instead of redirecting
        if request.form.get('debug_mode') == 'true':
            print("[DEBUG] Debug mode enabled - showing results instead of redirecting")
            incidents_for_shift = Incident.query.filter_by(shift_id=shift.id).all()
            return f"""
            <html><body style="font-family: monospace; background: #f0f0f0; padding: 20px;">
            <h2>🔍 HANDOVER DEBUG RESULTS</h2>
            <p><strong>Shift ID:</strong> {shift.id}</p>
            <p><strong>Status:</strong> {shift.status}</p>
            <p><strong>Database Totals:</strong> {Shift.query.count()} shifts, {Incident.query.count()} incidents</p>
            <p><strong>Incidents for this shift:</strong> {len(incidents_for_shift)}</p>
            <h3>All incidents for shift {shift.id}:</h3>
            <ul>
            {''.join([f'<li><strong>{inc.incident_type}:</strong> {inc.title} (Priority: {inc.priority}, App: {inc.app_name})</li>' for inc in incidents_for_shift])}
            </ul>
            <p><strong>Change Info:</strong> {len(ShiftChangeInfo.query.filter_by(shift_id=shift.id).all())} entries</p>
            <p><strong>KB Updates:</strong> {len(ShiftKBUpdate.query.filter_by(shift_id=shift.id).all())} entries</p>
            <a href="/handover-reports">Go to Reports</a>
            </body></html>
            """
        
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
    # Get engineers for current shift (always use the default date)
    current_engineers_objs = get_engineers_for_shift(default_date, shift_map[current_shift_type])
    print(f"[SHIFT GET FIX] Current shift ({current_shift_type}) engineers from date: {default_date}")
    
    # Get engineers for next shift
    # For Night->Morning transitions, Morning engineers should come from next day
    if current_shift_type == 'Night' and next_shift_type == 'Morning':
        next_date = default_date + timedelta(days=1)
        next_engineers_objs = get_engineers_for_shift(next_date, shift_map[next_shift_type])
        print(f"[SHIFT GET FIX] Night->Morning transition: Next shift ({next_shift_type}) engineers from date: {next_date}")
    else:
        next_engineers_objs = get_engineers_for_shift(default_date, shift_map[next_shift_type])
        print(f"[SHIFT GET FIX] Regular transition: Next shift ({next_shift_type}) engineers from date: {default_date}")
    current_engineers = [m.name for m in current_engineers_objs]
    next_engineers = [m.name for m in next_engineers_objs]
    # 🔧 FIX: Load ALL open key points globally for pre-population (like dashboard)
    # Don't filter by specific shifts - key points should persist until closed
    # Use default_team_id for multi-team support
    query_team_id = default_team_id if default_team_id else current_user.team_id
    print(f"[DEBUG] Loading all open key points globally for account {current_user.account_id}, team {query_team_id}")
    
    # 🔧 ENHANCED KEY POINT FILTERING: Exclude key points from submitted handovers that were closed
    # Get all key points, then filter more intelligently
    all_kps_query = ShiftKeyPoint.query.filter(
        ShiftKeyPoint.account_id == current_user.account_id,
        ShiftKeyPoint.team_id == query_team_id
    ).order_by(ShiftKeyPoint.id.desc())
    
    print(f"[DEBUG] Total key points in database: {all_kps_query.count()}")
    
    # Filter to only Open/In Progress status
    all_prev_kps = all_kps_query.filter(
        ShiftKeyPoint.status.in_(['Open', 'In Progress'])
    ).all()  # Get all open/in-progress key points (removed arbitrary limit)
    
    print(f"[DEBUG] Open/In Progress key points: {len(all_prev_kps)}")
    
    # Additional check: exclude key points from shifts that have been submitted with 'Closed' status
    filtered_kps = []
    for kp in all_prev_kps:
        # Check if this key point's shift was submitted and this key point was marked closed
        shift = Shift.query.get(kp.shift_id)
        if shift and shift.status == 'sent':
            # This is from a submitted handover - check if there's a newer version that closed this key point
            newer_closed = ShiftKeyPoint.query.filter(
                ShiftKeyPoint.description == kp.description,
                ShiftKeyPoint.jira_id == kp.jira_id,
                ShiftKeyPoint.status == 'Closed',
                ShiftKeyPoint.id > kp.id
            ).first()
            if newer_closed:
                print(f"[DEBUG] Excluding key point ID {kp.id} - found newer closed version ID {newer_closed.id}")
                continue
        filtered_kps.append(kp)
    
    all_prev_kps = filtered_kps
    print(f"[DEBUG] After submission filtering: {len(all_prev_kps)} key points remain")
    
    print(f"[DEBUG] Found {len(all_prev_kps)} total open/in-progress key points globally")
    
    # Debug: show what we're working with before deduplication
    print("[DEBUG] Key points before deduplication:")
    for kp in all_prev_kps:
        print(f"   ID {kp.id}: '{kp.description[:40]}...' | JIRA: {repr(kp.jira_id)} | Status: {kp.status}")
    
    # Deduplicate: keep only the latest (by id) for each (description, normalized_jira_id) pair
    kp_map = {}
    for kp in all_prev_kps:
        if kp.status == 'Closed':
            continue
        # Normalize JIRA ID: treat None, NULL, empty string, and 'None' as equivalent
        normalized_jira = kp.jira_id if kp.jira_id and kp.jira_id.lower() not in ['none', 'null', ''] else None
        key = (kp.description, normalized_jira)
        if key not in kp_map or kp.id > kp_map[key].id:
            kp_map[key] = kp
    open_key_points = list(kp_map.values())
    
    print(f"[DEBUG] After deduplication: {len(open_key_points)} unique key points")
    for kp in open_key_points:
        print(f"   ID {kp.id}: '{kp.description[:40]}...' | JIRA: {repr(kp.jira_id)} | Status: {kp.status}")
    
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

    # 🆕 CARRYFORWARD: Load Change Requests that haven't reached their scheduled date
    print(f"[DEBUG] Loading change requests for carryforward (account {current_user.account_id}, team {query_team_id})")
    
    # Get change requests from recent shifts (last 30 days) where change_datetime is in the future
    recent_date_for_changes = datetime.now().date() - timedelta(days=30)
    recent_shifts_for_changes = Shift.query.filter(
        Shift.date >= recent_date_for_changes,
        Shift.account_id == current_user.account_id,
        Shift.team_id == query_team_id
    ).all()
    recent_shift_ids_for_changes = [s.id for s in recent_shifts_for_changes] if recent_shifts_for_changes else []
    
    carryforward_change_infos = []
    if recent_shift_ids_for_changes:
        current_datetime = datetime.now()
        
        # 🔧 FIX: Show all pending/in-progress changes (not just future ones)
        # User might want to carry forward changes that are still being tracked
        raw_change_infos = ShiftChangeInfo.query.filter(
            ShiftChangeInfo.account_id == current_user.account_id,
            ShiftChangeInfo.team_id == query_team_id,
            ShiftChangeInfo.shift_id.in_(recent_shift_ids_for_changes),
            ~ShiftChangeInfo.status.in_(['Completed', 'Cancelled', 'Implemented'])  # Exclude completed/cancelled/implemented
        ).order_by(ShiftChangeInfo.id.desc()).all()
        
        print(f"[DEBUG] Found {len(raw_change_infos)} pending/in-progress change requests to carry forward")
        
        # Debug each change before deduplication
        for i, change in enumerate(raw_change_infos):
            print(f"[DEBUG]   Change {i+1}: {change.change_number} - {change.app_name} (Status: {change.status}, DateTime: {change.change_datetime})")
        
        # Deduplicate by change_number - keep most recent version of each unique change
        change_map = {}
        for change in raw_change_infos:
            change_key = change.change_number.strip().lower() if change.change_number else ''
            if change_key and (change_key not in change_map or change.id > change_map[change_key].id):
                change_map[change_key] = change
                print(f"[DEBUG]     Added/Updated change {change_key}: ID {change.id}")
        
        carryforward_change_infos = list(change_map.values())[:10]  # Limit to 10 changes
        print(f"[DEBUG] After deduplication: {len(carryforward_change_infos)} unique future changes to carry forward")
        
        # Debug final list
        for i, change in enumerate(carryforward_change_infos):
            engineer_name = ''
            if change.responsible_engineer_id:
                engineer = TeamMember.query.get(change.responsible_engineer_id)
                engineer_name = engineer.name if engineer else f"ID:{change.responsible_engineer_id}"
            print(f"[DEBUG]   Final Change {i+1}: {change.change_number} - Engineer: {engineer_name}")

    # Serialize change infos for template (similar to edit_handover function)
    def serialize_change_info_for_template(change_info):
        """Convert Change Info object to dictionary for template"""
        assigned_to_name = ''
        responsible_engineer_id = change_info.responsible_engineer_id
        if change_info.responsible_engineer_id:
            engineer = TeamMember.query.get(change_info.responsible_engineer_id)
            if engineer:
                assigned_to_name = engineer.name
        
        datetime_str = ''
        if change_info.change_datetime:
            datetime_str = change_info.change_datetime.strftime('%Y-%m-%dT%H:%M')
        
        return {
            'app_name': change_info.app_name,
            'change_number': change_info.change_number,
            'description': change_info.description,
            'change_datetime': datetime_str,
            'responsible_person': assigned_to_name,
            'responsible_engineer_id': responsible_engineer_id,  # Add ID for dropdown
            'status': getattr(change_info, 'status', 'New')  # Include status with default
        }

    change_infos = [serialize_change_info_for_template(ci) for ci in carryforward_change_infos]

    # 🆕 CARRYFORWARD: Load KB Updates that are not yet Published
    print(f"[DEBUG] Loading KB updates for carryforward (account {current_user.account_id}, team {query_team_id})")
    
    # Get KB updates from recent shifts (last 30 days) where status is not "Published"
    carryforward_kb_updates = []
    if recent_shift_ids_for_changes:  # Reuse the same recent shifts
        raw_kb_updates = ShiftKBUpdate.query.filter(
            ShiftKBUpdate.account_id == current_user.account_id,
            ShiftKBUpdate.team_id == query_team_id,
            ShiftKBUpdate.shift_id.in_(recent_shift_ids_for_changes),
            ShiftKBUpdate.status != 'Published'  # Exclude published KB updates
        ).order_by(ShiftKBUpdate.id.desc()).all()
        
        print(f"[DEBUG] Found {len(raw_kb_updates)} unpublished KB updates")
        
        # Debug each KB before deduplication
        for i, kb in enumerate(raw_kb_updates):
            print(f"[DEBUG]   KB {i+1}: {kb.kb_number} - {kb.app_name} (Status: {kb.status})")
        
        # Deduplicate by kb_number OR app_name+description - keep most recent version
        # 🔧 FIX: Allow KB updates without kb_number to be carried forward
        kb_map = {}
        for kb in raw_kb_updates:
            # Use kb_number if available, otherwise use app_name + description hash
            if kb.kb_number and kb.kb_number.strip():
                kb_key = kb.kb_number.strip().lower()
            else:
                kb_key = f"{kb.app_name or ''}_{(kb.description or '')[:50]}".strip().lower()
            
            if kb_key and (kb_key not in kb_map or kb.id > kb_map[kb_key].id):
                kb_map[kb_key] = kb
                print(f"[DEBUG]     Added/Updated KB {kb_key}: ID {kb.id}")
        
        carryforward_kb_updates = list(kb_map.values())[:10]  # Limit to 10 KB updates
        print(f"[DEBUG] After deduplication: {len(carryforward_kb_updates)} unique unpublished KB updates to carry forward")
        
        # Debug final list
        for i, kb in enumerate(carryforward_kb_updates):
            engineer_name = ''
            if kb.responsible_engineer_id:
                engineer = TeamMember.query.get(kb.responsible_engineer_id)
                engineer_name = engineer.name if engineer else f"ID:{kb.responsible_engineer_id}"
            print(f"[DEBUG]   Final KB {i+1}: {kb.kb_number} - Engineer: {engineer_name}")

    # Serialize KB updates for template (similar to edit_handover function)
    def serialize_kb_update_for_template(kb_update):
        """Convert KB Update object to dictionary for template"""
        assigned_to_name = ''
        responsible_engineer_id = kb_update.responsible_engineer_id
        if kb_update.responsible_engineer_id:
            engineer = TeamMember.query.get(kb_update.responsible_engineer_id)
            if engineer:
                assigned_to_name = engineer.name
        
        return {
            'app_name': kb_update.app_name,
            'kb_number': kb_update.kb_number,
            'description': kb_update.description,
            'responsible_person': assigned_to_name,
            'responsible_engineer_id': responsible_engineer_id,  # Add ID for dropdown
            'status': kb_update.status
        }

    kb_updates = [serialize_kb_update_for_template(kb) for kb in carryforward_kb_updates]
    
    print(f"[DEBUG] CARRYFORWARD SUMMARY: {len(open_key_points)} key points, {len(change_infos)} change requests, {len(kb_updates)} KB updates")

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
        escalated_incidents=[],
        change_infos=change_infos,
        kb_updates=kb_updates,
        today=handover_date.strftime('%Y-%m-%d'),  # Use adjusted handover_date instead of default_date
        show_team_error=show_team_error,
        # ServiceNow configuration for template
        assignment_groups_filter=assignment_groups_filter,
        assignment_groups_filtered=assignment_groups_filtered
    )

