# Workaround for Python 3.13 Windows platform detection issue
import platform
import os

# Override platform.machine() to avoid WMI query issues
_original_machine = platform.machine

def patched_machine():
    try:
        return _original_machine()
    except OSError:
        # Fallback for Windows platform detection issues
        return os.environ.get('PROCESSOR_ARCHITECTURE', 'AMD64')

platform.machine = patched_machine