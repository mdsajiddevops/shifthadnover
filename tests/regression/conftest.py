"""
Pytest fixtures for regression tests.
Provides admin_session and user_session with full HTTP verb support.
"""
import pytest
import requests
from bs4 import BeautifulSoup

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from tests.config import TestConfig


class TestSession:
    """Authenticated HTTP session for regression tests."""

    def __init__(self, base_url=TestConfig.BASE_URL):
        self.base_url = base_url.rstrip('/')
        self.session  = requests.Session()
        self.logged_in = False

    def login(self, username, password):
        login_url = f"{self.base_url}/login"
        resp = self.session.get(login_url, timeout=TestConfig.REQUEST_TIMEOUT)
        soup = BeautifulSoup(resp.text, 'html.parser')
        csrf = soup.find('input', {'name': 'csrf_token'})
        csrf_value = csrf['value'] if csrf else ''
        resp = self.session.post(
            login_url,
            data={
                'username': username,
                'password': password,
                'csrf_token': csrf_value,
                'account_id': TestConfig.TEST_ACCOUNT_ID,
                'team_id': TestConfig.TEST_TEAM_ID,
            },
            timeout=TestConfig.REQUEST_TIMEOUT,
            allow_redirects=True,
        )
        self.logged_in = resp.status_code == 200 and '/login' not in resp.url
        return self.logged_in

    def get(self, endpoint, **kwargs):
        return self.session.get(
            f"{self.base_url}{endpoint}",
            timeout=TestConfig.REQUEST_TIMEOUT, **kwargs
        )

    def post(self, endpoint, **kwargs):
        return self.session.post(
            f"{self.base_url}{endpoint}",
            timeout=TestConfig.REQUEST_TIMEOUT, **kwargs
        )

    def put(self, endpoint, **kwargs):
        return self.session.put(
            f"{self.base_url}{endpoint}",
            timeout=TestConfig.REQUEST_TIMEOUT, **kwargs
        )

    def delete(self, endpoint, **kwargs):
        return self.session.delete(
            f"{self.base_url}{endpoint}",
            timeout=TestConfig.REQUEST_TIMEOUT, **kwargs
        )

    def logout(self):
        self.session.get(f"{self.base_url}/logout")
        self.logged_in = False


@pytest.fixture(scope='module')
def admin_session():
    creds = TestConfig.TEST_USERS['super_admin']
    s = TestSession()
    if not s.login(creds['username'], creds['password']):
        pytest.skip('Admin login failed — check credentials and app availability')
    yield s
    s.logout()


@pytest.fixture(scope='module')
def user_session():
    creds = TestConfig.TEST_USERS['regular_user']
    s = TestSession()
    if not s.login(creds['username'], creds['password']):
        pytest.skip('Regular user login failed — check credentials and app availability')
    yield s
    s.logout()
