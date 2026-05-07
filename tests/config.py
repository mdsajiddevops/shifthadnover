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
from urllib.parse import urlparse


class ConfigurationError(Exception):
    """Raised when test credentials are unsafe for a non-localhost target."""


def _is_localhost(url: str) -> bool:
    host = urlparse(url).hostname or ''
    return host in ('localhost', '127.0.0.1', '::1')


def _safe_credential(env_var: str, sentinel: str, base_url: str, label: str) -> str:
    """Return env var value, or sentinel if targeting localhost only.

    Raises ConfigurationError when the target is not localhost and the env
    var is unset — prevents sentinel credentials reaching a remote system.
    """
    value = os.environ.get(env_var)
    if value is not None:
        return value
    if _is_localhost(base_url):
        return sentinel
    raise ConfigurationError(
        f"{label}: environment variable {env_var!r} is not set but "
        f"TEST_BASE_URL={base_url!r} targets a non-localhost host. "
        "Set the variable before running tests against a remote target."
    )


class TestConfig:
    BASE_URL = os.environ.get('TEST_BASE_URL', 'http://localhost:5000')

    TEST_USERS = {
        'super_admin': {
            'username': os.environ.get('TEST_SUPERADMIN_USER', 'superadmin'),
            'password': _safe_credential(
                'TEST_SUPERADMIN_PASSWORD', 'admin123', BASE_URL, 'super_admin password'
            ),
        },
        'account_admin': {
            'username': os.environ.get('TEST_ADMIN_USER', 'accountadmin'),
            'password': _safe_credential(
                'TEST_ADMIN_PASSWORD', 'admin123', BASE_URL, 'account_admin password'
            ),
        },
        'regular_user': {
            'username': os.environ.get('TEST_USER', 'ctctestuser'),
            'password': _safe_credential(
                'TEST_USER_PASSWORD', 'test123', BASE_URL, 'regular_user password'
            ),
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
