from tcms.bugs.models import Bug
from tcms.dao.firestore.client import get_firestore_client
from tcms.dao.firestore.post_filtering.bug_post_filterer import BugPostFilterer

_COLLECTION = 'bugs'

_BUG_FIELDS = (
    'id', 'summary', 'created_at', 'status',
    'reporter_id', 'assignee_id', 'product_id', 'version_id', 'build_id', 'severity_id',
)

_NAME_FIELDS = (
    'pk', 'summary', 'created_at',
    'product__name', 'version__value', 'build__name',
    'reporter__username', 'assignee__username',
    'severity__name', 'severity__color', 'severity__icon',
)

_CANONICAL_FIELDS = (
    'id', 'summary', 'created_at', 'status',
    'reporter_id', 'assignee_id', 'product_id', 'version_id', 'build_id', 'severity_id',
)


class FirestoreBugDAO:
    """
    Firestore-backed DAO for Bug.

    filter_with_names() / filter_canonical() — reads from Firestore, applies post-filtering.
    save()    — dual-write: persists via ORM then syncs the document to Firestore.
    remove()  — deletes from ORM and Firestore.

    get_by_id() is not implemented here because it returns a Django ORM object
    required by the view layer.
    """

    def __init__(self):
        db = get_firestore_client()
        self._collection = db.collection(_COLLECTION)
        self._post_filterer = BugPostFilterer()

    # ------------------------------------------------------------------
    # internal helpers
    # ------------------------------------------------------------------

    def _to_dict(self, bug):
        result = {field: getattr(bug, field) for field in _BUG_FIELDS}
        result['pk'] = bug.pk
        extra = Bug.objects.filter(pk=bug.pk).values(
            'reporter__username', 'assignee__username', 'product__name',
            'version__value', 'build__name', 'severity__name',
            'severity__color', 'severity__icon',
        ).first() or {}
        result.update(extra)
        return result

    def _doc_ref(self, bug_id):
        return self._collection.document(str(bug_id))

    # ------------------------------------------------------------------
    # READ
    # ------------------------------------------------------------------

    def filter(self, query):
        """Return bugs with FK IDs only."""
        all_docs = [doc.to_dict() for doc in self._collection.stream()]
        filtered = self._post_filterer.filter(all_docs, query)
        return [{k: doc[k] for k in _BUG_FIELDS if k in doc} for doc in filtered]

    def filter_with_names(self, query):
        """Return bugs with denormalized related-object names."""
        all_docs = [doc.to_dict() for doc in self._collection.stream()]
        filtered = self._post_filterer.filter(all_docs, query)
        return [{k: doc[k] for k in _NAME_FIELDS if k in doc} for doc in filtered]

    def filter_canonical(self, query):
        """Return bugs with FK IDs (canonical form)."""
        all_docs = [doc.to_dict() for doc in self._collection.stream()]
        filtered = self._post_filterer.filter(all_docs, query)
        return [{k: doc[k] for k in _CANONICAL_FIELDS if k in doc} for doc in filtered]

    # ------------------------------------------------------------------
    # WRITE
    # ------------------------------------------------------------------

    def save(self, bug, update_fields=None):
        """Persist a Bug: ORM save first, then sync to Firestore."""
        if update_fields:
            bug.save(update_fields=update_fields)
        else:
            bug.save()

        self._doc_ref(bug.pk).set(self._to_dict(bug))
        return bug

    def remove(self, query):
        """Delete Bug objects matching query in ORM and Firestore."""
        bug_ids = list(Bug.objects.filter(**query).values_list('pk', flat=True))
        deleted = Bug.objects.filter(**query).delete()

        for bug_id in bug_ids:
            self._doc_ref(bug_id).delete()

        return deleted


firestore_bug_dao = FirestoreBugDAO()
