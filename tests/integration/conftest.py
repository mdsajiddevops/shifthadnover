"""
Shared fixtures for CoreAction integration tests.
"""
import os
from unittest.mock import MagicMock


def make_fake_user(role="user", user_id="user_test_1"):
    """Return a MagicMock that mimics a logged-in User model instance.

    Sets all attributes accessed by the session-validation middleware to
    non-MagicMock values so datetime comparisons don't raise TypeError.
    """
    user = MagicMock()
    user.is_authenticated = True
    user.is_active = True
    user.role = role
    user.id = user_id
    user.username = f"test_{user_id}"
    user.session_token = None          # no token → session-validation skips comparison
    user.sessions_terminated_at = None # avoids `sessions_terminated_at > last_login`
    user.last_login = None
    user.last_activity = None
    user.needs_onboarding = False
    user.onboarding_completed = True
    user.account_id = 1
    user.team_id = 1
    return user
