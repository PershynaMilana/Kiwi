from tcms.dao.firestore.client import get_firestore_client
from tcms.dao.firestore.post_filtering.classification_post_filterer import ClassificationPostFilterer
from tcms.management.models import Classification

_COLLECTION = 'classifications'


class FirestoreClassificationDAO:
    """
    Firestore-backed DAO for Classification.

    filter() — reads from Firestore, applies post-filtering in Python.
    save()   — dual-write: persists via ORM then syncs the document to Firestore.
    """

    def __init__(self):
        db = get_firestore_client()
        self._collection = db.collection(_COLLECTION)
        self._post_filterer = ClassificationPostFilterer()

    def _to_dict(self, classification):
        return {
            'id': classification.id,
            'name': classification.name,
        }

    def _doc_ref(self, classification_id):
        return self._collection.document(str(classification_id))

    def filter(self, query):
        """Fetch all Classification documents from Firestore and apply post-filtering."""
        all_docs = [doc.to_dict() for doc in self._collection.stream()]
        return self._post_filterer.filter(all_docs, query)

    def save(self, classification):
        """Persist a Classification: ORM save first, then sync to Firestore."""
        classification.save()
        self._doc_ref(classification.pk).set(self._to_dict(classification))
        return classification


firestore_classification_dao = FirestoreClassificationDAO()
