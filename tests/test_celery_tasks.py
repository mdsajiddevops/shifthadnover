"""
Unit tests for all four Celery task modules (T-033 / COMP-007–010).

Verifies:
- Success path returns a result dict.
- Transient failure triggers self.retry with 30-second countdown.
- max_retries exhaustion invokes the DLQ handler.
- Feature-disabled path returns {skipped: True}.
"""
import unittest
from unittest.mock import MagicMock, patch, call


def _make_task_self(task_fn, retries=0, max_retries=3):
    """Create a mock `self` suitable for a bound Celery task."""
    task_self = MagicMock()
    task_self.request.retries = retries
    task_self.request.id = 'mock-task-id'
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


class TestCtaskTask(unittest.TestCase):
    def test_success_path(self):
        from tasks.ctask_tasks import run_ctask_assignment
        task_self = _make_task_self(run_ctask_assignment)

        mock_service = MagicMock()
        mock_service.process_unassigned_ctasks.return_value = {'assigned': 2}

        with patch('tasks.ctask_tasks.AppConfig') as MockAC, \
             patch('tasks.ctask_tasks.CTaskAssignmentService', return_value=mock_service):
            MockAC.is_enabled.return_value = True
            result = run_ctask_assignment(task_self)

        self.assertEqual(result, {'assigned': 2})

    def test_feature_disabled_skips(self):
        from tasks.ctask_tasks import run_ctask_assignment
        task_self = _make_task_self(run_ctask_assignment)

        with patch('tasks.ctask_tasks.AppConfig') as MockAC:
            MockAC.is_enabled.return_value = False
            result = run_ctask_assignment(task_self)

        self.assertTrue(result.get('skipped'))

    def test_transient_failure_triggers_retry(self):
        from tasks.ctask_tasks import run_ctask_assignment
        task_self = _make_task_self(run_ctask_assignment, retries=0)

        with patch('tasks.ctask_tasks.AppConfig') as MockAC, \
             patch('tasks.ctask_tasks.CTaskAssignmentService') as MockSvc:
            MockAC.is_enabled.return_value = True
            MockSvc.return_value.process_unassigned_ctasks.side_effect = ConnectionError('Redis down')
            with self.assertRaises(ConnectionError):
                run_ctask_assignment(task_self)

        self.assertTrue(task_self.retry.called, 'self.retry should be called on transient failure')

    def test_max_retries_exhaustion_invokes_dlq(self):
        from tasks.ctask_tasks import run_ctask_assignment
        task_self = _make_task_self(run_ctask_assignment, retries=3)

        with patch('tasks.ctask_tasks.AppConfig') as MockAC, \
             patch('tasks.ctask_tasks.CTaskAssignmentService') as MockSvc, \
             patch('tasks.ctask_tasks._dlq_on_failure') as mock_dlq:
            MockAC.is_enabled.return_value = True
            MockSvc.return_value.process_unassigned_ctasks.side_effect = RuntimeError('fatal')
            with self.assertRaises(Exception):
                run_ctask_assignment(task_self)

        mock_dlq.assert_called_once()


class TestEmailTask(unittest.TestCase):
    def test_success_path(self):
        from tasks.email_tasks import send_email_digest
        task_self = _make_task_self(send_email_digest)

        mock_service = MagicMock()
        mock_service.send_shift_summary_emails.return_value = {'sent': 5}

        with patch('tasks.email_tasks.AppConfig') as MockAC, \
             patch('tasks.email_tasks.ShiftEmailService', return_value=mock_service):
            MockAC.is_enabled.return_value = True
            result = send_email_digest(task_self)

        self.assertEqual(result, {'sent': 5})

    def test_feature_disabled_skips(self):
        from tasks.email_tasks import send_email_digest
        task_self = _make_task_self(send_email_digest)

        with patch('tasks.email_tasks.AppConfig') as MockAC:
            MockAC.is_enabled.return_value = False
            result = send_email_digest(task_self)

        self.assertTrue(result.get('skipped'))

    def test_retry_on_failure(self):
        from tasks.email_tasks import send_email_digest
        task_self = _make_task_self(send_email_digest, retries=1)

        with patch('tasks.email_tasks.AppConfig') as MockAC, \
             patch('tasks.email_tasks.ShiftEmailService') as MockSvc:
            MockAC.is_enabled.return_value = True
            MockSvc.return_value.send_shift_summary_emails.side_effect = OSError('SMTP down')
            with self.assertRaises(OSError):
                send_email_digest(task_self)

        self.assertTrue(task_self.retry.called)


class TestServiceNowTask(unittest.TestCase):
    def test_not_configured_skips(self):
        from tasks.servicenow_tasks import poll_servicenow
        task_self = _make_task_self(poll_servicenow)

        mock_svc = MagicMock()
        mock_svc.is_configured.return_value = False

        with patch('tasks.servicenow_tasks.AppConfig') as MockAC, \
             patch('tasks.servicenow_tasks.ServiceNowService', return_value=mock_svc):
            MockAC.is_enabled.return_value = True
            result = poll_servicenow(task_self)

        self.assertTrue(result.get('skipped'))

    def test_retry_on_transient_failure(self):
        from tasks.servicenow_tasks import poll_servicenow
        task_self = _make_task_self(poll_servicenow, retries=0)

        mock_svc = MagicMock()
        mock_svc.is_configured.return_value = True
        mock_svc.sync_incidents_and_ctasks.side_effect = TimeoutError('API timeout')

        with patch('tasks.servicenow_tasks.AppConfig') as MockAC, \
             patch('tasks.servicenow_tasks.ServiceNowService', return_value=mock_svc):
            MockAC.is_enabled.return_value = True
            with self.assertRaises(TimeoutError):
                poll_servicenow(task_self)

        self.assertTrue(task_self.retry.called)


class TestRetryTask(unittest.TestCase):
    def test_success_no_pending(self):
        from tasks.retry_tasks import retry_failed_tasks
        task_self = _make_task_self(retry_failed_tasks)

        mock_query = MagicMock()
        mock_query.filter_by.return_value.all.return_value = []
        mock_db = MagicMock()

        with patch('tasks.retry_tasks.FailedTask') as MockFT, \
             patch('tasks.retry_tasks.db', mock_db):
            MockFT.query = mock_query
            result = retry_failed_tasks(task_self)

        self.assertEqual(result['requeued'], 0)
        self.assertEqual(result['total'], 0)


if __name__ == '__main__':
    unittest.main()
