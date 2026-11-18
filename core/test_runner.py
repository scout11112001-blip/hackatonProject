"""Test runner that redirects private uploads to a temporary directory."""

import os
import shutil
import tempfile
from pathlib import Path

from django.test.runner import DiscoverRunner
from django.test.utils import override_settings

PRIVATE_MEDIA_ENV = "PRIVATE_MEDIA_ROOT"


class ProjectTestRunner(DiscoverRunner):
    """Uploads go to a temporary directory in the parent and in every worker.

    Parallel workers started with "spawn" (macOS) re-import settings, so the
    directory is also passed through the environment (settings read it).
    """

    def setup_test_environment(self, **kwargs) -> None:
        super().setup_test_environment(**kwargs)
        self._private_dir = tempfile.mkdtemp(prefix="test-private-media-")
        self._old_private_env = os.environ.get(PRIVATE_MEDIA_ENV)
        os.environ[PRIVATE_MEDIA_ENV] = self._private_dir
        self._private_override = override_settings(PRIVATE_MEDIA_ROOT=Path(self._private_dir))
        self._private_override.enable()

    def teardown_test_environment(self, **kwargs) -> None:
        self._private_override.disable()
        if self._old_private_env is None:
            os.environ.pop(PRIVATE_MEDIA_ENV, None)
        else:
            os.environ[PRIVATE_MEDIA_ENV] = self._old_private_env
        shutil.rmtree(self._private_dir, ignore_errors=True)
        super().teardown_test_environment(**kwargs)
