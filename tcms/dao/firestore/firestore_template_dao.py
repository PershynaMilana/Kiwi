from tcms.dao.firestore.client import get_firestore_client
from tcms.dao.firestore.post_filtering.template_post_filterer import TemplatePostFilterer
from tcms.testcases.models import Template

_COLLECTION = 'templates'


class FirestoreTemplateDAO:
    """
    Firestore-backed DAO for Template.

    filter() — reads from Firestore, applies post-filtering in Python.
    save()   — dual-write: persists via ORM then syncs the document to Firestore.

    filter_objects() and get_by_id() are not implemented here because they
    return Django ORM objects required by the view layer.
    """

    def __init__(self):
        db = get_firestore_client()
        self._collection = db.collection(_COLLECTION)
        self._post_filterer = TemplatePostFilterer()

    def _to_dict(self, template):
        return {
            'id': template.id,
            'name': template.name,
            'text': template.text,
        }

    def _doc_ref(self, template_id):
        return self._collection.document(str(template_id))

    def filter(self, query):
        """Fetch all Template documents from Firestore and apply post-filtering."""
        all_docs = [doc.to_dict() for doc in self._collection.stream()]
        return self._post_filterer.filter(all_docs, query)

    def save(self, template):
        """Persist a Template: ORM save first, then sync to Firestore."""
        template.save()
        self._doc_ref(template.pk).set(self._to_dict(template))
        return template


firestore_template_dao = FirestoreTemplateDAO()
