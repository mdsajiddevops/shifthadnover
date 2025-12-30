# Shift Handover Application - Test Suite

## Quick Start

### 1. Install Dependencies
```bash
pip install -r tests/requirements.txt
```

## Test Suites Available

### 1. User Activities Tests (37 tests) - Any User
```bash
# Tests all regular user functionality
python tests/test_user_activities.py

# With your credentials
python tests/test_user_activities.py --user your_user --password your_pass

# For production
python tests/test_user_activities.py --url https://your-server.com --user your_user --password your_pass
```

**What it tests:**
- Dashboard, Reports, Key Points, Roster, Escalation Matrix, Vendor Details
- Handover form structure and workflow
- Team-based filtering
- Draft save functionality

---

### 2. Admin Activities Tests (31 tests) - Admin Only
```bash
# Tests all admin-only functionality
python tests/test_admin_activities.py

# With admin credentials
python tests/test_admin_activities.py --user admin_user --password admin_pass

# For production
python tests/test_admin_activities.py --url https://your-server.com --user admin --password admin_pass
```

**What it tests:**
- System Configuration
- Email Monitoring
- Active Sessions
- User Management
- Email Configuration

---

### 3. End-to-End Workflow Test (26 tests) - Any User
```bash
# Full handover workflow: create → draft → edit → submit → verify
python tests/test_handover_workflow.py

# With custom credentials
python tests/test_handover_workflow.py --user your_user --password your_pass -v
```

**What it tests:**
- Fill handover form with test data (incidents, KBs, change info, key points)
- Save as draft
- Open and verify draft
- Edit draft
- Submit final handover
- Verify in reports
- Check email delivery status

---

### 4. Quick Sanity Tests (28 tests) - Admin Recommended
```bash
# Combined quick checks (includes admin pages)
python tests/run_tests.py

# With credentials
python tests/run_tests.py --user superadmin --password admin123
```

---

## Run All Tests After Updates

```bash
# For regular users - run user tests + workflow
python tests/test_user_activities.py --user your_user --password your_pass
python tests/test_handover_workflow.py --user your_user --password your_pass

# For admins - run all tests
python tests/test_user_activities.py --user admin --password admin_pass
python tests/test_admin_activities.py --user admin --password admin_pass
python tests/test_handover_workflow.py --user admin --password admin_pass
```

## Production Testing

```bash
# User tests on production
python tests/test_user_activities.py --url https://prod-server.com --user user --password pass

# Admin tests on production
python tests/test_admin_activities.py --url https://prod-server.com --user admin --password pass

# Workflow test on production  
python tests/test_handover_workflow.py --url https://prod-server.com --user user --password pass
```

### 3. Run Full Test Suite with pytest
```bash
# Run all tests
pytest tests/test_application.py -v

# Generate HTML report
pytest tests/test_application.py -v --html=test_report.html --self-contained-html

# Run specific test class
pytest tests/test_application.py::TestPageAccessibility -v

# Run specific test
pytest tests/test_application.py::TestKeyPointsConsistency::test_no_duplicate_keypoints -v

# Stop on first failure
pytest tests/test_application.py -v -x
```

## Test Categories

### 1. Page Accessibility Tests
- Verifies all main pages return 200 status
- Tests: Dashboard, Handover Form, Reports, Key Points, Roster, etc.

### 2. Dashboard Tests
- Verifies dashboard loads and displays shift information
- Checks for key points section
- Validates engineer information display

### 3. Key Points Consistency Tests
- Checks for duplicate key points
- Verifies key points match between dashboard and key points page

### 4. Handover Form Tests
- Validates form structure and required fields
- Checks current/next shift engineers sections
- Verifies key points section exists

### 5. Draft Handover Tests
- Tests draft visibility in reports
- Validates draft filter functionality

### 6. Reports Tests
- Verifies reports page loads
- Checks filter options
- Validates shift data display

### 7. Email Monitoring Tests
- Tests email monitoring page accessibility
- Verifies email logs display
- Checks delivery status information

### 8. Multi-Team Filter Tests
- Tests team filtering on dashboard
- Validates team filter on reports
- Checks team filter on key points page

## Configuration

Edit `tests/config.py` to customize:
- Base URL
- Test user credentials
- Test account/team IDs
- Timeouts

## Test Report

After running with `--html=test_report.html`, open the generated HTML file in a browser to see a detailed test report.

## Adding New Tests

1. Add new test methods to existing classes or create new test classes in `test_application.py`
2. Follow the naming convention: `test_<description>`
3. Use the `admin_session` or `user_session` fixtures for authenticated requests

## Troubleshooting

### Login fails
- Check credentials in `tests/config.py`
- Ensure the application is running

### Timeout errors
- Increase `REQUEST_TIMEOUT` in `tests/config.py`
- Check network connectivity

### Tests fail unexpectedly
- Run with `-v` for verbose output
- Check if the application structure has changed
- Update CSS selectors in tests if needed

