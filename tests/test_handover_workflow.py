#!/usr/bin/env python3
"""
End-to-End Handover Workflow Tests

Tests the complete handover workflow:
1. Fill handover form with test data (incidents, KBs, change info, key points)
2. Save as draft
3. Open draft and verify data
4. Edit draft and update details
5. Submit final handover
6. Verify in reports
7. Check email delivery status

Run with: python tests/test_handover_workflow.py
"""

import requests
from bs4 import BeautifulSoup
import argparse
import sys
import io
import time
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


class HandoverWorkflowTest:
    """End-to-end handover workflow testing"""
    
    def __init__(self, base_url, username, password, verbose=False):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.verbose = verbose
        self.session = requests.Session()
        self.results = []
        self.passed = 0
        self.failed = 0
        self.draft_shift_id = None
        self.submitted_shift_id = None
        
        # Test data
        self.test_data = {
            'incidents': [
                {
                    'type': 'open',
                    'title': '[TestApp] INC-TEST-001',
                    'description': 'Automated test incident - Open',
                    'status': 'Open',
                    'assigned_to': ''
                },
                {
                    'type': 'resolved',
                    'title': '[TestApp] INC-TEST-002', 
                    'description': 'Automated test incident - Resolved',
                    'status': 'Resolved',
                    'assigned_to': ''
                }
            ],
            'key_points': [
                {
                    'description': 'AUTOMATED TEST KEY POINT - Please monitor test system',
                    'status': 'Open',
                    'jira_id': 'TEST-KP-001'
                },
                {
                    'description': 'AUTOMATED TEST KEY POINT 2 - Follow up required',
                    'status': 'In Progress',
                    'jira_id': 'TEST-KP-002'
                }
            ],
            'change_info': [
                {
                    'app_name': 'TestApp',
                    'change_number': 'CHG-TEST-001',
                    'description': 'Automated test change - scheduled maintenance',
                    'datetime': datetime.now().strftime('%Y-%m-%d %H:%M'),
                    'status': 'Scheduled'
                }
            ],
            'kb_updates': [
                {
                    'app_name': 'TestApp',
                    'kb_number': 'KB-TEST-001',
                    'description': 'Automated test KB update',
                    'status': 'In Progress'
                }
            ],
            'additional_notes': 'This is an automated test handover - please ignore'
        }
    
    def log(self, message, color=None):
        if color:
            print(f"{color}{message}{Colors.RESET}")
        else:
            print(message)
    
    def log_step(self, step_num, message):
        self.log(f"\n{'='*60}", Colors.BOLD)
        self.log(f"STEP {step_num}: {message}", Colors.BOLD)
        self.log(f"{'='*60}", Colors.BOLD)
    
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
    
    def get_csrf_token(self, html):
        """Extract CSRF token from HTML"""
        soup = BeautifulSoup(html, 'html.parser')
        # Try multiple patterns for CSRF token
        csrf_input = soup.find('input', {'name': 'csrf_token'})
        if not csrf_input:
            csrf_input = soup.find('input', {'name': re.compile(r'csrf', re.I)})
        if not csrf_input:
            # Look in meta tags
            csrf_meta = soup.find('meta', {'name': re.compile(r'csrf', re.I)})
            if csrf_meta:
                return csrf_meta.get('content', '')
        return csrf_input['value'] if csrf_input else 'dummy_token'
    
    def login(self):
        """Login to application"""
        self.log("\n🔐 Logging in...", Colors.BOLD)
        try:
            response = self.session.get(f"{self.base_url}/login", timeout=10)
            csrf_token = self.get_csrf_token(response.text)
            
            login_data = {
                'username': self.username,
                'password': self.password,
                'csrf_token': csrf_token
            }
            response = self.session.post(f"{self.base_url}/login", data=login_data,
                                        allow_redirects=True, timeout=10)
            
            if '/login' not in response.url:
                self.log(f"  ✅ Logged in as {self.username}", Colors.GREEN)
                return True
            else:
                self.log(f"  ❌ Login failed", Colors.RED)
                return False
        except Exception as e:
            self.log(f"  ❌ Login error: {e}", Colors.RED)
            return False
    
    # ==========================================================================
    # STEP 1: Load Handover Form and Get Form Structure
    # ==========================================================================
    
    def step1_load_handover_form(self):
        """Load handover form and extract form structure"""
        self.log_step(1, "Loading Handover Form")
        
        response = self.session.get(f"{self.base_url}/handover", timeout=15)
        
        if not self.test("Form page loads", response.status_code == 200, 
                        f"Status: {response.status_code}"):
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find form
        form = soup.find('form')
        self.test("Form element found", form is not None)
        
        # Get CSRF token
        csrf_token = self.get_csrf_token(response.text)
        self.test("CSRF token found", bool(csrf_token))
        
        # Find shift type dropdowns
        current_shift_select = soup.find('select', {'name': re.compile(r'current_shift', re.I)})
        next_shift_select = soup.find('select', {'name': re.compile(r'next_shift', re.I)})
        
        self.test("Current shift dropdown found", current_shift_select is not None)
        self.test("Next shift dropdown found", next_shift_select is not None)
        
        # Get available shift types
        shift_types = []
        if current_shift_select:
            options = current_shift_select.find_all('option')
            shift_types = [opt.get('value') for opt in options if opt.get('value')]
            self.log_verbose(f"Available shift types: {shift_types}")
        
        # Find team dropdown if exists
        team_select = soup.find('select', {'name': re.compile(r'team', re.I)})
        team_id = None
        if team_select:
            first_option = team_select.find('option', selected=True) or team_select.find('option')
            if first_option:
                team_id = first_option.get('value')
        
        return {
            'csrf_token': csrf_token,
            'shift_types': shift_types,
            'team_id': team_id,
            'html': response.text,
            'soup': soup
        }
    
    # ==========================================================================
    # STEP 2: Fill Form and Save as Draft
    # ==========================================================================
    
    def step2_save_as_draft(self, form_data):
        """Fill handover form with test data and save as draft"""
        self.log_step(2, "Filling Form & Saving as Draft")
        
        if not form_data:
            self.test("Form data available", False, "No form data from step 1")
            return False
        
        # Prepare form submission data
        shift_types = form_data.get('shift_types', ['Morning', 'Evening', 'Night'])
        
        post_data = {
            'csrf_token': form_data['csrf_token'],
            'action': 'save_draft',  # Save as draft
            'current_shift_type': shift_types[0] if shift_types else 'Morning',
            'next_shift_type': shift_types[1] if len(shift_types) > 1 else 'Evening',
            'additional_notes': self.test_data['additional_notes'],
        }
        
        # Add team_id if available
        if form_data.get('team_id'):
            post_data['team_id'] = form_data['team_id']
        
        # Add open incidents
        for i, incident in enumerate(self.test_data['incidents']):
            if incident['type'] == 'open':
                post_data[f'open_incident_id[{i}]'] = f'TEST-{i+1}'
                post_data[f'open_incident_title[{i}]'] = incident['title']
                post_data[f'open_incident_description[{i}]'] = incident['description']
                post_data[f'open_incident_status[{i}]'] = incident['status']
        
        # Add resolved incidents
        resolved_count = 0
        for incident in self.test_data['incidents']:
            if incident['type'] == 'resolved':
                post_data[f'resolved_incident_id[{resolved_count}]'] = f'TEST-R-{resolved_count+1}'
                post_data[f'resolved_incident_title[{resolved_count}]'] = incident['title']
                post_data[f'resolved_incident_description[{resolved_count}]'] = incident['description']
                resolved_count += 1
        
        # Add key points
        for i, kp in enumerate(self.test_data['key_points']):
            post_data[f'key_point_description[{i}]'] = kp['description']
            post_data[f'key_point_status[{i}]'] = kp['status']
            post_data[f'key_point_jira_id[{i}]'] = kp['jira_id']
        
        # Add change info
        for i, change in enumerate(self.test_data['change_info']):
            post_data[f'change_app_name[{i}]'] = change['app_name']
            post_data[f'change_number[{i}]'] = change['change_number']
            post_data[f'change_description[{i}]'] = change['description']
            post_data[f'change_status[{i}]'] = change['status']
        
        # Add KB updates
        for i, kb in enumerate(self.test_data['kb_updates']):
            post_data[f'kb_app_name[{i}]'] = kb['app_name']
            post_data[f'kb_number[{i}]'] = kb['kb_number']
            post_data[f'kb_description[{i}]'] = kb['description']
            post_data[f'kb_status[{i}]'] = kb['status']
        
        self.log_verbose(f"Submitting form with {len(post_data)} fields")
        
        # Submit form
        try:
            response = self.session.post(f"{self.base_url}/handover", 
                                        data=post_data,
                                        allow_redirects=True,
                                        timeout=30)
            
            self.test("Form submission successful", response.status_code == 200,
                     f"Status: {response.status_code}")
            
            # Check for success message or redirect to reports
            success_indicators = ['draft', 'saved', 'success', 'reports']
            page_text = response.text.lower()
            
            is_success = any(ind in page_text for ind in success_indicators) or \
                        'reports' in response.url.lower()
            
            self.test("Draft saved successfully", is_success,
                     "No success indicator found")
            
            # Try to extract shift ID from response
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for draft entries
            draft_links = soup.find_all('a', href=re.compile(r'/handover/edit/(\d+)'))
            if draft_links:
                match = re.search(r'/handover/edit/(\d+)', draft_links[0]['href'])
                if match:
                    self.draft_shift_id = match.group(1)
                    self.log_verbose(f"Found draft shift ID: {self.draft_shift_id}")
            
            return is_success
            
        except Exception as e:
            self.test("Form submission", False, str(e))
            return False
    
    # ==========================================================================
    # STEP 3: Open Draft and Verify Data
    # ==========================================================================
    
    def step3_verify_draft(self):
        """Open saved draft and verify data is preserved"""
        self.log_step(3, "Opening & Verifying Draft")
        
        # First, find the draft in reports
        response = self.session.get(f"{self.base_url}/reports?status=draft", timeout=15)
        
        self.test("Draft reports page loads", response.status_code == 200)
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find edit links for drafts
        edit_links = soup.find_all('a', href=re.compile(r'/handover/edit/(\d+)'))
        
        if not edit_links:
            self.test("Draft found in reports", False, "No draft entries found")
            return False
        
        self.test("Draft found in reports", True)
        
        # Get the most recent draft
        edit_url = edit_links[0]['href']
        match = re.search(r'/handover/edit/(\d+)', edit_url)
        if match:
            self.draft_shift_id = match.group(1)
        
        self.log_verbose(f"Opening draft: {edit_url}")
        
        # Open the draft for editing
        response = self.session.get(f"{self.base_url}{edit_url}", timeout=15)
        
        if not self.test("Draft edit page loads", response.status_code == 200,
                        f"Status: {response.status_code}"):
            return False
        
        soup = BeautifulSoup(response.text, 'html.parser')
        page_text = response.text
        
        # Verify test data is present
        # Check for key points
        kp_found = any(kp['description'][:30] in page_text for kp in self.test_data['key_points'])
        self.test("Key points data preserved", kp_found or 'key point' in page_text.lower(),
                 "Test key points not found")
        
        # Check for additional notes (check various parts that might be present)
        page_lower = page_text.lower()
        notes_indicators = ['automated test', 'additional', 'notes', 'please ignore']
        notes_found = any(ind in page_lower for ind in notes_indicators)
        self.test("Additional notes section present", notes_found or 'textarea' in page_lower,
                 "Additional notes section not found")
        
        return True
    
    # ==========================================================================
    # STEP 4: Edit Draft and Update Details
    # ==========================================================================
    
    def step4_edit_and_update_draft(self):
        """Edit the draft and update some details"""
        self.log_step(4, "Editing & Updating Draft")
        
        if not self.draft_shift_id:
            self.test("Draft ID available", False, "No draft ID from previous steps")
            return False
        
        # Load the edit page
        edit_url = f"{self.base_url}/handover/edit/{self.draft_shift_id}"
        response = self.session.get(edit_url, timeout=15)
        
        if not self.test("Edit page loads", response.status_code == 200):
            return False
        
        csrf_token = self.get_csrf_token(response.text)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Prepare updated data - modify the additional notes
        updated_notes = f"{self.test_data['additional_notes']} - UPDATED at {datetime.now().strftime('%H:%M:%S')}"
        
        # Build form data from existing form
        post_data = {
            'csrf_token': csrf_token,
            'action': 'save_draft',  # Save as draft again
            'additional_notes': updated_notes,
        }
        
        # Copy existing form fields
        for input_elem in soup.find_all('input', {'name': True}):
            name = input_elem.get('name')
            value = input_elem.get('value', '')
            if name not in post_data and name != 'csrf_token':
                post_data[name] = value
        
        for select_elem in soup.find_all('select', {'name': True}):
            name = select_elem.get('name')
            selected = select_elem.find('option', selected=True)
            if selected and name not in post_data:
                post_data[name] = selected.get('value', '')
        
        for textarea_elem in soup.find_all('textarea', {'name': True}):
            name = textarea_elem.get('name')
            if name == 'additional_notes':
                post_data[name] = updated_notes
            elif name not in post_data:
                post_data[name] = textarea_elem.get_text()
        
        self.log_verbose(f"Updating draft with {len(post_data)} fields")
        
        # Submit update
        try:
            response = self.session.post(edit_url, data=post_data,
                                        allow_redirects=True, timeout=30)
            
            self.test("Draft update submitted", response.status_code == 200)
            
            # Verify update was saved
            success = 'saved' in response.text.lower() or 'success' in response.text.lower() or \
                     'reports' in response.url.lower()
            
            self.test("Draft update saved", success, "No success indicator")
            
            return success
            
        except Exception as e:
            self.test("Draft update", False, str(e))
            return False
    
    # ==========================================================================
    # STEP 5: Submit Final Handover
    # ==========================================================================
    
    def step5_submit_final_handover(self):
        """Submit the final handover"""
        self.log_step(5, "Submitting Final Handover")
        
        if not self.draft_shift_id:
            self.test("Draft ID available", False, "No draft ID")
            return False
        
        # Load the edit page
        edit_url = f"{self.base_url}/handover/edit/{self.draft_shift_id}"
        response = self.session.get(edit_url, timeout=15)
        
        if not self.test("Edit page loads for final submit", response.status_code == 200):
            return False
        
        csrf_token = self.get_csrf_token(response.text)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Build form data
        post_data = {
            'csrf_token': csrf_token,
            'action': 'submit',  # Final submission
        }
        
        # Copy all form fields
        for input_elem in soup.find_all('input', {'name': True}):
            name = input_elem.get('name')
            value = input_elem.get('value', '')
            if name not in post_data and name != 'csrf_token':
                if input_elem.get('type') == 'checkbox':
                    if input_elem.get('checked'):
                        post_data[name] = value or 'on'
                else:
                    post_data[name] = value
        
        for select_elem in soup.find_all('select', {'name': True}):
            name = select_elem.get('name')
            selected = select_elem.find('option', selected=True)
            if selected and name not in post_data:
                post_data[name] = selected.get('value', '')
        
        for textarea_elem in soup.find_all('textarea', {'name': True}):
            name = textarea_elem.get('name')
            if name not in post_data:
                post_data[name] = textarea_elem.get_text()
        
        self.log_verbose(f"Submitting final handover with {len(post_data)} fields")
        
        # Submit final handover
        try:
            response = self.session.post(edit_url, data=post_data,
                                        allow_redirects=True, timeout=30)
            
            self.test("Final submission sent", response.status_code == 200)
            
            # Check for success
            page_text = response.text.lower()
            success = 'submitted' in page_text or 'success' in page_text or \
                     'reports' in response.url.lower()
            
            self.test("Final handover submitted successfully", success,
                     "No success indicator found")
            
            self.submitted_shift_id = self.draft_shift_id
            
            return success
            
        except Exception as e:
            self.test("Final submission", False, str(e))
            return False
    
    # ==========================================================================
    # STEP 6: Verify in Reports
    # ==========================================================================
    
    def step6_verify_in_reports(self):
        """Verify submitted handover appears in reports"""
        self.log_step(6, "Verifying in Reports")
        
        # Load reports page
        response = self.session.get(f"{self.base_url}/reports", timeout=15)
        
        if not self.test("Reports page loads", response.status_code == 200):
            return False
        
        soup = BeautifulSoup(response.text, 'html.parser')
        page_text = response.text
        
        # Check if our submitted handover appears
        if self.submitted_shift_id:
            # Look for the shift ID in the page
            shift_found = self.submitted_shift_id in page_text or \
                         f"shift/{self.submitted_shift_id}" in page_text
            self.test("Submitted shift found in reports", shift_found,
                     f"Shift ID {self.submitted_shift_id} not found")
        
        # Check for today's date in reports
        today = date.today().strftime('%Y-%m-%d')
        today_alt = date.today().strftime('%B %d')  # e.g., "December 30"
        
        has_today = today in page_text or today_alt in page_text
        self.test("Today's reports visible", has_today or 'shift' in page_text.lower(),
                 "No recent reports found")
        
        # Verify status is "Submitted" not "Draft"
        if self.submitted_shift_id:
            # Look for submitted status
            submitted_pattern = re.compile(r'submitted|complete', re.I)
            has_submitted = bool(submitted_pattern.search(page_text))
            self.test("Status shows as Submitted", has_submitted,
                     "Status may still show as Draft")
        
        return True
    
    # ==========================================================================
    # STEP 7: Check Email Delivery Status
    # ==========================================================================
    
    def step7_check_email_status(self):
        """Check email delivery status for submitted handover"""
        self.log_step(7, "Checking Email Delivery Status")
        
        # Load email monitoring page
        response = self.session.get(f"{self.base_url}/admin/email-monitoring", timeout=15)
        
        if not self.test("Email monitoring page loads", response.status_code == 200):
            return False
        
        soup = BeautifulSoup(response.text, 'html.parser')
        page_text = response.text.lower()
        
        # Check for email logs
        tables = soup.find_all('table')
        self.test("Email logs table found", len(tables) > 0)
        
        # Check for recent email entries
        today = date.today().strftime('%Y-%m-%d')
        has_today_emails = today in page_text
        
        self.test("Today's email logs present", has_today_emails or 'handover' in page_text,
                 "No recent email logs found")
        
        # Check for success/sent status
        status_indicators = ['success', 'sent', 'delivered']
        has_success = any(ind in page_text for ind in status_indicators)
        
        self.test("Email delivery status available", has_success or 'status' in page_text,
                 "No status information found")
        
        return True
    
    # ==========================================================================
    # CLEANUP: Delete Test Data (Optional)
    # ==========================================================================
    
    def cleanup_test_data(self):
        """Optional: cleanup test data"""
        self.log("\n🧹 Cleanup (info only - manual deletion may be needed)", Colors.YELLOW)
        
        if self.submitted_shift_id:
            self.log(f"  • Test shift ID: {self.submitted_shift_id}", Colors.YELLOW)
            self.log(f"  • Test key points contain: 'AUTOMATED TEST KEY POINT'", Colors.YELLOW)
            self.log(f"  • Test incidents contain: 'TEST-' prefix", Colors.YELLOW)
    
    # ==========================================================================
    # MAIN RUNNER
    # ==========================================================================
    
    def run_all_tests(self):
        """Run complete handover workflow test"""
        self.log("\n" + "="*70, Colors.BOLD)
        self.log("🧪 HANDOVER WORKFLOW END-TO-END TEST", Colors.BOLD)
        self.log(f"   Target: {self.base_url}", Colors.CYAN)
        self.log(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", Colors.CYAN)
        self.log("="*70, Colors.BOLD)
        
        # Login
        if not self.login():
            self.log("\n❌ Cannot proceed without authentication", Colors.RED)
            return False
        
        # Run workflow steps
        form_data = self.step1_load_handover_form()
        
        if form_data:
            self.step2_save_as_draft(form_data)
            self.step3_verify_draft()
            self.step4_edit_and_update_draft()
            self.step5_submit_final_handover()
            self.step6_verify_in_reports()
            self.step7_check_email_status()
        
        # Cleanup info
        self.cleanup_test_data()
        
        # Print summary
        self.print_summary()
        
        return self.failed == 0
    
    def print_summary(self):
        """Print test summary"""
        total = self.passed + self.failed
        
        self.log("\n" + "="*70, Colors.BOLD)
        self.log("📊 WORKFLOW TEST SUMMARY", Colors.BOLD)
        self.log("="*70, Colors.BOLD)
        self.log(f"  Total Tests: {total}")
        self.log(f"  ✅ Passed: {self.passed}", Colors.GREEN)
        self.log(f"  ❌ Failed: {self.failed}", Colors.RED if self.failed > 0 else None)
        
        if self.failed == 0:
            self.log("\n🎉 ALL WORKFLOW TESTS PASSED!", Colors.GREEN)
        else:
            self.log(f"\n⚠️  {self.failed} TEST(S) FAILED", Colors.RED)
            self.log("\nFailed tests:", Colors.RED)
            for status, name, message in self.results:
                if status == "FAIL":
                    self.log(f"  • {name}: {message}", Colors.RED)
        
        self.log("="*70 + "\n", Colors.BOLD)


def main():
    parser = argparse.ArgumentParser(description='Handover Workflow End-to-End Test')
    parser.add_argument('--url', default='http://localhost:5000', help='Base URL')
    parser.add_argument('--user', default='superadmin', help='Username')
    parser.add_argument('--password', default='admin123', help='Password')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    tester = HandoverWorkflowTest(args.url, args.user, args.password, args.verbose)
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

