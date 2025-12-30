"""
Test Configuration for Shift Handover Application
"""

# Test Environment Configuration
class TestConfig:
    # Base URL for the application
    BASE_URL = "http://localhost:5000"
    
    # Test user credentials
    TEST_USERS = {
        "super_admin": {
            "username": "superadmin",
            "password": "admin123"
        },
        "account_admin": {
            "username": "accountadmin",
            "password": "admin123"
        },
        "regular_user": {
            "username": "ctctestuser",
            "password": "test123"
        }
    }
    
    # Test team/account IDs (update based on your database)
    TEST_ACCOUNT_ID = 1
    TEST_TEAM_ID = 1
    
    # Timeouts
    REQUEST_TIMEOUT = 30
    PAGE_LOAD_TIMEOUT = 10
    
    # Test data
    TEST_INCIDENT = {
        "title": "[Test App] TEST-001",
        "description": "Automated test incident",
        "status": "Open"
    }
    
    TEST_KEY_POINT = {
        "description": "Automated test key point - please ignore",
        "status": "Open",
        "jira_id": "TEST-KP-001"
    }

