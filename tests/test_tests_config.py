"""
Unit tests for tests/config.py (T-038 / COMP-019).

Verifies:
- Env vars set → credential values match env vars.
- Env vars unset + localhost target → sentinel fallbacks used.
- Env vars unset + non-localhost target → ConfigurationError raised before credential transmitted.
"""
import importlib
import os
import sys
import unittest
from unittest.mock import patch


def _reload_config(env: dict, clear_vars=None):
    """Reload tests.config with specific environment variables."""
    if 'tests.config' in sys.modules:
        del sys.modules['tests.config']

    base_env = dict(os.environ)
    for var in (clear_vars or []):
        base_env.pop(var, None)
    base_env.update(env)

    with patch.dict(os.environ, base_env, clear=True):
        return importlib.import_module('tests.config')


class TestTestsConfigEnvVarsSet(unittest.TestCase):
    """When env vars are set, credential values match exactly."""

    def test_superadmin_password_from_env(self):
        mod = _reload_config({'TEST_SUPERADMIN_PASSWORD': 'secret-sa', 'TEST_BASE_URL': 'http://localhost:5000'})
        self.assertEqual(mod.TestConfig.TEST_USERS['super_admin']['password'], 'secret-sa')

    def test_admin_password_from_env(self):
        mod = _reload_config({'TEST_ADMIN_PASSWORD': 'secret-adm', 'TEST_BASE_URL': 'http://localhost:5000'})
        self.assertEqual(mod.TestConfig.TEST_USERS['account_admin']['password'], 'secret-adm')

    def test_user_password_from_env(self):
        mod = _reload_config({'TEST_USER_PASSWORD': 'secret-usr', 'TEST_BASE_URL': 'http://localhost:5000'})
        self.assertEqual(mod.TestConfig.TEST_USERS['regular_user']['password'], 'secret-usr')


class TestTestsConfigLocalhostFallback(unittest.TestCase):
    """Unset env vars + localhost target → sentinel values used (not an error)."""

    def test_sentinel_fallback_for_superadmin(self):
        mod = _reload_config(
            {'TEST_BASE_URL': 'http://localhost:5000'},
            clear_vars=['TEST_SUPERADMIN_PASSWORD', 'TEST_ADMIN_PASSWORD', 'TEST_USER_PASSWORD'],
        )
        self.assertEqual(mod.TestConfig.TEST_USERS['super_admin']['password'], 'admin123')

    def test_sentinel_fallback_for_regular_user(self):
        mod = _reload_config(
            {'TEST_BASE_URL': 'http://127.0.0.1:5000'},
            clear_vars=['TEST_USER_PASSWORD'],
        )
        self.assertEqual(mod.TestConfig.TEST_USERS['regular_user']['password'], 'test123')


class TestTestsConfigNonLocalhostGuard(unittest.TestCase):
    """Unset env vars + non-localhost target → ConfigurationError before credential transmitted."""

    def _assert_raises_config_error(self, base_url: str, missing_var: str):
        if 'tests.config' in sys.modules:
            del sys.modules['tests.config']

        env = dict(os.environ)
        env.pop(missing_var, None)
        env['TEST_BASE_URL'] = base_url

        with patch.dict(os.environ, env, clear=True):
            with self.assertRaises(Exception) as ctx:
                importlib.import_module('tests.config')

        exc_type_name = type(ctx.exception).__name__
        self.assertIn('ConfigurationError', exc_type_name, f'Expected ConfigurationError, got {exc_type_name}')

    def test_non_localhost_missing_superadmin_password_raises(self):
        self._assert_raises_config_error('http://10.0.0.1:5000', 'TEST_SUPERADMIN_PASSWORD')

    def test_non_localhost_missing_admin_password_raises(self):
        self._assert_raises_config_error('http://staging.example.com:5000', 'TEST_ADMIN_PASSWORD')

    def test_non_localhost_missing_user_password_raises(self):
        self._assert_raises_config_error('https://prod.example.com', 'TEST_USER_PASSWORD')


if __name__ == '__main__':
    unittest.main()
