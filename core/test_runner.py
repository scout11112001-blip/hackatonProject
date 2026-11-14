"""Test runner that redirects private uploads to a temporary directory."""

import shutil
import tempfile
from pathlib import Path

from django.test.runner import DiscoverRunner
from django.test.utils import override_settings


class ProjectTestRunner(DiscoverRunner):
    def setup_test_environment(self, **kwargs) -> None:
        super().setup_test_environment(**kwargs)
        self._private_dir = tempfile.mkdtemp(prefix="test-private-media-")
        self._private_override = override_settings(PRIVATE_MEDIA_ROOT=Path(self._private_dir))
        self._private_override.enable()

    def teardown_test_environment(self, **kwargs) -> None:
        self._private_override.disable()
        shutil.rmtree(self._private_dir, ignore_errors=True)
        super().teardown_test_environment(**kwargs)
