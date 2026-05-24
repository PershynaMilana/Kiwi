from tcms.dao.firestore.client import get_firestore_client
from tcms.dao.firestore.post_filtering.category_post_filterer import CategoryPostFilterer
from tcms.testcases.models import Category

_COLLECTION = 'categories'


class FirestoreCategoryDAO:
    """
    Firestore-backed DAO for Category.

    filter() — reads from Firestore, applies post-filtering in Python.
    save()   — dual-write: persists via ORM then syncs the document to Firestore.

    get_by_id() is not implemented here because it returns a Django ORM object
    required by the view layer.
    """

    def __init__(self):
        db = get_firestore_client()
        self._collection = db.collection(_COLLECTION)
        self._post_filterer = CategoryPostFilterer()

    def _to_dict(self, category):
        return {
            'id': category.id,
            'name': category.name,
            'product_id': category.product_id,
            'description': category.description,
        }

    def _doc_ref(self, category_id):
        return self._collection.document(str(category_id))

    def filter(self, query):
        """Fetch all Category documents from Firestore and apply post-filtering."""
        all_docs = [doc.to_dict() for doc in self._collection.stream()]
        return self._post_filterer.filter(all_docs, query)

    def save(self, category):
        """Persist a Category: ORM save first, then sync to Firestore."""
        category.save()
        self._doc_ref(category.pk).set(self._to_dict(category))
        return category


firestore_category_dao = FirestoreCategoryDAO()
