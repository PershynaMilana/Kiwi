from tcms.dao.firestore.client import get_firestore_client
from tcms.dao.firestore.post_filtering.version_post_filterer import VersionPostFilterer
from tcms.management.models import Version

_COLLECTION = 'versions'


class FirestoreVersionDAO:
    """
    Firestore-backed DAO for Version.

    filter() — reads from Firestore, applies post-filtering in Python.
    save()   — dual-write: persists via ORM then syncs the document to Firestore.
    """

    def __init__(self):
        db = get_firestore_client()
        self._collection = db.collection(_COLLECTION)
        self._post_filterer = VersionPostFilterer()

    # ------------------------------------------------------------------
    # internal helpers
    # ------------------------------------------------------------------

    def _to_dict(self, version):
        result = {
            'id': version.id,
            'value': version.value,
            'product_id': version.product_id,
        }
        extra = Version.objects.filter(pk=version.pk).values('product__name').first() or {}
        result.update(extra)
        return result

    def _doc_ref(self, version_id):
        return self._collection.document(str(version_id))

    # ------------------------------------------------------------------
    # READ
    # ------------------------------------------------------------------

    def filter(self, query):
        """Fetch all Version documents from Firestore and apply post-filtering."""
        all_docs = [doc.to_dict() for doc in self._collection.stream()]
        return self._post_filterer.filter(all_docs, query)

    # ------------------------------------------------------------------
    # WRITE
    # ------------------------------------------------------------------

    def save(self, version, update_fields=None):
        """Persist a Version: ORM save first, then sync to Firestore."""
        if update_fields:
            version.save(update_fields=update_fields)
        else:
            version.save()

        self._doc_ref(version.pk).set(self._to_dict(version))
        return version


firestore_version_dao = FirestoreVersionDAO()
