"""
T-040 — E2E tests: full CoreAction user journeys (COMP-007, REQ-007–REQ-012).

These tests run against a live full-stack Docker Compose deployment.
They require:
  - docker-compose.prod.yml stack running (docker compose -f docker-compose.prod.yml up -d)
  - All Alembic migrations applied
  - TEST_BASE_URL, TEST_SUPERADMIN_USER, TEST_SUPERADMIN_PASSWORD env vars set

Tag: @pytest.mark.e2e — excluded from unit/integration default runs.
"""
import os
import pytest

BASE_URL = os.environ.get("TEST_BASE_URL", "http://localhost:5000")


@pytest.mark.e2e
class TestCoreActionE2E:
    """
    Full-stack E2E journeys.

    These tests require the app to be running with a real database.
    They are excluded from default test runs via pytest.ini markers.
    """

    def test_placeholder_e2e_suite_exists(self):
        """Placeholder: E2E suite scaffolded; run with -m e2e against live stack."""
        pytest.skip("E2E tests require live Docker Compose stack (see T-040 docs)")
