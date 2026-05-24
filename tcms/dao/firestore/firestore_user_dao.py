from django.contrib.auth import get_user_model

from tcms.dao.firestore.client import get_firestore_client
from tcms.dao.firestore.post_filtering.user_post_filterer import UserPostFilterer
from tcms.utils import user as user_utils

User = get_user_model()

_COLLECTION = 'users'

_USER_FIELDS = (
    'email', 'first_name', 'id', 'is_active',
    'is_staff', 'is_superuser', 'last_name', 'username',
)


class FirestoreUserDAO:
    """
    Firestore-backed DAO for User.

    filter()     — reads from Firestore, applies post-filtering in Python.
    save()       — dual-write: persists via ORM then syncs the document to Firestore.
    deactivate() — ORM deactivate then updates is_active in the Firestore document.

    get_by_id(), get_by_username(), filter_objects(), and add_to_group() are not
    implemented here because they return Django ORM objects required by the view layer.
    """

    def __init__(self):
        db = get_firestore_client()
        self._collection = db.collection(_COLLECTION)
        self._post_filterer = UserPostFilterer()

    def _to_dict(self, user):
        return {field: getattr(user, field) for field in _USER_FIELDS}

    def _doc_ref(self, user_id):
        return self._collection.document(str(user_id))

    # ------------------------------------------------------------------
    # READ
    # ------------------------------------------------------------------

    def filter(self, query):
        """Fetch all User documents from Firestore and apply post-filtering."""
        all_docs = [doc.to_dict() for doc in self._collection.stream()]
        return self._post_filterer.filter(all_docs, query)

    # ------------------------------------------------------------------
    # WRITE
    # ------------------------------------------------------------------

    def save(self, user, update_fields=None):
        """Persist a User: ORM save first, then sync public fields to Firestore."""
        if update_fields:
            user.save(update_fields=update_fields)
        else:
            user.save()

        self._doc_ref(user.pk).set(self._to_dict(user))
        return user

    def deactivate(self, user):
        """Deactivate a user in ORM and update the Firestore document."""
        user_utils.deactivate(user)
        self._doc_ref(user.pk).set(self._to_dict(user))


firestore_user_dao = FirestoreUserDAO()
