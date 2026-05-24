from tcms.dao.firestore.client import get_firestore_client
from tcms.dao.firestore.post_filtering.priority_post_filterer import PriorityPostFilterer
from tcms.management.models import Priority

_COLLECTION = 'priorities'


class FirestorePriorityDAO:
    """
    Firestore-backed DAO for Priority.

    filter() — reads from Firestore, applies post-filtering in Python.
    save()   — dual-write: persists via ORM then syncs the document to Firestore.
    """

    def __init__(self):
        db = get_firestore_client()
        self._collection = db.collection(_COLLECTION)
        self._post_filterer = PriorityPostFilterer()

    def _to_dict(self, priority):
        return {
            'id': priority.id,
            'value': priority.value,
            'is_active': priority.is_active,
        }

    def _doc_ref(self, priority_id):
        return self._collection.document(str(priority_id))

    def filter(self, query):
        """Fetch all Priority documents from Firestore and apply post-filtering."""
        all_docs = [doc.to_dict() for doc in self._collection.stream()]
        return self._post_filterer.filter(all_docs, query)

    def save(self, priority):
        """Persist a Priority: ORM save first, then sync to Firestore."""
        priority.save()
        self._doc_ref(priority.pk).set(self._to_dict(priority))
        return priority


firestore_priority_dao = FirestorePriorityDAO()
