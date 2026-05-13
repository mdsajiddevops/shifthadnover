"""T-033 — Unit tests for Dependency Pin Validator script (COMP-004, REQ-004)."""
import subprocess
import sys
import textwrap
import pytest


def _write_reqs(tmp_path, content: str):
    reqs = tmp_path / "requirements.txt"
    reqs.write_text(textwrap.dedent(content))
    return str(reqs)


class TestValidatePins:
    def test_all_exact_pins_exits_zero(self, tmp_path):
        path = _write_reqs(tmp_path, """\
            flask==2.3.0
            requests==2.28.2
            sqlalchemy==2.0.0
        """)
        result = subprocess.run(
            [sys.executable, "scripts/validate_pins.py", "--requirements", path],
            capture_output=True, text=True,
        )
        assert result.returncode == 0

    def test_gte_specifier_exits_nonzero_and_names_package(self, tmp_path):
        path = _write_reqs(tmp_path, """\
            flask>=2.3.0
            requests==2.28.2
        """)
        result = subprocess.run(
            [sys.executable, "scripts/validate_pins.py", "--requirements", path],
            capture_output=True, text=True,
        )
        assert result.returncode != 0
        assert "flask" in result.stdout

    def test_tilde_equal_specifier_exits_nonzero(self, tmp_path):
        path = _write_reqs(tmp_path, """\
            requests~=2.28.0
        """)
        result = subprocess.run(
            [sys.executable, "scripts/validate_pins.py", "--requirements", path],
            capture_output=True, text=True,
        )
        assert result.returncode != 0
        assert "requests" in result.stdout

    def test_gt_specifier_exits_nonzero(self, tmp_path):
        path = _write_reqs(tmp_path, """\
            foo>1.0.0
        """)
        result = subprocess.run(
            [sys.executable, "scripts/validate_pins.py", "--requirements", path],
            capture_output=True, text=True,
        )
        assert result.returncode != 0
        assert "foo" in result.stdout

    def test_multiple_offenders_all_named(self, tmp_path):
        path = _write_reqs(tmp_path, """\
            badpkg>=1.0.0
            good==1.2.3
            anotherbad~=2.0
        """)
        result = subprocess.run(
            [sys.executable, "scripts/validate_pins.py", "--requirements", path],
            capture_output=True, text=True,
        )
        assert result.returncode != 0
        assert "badpkg" in result.stdout
        assert "anotherbad" in result.stdout

    def test_empty_file_exits_zero(self, tmp_path):
        path = _write_reqs(tmp_path, "")
        result = subprocess.run(
            [sys.executable, "scripts/validate_pins.py", "--requirements", path],
            capture_output=True, text=True,
        )
        assert result.returncode == 0

    def test_comment_lines_not_flagged(self, tmp_path):
        path = _write_reqs(tmp_path, """\
            # this is a comment
            flask==2.3.0
        """)
        result = subprocess.run(
            [sys.executable, "scripts/validate_pins.py", "--requirements", path],
            capture_output=True, text=True,
        )
        assert result.returncode == 0

    def test_blank_lines_not_flagged(self, tmp_path):
        path = _write_reqs(tmp_path, """\
            flask==2.3.0

            requests==2.28.2
        """)
        result = subprocess.run(
            [sys.executable, "scripts/validate_pins.py", "--requirements", path],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
