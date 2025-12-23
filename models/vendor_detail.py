from models.models import db
from datetime import datetime


class VendorDetail(db.Model):
    """Model for storing SC Vendor details."""
    __tablename__ = 'vendor_detail'
    
    id = db.Column(db.Integer, primary_key=True)
    application = db.Column(db.String(256), nullable=False)
    sme_app_admin = db.Column(db.Text, nullable=True)
    epam_sme = db.Column(db.String(128), nullable=True)
    vendor_details_received = db.Column(db.String(32), nullable=True)
    email_sent = db.Column(db.String(32), nullable=True)
    it_application_owner = db.Column(db.String(256), nullable=True)
    vendor_name = db.Column(db.String(256), nullable=True)
    vendor_support_3rd_party = db.Column(db.String(32), nullable=True)
    product_under_vendor_support = db.Column(db.String(32), nullable=True)
    vendor_email = db.Column(db.Text, nullable=True)
    hotline_contact = db.Column(db.Text, nullable=True)
    vendor_department = db.Column(db.String(256), nullable=True)
    vendor_availability = db.Column(db.Text, nullable=True)
    company_site_account_id = db.Column(db.Text, nullable=True)
    ctc_poc = db.Column(db.Text, nullable=True)
    vendor_website = db.Column(db.Text, nullable=True)
    vendor_escalation_poc = db.Column(db.Text, nullable=True)
    vendor_site_access = db.Column(db.Text, nullable=True)
    meeting_invite_method = db.Column(db.Text, nullable=True)
    
    # Account and Team association for multi-tenant support
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=True)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=True)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    account = db.relationship('Account', backref='vendor_details', lazy=True, foreign_keys=[account_id])
    team = db.relationship('Team', backref='vendor_details', lazy=True, foreign_keys=[team_id])

    def to_dict(self):
        return {
            'id': self.id,
            'application': self.application,
            'sme_app_admin': self.sme_app_admin,
            'epam_sme': self.epam_sme,
            'vendor_details_received': self.vendor_details_received,
            'email_sent': self.email_sent,
            'it_application_owner': self.it_application_owner,
            'vendor_name': self.vendor_name,
            'vendor_support_3rd_party': self.vendor_support_3rd_party,
            'product_under_vendor_support': self.product_under_vendor_support,
            'vendor_email': self.vendor_email,
            'hotline_contact': self.hotline_contact,
            'vendor_department': self.vendor_department,
            'vendor_availability': self.vendor_availability,
            'company_site_account_id': self.company_site_account_id,
            'ctc_poc': self.ctc_poc,
            'vendor_website': self.vendor_website,
            'vendor_escalation_poc': self.vendor_escalation_poc,
            'vendor_site_access': self.vendor_site_access,
            'meeting_invite_method': self.meeting_invite_method,
            'account_id': self.account_id,
            'team_id': self.team_id,
            'is_active': self.is_active,
        }
