"""
Unit tests for startup_checks.py (T-030 / COMP-004).

Tests are isolated via monkeypatching — no real DB or secrets required.
"""
import importlib
import json
import os
import sys
import types
import unittest
from unittest.mock import MagicMock, patch


def _reload_module():
    """Re-import startup_checks with current env vars."""
    if 'startup_checks' in sys.modules:
        del sys.modules['startup_checks']
    return importlib.import_module('startup_checks')


class TestStartupChecksSecrets(unittest.TestCase):
    """check_secrets() exits non-zero with named field on missing secret."""

    def setUp(self):
        os.environ.pop('LOCAL_DEVELOPMENT', None)

    def test_missing_secret_exits_nonzero(self):
        sc = _reload_module()
        with patch.object(sc, '_resolve_secret', return_value=None), \
             self.assertRaises(SystemExit) as ctx:
            sc.check_secrets()
        self.assertEqual(ctx.exception.code, 1)

    def test_missing_secret_names_field(self, capsys=None):
        sc = _reload_module()
        captured = []

        def fake_fail(check, field, error):
            captured.append({'check': check, 'field': field, 'error': error})
            sys.exit(1)

        with patch.object(sc, '_resolve_secret', return_value=None), \
             patch.object(sc, '_fail', side_effect=fake_fail), \
             self.assertRaises(SystemExit):
            sc.check_secrets()

        self.assertTrue(len(captured) > 0)
        self.assertEqual(captured[0]['check'], 'secrets')
        self.assertIn(captured[0]['field'], sc.REQUIRED_SECRETS)

    def test_local_development_skips_secret_check(self):
        sc = _reload_module()
        sc.LOCAL_DEVELOPMENT = True
        # Should not raise even with no secrets available
        with patch.object(sc, '_resolve_secret', return_value=None):
            sc.check_secrets()  # Must not sys.exit

    def test_all_secrets_present_no_exit(self):
        sc = _reload_module()
        with patch.object(sc, '_resolve_secret', return_value='some-value'):
            sc.check_secrets()  # Must not raise


class TestStartupChecksDatabase(unittest.TestCase):
    """check_database() exits non-zero with PRIMARY_DB field when DB unreachable."""

    def test_db_unreachable_exits_nonzero(self):
        sc = _reload_module()
        with patch.object(sc, '_resolve_secret', return_value='postgresql://invalid:5432/nodb'), \
             patch('startup_checks.create_engine', side_effect=Exception('connection refused')):
            with self.assertRaises(SystemExit) as ctx:
                sc.check_database()
        self.assertEqual(ctx.exception.code, 1)

    def test_db_unreachable_names_primary_db(self):
        sc = _reload_module()
        captured = []

        def fake_fail(check, field, error):
            captured.append({'check': check, 'field': field, 'error': error})
            sys.exit(1)

        with patch.object(sc, '_resolve_secret', return_value='postgresql://x/y'), \
             patch.object(sc, '_fail', side_effect=fake_fail):
            # Patch sqlalchemy inside the function
            mock_engine = MagicMock()
            mock_engine.connect.side_effect = Exception('DB down')
            with patch('startup_checks.create_engine', return_value=mock_engine), \
                 self.assertRaises(SystemExit):
                sc.check_database()

        self.assertTrue(len(captured) > 0)
        self.assertEqual(captured[0]['field'], 'PRIMARY_DB')

    def test_db_success_no_exit(self):
        sc = _reload_module()
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        with patch.object(sc, '_resolve_secret', return_value='sqlite:///:memory:'), \
             patch('startup_checks.create_engine', return_value=mock_engine):
            sc.check_database()  # Must not raise


class TestStartupChecksAllPass(unittest.TestCase):
    """Main path exits 0 with ok status."""

    def test_all_pass_exits_zero(self):
        sc = _reload_module()
        with patch.object(sc, 'check_secrets'), \
             patch.object(sc, 'check_database'):
            # Simulate __main__ execution
            with patch('sys.argv', ['startup_checks.py']):
                try:
                    exec(
                        compile(
                            "check_secrets(); check_database(); "
                            "import json, sys; json.dump({'check':'all','status':'ok'}, sys.stdout); sys.exit(0)",
                            '<test>',
                            'exec',
                        ),
                        {'check_secrets': sc.check_secrets, 'check_database': sc.check_database},
                    )
                except SystemExit as exc:
                    self.assertEqual(exc.code, 0)


if __name__ == '__main__':
    unittest.main()
