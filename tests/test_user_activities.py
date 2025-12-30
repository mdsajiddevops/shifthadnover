#!/usr/bin/env python3
"""
User Activities Test Suite

Tests all functionality accessible to regular users:
- Dashboard
- Handover Form (create, draft, edit, submit)
- Reports
- Key Points
- Shift Roster
- Escalation Matrix
- Vendor Details

Run with: python tests/test_user_activities.py
"""

import requests
from bs4 import BeautifulSoup
import argparse
import sys
import io
import re
from datetime import datetime, date

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


class UserActivityTests:
    """Tests for regular user activities"""
    
    def __init__(self, base_url, username, password, verbose=False):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.verbose = verbose
        self.session = requests.Session()
        self.results = []
        self.passed = 0
        self.failed = 0
        self.skipped = 0
    
    def log(self, message, color=None):
        if color:
            print(f"{color}{message}{Colors.RESET}")
        else:
            print(message)
    
    def log_verbose(self, message):
        if self.verbose:
            print(f"  {Colors.BLUE}→ {message}{Colors.RESET}")
    
    def test(self, name, condition, message=""):
        if condition:
            self.log(f"  ✅ {name}", Colors.GREEN)
            self.passed += 1
            self.results.append(("PASS", name, message))
            return True
        else:
            self.log(f"  ❌ {name}: {message}", Colors.RED)
            self.failed += 1
            self.results.append(("FAIL", name, message))
            return False
    
    def skip(self, name, reason):
        self.log(f"  ⏭️  {name}: {reason}", Colors.YELLOW)
        self.skipped += 1
        self.results.append(("SKIP", name, reason))
    
    def get_csrf_token(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        csrf_input = soup.find('input', {'name': 'csrf_token'})
        if not csrf_input:
            csrf_input = soup.find('input', {'name': re.compile(r'csrf', re.I)})
        return csrf_input['value'] if csrf_input else 'token'
    
    def login(self):
        self.log("\n🔐 Authenticating...", Colors.BOLD)
        try:
            response = self.session.get(f"{self.base_url}/login", timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Try multiple ways to find CSRF token
            csrf_token = ''
            csrf_input = soup.find('input', {'name': 'csrf_token'})
            if csrf_input:
                csrf_token = csrf_input.get('value', '')
            
            if not csrf_token:
                # Try finding by id
                csrf_input = soup.find('input', {'id': 'csrf_token'})
                if csrf_input:
                    csrf_token = csrf_input.get('value', '')
            
            if not csrf_token:
                # Try meta tag
                csrf_meta = soup.find('meta', {'name': 'csrf-token'})
                if csrf_meta:
                    csrf_token = csrf_meta.get('content', '')
            
            self.log_verbose(f"CSRF token found: {bool(csrf_token)}")
            
            login_data = {
                'username': self.username,
                'password': self.password,
            }
            
            # Only add csrf_token if found
            if csrf_token:
                login_data['csrf_token'] = csrf_token
            
            self.log_verbose(f"Posting to {self.base_url}/login")
            
            response = self.session.post(f"{self.base_url}/login", data=login_data,
                                        allow_redirects=True, timeout=10)
            
            self.log_verbose(f"Response URL: {response.url}")
            self.log_verbose(f"Response status: {response.status_code}")
            
            # Check for successful login
            if '/login' not in response.url and response.status_code == 200:
                self.log(f"  ✅ Logged in as {self.username}", Colors.GREEN)
                return True
            
            # Check if we're on dashboard or another page (successful login)
            if response.status_code == 200 and ('dashboard' in response.text.lower() or 'logout' in response.text.lower()):
                self.log(f"  ✅ Logged in as {self.username}", Colors.GREEN)
                return True
            
            # Check for error message in response
            if 'invalid' in response.text.lower() or 'incorrect' in response.text.lower():
                self.log(f"  ❌ Login failed: Invalid credentials", Colors.RED)
            else:
                self.log(f"  ❌ Login failed for {self.username}", Colors.RED)
                self.log_verbose(f"Final URL: {response.url}")
            
            return False
        except Exception as e:
            self.log(f"  ❌ Login error: {e}", Colors.RED)
            return False
    
    def get_page(self, endpoint):
        try:
            return self.session.get(f"{self.base_url}{endpoint}", timeout=10)
        except:
            return None
    
    # ==========================================================================
    # USER PAGE ACCESSIBILITY TESTS
    # ==========================================================================
    
    def test_user_pages(self):
        """Test all user-accessible pages"""
        self.log("\n📄 Testing User Page Accessibility...", Colors.BOLD)
        
        pages = [
            ("/", "Dashboard"),
            ("/handover", "Handover Form"),
            ("/reports", "Reports"),
            ("/keypoints", "Key Points"),
            ("/roster", "Shift Roster"),
            ("/escalation-matrix", "Escalation Matrix"),
            ("/vendor-details", "Vendor Details"),
        ]
        
        for endpoint, name in pages:
            response = self.get_page(endpoint)
            if response:
                self.test(f"{name} ({endpoint})", 
                         response.status_code == 200,
                         f"Status: {response.status_code}")
            else:
                self.test(f"{name} ({endpoint})", False, "Request failed")
    
    # ==========================================================================
    # DASHBOARD TESTS
    # ==========================================================================
    
    def test_dashboard(self):
        """Test dashboard functionality"""
        self.log("\n📊 Testing Dashboard...", Colors.BOLD)
        
        response = self.get_page("/")
        if not response or response.status_code != 200:
            self.skip("Dashboard tests", "Could not load dashboard")
            return
        
        page_text = response.text.lower()
        
        self.test("Has shift information", 'shift' in page_text)
        self.test("Has key points section", 'key point' in page_text or 'keypoint' in page_text or 'key-point' in page_text)
        self.test("Has team/engineer information", 'engineer' in page_text or 'team' in page_text or 'member' in page_text)
        self.test("Has incident information", 'incident' in page_text or 'ticket' in page_text)
    
    # ==========================================================================
    # KEY POINTS TESTS
    # ==========================================================================
    
    def test_keypoints(self):
        """Test key points page"""
        self.log("\n🔑 Testing Key Points...", Colors.BOLD)
        
        response = self.get_page("/keypoints")
        if not response or response.status_code != 200:
            self.skip("Key points tests", "Could not load key points page")
            return
        
        soup = BeautifulSoup(response.text, 'html.parser')
        page_text = response.text.lower()
        
        # Check for table or list of key points
        tables = soup.find_all('table')
        cards = soup.find_all(class_=re.compile(r'card|list|item', re.I))
        self.test("Has key points display", len(tables) > 0 or len(cards) > 0 or 'key point' in page_text)
        
        # Check for status filters or status indicators
        page_text = response.text.lower()
        status_indicators = ['open', 'closed', 'in progress', 'status', 'filter', 'pending']
        self.test("Has status indicators", any(s in page_text for s in status_indicators))
        
        # Check for no duplicates
        descriptions = []
        for row in soup.find_all('tr'):
            cells = row.find_all('td')
            if len(cells) >= 2:
                for cell in cells:
                    text = cell.get_text(strip=True).lower()
                    if len(text) > 30:
                        descriptions.append(text)
        
        unique = set(descriptions)
        duplicates = len(descriptions) - len(unique)
        self.test("No duplicate key points", duplicates == 0, f"Found {duplicates} duplicates")
    
    # ==========================================================================
    # HANDOVER FORM TESTS
    # ==========================================================================
    
    def test_handover_form(self):
        """Test handover form structure"""
        self.log("\n📝 Testing Handover Form...", Colors.BOLD)
        
        response = self.get_page("/handover")
        if not response or response.status_code != 200:
            self.skip("Handover form tests", "Could not load form")
            return
        
        soup = BeautifulSoup(response.text, 'html.parser')
        page_text = response.text.lower()
        
        # Form structure
        form = soup.find('form')
        self.test("Has form element", form is not None)
        
        # Shift dropdowns
        selects = soup.find_all('select')
        self.test("Has dropdown fields", len(selects) > 0)
        
        # Engineers section - check for shift-related content
        has_current = ('current' in page_text and ('shift' in page_text or 'engineer' in page_text)) or 'current_shift' in page_text
        has_next = ('next' in page_text and ('shift' in page_text or 'engineer' in page_text)) or 'next_shift' in page_text
        self.test("Has current shift section", has_current or 'morning' in page_text or 'evening' in page_text)
        self.test("Has next shift section", has_next or 'morning' in page_text or 'evening' in page_text)
        
        # Key sections
        self.test("Has incidents section", 'incident' in page_text)
        self.test("Has key points section", 'key point' in page_text or 'keypoint' in page_text)
        self.test("Has change info section", 'change' in page_text)
        self.test("Has KB updates section", 'kb' in page_text or 'knowledge' in page_text)
    
    # ==========================================================================
    # REPORTS TESTS
    # ==========================================================================
    
    def test_reports(self):
        """Test reports page"""
        self.log("\n📋 Testing Reports...", Colors.BOLD)
        
        response = self.get_page("/reports")
        if not response or response.status_code != 200:
            self.skip("Reports tests", "Could not load reports page")
            return
        
        soup = BeautifulSoup(response.text, 'html.parser')
        page_text = response.text.lower()
        
        # Filter dropdowns
        selects = soup.find_all('select')
        self.test("Has filter dropdowns", len(selects) > 0)
        
        # Content
        self.test("Has shift/handover content", 'shift' in page_text or 'handover' in page_text)
        
        # Draft filter
        draft_response = self.get_page("/reports?status=draft")
        self.test("Draft filter works", draft_response and draft_response.status_code == 200)
        
        # Submitted filter
        submitted_response = self.get_page("/reports?status=submitted")
        self.test("Submitted filter works", submitted_response and submitted_response.status_code == 200)
    
    # ==========================================================================
    # SHIFT ROSTER TESTS
    # ==========================================================================
    
    def test_roster(self):
        """Test shift roster page"""
        self.log("\n📅 Testing Shift Roster...", Colors.BOLD)
        
        response = self.get_page("/roster")
        if not response or response.status_code != 200:
            self.skip("Roster tests", "Could not load roster page")
            return
        
        page_text = response.text.lower()
        
        self.test("Has roster information", 'roster' in page_text or 'schedule' in page_text)
        self.test("Has shift information", 'shift' in page_text)
        self.test("Has engineer/team info", 'engineer' in page_text or 'team' in page_text)
    
    # ==========================================================================
    # ESCALATION MATRIX TESTS
    # ==========================================================================
    
    def test_escalation_matrix(self):
        """Test escalation matrix page"""
        self.log("\n📞 Testing Escalation Matrix...", Colors.BOLD)
        
        response = self.get_page("/escalation-matrix")
        if not response or response.status_code != 200:
            self.skip("Escalation matrix tests", "Could not load page")
            return
        
        soup = BeautifulSoup(response.text, 'html.parser')
        page_text = response.text.lower()
        
        # Check for escalation content (table, cards, or text)
        tables = soup.find_all('table')
        cards = soup.find_all(class_=re.compile(r'card|entry|row', re.I))
        has_content = len(tables) > 0 or len(cards) > 0 or 'escalation' in page_text or 'matrix' in page_text
        self.test("Has escalation content", has_content)
        
        # Check for contact or application info
        contact_indicators = ['contact', 'phone', 'email', 'application', 'app', 'team', 'name']
        self.test("Has relevant information", any(c in page_text for c in contact_indicators))
    
    # ==========================================================================
    # TEAM FILTERING TESTS
    # ==========================================================================
    
    def test_team_filtering(self):
        """Test team-based filtering"""
        self.log("\n👥 Testing Team Filtering...", Colors.BOLD)
        
        # Dashboard
        response = self.get_page("/?team_id=1")
        self.test("Dashboard team filter", response and response.status_code == 200)
        
        # Reports
        response = self.get_page("/reports?team_id=1")
        self.test("Reports team filter", response and response.status_code == 200)
        
        # Key points
        response = self.get_page("/keypoints?team_id=1")
        self.test("Key points team filter", response and response.status_code == 200)
        
        # Roster
        response = self.get_page("/roster?team_id=1")
        self.test("Roster team filter", response and response.status_code == 200)
    
    # ==========================================================================
    # HANDOVER WORKFLOW TEST
    # ==========================================================================
    
    def test_handover_workflow(self):
        """Test basic handover workflow (draft save)"""
        self.log("\n🔄 Testing Handover Workflow...", Colors.BOLD)
        
        # Load form
        response = self.get_page("/handover")
        if not response or response.status_code != 200:
            self.skip("Handover workflow", "Could not load form")
            return
        
        soup = BeautifulSoup(response.text, 'html.parser')
        csrf_token = self.get_csrf_token(response.text)
        
        # Get shift types
        current_shift = soup.find('select', {'name': re.compile(r'current_shift', re.I)})
        shift_types = []
        if current_shift:
            options = current_shift.find_all('option')
            shift_types = [opt.get('value') for opt in options if opt.get('value')]
        
        # Prepare minimal form data for draft
        post_data = {
            'csrf_token': csrf_token,
            'action': 'save_draft',
            'current_shift_type': shift_types[0] if shift_types else 'Morning',
            'next_shift_type': shift_types[1] if len(shift_types) > 1 else 'Evening',
            'additional_notes': f'Automated test - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
        }
        
        # Try to save draft
        try:
            response = self.session.post(f"{self.base_url}/handover", 
                                        data=post_data,
                                        allow_redirects=True,
                                        timeout=30)
            
            self.test("Draft save request successful", response.status_code == 200)
            
            # Check for success indicators (various possible responses)
            page_text = response.text.lower()
            url_lower = response.url.lower()
            success_indicators = ['draft', 'saved', 'success', 'report', 'handover', 'submitted']
            url_success = 'reports' in url_lower or 'handover' in url_lower
            text_success = any(s in page_text for s in success_indicators)
            # Also check that we're not on an error page
            no_error = 'error' not in page_text[:500] and 'exception' not in page_text[:500]
            
            self.test("Draft workflow completed", (text_success or url_success) and no_error)
            
        except Exception as e:
            self.test("Draft save workflow", False, str(e))
    
    # ==========================================================================
    # MAIN RUNNER
    # ==========================================================================
    
    def run_all_tests(self):
        """Run all user activity tests"""
        self.log("\n" + "="*60, Colors.BOLD)
        self.log("👤 USER ACTIVITIES TEST SUITE", Colors.BOLD)
        self.log(f"   Target: {self.base_url}", Colors.CYAN)
        self.log(f"   User: {self.username}", Colors.CYAN)
        self.log(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", Colors.CYAN)
        self.log("="*60, Colors.BOLD)
        
        if not self.login():
            self.log("\n❌ Cannot proceed without authentication", Colors.RED)
            return False
        
        # Run all tests
        self.test_user_pages()
        self.test_dashboard()
        self.test_keypoints()
        self.test_handover_form()
        self.test_reports()
        self.test_roster()
        self.test_escalation_matrix()
        self.test_team_filtering()
        self.test_handover_workflow()
        
        self.print_summary()
        return self.failed == 0
    
    def print_summary(self):
        total = self.passed + self.failed + self.skipped
        
        self.log("\n" + "="*60, Colors.BOLD)
        self.log("📊 USER ACTIVITIES TEST SUMMARY", Colors.BOLD)
        self.log("="*60, Colors.BOLD)
        self.log(f"  Total Tests: {total}")
        self.log(f"  ✅ Passed: {self.passed}", Colors.GREEN)
        self.log(f"  ❌ Failed: {self.failed}", Colors.RED if self.failed > 0 else None)
        self.log(f"  ⏭️  Skipped: {self.skipped}", Colors.YELLOW if self.skipped > 0 else None)
        
        if self.failed == 0:
            self.log("\n🎉 ALL USER TESTS PASSED!", Colors.GREEN)
        else:
            self.log(f"\n⚠️  {self.failed} TEST(S) FAILED", Colors.RED)
        
        self.log("="*60 + "\n", Colors.BOLD)


def main():
    parser = argparse.ArgumentParser(description='User Activities Test Suite')
    parser.add_argument('--url', default='http://localhost:5000', help='Base URL')
    parser.add_argument('--user', default='ctctestuser', help='Username (any user)')
    parser.add_argument('--password', default='test123', help='Password')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    runner = UserActivityTests(args.url, args.user, args.password, args.verbose)
    success = runner.run_all_tests()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

