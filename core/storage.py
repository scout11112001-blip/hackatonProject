"""Private file storage for petition attachments.

Files are stored outside ``static/`` and ``STATIC_ROOT`` and must never be
served by Django URL patterns or nginx. ``url()`` raises by design: every
download goes through an access-checked view.
"""

import os

from django.conf import settings
from django.core.files.storage import FileSystemStorage


class PrivateFileStorage(FileSystemStorage):
    def __init__(self) -> None:
        super().__init__(base_url=None)

    @property
    def base_location(self) -> str:
        return str(settings.PRIVATE_MEDIA_ROOT)

    @property
    def location(self) -> str:
        return os.path.abspath(self.base_location)

    def url(self, name: str | None) -> str:
        raise ValueError("Private files have no public URL.")

    def get_available_name(self, name: str, max_length: int | None = None) -> str:
        if self.exists(name):
            raise FileExistsError(name)
        return name


_private_storage = PrivateFileStorage()


def get_private_storage() -> PrivateFileStorage:
    return _private_storage
