from tcms.dao.firestore.client import get_firestore_client
from tcms.dao.firestore.post_filtering.environment_post_filterer import (
    EnvironmentPostFilterer,
    EnvironmentPropertyPostFilterer,
)
from tcms.testruns.models import Environment, EnvironmentProperty

_ENV_COLLECTION = 'environments'
_ENV_PROPERTY_COLLECTION = 'environment_properties'


class FirestoreEnvironmentDAO:
    """
    Firestore-backed DAO for Environment.

    filter() — reads from Firestore, applies post-filtering in Python.
    save()   — dual-write: persists via ORM then syncs the document to Firestore.
    """

    def __init__(self):
        db = get_firestore_client()
        self._collection = db.collection(_ENV_COLLECTION)
        self._post_filterer = EnvironmentPostFilterer()

    def _to_dict(self, env):
        return {
            'id': env.id,
            'name': env.name,
            'description': env.description,
        }

    def _doc_ref(self, env_id):
        return self._collection.document(str(env_id))

    def filter(self, query):
        """Fetch all Environment documents from Firestore and apply post-filtering."""
        all_docs = [doc.to_dict() for doc in self._collection.stream()]
        return self._post_filterer.filter(all_docs, query)

    def save(self, env):
        """Persist an Environment: ORM save first, then sync to Firestore."""
        env.save()
        self._doc_ref(env.pk).set(self._to_dict(env))
        return env


class FirestoreEnvironmentPropertyDAO:
    """
    Firestore-backed DAO for EnvironmentProperty.

    filter()       — reads from Firestore, applies post-filtering in Python.
    get_or_create() — ORM get-or-create then syncs the document to Firestore.
    remove()       — deletes from ORM and Firestore.
    """

    def __init__(self):
        db = get_firestore_client()
        self._collection = db.collection(_ENV_PROPERTY_COLLECTION)
        self._post_filterer = EnvironmentPropertyPostFilterer()

    def _to_dict(self, prop):
        return {
            'id': prop.id,
            'environment_id': prop.environment_id,
            'name': prop.name,
            'value': prop.value,
        }

    def _doc_ref(self, prop_id):
        return self._collection.document(str(prop_id))

    def filter(self, query):
        """Fetch all EnvironmentProperty documents from Firestore and apply post-filtering."""
        all_docs = [doc.to_dict() for doc in self._collection.stream()]
        return self._post_filterer.filter(all_docs, query)

    def get_or_create(self, environment_id, name, value):
        """Get or create an EnvironmentProperty in ORM and sync to Firestore."""
        prop, created = EnvironmentProperty.objects.get_or_create(
            environment_id=environment_id, name=name, value=value
        )
        self._doc_ref(prop.pk).set(self._to_dict(prop))
        return prop, created

    def remove(self, query):
        """Delete EnvironmentProperty objects matching query in ORM and Firestore."""
        prop_ids = list(EnvironmentProperty.objects.filter(**query).values_list('pk', flat=True))
        EnvironmentProperty.objects.filter(**query).delete()
        for prop_id in prop_ids:
            self._doc_ref(prop_id).delete()


firestore_environment_dao = FirestoreEnvironmentDAO()
firestore_environment_property_dao = FirestoreEnvironmentPropertyDAO()
