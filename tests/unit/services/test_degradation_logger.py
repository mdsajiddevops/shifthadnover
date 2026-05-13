"""T-031 — Unit tests for Degradation Logger (COMP-015, REQ-012)."""
import logging
import pytest
from services.degradation_logger import log_degradation, no_degradation, DegradationSignal


class TestLogDegradation:
    def test_db_timeout_returns_degraded_signal(self, caplog):
        from sqlalchemy.exc import OperationalError
        exc = OperationalError("timeout", None, None)
        with caplog.at_level(logging.ERROR, logger="services.degradation_logger"):
            signal = log_degradation(exc, {"resource_id": "abc"})

        assert isinstance(signal, DegradationSignal)
        assert signal.degraded is True
        assert signal.category == "db_timeout"
        assert signal.original_exception_type == "OperationalError"
        assert signal.detail  # non-empty

    def test_service_unavailable_category(self, caplog):
        exc = ConnectionError("host unreachable")
        with caplog.at_level(logging.ERROR):
            signal = log_degradation(exc, {})

        assert signal.degraded is True
        assert signal.category == "service_unavailable"

    def test_unknown_exception_category(self, caplog):
        exc = ValueError("something unexpected")
        with caplog.at_level(logging.ERROR):
            signal = log_degradation(exc, {})

        assert signal.degraded is True
        assert signal.category == "unknown_error"

    def test_log_record_emitted_at_error_level(self):
        import logging as _logging
        from unittest.mock import patch, MagicMock
        mock_logger = MagicMock()
        exc = RuntimeError("boom")
        with patch("services.degradation_logger.logger", mock_logger):
            log_degradation(exc, {"component": "test"})
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        # extra dict must contain exception_type and message
        extra = call_args.kwargs.get("extra", {})
        assert "exception_type" in extra
        assert "message" in extra

    def test_does_not_reraise_exception(self):
        exc = RuntimeError("fatal")
        # Must not raise — degradation logger is a never-raise utility
        signal = log_degradation(exc, {})
        assert signal.degraded is True

    def test_no_degradation_returns_false_degraded(self, caplog):
        signal = no_degradation()
        assert signal.degraded is False
        # Must not log anything at ERROR level on the happy path
        error_records = [r for r in caplog.records if r.levelno == logging.ERROR]
        assert len(error_records) == 0
