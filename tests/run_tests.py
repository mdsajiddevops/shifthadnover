#!/usr/bin/env python3
"""
Quick Test Runner for Shift Handover Application

This script runs quick sanity checks on the application.
Run with: python tests/run_tests.py

Options:
    --url URL       Base URL (default: http://localhost:5000)
    --user USER     Username (default: superadmin)
    --pass PASS     Password (default: admin123)
    --verbose       Show detailed output
"""

import requests
from bs4 import BeautifulSoup
import argparse
import sys
from datetime import datetime
import re
import io

# Fix Windows console encoding for emojis
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


class TestRunner:
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
        """Print message with optional color"""
        if color:
            print(f"{color}{message}{Colors.RESET}")
        else:
            print(message)
    
    def log_verbose(self, message):
        """Print only in verbose mode"""
        if self.verbose:
            print(f"  {Colors.BLUE}→ {message}{Colors.RESET}")
    
    def test(self, name, condition, message=""):
        """Record a test result"""
        if condition:
            self.log(f"  ✅ {name}", Colors.GREEN)
            self.passed += 1
            self.results.append(("PASS", name, message))
        else:
            self.log(f"  ❌ {name}: {message}", Colors.RED)
            self.failed += 1
            self.results.append(("FAIL", name, message))
        return condition
    
    def skip(self, name, reason):
        """Skip a test"""
        self.log(f"  ⏭️  {name}: {reason}", Colors.YELLOW)
        self.skipped += 1
        self.results.append(("SKIP", name, reason))
    
    def login(self):
        """Login to the application"""
        self.log("\n🔐 Authenticating...", Colors.BOLD)
        
        try:
            # Get login page and CSRF token
            response = self.session.get(f"{self.base_url}/login", timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            csrf_input = soup.find('input', {'name': 'csrf_token'})
            csrf_token = csrf_input['value'] if csrf_input else ''
            
            # Login
            login_data = {
                'username': self.username,
                'password': self.password,
                'csrf_token': csrf_token
            }
            response = self.session.post(f"{self.base_url}/login", data=login_data, 
                                        allow_redirects=True, timeout=10)
            
            if '/login' not in response.url and response.status_code == 200:
                self.log(f"  ✅ Logged in as {self.username}", Colors.GREEN)
                return True
            else:
                self.log(f"  ❌ Login failed for {self.username}", Colors.RED)
                return False
        except Exception as e:
            self.log(f"  ❌ Login error: {e}", Colors.RED)
            return False
    
    def get_page(self, endpoint):
        """Get a page and return response"""
        try:
            response = self.session.get(f"{self.base_url}{endpoint}", timeout=10)
            return response
        except Exception as e:
            return None
    
    # ==========================================================================
    # TEST METHODS
    # ==========================================================================
    
    def test_page_accessibility(self):
        """Test all main pages are accessible"""
        self.log("\n📄 Testing Page Accessibility...", Colors.BOLD)
        
        pages = [
            ("/", "Dashboard"),
            ("/handover", "Handover Form"),
            ("/reports", "Reports"),
            ("/keypoints", "Key Points"),
            ("/roster", "Shift Roster"),
            ("/escalation-matrix", "Escalation Matrix"),
            ("/vendor-details", "Vendor Details"),
            ("/admin/configuration", "System Configuration"),
            ("/admin/email-monitoring", "Email Monitoring"),
            ("/admin/active-sessions", "Active Sessions"),
        ]
        
        for endpoint, name in pages:
            response = self.get_page(endpoint)
            if response:
                self.test(f"{name} ({endpoint})", 
                         response.status_code == 200,
                         f"Status: {response.status_code}")
            else:
                self.test(f"{name} ({endpoint})", False, "Request failed")
    
    def test_dashboard_content(self):
        """Test dashboard has expected content"""
        self.log("\n📊 Testing Dashboard Content...", Colors.BOLD)
        
        response = self.get_page("/")
        if not response or response.status_code != 200:
            self.skip("Dashboard content", "Could not load dashboard")
            return
        
        soup = BeautifulSoup(response.text, 'html.parser')
        page_text = response.text.lower()
        
        # Check for key sections
        self.test("Has shift information", 
                 'shift' in page_text,
                 "No shift information found")
        
        self.test("Has key points section",
                 'key point' in page_text or 'keypoint' in page_text,
                 "No key points section found")
        
        self.test("Has engineer information",
                 'engineer' in page_text,
                 "No engineer information found")
    
    def test_keypoints_consistency(self):
        """Test key points are consistent (no duplicates)"""
        self.log("\n🔑 Testing Key Points Consistency...", Colors.BOLD)
        
        response = self.get_page("/keypoints")
        if not response or response.status_code != 200:
            self.skip("Key points consistency", "Could not load key points page")
            return
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all table rows (assuming key points are in a table)
        rows = soup.find_all('tr')
        descriptions = []
        
        for row in rows:
            cells = row.find_all('td')
            if len(cells) >= 2:  # Assuming description is in one of the cells
                for cell in cells:
                    text = cell.get_text(strip=True)
                    if len(text) > 20:  # Likely a description
                        descriptions.append(text.lower())
        
        # Check for duplicates
        unique = set(descriptions)
        duplicates = len(descriptions) - len(unique)
        
        self.test("No duplicate key points",
                 duplicates == 0,
                 f"Found {duplicates} duplicates")
        
        self.log_verbose(f"Total key points: {len(descriptions)}, Unique: {len(unique)}")
    
    def test_handover_form(self):
        """Test handover form structure"""
        self.log("\n📝 Testing Handover Form...", Colors.BOLD)
        
        response = self.get_page("/handover")
        if not response or response.status_code != 200:
            self.skip("Handover form", "Could not load handover form")
            return
        
        soup = BeautifulSoup(response.text, 'html.parser')
        page_text = response.text.lower()
        
        # Check for form element
        form = soup.find('form')
        self.test("Has form element", form is not None, "No form found")
        
        # Check for shift dropdowns
        selects = soup.find_all('select')
        self.test("Has dropdown fields", len(selects) > 0, "No dropdown fields found")
        
        # Check for engineer sections
        self.test("Has current shift engineers section",
                 'current' in page_text and 'engineer' in page_text,
                 "Missing current shift engineers")
        
        self.test("Has next shift engineers section",
                 'next' in page_text and 'engineer' in page_text,
                 "Missing next shift engineers")
        
        # Check for key points section
        self.test("Has key points section",
                 'key point' in page_text or 'keypoint' in page_text,
                 "Missing key points section")
        
        # Check for submit buttons (various types)
        submit_buttons = soup.find_all('button', type='submit')
        all_buttons = soup.find_all('button')
        submit_inputs = soup.find_all('input', type='submit')
        has_submit = len(submit_buttons) > 0 or len(submit_inputs) > 0 or len(all_buttons) > 0
        self.test("Has action buttons", has_submit, "No action buttons found")
    
    def test_reports_page(self):
        """Test reports page functionality"""
        self.log("\n📋 Testing Reports Page...", Colors.BOLD)
        
        response = self.get_page("/reports")
        if not response or response.status_code != 200:
            self.skip("Reports page", "Could not load reports page")
            return
        
        soup = BeautifulSoup(response.text, 'html.parser')
        page_text = response.text.lower()
        
        # Check for filter options
        selects = soup.find_all('select')
        self.test("Has filter dropdowns", len(selects) > 0, "No filter dropdowns")
        
        # Check for report content
        self.test("Has shift/handover content",
                 'shift' in page_text or 'handover' in page_text,
                 "No shift/handover content found")
        
        # Test draft filter
        draft_response = self.get_page("/reports?status=draft")
        self.test("Draft filter works",
                 draft_response and draft_response.status_code == 200,
                 "Draft filter failed")
    
    def test_email_monitoring(self):
        """Test email monitoring functionality"""
        self.log("\n📧 Testing Email Monitoring...", Colors.BOLD)
        
        response = self.get_page("/admin/email-monitoring")
        if not response or response.status_code != 200:
            self.skip("Email monitoring", "Could not load email monitoring page")
            return
        
        soup = BeautifulSoup(response.text, 'html.parser')
        page_text = response.text.lower()
        
        # Check for table
        tables = soup.find_all('table')
        self.test("Has email logs table", len(tables) > 0, "No table found")
        
        # Check for status indicators
        self.test("Has status information",
                 any(term in page_text for term in ['success', 'sent', 'failed', 'status']),
                 "No status information found")
    
    def test_multi_team_filtering(self):
        """Test multi-team filtering"""
        self.log("\n👥 Testing Multi-Team Filtering...", Colors.BOLD)
        
        # Test team filter on dashboard
        response = self.get_page("/?team_id=1")
        self.test("Dashboard team filter",
                 response and response.status_code == 200,
                 "Team filter failed on dashboard")
        
        # Test team filter on reports
        response = self.get_page("/reports?team_id=1")
        self.test("Reports team filter",
                 response and response.status_code == 200,
                 "Team filter failed on reports")
        
        # Test team filter on key points
        response = self.get_page("/keypoints?team_id=1")
        self.test("Key points team filter",
                 response and response.status_code == 200,
                 "Team filter failed on key points")
    
    def run_all_tests(self):
        """Run all tests"""
        self.log("\n" + "="*60, Colors.BOLD)
        self.log("🧪 SHIFT HANDOVER APPLICATION TEST SUITE", Colors.BOLD)
        self.log(f"   Target: {self.base_url}", Colors.BLUE)
        self.log(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", Colors.BLUE)
        self.log("="*60, Colors.BOLD)
        
        # Login first
        if not self.login():
            self.log("\n❌ Cannot proceed without authentication", Colors.RED)
            return False
        
        # Run all test categories
        self.test_page_accessibility()
        self.test_dashboard_content()
        self.test_keypoints_consistency()
        self.test_handover_form()
        self.test_reports_page()
        self.test_email_monitoring()
        self.test_multi_team_filtering()
        
        # Print summary
        self.print_summary()
        
        return self.failed == 0
    
    def print_summary(self):
        """Print test summary"""
        total = self.passed + self.failed + self.skipped
        
        self.log("\n" + "="*60, Colors.BOLD)
        self.log("📊 TEST SUMMARY", Colors.BOLD)
        self.log("="*60, Colors.BOLD)
        self.log(f"  Total Tests: {total}")
        self.log(f"  ✅ Passed: {self.passed}", Colors.GREEN)
        self.log(f"  ❌ Failed: {self.failed}", Colors.RED if self.failed > 0 else None)
        self.log(f"  ⏭️  Skipped: {self.skipped}", Colors.YELLOW if self.skipped > 0 else None)
        
        if self.failed == 0:
            self.log("\n🎉 ALL TESTS PASSED!", Colors.GREEN)
        else:
            self.log(f"\n⚠️  {self.failed} TEST(S) FAILED", Colors.RED)
            self.log("\nFailed tests:", Colors.RED)
            for status, name, message in self.results:
                if status == "FAIL":
                    self.log(f"  • {name}: {message}", Colors.RED)
        
        self.log("="*60 + "\n", Colors.BOLD)


def main():
    parser = argparse.ArgumentParser(description='Shift Handover Application Test Runner')
    parser.add_argument('--url', default='http://localhost:5000', help='Base URL')
    parser.add_argument('--user', default='superadmin', help='Username')
    parser.add_argument('--password', default='admin123', help='Password')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    runner = TestRunner(args.url, args.user, args.password, args.verbose)
    success = runner.run_all_tests()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

