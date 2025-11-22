
import logging
from flask import session, send_from_directory
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
import pandas as pd
from werkzeug.utils import secure_filename
import os
from functools import wraps
from models.models import db, TeamMember, ShiftRoster, Account, Team

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

roster_upload_bp = Blueprint('roster_upload', __name__)

UPLOAD_FOLDER = 'uploads/roster'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {'xlsx'}

def admin_required(f):
    """Decorator to check if user has admin privileges (super_admin, account_admin, or team_admin)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in ['super_admin', 'account_admin', 'team_admin']:
            flash('Access denied. Administrator privileges required.', 'error')
            return redirect(url_for('dashboard.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@roster_upload_bp.route('/roster-upload', methods=['GET', 'POST'])
@login_required
@admin_required
def roster_upload():
    table_data = None
    if request.method == 'POST':
        try:
            logger.info(f"[UPLOAD] user={getattr(current_user, 'username', None)}, role={getattr(current_user, 'role', None)}")
            
            # Check user permissions
            if current_user.role not in ['super_admin', 'account_admin', 'team_admin']:
                flash('You do not have permission to upload shift roster.')
                logger.warning('Permission denied for upload.')
                return redirect(url_for('roster_upload.roster_upload'))

            # Ensure account_id and team_id are set based on user role
            account_id = None
            team_id = None
            
            if current_user.role == 'super_admin':
                # Super admin needs to select account and team
                account_id = request.form.get('account_id')
                team_id = request.form.get('team_id')
                if not account_id or not team_id:
                    flash('Please select both Account and Team before uploading.')
                    return redirect(url_for('roster_upload.roster_upload'))
            elif current_user.role == 'account_admin':
                # Account admin can only upload for their account
                account_id = current_user.account_id
                team_id = request.form.get('team_id')
                if not team_id:
                    flash('Please select a Team before uploading.')
                    return redirect(url_for('roster_upload.roster_upload'))
            elif current_user.role == 'team_admin':
                # Team admin can only upload for their team
                account_id = current_user.account_id
                team_id = current_user.team_id

            # Handle file upload
            file = request.files.get('file')
            if not file or file.filename == '':
                flash('No file selected.')
                return redirect(url_for('roster_upload.roster_upload'))
            if not ('.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS):
                flash('Invalid file type. Only XLSX files are allowed.')
                return redirect(url_for('roster_upload.roster_upload'))
            filename = secure_filename(file.filename)
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)

            # Parse XLSX
            try:
                df = pd.read_excel(filepath)
            except Exception as e:
                flash(f'Error reading Excel file: {e}')
                return redirect(url_for('roster_upload.roster_upload'))

            # Support wide format: first column is 'Member Name', rest are dates
            # Normalize all column headers to string and strip whitespace
            df.columns = [str(col).strip() for col in df.columns]
            member_name_col = next((c for c in df.columns if c.lower() == 'member name'.lower()), None)
            if member_name_col:
                long_df = df.melt(id_vars=[member_name_col], var_name='Date', value_name='Shift')
                long_df = long_df.rename(columns={member_name_col: 'Team Member'})
                # Drop rows with missing Team Member, Date, or Shift
                long_df = long_df.dropna(subset=['Team Member', 'Date', 'Shift'])
                # Fix datetime parsing with robust error handling
                try:
                    long_df['Date'] = pd.to_datetime(long_df['Date'], errors='coerce')
                except Exception as e:
                    # Try different datetime formats
                    try:
                        long_df['Date'] = pd.to_datetime(long_df['Date'], format='mixed', errors='coerce')
                    except Exception:
                        # Last resort: parse each date individually
                        def safe_parse_date(date_val):
                            try:
                                if pd.isna(date_val):
                                    return None
                                # Convert to string and remove microseconds if present
                                date_str = str(date_val)
                                if '.' in date_str and date_str.count('.') == 1:
                                    date_str = date_str.split('.')[0]
                                return pd.to_datetime(date_str, errors='coerce')
                            except:
                                return None
                        long_df['Date'] = long_df['Date'].apply(safe_parse_date)
                # Remove rows where date parsing failed
                long_df = long_df.dropna(subset=['Date'])
                df = long_df[['Date', 'Shift', 'Team Member']]

            # Validate columns
            required_cols = {'Date', 'Shift', 'Team Member'}
            df.columns = [str(col).strip() for col in df.columns]
            if not required_cols.issubset(set(df.columns)):
                flash(f'Missing required columns. Found: {[str(c) for c in df.columns]}')
                # Debug: show all column types
                flash(f'Column types: {[type(c) for c in df.columns]}')
                return redirect(url_for('roster_upload.roster_upload'))

            # Validate that account_id and team_id are properly set
            if not account_id:
                flash('Error: No account selected. Please select an account before uploading roster.')
                return redirect(url_for('roster_upload.roster_upload'))
            
            if not team_id:
                flash('Error: No team selected. Please select a team before uploading roster.')
                return redirect(url_for('roster_upload.roster_upload'))

            # Determine month/year from first row
            # Fix datetime parsing with robust error handling
            try:
                df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            except Exception as e:
                # Try different datetime formats
                try:
                    df['Date'] = pd.to_datetime(df['Date'], format='mixed', errors='coerce')
                except Exception:
                    # Last resort: parse each date individually
                    def safe_parse_date(date_val):
                        try:
                            if pd.isna(date_val):
                                return None
                            # Convert to string and remove microseconds if present
                            date_str = str(date_val)
                            if '.' in date_str and date_str.count('.') == 1:
                                date_str = date_str.split('.')[0]
                            return pd.to_datetime(date_str, errors='coerce')
                        except:
                            return None
                    df['Date'] = df['Date'].apply(safe_parse_date)
            # Remove rows where date parsing failed
            df = df.dropna(subset=['Date'])
            if df.empty:
                flash('Error: No valid dates found in the file. Please check the date format.')
                return redirect(url_for('roster_upload.roster_upload'))
            month = df['Date'].dt.month.iloc[0]
            year = df['Date'].dt.year.iloc[0]

            # Enhancement: For same month, override roster for existing members, add new members, avoid duplicates
            inserted = 0
            skipped = 0
            auto_linked_count = 0  # Track automatic user-teammember links
            for _, row in df.iterrows():
                member_name = row['Team Member']
                date = row['Date']
                shift_code = row['Shift']
                if pd.isna(member_name) or pd.isna(date) or pd.isna(shift_code):
                    skipped += 1
                    continue
                # Robust date conversion
                try:
                    if hasattr(date, 'date'):
                        date = date.date()
                    else:
                        date = pd.to_datetime(date, errors='coerce').date()
                except Exception as e:
                    logger.warning(f"Failed to parse date {date}: {e}")
                    skipped += 1
                    continue
                member_name = str(member_name).strip()
                shift_code = str(shift_code).strip()
                if not member_name or not shift_code:
                    skipped += 1
                    continue
                norm_name = member_name.strip().lower()
                member = TeamMember.query.filter(
                    db.func.lower(db.func.trim(TeamMember.name)) == norm_name,
                    TeamMember.account_id == account_id,
                    TeamMember.team_id == team_id
                ).first()
                if not member:
                    member = TeamMember.query.filter(
                        TeamMember.name.ilike(f"%{member_name.strip()}%"),
                        TeamMember.account_id == account_id,
                        TeamMember.team_id == team_id
                    ).first()
                if not member:
                    # New member: create in team details
                    member = TeamMember(
                        name=member_name.strip(),
                        email=f"{member_name.strip().replace(' ', '_').lower()}@example.com",
                        contact_number="N/A",
                        role="AutoImported",
                        account_id=account_id,
                        team_id=team_id
                    )
                    db.session.add(member)
                    db.session.flush()  # Get member.id
                    
                    # Enhanced: Try to automatically link to existing User
                    try:
                        import sys
                        sys.path.append('/app')
                        from user_linking_service import UserTeamMemberLinkingService
                        from models.models import User
                        
                        # Look for users that might match this team member
                        # Check by name similarity and account matching
                        potential_users = User.query.filter(
                            User.account_id == account_id
                        ).all()
                        
                        best_user = None
                        best_confidence = 0
                        
                        for user in potential_users:
                            # Skip if user is already linked to another team member
                            existing_link = TeamMember.query.filter_by(user_id=user.id).first()
                            if existing_link:
                                continue
                            
                            confidence = 0
                            
                            # Check username match
                            if user.username:
                                username_similarity = UserTeamMemberLinkingService.similarity_score(
                                    user.username, member_name
                                )
                                confidence = max(confidence, username_similarity)
                            
                            # Check full name match if available
                            if hasattr(user, 'first_name') and hasattr(user, 'last_name'):
                                full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
                                if full_name:
                                    name_similarity = UserTeamMemberLinkingService.similarity_score(
                                        full_name, member_name
                                    )
                                    confidence = max(confidence, name_similarity)
                            
                            # Check email local part similarity
                            if user.email:
                                email_local = user.email.split('@')[0].replace('.', ' ').replace('_', ' ')
                                email_similarity = UserTeamMemberLinkingService.similarity_score(
                                    email_local, member_name
                                )
                                confidence = max(confidence, email_similarity * 0.8)  # Lower weight for email
                            
                            # Update best match if this is better
                            if confidence > best_confidence and confidence >= 70:
                                best_user = user
                                best_confidence = confidence
                        
                        # Link if good match found
                        if best_user:
                            member.user_id = best_user.id
                            
                            # Update user's team info if not set
                            if not best_user.team_id:
                                best_user.team_id = team_id
                            if not best_user.account_id:
                                best_user.account_id = account_id
                            
                            logger.info(f"🔗 ROSTER AUTO-LINK: Linked TeamMember '{member_name}' to User '{best_user.username}' ({best_confidence:.1f}% confidence)")
                            
                            # Track successful links for summary message
                            auto_linked_count += 1
                            
                        else:
                            logger.info(f"⚠️ ROSTER NO-LINK: No suitable User match found for TeamMember '{member_name}' (best confidence was {best_confidence:.1f}%)")
                            
                    except Exception as link_error:
                        logger.error(f"❌ ROSTER LINK ERROR for '{member_name}': {str(link_error)}")
                        # Continue without breaking roster upload
                # For existing members, override roster for same month
                # Delete any existing roster for this member/date/account/team
                db.session.query(ShiftRoster).filter(
                    ShiftRoster.account_id == account_id,
                    ShiftRoster.team_id == team_id,
                    ShiftRoster.team_member_id == member.id,
                    ShiftRoster.date == date
                ).delete()
                entry = ShiftRoster(
                    date=date,
                    shift_code=shift_code,
                    team_member_id=member.id,
                    account_id=account_id,
                    team_id=team_id
                )
                db.session.add(entry)
                inserted += 1
            db.session.commit()
            
            # Enhanced success message with auto-linking info
            success_message = f'Roster uploaded: {inserted} entries added, {skipped} skipped.'
            if auto_linked_count > 0:
                success_message += f' {auto_linked_count} team members automatically linked to existing users.'
            success_message += ' Existing members updated, new members created.'
            flash(success_message)
            # Optionally show table preview
            table_data = df.head(20).to_dict(orient='records')
            columns = df.columns.tolist()
            
            # Get accounts and teams for the template
            accounts = []
            teams = []
            if current_user.role == 'super_admin':
                accounts = Account.query.filter_by(is_active=True).all()
                teams = Team.query.filter_by(is_active=True).all()
            elif current_user.role == 'account_admin':
                accounts = [Account.query.get(current_user.account_id)] if current_user.account_id else []
                teams = Team.query.filter_by(account_id=current_user.account_id, is_active=True).all() if current_user.account_id else []
            else:
                accounts = [Account.query.get(current_user.account_id)] if current_user.account_id else []
                teams = [Team.query.get(current_user.team_id)] if current_user.team_id else []
            
            return render_template('shift_roster_upload.html', table_data=table_data, columns=columns, accounts=accounts, teams=teams)
        except Exception as e:
            logger.error(f"Unexpected error in upload handler: {e}")
            db.session.rollback()
            flash(f"Unexpected error: {e}")
            return redirect(url_for('roster_upload.roster_upload'))
    
    # GET method - show the upload form
    accounts = []
    teams = []
    if current_user.role == 'super_admin':
        accounts = Account.query.filter_by(is_active=True).all()
        teams = Team.query.filter_by(is_active=True).all()
    elif current_user.role == 'account_admin':
        accounts = [Account.query.get(current_user.account_id)] if current_user.account_id else []
        teams = Team.query.filter_by(account_id=current_user.account_id, is_active=True).all() if current_user.account_id else []
    else:
        accounts = [Account.query.get(current_user.account_id)] if current_user.account_id else []
        teams = [Team.query.get(current_user.team_id)] if current_user.team_id else []
    
    return render_template('shift_roster_upload.html', table_data=table_data, accounts=accounts, teams=teams)

@roster_upload_bp.route('/download-wide-format-roster')
@login_required
def download_wide_format_roster():
    """Download the wide format sample shift roster Excel file"""
    try:
        # Debug: Check if file exists
        sample_dir = os.path.join('static', 'samples')
        file_path = os.path.join(sample_dir, 'wide_format_roster_sample.xlsx')
        
        print(f"DEBUG: Looking for file at: {file_path}")
        print(f"DEBUG: File exists: {os.path.exists(file_path)}")
        print(f"DEBUG: Current working directory: {os.getcwd()}")
        
        if not os.path.exists(file_path):
            flash(f'Sample file not found at: {file_path}', 'error')
            return redirect(url_for('roster_upload.roster_upload'))
            
        return send_from_directory(
            sample_dir, 
            'wide_format_roster_sample.xlsx',
            as_attachment=True,
            download_name='wide_format_roster_sample.xlsx'
        )
    except Exception as e:
        flash(f'Error downloading wide format sample file: {e}', 'error')
        print(f"DEBUG: Exception details: {str(e)}")
        return redirect(url_for('roster_upload.roster_upload'))

