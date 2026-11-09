from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.utils.deconstruct import deconstructible


@deconstructible
class PrivateResourceStorage(FileSystemStorage):
    def __init__(self):
        super().__init__()

    @property
    def base_location(self):
        return settings.PRIVATE_RESOURCE_ROOT

    @property
    def location(self):
        return str(Path(self.base_location).resolve())

    def url(self, name):
        raise ValueError("Private resources must be served through the authorized resource endpoint.")


def resource_upload_path(instance, filename):
    extension = Path(filename).suffix.lower()[:16]
    return f"{uuid4().hex}{extension}"
