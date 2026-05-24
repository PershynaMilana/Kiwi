from tcms.dao.firestore.client import get_firestore_client
from tcms.dao.firestore.post_filtering.test_execution_status_post_filterer import TestExecutionStatusPostFilterer
from tcms.testruns.models import TestExecutionStatus

_COLLECTION = 'test_execution_statuses'


class FirestoreTestExecutionStatusDAO:
    """
    Firestore-backed DAO for TestExecutionStatus.

    filter() — reads from Firestore, applies post-filtering in Python.
    save()   — dual-write: persists via ORM then syncs the document to Firestore.
    """

    def __init__(self):
        db = get_firestore_client()
        self._collection = db.collection(_COLLECTION)
        self._post_filterer = TestExecutionStatusPostFilterer()

    def _to_dict(self, status):
        return {
            'id': status.id,
            'name': status.name,
            'weight': status.weight,
            'icon': status.icon,
            'color': status.color,
        }

    def _doc_ref(self, status_id):
        return self._collection.document(str(status_id))

    def filter(self, query):
        """Fetch all TestExecutionStatus documents from Firestore and apply post-filtering."""
        all_docs = [doc.to_dict() for doc in self._collection.stream()]
        return self._post_filterer.filter(all_docs, query)

    def save(self, status):
        """Persist a TestExecutionStatus: ORM save first, then sync to Firestore."""
        status.save()
        self._doc_ref(status.pk).set(self._to_dict(status))
        return status


firestore_test_execution_status_dao = FirestoreTestExecutionStatusDAO()
