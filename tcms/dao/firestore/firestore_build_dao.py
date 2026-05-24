from tcms.dao.firestore.client import get_firestore_client
from tcms.dao.firestore.post_filtering.build_post_filterer import BuildPostFilterer
from tcms.management.models import Build

_COLLECTION = 'builds'


class FirestoreBuildDAO:
    """
    Firestore-backed DAO for Build.

    filter() — reads from Firestore, applies post-filtering in Python.
    save()   — dual-write: persists via ORM then syncs the document to Firestore.

    get_by_id() is not implemented here because it returns a Django ORM object
    required by the view layer.
    """

    def __init__(self):
        db = get_firestore_client()
        self._collection = db.collection(_COLLECTION)
        self._post_filterer = BuildPostFilterer()

    # ------------------------------------------------------------------
    # internal helpers
    # ------------------------------------------------------------------

    def _to_dict(self, build):
        result = {
            'id': build.id,
            'name': build.name,
            'version_id': build.version_id,
            'is_active': build.is_active,
        }
        extra = Build.objects.filter(pk=build.pk).values('version__value').first() or {}
        result.update(extra)
        return result

    def _doc_ref(self, build_id):
        return self._collection.document(str(build_id))

    # ------------------------------------------------------------------
    # READ
    # ------------------------------------------------------------------

    def filter(self, query):
        """Fetch all Build documents from Firestore and apply post-filtering."""
        all_docs = [doc.to_dict() for doc in self._collection.stream()]
        return self._post_filterer.filter(all_docs, query)

    # ------------------------------------------------------------------
    # WRITE
    # ------------------------------------------------------------------

    def save(self, build, update_fields=None):
        """Persist a Build: ORM save first, then sync to Firestore."""
        if update_fields:
            build.save(update_fields=update_fields)
        else:
            build.save()

        self._doc_ref(build.pk).set(self._to_dict(build))
        return build


firestore_build_dao = FirestoreBuildDAO()
