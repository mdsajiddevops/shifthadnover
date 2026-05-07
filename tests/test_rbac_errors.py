"""
Unit tests for utils/rbac_errors.py (T-036 / COMP-016).

Verifies:
- Every supported role/action combination returns a non-generic message.
- 'user' attempting a 'team_admin' action identifies 'team_admin' by name.
- Unauthenticated (None role) messages reference the required role.
"""
import unittest
from utils.rbac_errors import resolve_rbac_error, check_role, _ACTION_REQUIREMENTS


class TestResolveRbacError(unittest.TestCase):
    def test_unauthenticated_message_includes_required_role(self):
        msg = resolve_rbac_error(None, 'team_admin', 'approve_handover')
        self.assertIn('Team Admin', msg)
        self.assertNotIn('generic', msg.lower())

    def test_user_attempting_team_admin_action_identifies_team_admin(self):
        msg = resolve_rbac_error('user', 'team_admin', 'approve_handover')
        self.assertIn('Team Admin', msg)
        self.assertIn('User', msg)

    def test_message_is_not_generic_403(self):
        msg = resolve_rbac_error('user', 'account_admin', 'manage_users')
        self.assertNotEqual(msg, 'Access denied')
        self.assertNotEqual(msg, '403')
        self.assertGreater(len(msg), 30)

    def test_every_defined_action_returns_specific_message(self):
        for action, required_role in _ACTION_REQUIREMENTS.items():
            with self.subTest(action=action):
                msg = resolve_rbac_error('user', required_role, action)
                self.assertIsInstance(msg, str)
                self.assertGreater(len(msg), 20, f'Message for {action!r} is too short')
                # Must name the required role — not a generic string
                from utils.rbac_errors import _ROLE_LABELS
                required_label = _ROLE_LABELS.get(required_role, required_role)
                self.assertIn(required_label, msg, f'Message for {action!r} does not name required role')


class TestCheckRole(unittest.TestCase):
    def test_permitted_returns_none(self):
        result = check_role('team_admin', 'approve_handover')
        self.assertIsNone(result)

    def test_insufficient_role_returns_error_string(self):
        result = check_role('user', 'approve_handover')
        self.assertIsNotNone(result)
        self.assertIn('Team Admin', result)

    def test_unknown_action_returns_none(self):
        result = check_role('user', 'unknown_action_xyz')
        self.assertIsNone(result)

    def test_unauthenticated_returns_error_string(self):
        result = check_role(None, 'approve_handover')
        self.assertIsNotNone(result)

    def test_super_admin_can_do_everything(self):
        for action in _ACTION_REQUIREMENTS:
            with self.subTest(action=action):
                result = check_role('super_admin', action)
                self.assertIsNone(result, f'super_admin should be permitted for {action!r}')


if __name__ == '__main__':
    unittest.main()
