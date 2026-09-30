import os
import subprocess
from functools import lru_cache

from django.conf import settings


@lru_cache(maxsize=1)
def _app_version():
    # An explicit APP_VERSION (e.g. set at deploy time) wins; otherwise the
    # minor number is the commit count of the checked-out repository.
    version = os.environ.get("APP_VERSION")
    if version:
        return version
    try:
        count = subprocess.run(
            ["git", "rev-list", "--count", "HEAD"],
            cwd=settings.BASE_DIR,
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        count = ""
    return f"v1.{count or 0}"


def app_version(request):
    return {"APP_VERSION": _app_version()}
