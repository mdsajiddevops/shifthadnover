"""
Unit tests for services/ctask_scheduler.py (T-034 / COMP-012).

Verifies:
- get_scheduler_status() returns structured dict within 5 s with/without broker.
- force_scheduler_check() enqueues a Celery task.
- start/stop functions log appropriately (no-op, Celery manages scheduling).
"""
import time
import unittest
from unittest.mock import MagicMock, patch


class TestGetSchedulerStatus(unittest.TestCase):
    def test_returns_dict_with_broker_available(self):
        mock_celery = MagicMock()
        mock_inspect = MagicMock()
        mock_inspect.active.return_value = {'worker@host': []}
        mock_celery.control.inspect.return_value = mock_inspect

        with patch('services.ctask_scheduler.celery', mock_celery):
            from services.ctask_scheduler import get_scheduler_status
            status = get_scheduler_status()

        self.assertIn('running', status)
        self.assertIn('status', status)
        self.assertIn('engine', status)
        self.assertEqual(status['engine'], 'celery')

    def test_completes_within_five_seconds(self):
        mock_celery = MagicMock()
        mock_inspect = MagicMock()
        mock_inspect.active.return_value = {'worker@host': []}
        mock_celery.control.inspect.return_value = mock_inspect

        with patch('services.ctask_scheduler.celery', mock_celery):
            from services.ctask_scheduler import get_scheduler_status
            start = time.monotonic()
            get_scheduler_status()
            elapsed = time.monotonic() - start

        self.assertLess(elapsed, 5.0, f'get_scheduler_status took {elapsed:.2f}s (limit 5s)')

    def test_returns_degraded_dict_when_broker_unavailable(self):
        mock_celery = MagicMock()
        mock_celery.control.inspect.side_effect = Exception('Connection refused')

        with patch('services.ctask_scheduler.celery', mock_celery):
            from services.ctask_scheduler import get_scheduler_status
            status = get_scheduler_status()

        self.assertFalse(status['running'])
        self.assertIn('engine', status)

    def test_does_not_raise_when_broker_unavailable(self):
        mock_celery = MagicMock()
        mock_celery.control.inspect.side_effect = Exception('Broker down')

        with patch('services.ctask_scheduler.celery', mock_celery):
            from services.ctask_scheduler import get_scheduler_status
            # Must not raise — returns degraded dict instead (REQ-004)
            status = get_scheduler_status()

        self.assertIsInstance(status, dict)

    def test_degraded_dict_completes_within_five_seconds(self):
        mock_celery = MagicMock()
        mock_inspect = MagicMock()
        mock_inspect.active.return_value = None  # Simulates no workers
        mock_celery.control.inspect.return_value = mock_inspect

        with patch('services.ctask_scheduler.celery', mock_celery):
            from services.ctask_scheduler import get_scheduler_status
            start = time.monotonic()
            get_scheduler_status()
            elapsed = time.monotonic() - start

        self.assertLess(elapsed, 5.0)


class TestForceSchedulerCheck(unittest.TestCase):
    def test_enqueues_task_via_delay(self):
        mock_task = MagicMock()
        mock_result = MagicMock()
        mock_result.id = 'task-abc-123'
        mock_task.delay.return_value = mock_result

        with patch('services.ctask_scheduler.run_ctask_assignment', mock_task):
            from services.ctask_scheduler import force_scheduler_check
            result = force_scheduler_check()

        mock_task.delay.assert_called_once()
        self.assertTrue(result['dispatched'])
        self.assertEqual(result['task_id'], 'task-abc-123')


class TestStartStopNoOp(unittest.TestCase):
    def test_start_does_not_raise(self):
        from services.ctask_scheduler import start_ctask_scheduler
        start_ctask_scheduler()  # Should be a no-op, not raise

    def test_stop_does_not_raise(self):
        from services.ctask_scheduler import stop_ctask_scheduler
        stop_ctask_scheduler()  # Should be a no-op, not raise


if __name__ == '__main__':
    unittest.main()
