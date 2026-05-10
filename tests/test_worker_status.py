"""
Unit tests for services/worker_status.py (T-023 / COMP-011).

Verifies that get_worker_status() never raises and correctly maps Celery
inspect output to WorkerStatusResult, including all failure paths.
"""
import unittest
from unittest.mock import MagicMock, patch


def _make_celery_with_active(active_return):
    """Build a mock celery instance whose inspect().active() returns active_return."""
    mock_inspect = MagicMock()
    mock_inspect.active.return_value = active_return
    mock_celery = MagicMock()
    mock_celery.control.inspect.return_value = mock_inspect
    return mock_celery


def _make_celery_with_side_effect(exc):
    """Build a mock celery instance whose inspect().active() raises exc."""
    mock_inspect = MagicMock()
    mock_inspect.active.side_effect = exc
    mock_celery = MagicMock()
    mock_celery.control.inspect.return_value = mock_inspect
    return mock_celery


class TestWorkerStatusHealthy(unittest.TestCase):
    """Happy path: inspect returns worker data → available=True."""

    def test_healthy_inspect_returns_correct_counts(self):
        active_data = {
            'worker1@host': [{'id': 'abc'}, {'id': 'def'}],
            'worker2@host': [{'id': 'ghi'}],
        }
        mock_celery = _make_celery_with_active(active_data)

        import services.worker_status as wm
        with patch.object(wm, '_get_celery', return_value=mock_celery):
            result = wm.get_worker_status()

        self.assertTrue(result['available'])
        self.assertEqual(result['worker_count'], 2)
        self.assertEqual(result['active_tasks'], 3)
        self.assertIsNone(result['error'])

    def test_single_worker_no_tasks(self):
        mock_celery = _make_celery_with_active({'worker1@host': []})

        import services.worker_status as wm
        with patch.object(wm, '_get_celery', return_value=mock_celery):
            result = wm.get_worker_status()

        self.assertTrue(result['available'])
        self.assertEqual(result['worker_count'], 1)
        self.assertEqual(result['active_tasks'], 0)


class TestWorkerStatusDegraded(unittest.TestCase):
    """All failure paths must return available=False without raising."""

    def _call(self, exc_or_none):
        import services.worker_status as wm
        if exc_or_none is None:
            mock_celery = _make_celery_with_active(None)
        else:
            mock_celery = _make_celery_with_side_effect(exc_or_none)
        with patch.object(wm, '_get_celery', return_value=mock_celery):
            return wm.get_worker_status()

    def test_connection_error_returns_degraded(self):
        result = self._call(ConnectionError("broker down"))
        self.assertFalse(result['available'])
        self.assertEqual(result['worker_count'], 0)
        self.assertEqual(result['active_tasks'], 0)
        self.assertIsNotNone(result['error'])

    def test_connection_error_does_not_raise(self):
        try:
            self._call(ConnectionError("broker down"))
        except Exception as e:
            self.fail(f"get_worker_status() raised: {e}")

    def test_timeout_error_returns_degraded(self):
        result = self._call(TimeoutError("inspect timed out"))
        self.assertFalse(result['available'])
        self.assertEqual(result['worker_count'], 0)

    def test_none_response_returns_degraded(self):
        result = self._call(None)
        self.assertFalse(result['available'])
        self.assertEqual(result['worker_count'], 0)
        self.assertEqual(result['active_tasks'], 0)

    def test_generic_exception_returns_degraded(self):
        result = self._call(RuntimeError("unexpected error"))
        self.assertFalse(result['available'])

    def test_warning_log_emitted_on_failure(self):
        import services.worker_status as wm
        mock_celery = _make_celery_with_side_effect(ConnectionError("broker down"))
        with patch.object(wm, '_get_celery', return_value=mock_celery):
            with self.assertLogs('services.worker_status', level='WARNING') as cm:
                wm.get_worker_status()
        self.assertTrue(any('WORKER_STATUS_CHECK_FAILED' in line for line in cm.output))

    def test_timeout_does_not_raise(self):
        try:
            self._call(TimeoutError("timeout"))
        except Exception as e:
            self.fail(f"get_worker_status() raised: {e}")


if __name__ == '__main__':
    unittest.main()
