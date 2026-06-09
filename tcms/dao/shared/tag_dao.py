from tcms.management.models import Tag


class TagDAO:
    # ------------------------------------------------------------------
    # internal helpers
    # ------------------------------------------------------------------

    def _collection(self, model_obj):
        return f"{model_obj.__class__.__name__.lower()}_tag"

    def _entity_key(self, model_obj):
        return f"{model_obj.__class__.__name__.lower()}_id"

    # ------------------------------------------------------------------
    # WRITE operations
    # ------------------------------------------------------------------

    def add_tag(self, model_obj, tag):
        """
        Add tag to a model object (TestCase, TestPlan, or TestRun).
        """
        model_obj.add_tag(tag)

    def remove_tag(self, model_obj, tag):
        """
        Remove tag from a model object (TestCase, TestPlan, or TestRun).
        """
        model_obj.remove_tag(tag)

    # ------------------------------------------------------------------
    # READ operations
    # ------------------------------------------------------------------

    def get_tags(self, model_obj):
        """
        Get all tags for a model object.
        Returns list of {"id": ..., "name": ...} dicts.
        """
        return list(model_obj.tag.values("id", "name"))

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


from django.conf import settings as _settings  # noqa: E402
if getattr(_settings, 'USE_FIRESTORE_DAOS', False):
    from tcms.dao.firestore.shared.tag_dao import tag_dao  # noqa: F401, F811
