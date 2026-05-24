from tcms.dao.firestore.client import get_firestore_client
from tcms.dao.firestore.post_filtering.plan_type_post_filterer import PlanTypePostFilterer
from tcms.testplans.models import PlanType

_COLLECTION = 'plan_types'


class FirestorePlanTypeDAO:
    """
    Firestore-backed DAO for PlanType.

    filter() — reads from Firestore, applies post-filtering in Python.
    save()   — dual-write: persists via ORM then syncs the document to Firestore.
    """

    def __init__(self):
        db = get_firestore_client()
        self._collection = db.collection(_COLLECTION)
        self._post_filterer = PlanTypePostFilterer()

    def _to_dict(self, plan_type):
        return {
            'id': plan_type.id,
            'name': plan_type.name,
            'description': plan_type.description,
        }

    def _doc_ref(self, plan_type_id):
        return self._collection.document(str(plan_type_id))

    def filter(self, query):
        """Fetch all PlanType documents from Firestore and apply post-filtering."""
        all_docs = [doc.to_dict() for doc in self._collection.stream()]
        return self._post_filterer.filter(all_docs, query)

    def save(self, plan_type):
        """Persist a PlanType: ORM save first, then sync to Firestore."""
        plan_type.save()
        self._doc_ref(plan_type.pk).set(self._to_dict(plan_type))
        return plan_type


firestore_plan_type_dao = FirestorePlanTypeDAO()
