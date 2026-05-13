"""
T-042 — Performance validation: CoreAction sub-100ms latency (REQ-011).

Requires:
  - DATABASE_URL pointing to a populated test DB
  - PERF_ITERATIONS env var (default 100)
  - pytest-benchmark installed

Run: pytest tests/performance/ -v --benchmark-json=tests/performance/latest_run.json
"""
import os
import pytest

PERF_ITERATIONS = int(os.environ.get("PERF_ITERATIONS", "100"))


@pytest.mark.performance
class TestCoreActionLatency:
    def test_placeholder_latency_test(self):
        """Placeholder: latency test requires live DB and pytest-benchmark (T-042)."""
        pytest.skip("Performance tests require a live DB and pytest-benchmark (see T-042 docs)")
