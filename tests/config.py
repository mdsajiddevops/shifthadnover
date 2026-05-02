"""
Test Configuration for Shift Handover Application

Credentials are read from environment variables so they are never hardcoded
for network-accessible environments. The fallback values only work against
a locally seeded dev instance (localhost:5000).

Export before running:
    export TEST_SUPERADMIN_PASSWORD=<your-superadmin-password>
    export TEST_ADMIN_PASSWORD=<your-admin-password>
    export TEST_USER_PASSWORD=<your-user-password>
    export TEST_BASE_URL=http://localhost:5000   # optional
"""
import os


class TestConfig:
    BASE_URL = os.environ.get('TEST_BASE_URL', 'http://localhost:5000')

    TEST_USERS = {
        'super_admin': {
            'username': os.environ.get('TEST_SUPERADMIN_USER', 'superadmin'),
            'password': os.environ.get('TEST_SUPERADMIN_PASSWORD', 'admin123'),
        },
        'account_admin': {
            'username': os.environ.get('TEST_ADMIN_USER', 'accountadmin'),
            'password': os.environ.get('TEST_ADMIN_PASSWORD', 'admin123'),
        },
        'regular_user': {
            'username': os.environ.get('TEST_USER', 'ctctestuser'),
            'password': os.environ.get('TEST_USER_PASSWORD', 'test123'),
        },
    }

    TEST_ACCOUNT_ID = int(os.environ.get('TEST_ACCOUNT_ID', 1))
    TEST_TEAM_ID = int(os.environ.get('TEST_TEAM_ID', 1))

    REQUEST_TIMEOUT = 30
    PAGE_LOAD_TIMEOUT = 10

    TEST_INCIDENT = {
        'title': '[Test App] TEST-001',
        'description': 'Automated test incident',
        'status': 'Open',
    }

    TEST_KEY_POINT = {
        'description': 'Automated test key point - please ignore',
        'status': 'Open',
        'jira_id': 'TEST-KP-001',
    }
