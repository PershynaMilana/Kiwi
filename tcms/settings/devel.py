# pylint: disable=wildcard-import, unused-wildcard-import
"""
Django settings for devel env.
"""

import os

from .common import *  # noqa: F403

# Debug settings
DEBUG = True

# Use Firestore-compatible DAOs (gcloudc ORM with chunking, no related ordering, etc.)
USE_FIRESTORE_DAOS = True

# Database settings — Firestore Native Mode via django-gcloud-connectors
DATABASES = {
    "default": {
        "ENGINE": "gcloudc.db.backends.firestore",
        "PROJECT": "kiwi-tcms-d90e9",
        "INDEXES_FILE": os.path.join(TCMS_ROOT_PATH, "..", "firestore.indexes.yaml"),  # noqa: F405
    }
}


CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.dummy.DummyCache",
    }
}
# django-debug-toolbar settings

MIDDLEWARE += [  # noqa: F405
    "tcms.core.middleware.ExtraHeadersMiddleware",
]

MEDIA_ROOT = os.path.join(TCMS_ROOT_PATH, "..", "uploads")  # noqa: F405

# Needed by django.template.context_processors.debug:
# See:
# http://docs.djangoproject.com/en/dev/ref/templates/api/#django-template-context-processors-debug
INTERNAL_IPS = ("127.0.0.1",)

STORAGES["staticfiles"][  # noqa: F405
    "BACKEND"
] = "tcms.tests.storage.RaiseWhenFileNotFound"

ANONYMOUS_ANALYTICS = False

# gcloudc has a timezone-naive/aware comparison bug in session queries — use file sessions instead
SESSION_ENGINE = "django.contrib.sessions.backends.file"

# Skip gcloudc's index-coverage check for third-party models whose fields
# we cannot annotate with db_index=True.  Firestore indexes all fields by
# default, so these queries work fine at the database level.
GCLOUDC_EXCLUDE_FROM_INDEX_CHECKS = [
    "django_comments.Comment",
]

# Firestore credentials — point to your Firebase service account JSON key.
# Download from: Firebase Console → Project Settings → Service Accounts → Generate new private key
FIRESTORE_CREDENTIALS_PATH = os.path.join(TCMS_ROOT_PATH, "..", "firestore-credentials.json")  # noqa: F405

try:
    from .local_settings import *  # noqa: F401,F403
except ImportError:
    pass