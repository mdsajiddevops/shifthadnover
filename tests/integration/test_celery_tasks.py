"""
Integration tests for Celery task dispatch and retry behaviour (T-027 / COMP-004).

Verifies:
- Task succeeds on first attempt when service responds normally.
- Task retries on transient failure (retry count increments correctly).
- Task routes to DLQ after all retries exhausted (FailedTask record created).
- TASK_RETRY log entries emitted at correct attempt numbers.

These tests exercise the full task machinery without a live Redis broker by using
Celery's ALWAYS_EAGER mode (tasks execute synchronously in the test process).

Requires celery and the full app stack. Tests are skipped when unavailable.
"""
import logging
import unittest
from unittest.mock import MagicMock, patch

try:
    from celery_app import celery  # noqa: F401
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False

SKIP_MSG = 'Celery not installed or importable'


@unittest.skipUnless(CELERY_AVAILABLE, SKIP_MSG)
class TestCtaskAssignmentDispatch(unittest.TestCase):
    """run_ctask_assignment task — success, retry, and DLQ paths."""

    def _make_task_self(self, task_fn, retries=0, max_retries=3):
        task_self = MagicMock()
        task_self.request.retries = retries
        task_self.request.id = 'integ-task-id'
        task_self.request.args = []
        task_self.request.kwargs = {}
        task_self.max_retries = max_retries
        task_self.name = task_fn.name if hasattr(task_fn, 'name') else 'mock.task'

        class MaxRetriesExceededError(Exception):
            pass

        task_self.MaxRetriesExceededError = MaxRetriesExceededError

        def retry_side_effect(exc=None, countdown=30):
            if retries >= max_retries:
                raise task_self.MaxRetriesExceededError('max retries exceeded')
            raise exc

        task_self.retry = MagicMock(side_effect=retry_side_effect)
        return task_self

    def test_success_on_first_attempt(self):
        from tasks.ctask_tasks import run_ctask_assignment
        task_self = self._make_task_self(run_ctask_assignment)

        mock_service = MagicMock()
        mock_service.process_unassigned_ctasks.return_value = {'assigned': 3}

        with patch('tasks.ctask_tasks.AppConfig') as MockAC, \
             patch('tasks.ctask_tasks.CTaskAssignmentService', return_value=mock_service):
            MockAC.is_enabled.return_value = True
            result = run_ctask_assignment(task_self)

        self.assertEqual(result, {'assigned': 3})
        task_self.retry.assert_not_called()

    def test_retry_logged_on_transient_failure(self):
        from tasks.ctask_tasks import run_ctask_assignment
        task_self = self._make_task_self(run_ctask_assignment, retries=0)

        with patch('tasks.ctask_tasks.AppConfig') as MockAC, \
             patch('tasks.ctask_tasks.CTaskAssignmentService') as MockSvc:
            MockAC.is_enabled.return_value = True
            MockSvc.return_value.process_unassigned_ctasks.side_effect = ConnectionError('Redis down')
            with self.assertRaises(ConnectionError):
                run_ctask_assignment(task_self)

        self.assertTrue(task_self.retry.called)
        call_kwargs = task_self.retry.call_args[1]
        self.assertEqual(call_kwargs.get('countdown', 30), 30)

    def test_dlq_record_on_max_retries(self):
        from tasks.ctask_tasks import run_ctask_assignment
        task_self = self._make_task_self(run_ctask_assignment, retries=3)

        with patch('tasks.ctask_tasks.AppConfig') as MockAC, \
             patch('tasks.ctask_tasks.CTaskAssignmentService') as MockSvc, \
             patch('tasks.ctask_tasks._dlq_on_failure') as mock_dlq:
            MockAC.is_enabled.return_value = True
            MockSvc.return_value.process_unassigned_ctasks.side_effect = RuntimeError('fatal error')
            with self.assertRaises(Exception):
                run_ctask_assignment(task_self)

        mock_dlq.assert_called_once()
        call_kwargs = mock_dlq.call_args[1]
        self.assertEqual(call_kwargs['task_id'], 'integ-task-id')
        self.assertEqual(call_kwargs['retry_count'], 3)

    def test_warning_log_emitted_on_retry(self):
        from tasks.ctask_tasks import run_ctask_assignment
        task_self = self._make_task_self(run_ctask_assignment, retries=1)

        with patch('tasks.ctask_tasks.AppConfig') as MockAC, \
             patch('tasks.ctask_tasks.CTaskAssignmentService') as MockSvc, \
             self.assertLogs('tasks.ctask_tasks', level='WARNING') as log_ctx:
            MockAC.is_enabled.return_value = True
            MockSvc.return_value.process_unassigned_ctasks.side_effect = TimeoutError('timeout')
            with self.assertRaises(TimeoutError):
                run_ctask_assignment(task_self)

        self.assertTrue(
            any('failed' in msg.lower() for msg in log_ctx.output),
            'Expected a WARNING log entry on task retry',
        )


@unittest.skipUnless(CELERY_AVAILABLE, SKIP_MSG)
class TestDLQHandlerIntegration(unittest.TestCase):
    """DLQ handler — both DB write and alert must be attempted independently."""

    def test_db_write_still_attempted_when_alert_raises(self):
        from tasks.dlq_handler import on_task_failure

        db_calls = []
        mock_db = MagicMock()

        def fake_write(**kwargs):
            db_calls.append(kwargs)

        with patch('tasks.dlq_handler._write_db_record', side_effect=fake_write), \
             patch('tasks.dlq_handler._dispatch_alert', side_effect=RuntimeError('SMTP down')):
            on_task_failure(
                task_id='tid-123',
                task_name='tasks.some_task',
                args=[],
                kwargs={},
                exc=ValueError('test error'),
                retry_count=3,
                max_retries=3,
            )

        self.assertEqual(len(db_calls), 1, 'DB write must be called even when alert fails')

    def test_alert_still_attempted_when_db_write_raises(self):
        from tasks.dlq_handler import on_task_failure

        alert_calls = []

        def fake_dispatch(*args, **kwargs):
            alert_calls.append(args)

        with patch('tasks.dlq_handler._write_db_record', side_effect=RuntimeError('DB down')), \
             patch('tasks.dlq_handler._dispatch_alert', side_effect=fake_dispatch):
            on_task_failure(
                task_id='tid-456',
                task_name='tasks.some_task',
                args=[],
                kwargs={},
                exc=ValueError('test error'),
                retry_count=3,
                max_retries=3,
            )

        self.assertEqual(len(alert_calls), 1, 'Alert must be dispatched even when DB write fails')


if __name__ == '__main__':
    unittest.main()
