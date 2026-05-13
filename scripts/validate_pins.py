#!/usr/bin/env python3
"""
Dependency Pin Validator — COMP-004 (CTCOAMSHM-115, REQ-004)

Scans requirements.txt and exits non-zero if any line contains a non-== specifier.
Reports all offenders before exiting so the CI log shows the full list in one run.

Usage:
    python scripts/validate_pins.py [--requirements <path>]
"""
import argparse
import re
import sys

_EXACT_PIN_RE = re.compile(r"^[A-Za-z0-9_.\-]+(\[.*?\])?==\S+$")


def validate(requirements_path: str) -> list[str]:
    """Return a list of offending lines. Empty list means all pins are exact."""
    offenders = []
    try:
        with open(requirements_path) as fh:
            for raw in fh:
                line = raw.strip()
                # Skip blank lines and comments
                if not line or line.startswith("#"):
                    continue
                # Strip inline comments
                line = line.split(" #")[0].strip()
                if not _EXACT_PIN_RE.match(line):
                    offenders.append(line)
    except FileNotFoundError:
        print(f"ERROR: requirements file not found: {requirements_path}", file=sys.stderr)
        sys.exit(2)
    return offenders


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate all requirements are exactly == pinned.")
    parser.add_argument(
        "--requirements",
        default="requirements.txt",
        help="Path to requirements file (default: requirements.txt)",
    )
    args = parser.parse_args()

    offenders = validate(args.requirements)
    if offenders:
        print("ERROR: Non-exact pin detected:")
        for pkg in offenders:
            print(f"  {pkg}")
        print(f"Failing: {len(offenders)} package(s) require exact == pinning.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
