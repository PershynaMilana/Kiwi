import firebase_admin
from firebase_admin import credentials, firestore
from django.conf import settings

_db = None


def get_firestore_client():
    global _db
    if _db is None:
        if not firebase_admin._apps:
            cred = credentials.Certificate(settings.FIRESTORE_CREDENTIALS_PATH)
            firebase_admin.initialize_app(cred)
        _db = firestore.client()
    return _db
