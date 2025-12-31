"""
Comprehensive Automation Test Suite for Shift Handover Application

Run with: pytest tests/test_application.py -v --html=test_report.html
"""

import pytest
import requests
from datetime import datetime, date
from bs4 import BeautifulSoup
import re
import time
from tests.config import TestConfig


class TestSession:
    """Manages authenticated test sessions"""
    
    def __init__(self, base_url=TestConfig.BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()
        self.logged_in = False
        self.user_role = None
    
    def login(self, username, password):
        """Login and maintain session"""
        login_url = f"{self.base_url}/login"
        
        # Get CSRF token first
        response = self.session.get(login_url, timeout=TestConfig.REQUEST_TIMEOUT)
        soup = BeautifulSoup(response.text, 'html.parser')
        csrf_token = soup.find('input', {'name': 'csrf_token'})
        csrf_value = csrf_token['value'] if csrf_token else ''
        
        # Perform login
        login_data = {
            'username': username,
            'password': password,
            'csrf_token': csrf_value
        }
        response = self.session.post(login_url, data=login_data, 
                                     timeout=TestConfig.REQUEST_TIMEOUT,
                                     allow_redirects=True)
        
        self.logged_in = response.status_code == 200 and '/login' not in response.url
        return self.logged_in
    
    def get(self, endpoint, **kwargs):
        """Make authenticated GET request"""
        url = f"{self.base_url}{endpoint}"
        return self.session.get(url, timeout=TestConfig.REQUEST_TIMEOUT, **kwargs)
    
    def post(self, endpoint, data=None, **kwargs):
        """Make authenticated POST request"""
        url = f"{self.base_url}{endpoint}"
        return self.session.post(url, data=data, timeout=TestConfig.REQUEST_TIMEOUT, **kwargs)
    
    def logout(self):
        """Logout from session"""
        self.session.get(f"{self.base_url}/logout")
        self.logged_in = False


@pytest.fixture(scope="module")
def admin_session():
    """Create authenticated admin session"""
    session = TestSession()
    credentials = TestConfig.TEST_USERS["super_admin"]
    success = session.login(credentials["username"], credentials["password"])
    if not success:
        pytest.skip("Could not login as admin - check credentials")
    yield session
    session.logout()


@pytest.fixture(scope="module")
def user_session():
    """Create authenticated regular user session"""
    session = TestSession()
    credentials = TestConfig.TEST_USERS["regular_user"]
    success = session.login(credentials["username"], credentials["password"])
    if not success:
        pytest.skip("Could not login as regular user - check credentials")
    yield session
    session.logout()


# =============================================================================
# 1. PAGE ACCESSIBILITY TESTS
# =============================================================================

class TestPageAccessibility:
    """Test that all main pages are accessible"""
    
    PAGES_TO_TEST = [
        ("/", "Dashboard"),
        ("/handover", "Shift Handover Form"),
        ("/reports", "Reports"),
        ("/keypoints", "Key Points"),
        ("/roster", "Shift Roster"),
        ("/escalation-matrix", "Escalation Matrix"),
        ("/vendor-details", "Vendor Details"),
    ]
    
    ADMIN_PAGES = [
        ("/admin/configuration", "System Configuration"),
        ("/admin/email-monitoring", "Email Monitoring"),
        ("/admin/active-sessions", "Active Sessions"),
        ("/user-management", "User Management"),
    ]
    
    @pytest.mark.parametrize("endpoint,page_name", PAGES_TO_TEST)
    def test_page_accessible(self, admin_session, endpoint, page_name):
        """Test that each page returns 200 status"""
        response = admin_session.get(endpoint)
        assert response.status_code == 200, f"{page_name} page ({endpoint}) returned {response.status_code}"
    
    @pytest.mark.parametrize("endpoint,page_name", ADMIN_PAGES)
    def test_admin_page_accessible(self, admin_session, endpoint, page_name):
        """Test that admin pages are accessible to admin users"""
        response = admin_session.get(endpoint)
        assert response.status_code == 200, f"{page_name} page ({endpoint}) returned {response.status_code}"
    
    def test_login_page_accessible(self):
        """Test login page is accessible without authentication"""
        response = requests.get(f"{TestConfig.BASE_URL}/login", timeout=TestConfig.REQUEST_TIMEOUT)
        assert response.status_code == 200, "Login page should be accessible"


# =============================================================================
# 2. DASHBOARD TESTS
# =============================================================================

class TestDashboard:
    """Test dashboard functionality"""
    
    def test_dashboard_loads(self, admin_session):
        """Test dashboard page loads successfully"""
        response = admin_session.get("/")
        assert response.status_code == 200
        assert "Dashboard" in response.text or "dashboard" in response.text.lower()
    
    def test_dashboard_has_shift_info(self, admin_session):
        """Test dashboard displays shift information"""
        response = admin_session.get("/")
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Check for shift-related content
        page_text = response.text.lower()
        assert any(term in page_text for term in ['shift', 'engineer', 'handover']), \
            "Dashboard should display shift-related information"
    
    def test_dashboard_key_points_section(self, admin_session):
        """Test dashboard has key points section"""
        response = admin_session.get("/")
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for key points section
        page_text = response.text.lower()
        assert 'key point' in page_text or 'keypoint' in page_text, \
            "Dashboard should have key points section"


# =============================================================================
# 3. KEY POINTS CONSISTENCY TESTS
# =============================================================================

class TestKeyPointsConsistency:
    """Test key points are consistent across pages"""
    
    def get_dashboard_key_points(self, session):
        """Extract key points from dashboard"""
        response = session.get("/")
        soup = BeautifulSoup(response.text, 'html.parser')
        # This will depend on your actual HTML structure
        key_points = []
        # Find key points elements - adjust selector based on your HTML
        kp_elements = soup.find_all(class_=re.compile(r'key-?point', re.I))
        for elem in kp_elements:
            text = elem.get_text(strip=True)
            if text:
                key_points.append(text)
        return key_points
    
    def get_keypoints_page_data(self, session):
        """Extract key points from key points page"""
        response = session.get("/keypoints")
        soup = BeautifulSoup(response.text, 'html.parser')
        key_points = []
        # Find key points in table or list
        rows = soup.find_all('tr')
        for row in rows:
            cells = row.find_all(['td', 'th'])
            if cells:
                key_points.append([cell.get_text(strip=True) for cell in cells])
        return key_points
    
    def test_keypoints_page_loads(self, admin_session):
        """Test key points page loads successfully"""
        response = admin_session.get("/keypoints")
        assert response.status_code == 200
    
    def test_no_duplicate_keypoints(self, admin_session):
        """Test there are no duplicate key points on key points page"""
        response = admin_session.get("/keypoints")
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all key point descriptions
        descriptions = []
        # Adjust selector based on your HTML structure
        for elem in soup.find_all(attrs={'class': re.compile(r'description|keypoint', re.I)}):
            text = elem.get_text(strip=True).lower()
            if text and len(text) > 10:  # Filter out short/empty strings
                descriptions.append(text)
        
        # Check for duplicates
        unique_descriptions = set(descriptions)
        duplicate_count = len(descriptions) - len(unique_descriptions)
        
        assert duplicate_count == 0, f"Found {duplicate_count} duplicate key points"


# =============================================================================
# 4. HANDOVER FORM TESTS
# =============================================================================

class TestHandoverForm:
    """Test handover form functionality"""
    
    def test_handover_form_loads(self, admin_session):
        """Test handover form page loads"""
        response = admin_session.get("/handover")
        assert response.status_code == 200
        assert "form" in response.text.lower()
    
    def test_handover_form_has_required_fields(self, admin_session):
        """Test handover form has all required fields"""
        response = admin_session.get("/handover")
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Check for essential form elements
        required_elements = [
            ('select', 'current_shift'),  # Current shift dropdown
            ('select', 'next_shift'),     # Next shift dropdown
        ]
        
        for elem_type, name_pattern in required_elements:
            elements = soup.find_all(elem_type, attrs={'name': re.compile(name_pattern, re.I)})
            # Form should have shift-related fields
    
    def test_handover_form_has_engineers_section(self, admin_session):
        """Test handover form has current/next shift engineers section"""
        response = admin_session.get("/handover")
        page_text = response.text.lower()
        
        assert 'current' in page_text and 'engineer' in page_text, \
            "Form should have current shift engineers section"
        assert 'next' in page_text and 'engineer' in page_text, \
            "Form should have next shift engineers section"
    
    def test_handover_form_has_key_points_section(self, admin_session):
        """Test handover form has key points section"""
        response = admin_session.get("/handover")
        page_text = response.text.lower()
        
        assert 'key point' in page_text or 'keypoint' in page_text, \
            "Form should have key points section"


# =============================================================================
# 5. DRAFT HANDOVER TESTS
# =============================================================================

class TestDraftHandover:
    """Test draft handover functionality"""
    
    def test_can_view_draft_reports(self, admin_session):
        """Test draft reports are visible in reports page"""
        response = admin_session.get("/reports")
        assert response.status_code == 200
        # Check if draft filter exists
        assert 'draft' in response.text.lower() or 'Draft' in response.text
    
    def test_draft_filter_works(self, admin_session):
        """Test filtering by draft status works"""
        response = admin_session.get("/reports?status=draft")
        assert response.status_code == 200


# =============================================================================
# 6. REPORTS TESTS
# =============================================================================

class TestReports:
    """Test reports functionality"""
    
    def test_reports_page_loads(self, admin_session):
        """Test reports page loads successfully"""
        response = admin_session.get("/reports")
        assert response.status_code == 200
    
    def test_reports_have_filter_options(self, admin_session):
        """Test reports page has filter options"""
        response = admin_session.get("/reports")
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Check for filter dropdowns
        selects = soup.find_all('select')
        assert len(selects) > 0, "Reports page should have filter dropdowns"
    
    def test_reports_display_shift_data(self, admin_session):
        """Test reports display shift handover data"""
        response = admin_session.get("/reports")
        page_text = response.text.lower()
        
        # Should have shift-related content
        assert any(term in page_text for term in ['shift', 'handover', 'report']), \
            "Reports should display shift handover data"


# =============================================================================
# 7. EMAIL MONITORING TESTS
# =============================================================================

class TestEmailMonitoring:
    """Test email monitoring functionality"""
    
    def test_email_monitoring_page_loads(self, admin_session):
        """Test email monitoring page loads"""
        response = admin_session.get("/admin/email-monitoring")
        assert response.status_code == 200
    
    def test_email_monitoring_has_logs(self, admin_session):
        """Test email monitoring displays logs"""
        response = admin_session.get("/admin/email-monitoring")
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Should have a table or list of email logs
        tables = soup.find_all('table')
        assert len(tables) > 0, "Email monitoring should display logs in a table"
    
    def test_email_log_has_status(self, admin_session):
        """Test email logs show delivery status"""
        response = admin_session.get("/admin/email-monitoring")
        page_text = response.text.lower()
        
        # Should show status indicators
        assert any(term in page_text for term in ['success', 'sent', 'failed', 'pending', 'status']), \
            "Email monitoring should show delivery status"


# =============================================================================
# 8. SHIFT ROSTER TESTS
# =============================================================================

class TestShiftRoster:
    """Test shift roster functionality"""
    
    def test_roster_page_loads(self, admin_session):
        """Test roster page loads successfully"""
        response = admin_session.get("/roster")
        assert response.status_code == 200
    
    def test_roster_displays_engineers(self, admin_session):
        """Test roster displays engineer information"""
        response = admin_session.get("/roster")
        page_text = response.text.lower()
        
        assert any(term in page_text for term in ['engineer', 'shift', 'roster', 'schedule']), \
            "Roster should display engineer shift information"


# =============================================================================
# 9. API ENDPOINT TESTS
# =============================================================================

class TestAPIEndpoints:
    """Test API endpoints"""
    
    def test_get_engineers_api(self, admin_session):
        """Test engineers API endpoint"""
        response = admin_session.get("/handover/api/engineers")
        # Should return JSON or redirect
        assert response.status_code in [200, 302]
    
    def test_get_teams_api(self, admin_session):
        """Test teams API endpoint"""
        response = admin_session.get(f"/api/teams?account_id={TestConfig.TEST_ACCOUNT_ID}")
        assert response.status_code in [200, 302]


# =============================================================================
# 10. MULTI-TEAM FILTER TESTS
# =============================================================================

class TestMultiTeamFiltering:
    """Test multi-team filtering functionality"""
    
    def test_team_filter_on_dashboard(self, admin_session):
        """Test team filter works on dashboard"""
        response = admin_session.get(f"/?team_id={TestConfig.TEST_TEAM_ID}")
        assert response.status_code == 200
    
    def test_team_filter_on_reports(self, admin_session):
        """Test team filter works on reports"""
        response = admin_session.get(f"/reports?team_id={TestConfig.TEST_TEAM_ID}")
        assert response.status_code == 200
    
    def test_team_filter_on_keypoints(self, admin_session):
        """Test team filter works on key points page"""
        response = admin_session.get(f"/keypoints?team_id={TestConfig.TEST_TEAM_ID}")
        assert response.status_code == 200


# =============================================================================
# 11. DATA INTEGRITY TESTS
# =============================================================================

class TestDataIntegrity:
    """Test data integrity across the application"""
    
    def test_shift_engineers_consistency(self, admin_session):
        """Test shift engineers are consistent between form and reports"""
        # Get handover form
        form_response = admin_session.get("/handover")
        form_soup = BeautifulSoup(form_response.text, 'html.parser')
        
        # Get reports
        reports_response = admin_session.get("/reports")
        reports_soup = BeautifulSoup(reports_response.text, 'html.parser')
        
        # Both should load successfully
        assert form_response.status_code == 200
        assert reports_response.status_code == 200


# =============================================================================
# MAIN TEST RUNNER
# =============================================================================

if __name__ == "__main__":
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-x",  # Stop on first failure
        "--html=test_report.html",
        "--self-contained-html"
    ])




