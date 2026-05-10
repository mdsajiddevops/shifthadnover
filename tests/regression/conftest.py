"""
Shared pytest fixtures for the regression test suite.

All tests require a running application instance. Configure via environment:
    export TEST_BASE_URL=http://localhost:5000
    export TEST_SUPERADMIN_USER=superadmin
    export TEST_SUPERADMIN_PASSWORD=admin123
    export TEST_USER=ctctestuser
    export TEST_USER_PASSWORD=test123

Run the full suite:
    pytest tests/regression/ -v
Run a single file:
    pytest tests/regression/test_auth_rbac.py -v
"""
import os
import re
import sys

import pytest
import requests
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from tests.config import TestConfig


class AppSession:
    """Thin wrapper around requests.Session with login helpers."""

    def __init__(self, base_url=TestConfig.BASE_URL):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.logged_in = False
        self.username = None

    def csrf_token_from_html(self, html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        inp = soup.find("input", {"name": "csrf_token"})
        if inp:
            return inp.get("value", "")
        meta = soup.find("meta", {"name": re.compile(r"csrf", re.I)})
        if meta:
            return meta.get("content", "")
        return ""

    def login(self, username: str, password: str) -> bool:
        resp = self.session.get(
            f"{self.base_url}/login", timeout=TestConfig.REQUEST_TIMEOUT
        )
        token = self.csrf_token_from_html(resp.text)
        resp = self.session.post(
            f"{self.base_url}/login",
            data={"username": username, "password": password, "csrf_token": token},
            allow_redirects=True,
            timeout=TestConfig.REQUEST_TIMEOUT,
        )
        self.logged_in = resp.status_code == 200 and "/login" not in resp.url
        if self.logged_in:
            self.username = username
        return self.logged_in

    def logout(self):
        self.session.get(f"{self.base_url}/logout", timeout=TestConfig.REQUEST_TIMEOUT)
        self.logged_in = False

    def get(self, path: str, **kwargs) -> requests.Response:
        return self.session.get(
            f"{self.base_url}{path}", timeout=TestConfig.REQUEST_TIMEOUT, **kwargs
        )

    def post(self, path: str, data=None, json=None, **kwargs) -> requests.Response:
        return self.session.post(
            f"{self.base_url}{path}",
            data=data,
            json=json,
            timeout=TestConfig.REQUEST_TIMEOUT,
            **kwargs,
        )

    def put(self, path: str, json=None, **kwargs) -> requests.Response:
        return self.session.put(
            f"{self.base_url}{path}",
            json=json,
            timeout=TestConfig.REQUEST_TIMEOUT,
            **kwargs,
        )

    def delete(self, path: str, **kwargs) -> requests.Response:
        return self.session.delete(
            f"{self.base_url}{path}", timeout=TestConfig.REQUEST_TIMEOUT, **kwargs
        )

    def csrf_for_path(self, path: str):
        """Return (csrf_token, response) by loading the page first."""
        resp = self.get(path)
        return self.csrf_token_from_html(resp.text), resp

    def soup(self, path: str) -> BeautifulSoup:
        return BeautifulSoup(self.get(path).text, "html.parser")


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


@pytest.fixture(scope="module")
def admin_session():
    creds = TestConfig.TEST_USERS["super_admin"]
    s = AppSession()
    if not s.login(creds["username"], creds["password"]):
        pytest.skip("Could not login as super_admin — app unavailable or wrong creds")
    yield s
    s.logout()


@pytest.fixture(scope="module")
def user_session():
    creds = TestConfig.TEST_USERS["regular_user"]
    s = AppSession()
    if not s.login(creds["username"], creds["password"]):
        pytest.skip("Could not login as regular_user — app unavailable or wrong creds")
    yield s
    s.logout()


@pytest.fixture(scope="module")
def anon_session():
    """Unauthenticated session — never logged in."""
    return AppSession()
