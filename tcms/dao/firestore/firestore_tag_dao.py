from tcms.dao.firestore.client import get_firestore_client
from tcms.management.models import Tag

_COLLECTION = 'tags'

_JUNCTION_COLLECTIONS = {
    'testplan': 'testplan_tags',
    'testcase': 'testcase_tags',
    'testrun': 'testrun_tags',
}


class FirestoreTagDAO:
    """
    Firestore-backed DAO for Tag.

    save()       — dual-write: persists via ORM then syncs the tag document to Firestore.
    add_tag()    — ORM add + writes a junction document to the entity-specific tag collection.
    remove_tag() — ORM remove + deletes the junction document from Firestore.

    filter() is intentionally NOT implemented here: the Tag.filter RPC returns M2M
    join data (one row per tag×entity combination) that cannot be replicated from a
    simple Firestore collection without extra joins — ORM handles it.
    """

    def __init__(self):
        db = get_firestore_client()
        self._collection = db.collection(_COLLECTION)
        self._db = db

    def _to_dict(self, tag):
        return {
            'id': tag.id,
            'name': tag.name,
        }

    def _doc_ref(self, tag_id):
        return self._collection.document(str(tag_id))

    def _junction_collection(self, model_obj):
        entity_type = model_obj.__class__.__name__.lower()
        collection_name = _JUNCTION_COLLECTIONS.get(entity_type)
        if collection_name:
            return self._db.collection(collection_name)
        return None

    def _junction_doc_id(self, model_obj, tag):
        entity_type = model_obj.__class__.__name__.lower()
        return f'{entity_type}_{model_obj.pk}_{tag.pk}'

    # ------------------------------------------------------------------
    # WRITE
    # ------------------------------------------------------------------

    def save(self, tag):
        """Persist a Tag: ORM save first, then sync to Firestore."""
        tag.save()
        self._doc_ref(tag.pk).set(self._to_dict(tag))
        return tag

    def add_tag(self, model_obj, tag):
        """Add tag to a model object in ORM and write junction doc to Firestore."""
        model_obj.add_tag(tag)

        junction = self._junction_collection(model_obj)
        if junction is not None:
            entity_type = model_obj.__class__.__name__.lower()
            junction.document(self._junction_doc_id(model_obj, tag)).set({
                f'{entity_type}_id': model_obj.pk,
                'tag_id': tag.pk,
                'tag_name': tag.name,
            })

    def remove_tag(self, model_obj, tag):
        """Remove tag from a model object in ORM and delete junction doc from Firestore."""
        model_obj.remove_tag(tag)

        junction = self._junction_collection(model_obj)
        if junction is not None:
            junction.document(self._junction_doc_id(model_obj, tag)).delete()


firestore_tag_dao = FirestoreTagDAO()
