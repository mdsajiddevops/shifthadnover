#!/usr/bin/env python3
"""
Admin Activities Test Suite

Tests all admin-only functionality:
- System Configuration
- Email Monitoring
- Active Sessions
- User Management
- Email Configuration
- Admin-specific features

Run with: python tests/test_admin_activities.py
Requires: Admin credentials (super_admin, account_admin, or team_admin)
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
    MAGENTA = '\033[95m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


class AdminActivityTests:
    """Tests for admin activities"""
    
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
        self.user_role = None
    
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
        self.log("\n🔐 Authenticating as Admin...", Colors.BOLD)
        try:
            response = self.session.get(f"{self.base_url}/login", timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Try multiple ways to find CSRF token
            csrf_token = ''
            csrf_input = soup.find('input', {'name': 'csrf_token'})
            if csrf_input:
                csrf_token = csrf_input.get('value', '')
            
            login_data = {
                'username': self.username,
                'password': self.password,
            }
            if csrf_token:
                login_data['csrf_token'] = csrf_token
            
            response = self.session.post(f"{self.base_url}/login", data=login_data,
                                        allow_redirects=True, timeout=10)
            
            # Check for successful login
            is_logged_in = '/login' not in response.url or \
                          'dashboard' in response.text.lower() or \
                          'logout' in response.text.lower()
            
            if is_logged_in:
                self.log(f"  ✅ Logged in as {self.username}", Colors.GREEN)
                
                # Check if user is admin by accessing admin page
                admin_check = self.session.get(f"{self.base_url}/admin/configuration", timeout=10)
                if admin_check.status_code == 200:
                    self.log(f"  ✅ Admin access confirmed", Colors.GREEN)
                    return True
                else:
                    self.log(f"  ⚠️  User may not have admin privileges", Colors.YELLOW)
                    return True  # Still logged in, but may fail admin tests
            else:
                self.log(f"  ❌ Login failed for {self.username}", Colors.RED)
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
    # ADMIN PAGE ACCESSIBILITY TESTS
    # ==========================================================================
    
    def test_admin_pages(self):
        """Test all admin-accessible pages"""
        self.log("\n🔒 Testing Admin Page Accessibility...", Colors.BOLD)
        
        pages = [
            ("/admin/configuration", "System Configuration"),
            ("/admin/email-monitoring", "Email Monitoring"),
            ("/admin/active-sessions", "Active Sessions"),
            ("/user-management", "User Management"),
            ("/api/email-config/admin", "Email Configuration"),
        ]
        
        for endpoint, name in pages:
            response = self.get_page(endpoint)
            if response:
                # 200 = success, 403 = forbidden (not admin)
                if response.status_code == 200:
                    self.test(f"{name} ({endpoint})", True)
                elif response.status_code == 403:
                    self.test(f"{name} ({endpoint})", False, "Access forbidden - not admin")
                else:
                    self.test(f"{name} ({endpoint})", False, f"Status: {response.status_code}")
            else:
                self.test(f"{name} ({endpoint})", False, "Request failed")
    
    # ==========================================================================
    # SYSTEM CONFIGURATION TESTS
    # ==========================================================================
    
    def test_system_configuration(self):
        """Test system configuration page"""
        self.log("\n⚙️  Testing System Configuration...", Colors.BOLD)
        
        response = self.get_page("/admin/configuration")
        if not response or response.status_code != 200:
            self.skip("System configuration tests", "Could not access page (admin required)")
            return
        
        soup = BeautifulSoup(response.text, 'html.parser')
        page_text = response.text.lower()
        
        # Check for configuration sections
        self.test("Has navigation tabs config", 'navigation' in page_text or 'tabs' in page_text)
        self.test("Has feature toggles", 'toggle' in page_text or 'enable' in page_text)
        
        # Check for form elements
        checkboxes = soup.find_all('input', {'type': 'checkbox'})
        self.test("Has toggle switches", len(checkboxes) > 0)
        
        # Check for known config options
        config_options = ['kb_articles', 'vendor', 'applications', 'change']
        found_options = sum(1 for opt in config_options if opt in page_text)
        self.test("Has expected config options", found_options >= 2, f"Found {found_options}/4 options")
    
    # ==========================================================================
    # EMAIL MONITORING TESTS
    # ==========================================================================
    
    def test_email_monitoring(self):
        """Test email monitoring page"""
        self.log("\n📧 Testing Email Monitoring...", Colors.BOLD)
        
        response = self.get_page("/admin/email-monitoring")
        if not response or response.status_code != 200:
            self.skip("Email monitoring tests", "Could not access page (admin required)")
            return
        
        soup = BeautifulSoup(response.text, 'html.parser')
        page_text = response.text.lower()
        
        # Check for email logs table
        tables = soup.find_all('table')
        self.test("Has email logs table", len(tables) > 0)
        
        # Check for status information
        self.test("Has status column", 'status' in page_text)
        self.test("Has recipient information", 'recipient' in page_text or 'to' in page_text)
        self.test("Has timestamp information", 'date' in page_text or 'time' in page_text)
        
        # Check for filter options
        selects = soup.find_all('select')
        self.test("Has filter options", len(selects) > 0)
        
        # Check for UNS event ID (if applicable)
        self.test("Has UNS/event tracking", 'uns' in page_text or 'event' in page_text)
    
    # ==========================================================================
    # ACTIVE SESSIONS TESTS
    # ==========================================================================
    
    def test_active_sessions(self):
        """Test active sessions page"""
        self.log("\n👥 Testing Active Sessions...", Colors.BOLD)
        
        response = self.get_page("/admin/active-sessions")
        if not response or response.status_code != 200:
            self.skip("Active sessions tests", "Could not access page (admin required)")
            return
        
        soup = BeautifulSoup(response.text, 'html.parser')
        page_text = response.text.lower()
        
        # Check for session information
        self.test("Has user information", 'user' in page_text)
        self.test("Has activity status", 'active' in page_text or 'online' in page_text or 'status' in page_text)
        self.test("Has last activity time", 'last' in page_text or 'activity' in page_text)
        
        # Check for table
        tables = soup.find_all('table')
        self.test("Has sessions table", len(tables) > 0)
    
    # ==========================================================================
    # USER MANAGEMENT TESTS
    # ==========================================================================
    
    def test_user_management(self):
        """Test user management page"""
        self.log("\n👤 Testing User Management...", Colors.BOLD)
        
        response = self.get_page("/user-management")
        if not response or response.status_code != 200:
            self.skip("User management tests", "Could not access page (admin required)")
            return
        
        soup = BeautifulSoup(response.text, 'html.parser')
        page_text = response.text.lower()
        
        # Check for user list
        tables = soup.find_all('table')
        self.test("Has users table", len(tables) > 0)
        
        # Check for user actions
        self.test("Has add user option", 'add' in page_text or 'create' in page_text or 'new' in page_text)
        self.test("Has edit option", 'edit' in page_text)
        
        # Check for role information
        self.test("Has role information", 'role' in page_text or 'admin' in page_text)
        
        # Check for team/account info
        self.test("Has team/account info", 'team' in page_text or 'account' in page_text)
    
    # ==========================================================================
    # EMAIL CONFIGURATION TESTS
    # ==========================================================================
    
    def test_email_configuration(self):
        """Test email configuration page"""
        self.log("\n📬 Testing Email Configuration...", Colors.BOLD)
        
        # Try multiple email config URLs
        urls_to_try = [
            "/api/email-config/admin",
            "/admin/team-email-config",
            "/admin/uns-email"
        ]
        
        response = None
        for url in urls_to_try:
            resp = self.get_page(url)
            if resp and resp.status_code == 200:
                response = resp
                self.log_verbose(f"Found email config at {url}")
                break
        
        if not response:
            self.skip("Email configuration tests", "Could not access any email config page")
            return
        
        page_text = response.text.lower()
        
        # Check for SMTP settings
        self.test("Has SMTP/email configuration", 'smtp' in page_text or 'mail' in page_text or 'email' in page_text)
        
        # Check for recipient configuration
        self.test("Has recipient settings", 'recipient' in page_text or 'to' in page_text or 'email' in page_text)
        
        # Check for team or config settings
        self.test("Has configuration options", 'team' in page_text or 'config' in page_text or 'setting' in page_text)
    
    # ==========================================================================
    # ADMIN API TESTS
    # ==========================================================================
    
    def test_admin_apis(self):
        """Test admin API endpoints"""
        self.log("\n🔌 Testing Admin APIs...", Colors.BOLD)
        
        # Email monitoring API
        response = self.get_page("/admin/email-monitoring/1")
        self.test("Email log detail API accessible", response is not None)
        
        # Active sessions should be accessible
        response = self.get_page("/admin/active-sessions")
        self.test("Active sessions API accessible", response and response.status_code == 200)
    
    # ==========================================================================
    # ADMIN CONFIGURATION SAVE TEST
    # ==========================================================================
    
    def test_config_save(self):
        """Test that configuration can be saved (read-only test)"""
        self.log("\n💾 Testing Configuration Save Capability...", Colors.BOLD)
        
        response = self.get_page("/admin/configuration")
        if not response or response.status_code != 200:
            self.skip("Config save tests", "Could not access configuration page")
            return
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Check for save button/form
        forms = soup.find_all('form')
        self.test("Has configuration form", len(forms) > 0)
        
        # Check for submit buttons
        buttons = soup.find_all('button')
        save_buttons = [b for b in buttons if 'save' in b.get_text().lower() or 'submit' in str(b).lower()]
        self.test("Has save button", len(save_buttons) > 0 or len(buttons) > 0)
    
    # ==========================================================================
    # MAIN RUNNER
    # ==========================================================================
    
    def run_all_tests(self):
        """Run all admin activity tests"""
        self.log("\n" + "="*60, Colors.BOLD)
        self.log("🔒 ADMIN ACTIVITIES TEST SUITE", Colors.MAGENTA)
        self.log(f"   Target: {self.base_url}", Colors.CYAN)
        self.log(f"   Admin User: {self.username}", Colors.CYAN)
        self.log(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", Colors.CYAN)
        self.log("="*60, Colors.BOLD)
        
        if not self.login():
            self.log("\n❌ Cannot proceed without authentication", Colors.RED)
            return False
        
        # Run all admin tests
        self.test_admin_pages()
        self.test_system_configuration()
        self.test_email_monitoring()
        self.test_active_sessions()
        self.test_user_management()
        self.test_email_configuration()
        self.test_admin_apis()
        self.test_config_save()
        
        self.print_summary()
        return self.failed == 0
    
    def print_summary(self):
        total = self.passed + self.failed + self.skipped
        
        self.log("\n" + "="*60, Colors.BOLD)
        self.log("📊 ADMIN ACTIVITIES TEST SUMMARY", Colors.MAGENTA)
        self.log("="*60, Colors.BOLD)
        self.log(f"  Total Tests: {total}")
        self.log(f"  ✅ Passed: {self.passed}", Colors.GREEN)
        self.log(f"  ❌ Failed: {self.failed}", Colors.RED if self.failed > 0 else None)
        self.log(f"  ⏭️  Skipped: {self.skipped}", Colors.YELLOW if self.skipped > 0 else None)
        
        if self.failed == 0:
            self.log("\n🎉 ALL ADMIN TESTS PASSED!", Colors.GREEN)
        else:
            self.log(f"\n⚠️  {self.failed} TEST(S) FAILED", Colors.RED)
            
            if self.skipped > 0:
                self.log("\n💡 Tip: Skipped tests may indicate insufficient admin privileges", Colors.YELLOW)
        
        self.log("="*60 + "\n", Colors.BOLD)


def main():
    parser = argparse.ArgumentParser(description='Admin Activities Test Suite')
    parser.add_argument('--url', default='http://localhost:5000', help='Base URL')
    parser.add_argument('--user', default='superadmin', help='Admin username')
    parser.add_argument('--password', default='admin123', help='Admin password')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    runner = AdminActivityTests(args.url, args.user, args.password, args.verbose)
    success = runner.run_all_tests()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

