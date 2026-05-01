from tcms.management.models import Tag


class TagDAO:
    def __init__(self):
        # junction collection: relation_type -> list of {entity_id, tag_id, tag_name}
        self._relations_store = {}

    # ------------------------------------------------------------------
    # internal helpers
    # ------------------------------------------------------------------

    def _collection(self, model_obj):
        return f"{model_obj.__class__.__name__.lower()}_tag"

    def _entity_key(self, model_obj):
        return f"{model_obj.__class__.__name__.lower()}_id"

    def _add_relation(self, collection, entry):
        if collection not in self._relations_store:
            self._relations_store[collection] = []
        if entry not in self._relations_store[collection]:
            self._relations_store[collection].append(entry)

    def _remove_relation(self, collection, match):
        if collection in self._relations_store:
            self._relations_store[collection] = [
                r for r in self._relations_store[collection]
                if not all(r.get(k) == v for k, v in match.items())
            ]

    def _get_relations(self, collection, match):
        return [
            r for r in self._relations_store.get(collection, [])
            if all(r.get(k) == v for k, v in match.items())
        ]

    # ------------------------------------------------------------------
    # WRITE operations
    # ------------------------------------------------------------------

    def add_tag(self, model_obj, tag):
        """
        Add tag to a model object (TestCase, TestPlan, or TestRun).
        """
        model_obj.add_tag(tag)

        self._add_relation(
            self._collection(model_obj),
            {self._entity_key(model_obj): model_obj.pk, "tag_id": tag.pk, "tag_name": tag.name},
        )
        print(f"[TagDAO] add_tag: added tag '{tag.name}' to ({model_obj.__class__.__name__.lower()}, {model_obj.pk})")

    def remove_tag(self, model_obj, tag):
        """
        Remove tag from a model object (TestCase, TestPlan, or TestRun).
        """
        model_obj.remove_tag(tag)

        self._remove_relation(
            self._collection(model_obj),
            {self._entity_key(model_obj): model_obj.pk, "tag_id": tag.pk},
        )
        print(f"[TagDAO] remove_tag: removed tag '{tag.name}' from ({model_obj.__class__.__name__.lower()}, {model_obj.pk})")

    # ------------------------------------------------------------------
    # READ operations
    # ------------------------------------------------------------------

    def get_tags(self, model_obj):
        """
        Get all tags for a model object, comparing old and new storage.
        Returns list of {"id": ..., "name": ...} dicts.
        """
        old_result = list(model_obj.tag.values("id", "name"))

        new_relations = self._get_relations(
            self._collection(model_obj),
            {self._entity_key(model_obj): model_obj.pk},
        )
        if new_relations:
            old_names = {t["name"] for t in old_result}
            new_names = {r["tag_name"] for r in new_relations}
            key = (model_obj.__class__.__name__.lower(), model_obj.pk)
            if old_names != new_names:
                print(f"[TagDAO] MISMATCH in 'get_tags for {key}':")
                print(f"  OLD: {old_names}")
                print(f"  NEW: {new_names}")
            else:
                print(f"[TagDAO] OK 'get_tags for {key}': results match")
        else:
            key = (model_obj.__class__.__name__.lower(), model_obj.pk)
            print(f"[TagDAO] get_tags: {key} not in new storage yet - skipping comparison")

        return old_result

    def filter(self, query, extra_fields=None):
        """
        Return a list of tag dicts matching query.
        Used by the Tag.filter RPC endpoint.
        """
        fields = ["id", "name"] + (extra_fields or [])
        return list(
            Tag.objects.filter(**query)
            .values(*fields)
            .order_by("id")
            .distinct()
        )

    @staticmethod
    def get_or_create(user, tag_name):
        """Wrapper around Tag.get_or_create for consistent access."""
        return Tag.get_or_create(user, tag_name)

    @staticmethod
    def get_by_name(tag_name):
        """Fetch a Tag by name from ORM."""
        return Tag.objects.get(name=tag_name)


tag_dao = TagDAO()
