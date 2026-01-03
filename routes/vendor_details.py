import os
import logging
import pandas as pd
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from models.vendor_detail import VendorDetail
from models.models import db, Account, Team
from services.team_access_service import TeamAccessService

# Module logger
logger = logging.getLogger(__name__)

bp = Blueprint('vendor_details', __name__)

# Excel file path
VENDOR_EXCEL_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'data', 'SC_Vendor_Details_Master.xlsx')


def load_vendors_from_excel():
    """Load vendor data from Excel file."""
    try:
        if not os.path.exists(VENDOR_EXCEL_FILE):
            return []
        
        df = pd.read_excel(VENDOR_EXCEL_FILE)
        
        # Clean column names (remove newlines and extra spaces)
        df.columns = [col.replace('\n', ' ').strip() for col in df.columns]
        
        # Map Excel columns to our fields
        column_mapping = {
            'Application': 'application',
            'SME App Admin (Kept just for reference, App Admin  Des and Sahrif no longer active in CTC)': 'sme_app_admin',
            'EPAM SME': 'epam_sme',
            'Vendor Details Received & Updated (Yes/No)': 'vendor_details_received',
            'Email Sent (Yes/No)': 'email_sent',
            'IT Application Owner': 'it_application_owner',
            'Vendor Name': 'vendor_name',
            'Vendor Support Through 3rd party (Y/N)': 'vendor_support_3rd_party',
            'Product under Vendor Support(Y/N)': 'product_under_vendor_support',
            'Vendor Email(Generic/Help desk)': 'vendor_email',
            'Hotline Contact Number': 'hotline_contact',
            'Vendor Department': 'vendor_department',
            'Vendor Availability': 'vendor_availability',
            'Company ID/Site ID/Account Number Required by Vendor': 'company_site_account_id',
            'CTC POC to Contact the Vendor': 'ctc_poc',
            'Vendor  Web Site(URL)': 'vendor_website',
            'Vendor Esclation POC': 'vendor_escalation_poc',
            'Vendor site access to EPAM': 'vendor_site_access',
            'How to Share Meeting Invite with Vendor': 'meeting_invite_method',
        }
        
        vendors = []
        for _, row in df.iterrows():
            vendor = {}
            for excel_col, model_field in column_mapping.items():
                if excel_col in df.columns:
                    value = row.get(excel_col, '')
                    vendor[model_field] = str(value) if pd.notna(value) else ''
            vendors.append(vendor)
        
        return vendors
    except Exception as e:
        current_app.logger.error(f"Failed to load vendor data from Excel: {e}")
        return []


def is_admin():
    """Check if current user is an admin."""
    return current_user.role in ['super_admin', 'account_admin']


@bp.route('/vendor-details', methods=['GET'])
@login_required
def vendor_details():
    """Display vendor details page with proper access control."""
    # Build query based on user role
    query = VendorDetail.query.filter_by(is_active=True)
    
    logger.debug(f"🔍 [VENDOR_DETAILS] Route accessed by {current_user.username} (Role: {current_user.role}, Account: {current_user.account_id})")
    
    # Filter based on user role
    if current_user.role == 'super_admin':
        # Super admin can see all vendors - no filtering needed
        logger.debug("[VENDOR_DETAILS] Super admin - showing all vendors")
        pass
    elif current_user.role == 'account_admin':
        # Account admin can ONLY see vendors for their account (all teams in their account)
        # Do NOT show vendors with NULL account_id (those are for super_admin only)
        user_account_id = current_user.account_id
        if user_account_id:
            query = query.filter(VendorDetail.account_id == user_account_id)
            logger.debug(f"[VENDOR_DETAILS] Account admin - filtering by account_id: {user_account_id}")
        else:
            # No account assigned, show nothing
            query = query.filter(db.literal(False))
            logger.warning(f"[VENDOR_DETAILS] Account admin {current_user.username} has no account_id assigned")
    elif current_user.role == 'team_admin':
        # Team admin can only see vendors for their team(s) within their account
        user_account_id = current_user.account_id
        user_team_ids = TeamAccessService.get_user_team_ids()
        
        if user_team_ids and user_account_id:
            # Show vendors for the team admin's teams only
            query = query.filter(
                db.and_(
                    VendorDetail.account_id == user_account_id,
                    db.or_(
                        VendorDetail.team_id.in_(user_team_ids),
                        VendorDetail.team_id.is_(None)  # Account-level vendors (no team)
                    )
                )
            )
            logger.debug(f"[VENDOR_DETAILS] Team admin - filtering by account_id: {user_account_id}, team_ids: {user_team_ids}")
        elif user_account_id:
            # Fallback: filter by account only if no teams assigned
            query = query.filter(VendorDetail.account_id == user_account_id)
            logger.debug(f"[VENDOR_DETAILS] Team admin fallback - filtering by account_id only: {user_account_id}")
        else:
            query = query.filter(db.literal(False))
            logger.warning(f"[VENDOR_DETAILS] Team admin {current_user.username} has no account/team assigned")
    else:
        # Regular users - support multi-team filtering
        user_account_id = current_user.account_id
        user_team_ids = TeamAccessService.get_user_team_ids()
        
        # Check if specific team requested via URL
        filter_team_id = request.args.get('team_id', type=int)
        
        if filter_team_id and filter_team_id in user_team_ids:
            # User selected a specific team - show only that team's vendors
            query = query.filter(
                db.and_(
                    VendorDetail.account_id == user_account_id,
                    db.or_(
                        VendorDetail.team_id == filter_team_id,
                        VendorDetail.team_id.is_(None)  # Account-level vendors
                    )
                )
            )
            logger.debug(f"[VENDOR_DETAILS] Regular user with team filter - team_id: {filter_team_id}")
        elif user_team_ids and user_account_id:
            # Show vendors for all user's teams
            query = query.filter(
                db.and_(
                    VendorDetail.account_id == user_account_id,
                    db.or_(
                        VendorDetail.team_id.in_(user_team_ids),
                        VendorDetail.team_id.is_(None)  # Account-level vendors
                    )
                )
            )
            logger.debug(f"[VENDOR_DETAILS] Regular user - filtering by account_id: {user_account_id}, team_ids: {user_team_ids}")
        elif user_account_id:
            # Fallback: filter by account only if no teams assigned
            query = query.filter(VendorDetail.account_id == user_account_id)
            logger.debug(f"[VENDOR_DETAILS] Regular user fallback - filtering by account_id only: {user_account_id}")
        else:
            query = query.filter(db.literal(False))
            logger.warning(f"[VENDOR_DETAILS] Regular user {current_user.username} has no account assigned")
    
    db_vendors = query.all()
    
    if db_vendors:
        vendors = [v.to_dict() for v in db_vendors]
    else:
        # Auto-import from Excel if database is empty (only for admins)
        if is_admin():
            excel_vendors = load_vendors_from_excel()
            if excel_vendors:
                try:
                    # Get default account for import
                    default_account_id = current_user.account_id if current_user.role == 'account_admin' else None
                    
                    for v in excel_vendors:
                        vendor = VendorDetail(
                            application=v.get('application', ''),
                            sme_app_admin=v.get('sme_app_admin', ''),
                            epam_sme=v.get('epam_sme', ''),
                            vendor_details_received=v.get('vendor_details_received', ''),
                            email_sent=v.get('email_sent', ''),
                            it_application_owner=v.get('it_application_owner', ''),
                            vendor_name=v.get('vendor_name', ''),
                            vendor_support_3rd_party=v.get('vendor_support_3rd_party', ''),
                            product_under_vendor_support=v.get('product_under_vendor_support', ''),
                            vendor_email=v.get('vendor_email', ''),
                            hotline_contact=v.get('hotline_contact', ''),
                            vendor_department=v.get('vendor_department', ''),
                            vendor_availability=v.get('vendor_availability', ''),
                            company_site_account_id=v.get('company_site_account_id', ''),
                            ctc_poc=v.get('ctc_poc', ''),
                            vendor_website=v.get('vendor_website', ''),
                            vendor_escalation_poc=v.get('vendor_escalation_poc', ''),
                            vendor_site_access=v.get('vendor_site_access', ''),
                            meeting_invite_method=v.get('meeting_invite_method', ''),
                            account_id=default_account_id,
                        )
                        db.session.add(vendor)
                    db.session.commit()
                    current_app.logger.info(f"Auto-imported {len(excel_vendors)} vendors from Excel")
                    # Re-fetch from database to get IDs
                    db_vendors = VendorDetail.query.filter_by(is_active=True).all()
                    vendors = [v.to_dict() for v in db_vendors]
                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(f"Auto-import failed: {e}")
                    vendors = []
            else:
                vendors = []
        else:
            vendors = []
    
    # Get unique applications for filter
    applications = sorted(set(v.get('application', '') for v in vendors if v.get('application')))
    
    # Get accounts list for admin filter
    accounts = []
    teams = []
    selected_team_id = request.args.get('team_id', type=int)
    
    if current_user.role == 'super_admin':
        accounts = Account.query.filter_by(is_active=True).order_by(Account.name).all()
        teams = Team.query.filter_by(is_active=True).order_by(Team.name).all()
    elif current_user.role == 'account_admin':
        # Account admin can only see their own account
        if current_user.account_id:
            account = Account.query.get(current_user.account_id)
            if account:
                accounts = [account]
            teams = Team.query.filter_by(account_id=current_user.account_id, is_active=True).order_by(Team.name).all()
    else:
        # Regular user - get their teams using TeamAccessService
        url_team_id = request.args.get('team_id', type=int)
        team_filter_context = TeamAccessService.get_team_filter_context(url_team_id=url_team_id)
        teams = team_filter_context.get('user_teams', [])
        if not selected_team_id:
            selected_team_id = team_filter_context.get('selected_team_id')
    
    return render_template(
        'vendor_details.html',
        vendors=vendors,
        applications=applications,
        accounts=accounts,
        teams=teams,
        selected_team_id=selected_team_id,
        total_vendors=len(vendors),
        is_admin=is_admin()
    )


@bp.route('/api/vendor-details/import', methods=['POST'])
@login_required
def import_vendors():
    """Import vendors from Excel file to database."""
    if not is_admin():
        return jsonify({'error': 'Unauthorized - Admin access required'}), 403
    
    try:
        vendors = load_vendors_from_excel()
        
        if not vendors:
            return jsonify({'error': 'No vendor data found in Excel file'}), 400
        
        # Get account_id from request or use current user's account
        account_id = request.json.get('account_id') if request.json else None
        if not account_id and current_user.role == 'account_admin':
            account_id = current_user.account_id
        
        # Clear existing vendors for this account
        if account_id:
            VendorDetail.query.filter_by(account_id=account_id).delete()
        else:
            # Super admin importing globally - clear all
            VendorDetail.query.delete()
        
        # Import new vendors
        for v in vendors:
            vendor = VendorDetail(
                application=v.get('application', ''),
                sme_app_admin=v.get('sme_app_admin', ''),
                epam_sme=v.get('epam_sme', ''),
                vendor_details_received=v.get('vendor_details_received', ''),
                email_sent=v.get('email_sent', ''),
                it_application_owner=v.get('it_application_owner', ''),
                vendor_name=v.get('vendor_name', ''),
                vendor_support_3rd_party=v.get('vendor_support_3rd_party', ''),
                product_under_vendor_support=v.get('product_under_vendor_support', ''),
                vendor_email=v.get('vendor_email', ''),
                hotline_contact=v.get('hotline_contact', ''),
                vendor_department=v.get('vendor_department', ''),
                vendor_availability=v.get('vendor_availability', ''),
                company_site_account_id=v.get('company_site_account_id', ''),
                ctc_poc=v.get('ctc_poc', ''),
                vendor_website=v.get('vendor_website', ''),
                vendor_escalation_poc=v.get('vendor_escalation_poc', ''),
                vendor_site_access=v.get('vendor_site_access', ''),
                meeting_invite_method=v.get('meeting_invite_method', ''),
                account_id=account_id,
            )
            db.session.add(vendor)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Successfully imported {len(vendors)} vendors',
            'count': len(vendors)
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to import vendors: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/api/vendor-details', methods=['GET'])
@login_required
def get_vendors_api():
    """API endpoint to get vendor data with proper access control."""
    application = request.args.get('application', '')
    search = request.args.get('search', '')
    account_id = request.args.get('account_id', '')
    team_id = request.args.get('team_id', '')
    
    query = VendorDetail.query.filter_by(is_active=True)
    
    # Apply access control based on user role first
    if current_user.role == 'super_admin':
        # Super admin can see all - apply optional filters
        if account_id:
            query = query.filter_by(account_id=int(account_id))
            if team_id:
                query = query.filter_by(team_id=int(team_id))
    elif current_user.role == 'account_admin':
        # Account admin sees ONLY their account's vendors (no NULL account_id)
        if current_user.account_id:
            query = query.filter(VendorDetail.account_id == current_user.account_id)
            if team_id:
                query = query.filter_by(team_id=int(team_id))
        else:
            query = query.filter(db.literal(False))
    elif current_user.role == 'team_admin':
        # Team admin sees vendors for their team(s) only
        from services.team_access_service import TeamAccessService
        user_team_ids = TeamAccessService.get_user_team_ids()
        user_account_id = current_user.account_id
        
        if user_team_ids and user_account_id:
            query = query.filter(
                db.and_(
                    VendorDetail.account_id == user_account_id,
                    db.or_(
                        VendorDetail.team_id.in_(user_team_ids),
                        VendorDetail.team_id.is_(None)
                    )
                )
            )
        else:
            query = query.filter(db.literal(False))
    
    db_vendors = query.all()
    vendors = [v.to_dict() for v in db_vendors]
    
    # Filter by application
    if application:
        vendors = [v for v in vendors if v.get('application', '').lower() == application.lower()]
    
    # Filter by search term
    if search:
        search_lower = search.lower()
        vendors = [
            v for v in vendors 
            if any(search_lower in str(val).lower() for val in v.values())
        ]
    
    return jsonify({'vendors': vendors, 'total': len(vendors)})


@bp.route('/api/vendor-details/<int:id>', methods=['GET'])
@login_required
def get_vendor_detail(id):
    """Get details for a specific vendor by ID."""
    vendor = VendorDetail.query.get_or_404(id)
    return jsonify({'vendor': vendor.to_dict()})


@bp.route('/api/vendor-details', methods=['POST'])
@login_required
def add_vendor():
    """Add a new vendor."""
    if not is_admin():
        return jsonify({'error': 'Unauthorized - Admin access required'}), 403
    
    data = request.json
    
    # Determine account_id and team_id
    account_id = data.get('account_id')
    team_id = data.get('team_id')
    if not account_id and current_user.role == 'account_admin':
        account_id = current_user.account_id
    
    vendor = VendorDetail(
        application=data.get('application', ''),
        vendor_name=data.get('vendor_name', ''),
        epam_sme=data.get('epam_sme', ''),
        it_application_owner=data.get('it_application_owner', ''),
        vendor_email=data.get('vendor_email', ''),
        hotline_contact=data.get('hotline_contact', ''),
        vendor_availability=data.get('vendor_availability', ''),
        vendor_department=data.get('vendor_department', ''),
        ctc_poc=data.get('ctc_poc', ''),
        vendor_website=data.get('vendor_website', ''),
        vendor_escalation_poc=data.get('vendor_escalation_poc', ''),
        company_site_account_id=data.get('company_site_account_id', ''),
        vendor_support_3rd_party=data.get('vendor_support_3rd_party', ''),
        product_under_vendor_support=data.get('product_under_vendor_support', ''),
        vendor_site_access=data.get('vendor_site_access', ''),
        meeting_invite_method=data.get('meeting_invite_method', ''),
        account_id=account_id,
        team_id=team_id,
    )
    db.session.add(vendor)
    db.session.commit()
    return jsonify({'id': vendor.id, 'success': True})


@bp.route('/api/vendor-details/<int:id>', methods=['PUT'])
@login_required
def edit_vendor(id):
    """Update a vendor."""
    if not is_admin():
        return jsonify({'error': 'Unauthorized - Admin access required'}), 403
    
    vendor = VendorDetail.query.get_or_404(id)
    data = request.json
    
    # All editable fields
    editable_fields = [
        'application', 'vendor_name', 'epam_sme', 'it_application_owner', 
        'vendor_email', 'hotline_contact', 'vendor_availability', 
        'vendor_department', 'ctc_poc', 'vendor_website', 'vendor_escalation_poc',
        'company_site_account_id', 'vendor_support_3rd_party', 
        'product_under_vendor_support', 'vendor_site_access', 'meeting_invite_method',
        'sme_app_admin', 'vendor_details_received', 'email_sent', 'account_id', 'team_id'
    ]
    
    for field in editable_fields:
        if field in data:
            setattr(vendor, field, data[field])
    
    db.session.commit()
    return jsonify({'success': True})


@bp.route('/api/vendor-details/<int:id>', methods=['DELETE'])
@login_required
def delete_vendor(id):
    """Delete a vendor (soft delete)."""
    if not is_admin():
        return jsonify({'error': 'Unauthorized - Admin access required'}), 403
    
    vendor = VendorDetail.query.get_or_404(id)
    vendor.is_active = False
    db.session.commit()
    return jsonify({'success': True})
