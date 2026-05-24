from tcms.dao.firestore.client import get_firestore_client
from tcms.dao.firestore.post_filtering.bug_system_post_filterer import BugSystemPostFilterer
from tcms.testcases.models import BugSystem

_COLLECTION = 'bug_systems'


class FirestoreBugSystemDAO:
    """
    Firestore-backed DAO for BugSystem.

    filter() — reads from Firestore, applies post-filtering in Python.
    save()   — dual-write: persists via ORM then syncs the document to Firestore.

    api_password is intentionally excluded from the Firestore document.

    get_by_id() and filter_objects() are not implemented here because they
    return Django ORM objects required by the view layer.
    """

    def __init__(self):
        db = get_firestore_client()
        self._collection = db.collection(_COLLECTION)
        self._post_filterer = BugSystemPostFilterer()

    def _to_dict(self, bug_system):
        return {
            'id': bug_system.id,
            'name': bug_system.name,
            'tracker_type': bug_system.tracker_type,
            'base_url': bug_system.base_url,
            'api_url': bug_system.api_url,
            'api_username': bug_system.api_username,
        }

    def _doc_ref(self, bug_system_id):
        return self._collection.document(str(bug_system_id))

    def filter(self, query):
        """Fetch all BugSystem documents from Firestore and apply post-filtering."""
        all_docs = [doc.to_dict() for doc in self._collection.stream()]
        return self._post_filterer.filter(all_docs, query)

    def save(self, bug_system):
        """Persist a BugSystem: ORM save first, then sync to Firestore (without api_password)."""
        bug_system.save()
        self._doc_ref(bug_system.pk).set(self._to_dict(bug_system))
        return bug_system


firestore_bug_system_dao = FirestoreBugSystemDAO()
