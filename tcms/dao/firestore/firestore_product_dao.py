from tcms.dao.firestore.client import get_firestore_client
from tcms.dao.firestore.post_filtering.product_post_filterer import ProductPostFilterer
from tcms.management.models import Product

_COLLECTION = 'products'


class FirestoreProductDAO:
    """
    Firestore-backed DAO for Product.

    filter() — reads from Firestore, applies post-filtering in Python.
    save()   — dual-write: persists via ORM then syncs the document to Firestore.
    """

    def __init__(self):
        db = get_firestore_client()
        self._collection = db.collection(_COLLECTION)
        self._post_filterer = ProductPostFilterer()

    # ------------------------------------------------------------------
    # internal helpers
    # ------------------------------------------------------------------

    def _to_dict(self, product):
        return {
            'id': product.id,
            'name': product.name,
            'description': product.description,
            'classification_id': product.classification_id,
        }

    def _doc_ref(self, product_id):
        return self._collection.document(str(product_id))

    # ------------------------------------------------------------------
    # READ
    # ------------------------------------------------------------------

    def filter(self, query):
        """Fetch all Product documents from Firestore and apply post-filtering."""
        all_docs = [doc.to_dict() for doc in self._collection.stream()]
        return self._post_filterer.filter(all_docs, query)

    # ------------------------------------------------------------------
    # WRITE
    # ------------------------------------------------------------------

    def save(self, product, update_fields=None):
        """Persist a Product: ORM save first, then sync to Firestore."""
        if update_fields:
            product.save(update_fields=update_fields)
        else:
            product.save()

        self._doc_ref(product.pk).set(self._to_dict(product))
        return product


firestore_product_dao = FirestoreProductDAO()
