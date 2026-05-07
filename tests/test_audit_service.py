"""
Unit tests for services/audit_service.py (T-037 / COMP-014).

Verifies:
- Both writes succeed → commit called.
- Audit log write fails → rollback called, handover record not persisted, exception re-raised.
- DB failure mid-transaction → full rollback.
"""
import unittest
from unittest.mock import MagicMock, patch, call


def _make_mock_db():
    db = MagicMock()
    db.session = MagicMock()
    return db


class TestSubmitHandoverWithAudit(unittest.TestCase):
    def _run(self, db, handover_record=None, action='Test Action', raise_on_commit=None):
        """Helper that patches db and optionally raises on commit."""
        if handover_record is None:
            handover_record = MagicMock()

        if raise_on_commit:
            db.session.commit.side_effect = raise_on_commit

        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.username = 'testuser'

        mock_request = MagicMock()
        mock_request.path = '/handover/submit'

        mock_audit_log_cls = MagicMock(return_value=MagicMock())

        with patch('services.audit_service.db', db), \
             patch('services.audit_service.current_user', mock_user), \
             patch('services.audit_service.request', mock_request), \
             patch('services.audit_service.AuditLog', mock_audit_log_cls):
            from services.audit_service import submit_handover_with_audit
            submit_handover_with_audit(handover_record, action)

        return mock_audit_log_cls

    def test_both_records_added_to_session(self):
        db = _make_mock_db()
        handover = MagicMock()
        self._run(db, handover_record=handover)
        self.assertEqual(db.session.add.call_count, 2)

    def test_commit_called_on_success(self):
        db = _make_mock_db()
        self._run(db)
        db.session.commit.assert_called_once()

    def test_rollback_called_on_commit_failure(self):
        db = _make_mock_db()
        with self.assertRaises(RuntimeError):
            self._run(db, raise_on_commit=RuntimeError('DB error'))
        db.session.rollback.assert_called_once()

    def test_exception_reraised_after_rollback(self):
        db = _make_mock_db()
        with self.assertRaises(RuntimeError) as ctx:
            self._run(db, raise_on_commit=RuntimeError('DB error'))
        self.assertIn('DB error', str(ctx.exception))

    def test_handover_not_persisted_on_audit_failure(self):
        """If commit raises, rollback undoes both — neither record is persisted."""
        db = _make_mock_db()
        handover = MagicMock()

        with self.assertRaises(Exception):
            self._run(db, handover_record=handover, raise_on_commit=Exception('audit write failed'))

        # Rollback must have been called
        db.session.rollback.assert_called_once()

    def test_db_failure_mid_transaction_triggers_rollback(self):
        """session.add() raises halfway through — rollback must be called."""
        db = _make_mock_db()
        call_count = [0]

        def add_side_effect(obj):
            call_count[0] += 1
            if call_count[0] == 2:
                raise RuntimeError('disk full')

        db.session.add.side_effect = add_side_effect
        handover = MagicMock()

        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.username = 'testuser'
        mock_request = MagicMock()
        mock_request.path = '/test'

        with patch('services.audit_service.db', db), \
             patch('services.audit_service.current_user', mock_user), \
             patch('services.audit_service.request', mock_request), \
             patch('services.audit_service.AuditLog', MagicMock(return_value=MagicMock())):
            from services.audit_service import submit_handover_with_audit
            with self.assertRaises(RuntimeError):
                submit_handover_with_audit(handover, 'Test')

        db.session.rollback.assert_called_once()


if __name__ == '__main__':
    unittest.main()
