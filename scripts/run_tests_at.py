"""Runs the test suite with the clock frozen at a Moscow time.

Tests must not depend on the real current date.

Usage: python scripts/run_tests_at.py 2027-03-01T12:00:00 [test labels...]
"""

import os
import sys
from datetime import datetime
from pathlib import Path
from unittest import mock
from zoneinfo import ZoneInfo

_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parent
sys.path.insert(0, str(_REPO_ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    when = datetime.fromisoformat(sys.argv[1]).replace(tzinfo=ZoneInfo("Europe/Moscow"))
    mock.patch("django.utils.timezone.now", return_value=when).start()

    import django
    from django.conf import settings
    from django.test.utils import get_runner

    django.setup()
    failures = get_runner(settings)(verbosity=1).run_tests(sys.argv[2:])
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
