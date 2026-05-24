from tcms.dao.firestore.client import get_firestore_client
from tcms.dao.firestore.post_filtering.test_case_status_post_filterer import TestCaseStatusPostFilterer
from tcms.testcases.models import TestCaseStatus

_COLLECTION = 'test_case_statuses'


class FirestoreTestCaseStatusDAO:
    """
    Firestore-backed DAO for TestCaseStatus.

    filter() — reads from Firestore, applies post-filtering in Python.
    save()   — dual-write: persists via ORM then syncs the document to Firestore.
    """

    def __init__(self):
        db = get_firestore_client()
        self._collection = db.collection(_COLLECTION)
        self._post_filterer = TestCaseStatusPostFilterer()

    def _to_dict(self, status):
        return {
            'id': status.id,
            'name': status.name,
            'description': status.description,
            'is_confirmed': status.is_confirmed,
        }

    def _doc_ref(self, status_id):
        return self._collection.document(str(status_id))

    def filter(self, query):
        """Fetch all TestCaseStatus documents from Firestore and apply post-filtering."""
        all_docs = [doc.to_dict() for doc in self._collection.stream()]
        return self._post_filterer.filter(all_docs, query)

    def save(self, status):
        """Persist a TestCaseStatus: ORM save first, then sync to Firestore."""
        status.save()
        self._doc_ref(status.pk).set(self._to_dict(status))
        return status


firestore_test_case_status_dao = FirestoreTestCaseStatusDAO()
