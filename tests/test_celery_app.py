"""
Unit tests for celery_app.py (T-031 / COMP-005).

Verifies broker URL is read from environment variables and that missing
env vars fall back to the documented default.
"""
import importlib
import os
import sys
import unittest
import unittest.mock
from unittest.mock import patch


def _reload_celery_app(env: dict):
    """Re-import celery_app with a clean env."""
    for mod in list(sys.modules.keys()):
        if mod in ('celery_app', 'celeryconfig'):
            del sys.modules[mod]
    with patch.dict(os.environ, env, clear=False):
        return importlib.import_module('celery_app')


class TestCeleryAppBrokerURL(unittest.TestCase):
    """Broker URL is read exclusively from CELERY_BROKER_URL env var."""

    def test_broker_url_from_env(self):
        mod = _reload_celery_app({'CELERY_BROKER_URL': 'redis://myhost:6380/1'})
        self.assertEqual(mod.BROKER_URL, 'redis://myhost:6380/1')

    def test_backend_url_from_env(self):
        mod = _reload_celery_app({'CELERY_RESULT_BACKEND': 'redis://backendhost:6379/2'})
        self.assertEqual(mod.RESULT_BACKEND, 'redis://backendhost:6379/2')

    def test_default_broker_url_when_env_unset(self):
        env = {k: v for k, v in os.environ.items() if k != 'CELERY_BROKER_URL'}
        for mod in list(sys.modules.keys()):
            if mod in ('celery_app', 'celeryconfig'):
                del sys.modules[mod]
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop('CELERY_BROKER_URL', None)
            mod = importlib.import_module('celery_app')
        self.assertEqual(mod.BROKER_URL, 'redis://redis:6379/0')

    def test_celery_instance_uses_broker_url(self):
        mod = _reload_celery_app({'CELERY_BROKER_URL': 'redis://testbroker:6379/0'})
        self.assertEqual(mod.celery.conf.broker_url, 'redis://testbroker:6379/0')


class TestCeleryAppContextTask(unittest.TestCase):
    """Flask app context is applied via ContextTask.__call__."""

    def test_context_task_calls_with_app_context(self):
        mod = _reload_celery_app({})

        mock_app = unittest.mock.MagicMock()
        ctx_manager = unittest.mock.MagicMock()
        mock_app.app_context.return_value = ctx_manager
        ctx_manager.__enter__ = unittest.mock.MagicMock(return_value=None)
        ctx_manager.__exit__ = unittest.mock.MagicMock(return_value=False)

        task = mod.ContextTask()
        task._flask_app = mock_app
        task.run = unittest.mock.MagicMock(return_value='ok')

        result = task.__call__()
        mock_app.app_context.assert_called_once()
        self.assertEqual(result, 'ok')


if __name__ == '__main__':
    unittest.main()
