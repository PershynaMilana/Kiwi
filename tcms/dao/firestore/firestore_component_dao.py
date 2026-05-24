from tcms.dao.firestore.client import get_firestore_client
from tcms.dao.firestore.post_filtering.component_post_filterer import ComponentPostFilterer
from tcms.management.models import Component

_COLLECTION = 'components'


class FirestoreComponentDAO:
    """
    Firestore-backed DAO for Component.

    filter() — reads from Firestore, applies post-filtering in Python.
    save()   — dual-write: persists via ORM then syncs the document to Firestore.

    filter_objects(), get_by_id(), and get_by_name_and_product() are not implemented
    here because they return Django ORM objects required by the view layer.
    """

    def __init__(self):
        db = get_firestore_client()
        self._collection = db.collection(_COLLECTION)
        self._post_filterer = ComponentPostFilterer()

    # ------------------------------------------------------------------
    # internal helpers
    # ------------------------------------------------------------------

    def _to_dict(self, component):
        return {
            'id': component.id,
            'name': component.name,
            'product_id': component.product_id,
            'initial_owner_id': component.initial_owner_id,
            'initial_qa_contact_id': component.initial_qa_contact_id,
            'description': component.description,
            'cases': None,
        }

    def _doc_ref(self, component_id):
        return self._collection.document(str(component_id))

    # ------------------------------------------------------------------
    # READ
    # ------------------------------------------------------------------

    def filter(self, query):
        """Fetch all Component documents from Firestore and apply post-filtering."""
        all_docs = [doc.to_dict() for doc in self._collection.stream()]
        return self._post_filterer.filter(all_docs, query)

    # ------------------------------------------------------------------
    # WRITE
    # ------------------------------------------------------------------

    def save(self, component, update_fields=None):
        """Persist a Component: ORM save first, then sync to Firestore."""
        if update_fields:
            component.save(update_fields=update_fields)
        else:
            component.save()

        self._doc_ref(component.pk).set(self._to_dict(component))
        return component


firestore_component_dao = FirestoreComponentDAO()
