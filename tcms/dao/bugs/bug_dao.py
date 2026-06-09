from tcms.bugs.models import Bug

_BUG_FIELDS = (
    "id",
    "summary",
    "created_at",
    "status",
    "reporter_id",
    "assignee_id",
    "product_id",
    "version_id",
    "build_id",
    "severity_id",
)


class BugDAO:
    # ------------------------------------------------------------------
    # READ operations
    # ------------------------------------------------------------------

    def filter(self, query):
        """
        Return a list of bug dicts matching query.
        Used internally and by Bug.filter_canonical RPC endpoint.
        """
        return list(
            Bug.objects.filter(**query)
            .values(*_BUG_FIELDS)
            .order_by("id")
            .distinct()
        )

    def filter_with_names(self, query):
        """
        Return a list of bug dicts with related field names.
        Used by the Bug.filter RPC endpoint.
        """
        _NAME_FIELDS = (
            "pk",
            "summary",
            "created_at",
            "product__name",
            "version__value",
            "build__name",
            "reporter__username",
            "assignee__username",
            "severity__name",
            "severity__color",
            "severity__icon",
        )
        return list(
            Bug.objects.filter(**query)
            .values(*_NAME_FIELDS)
            .distinct()
        )

    def filter_canonical(self, query):
        """
        Return a list of bug dicts with FK IDs.
        Used by the Bug.filter_canonical RPC endpoint.
        """
        _CANONICAL_FIELDS = (
            "id",
            "summary",
            "created_at",
            "status",
            "reporter",
            "assignee",
            "product",
            "version",
            "build",
            "severity",
        )
        return list(
            Bug.objects.filter(**query)
            .values(*_CANONICAL_FIELDS)
            .distinct()
        )

    def get_by_id(self, bug_id):
        """
        Return a single Bug object by primary key.
        """
        return Bug.objects.get(pk=bug_id)

    # ------------------------------------------------------------------
    # WRITE operations
    # ------------------------------------------------------------------

    def save(self, bug, update_fields=None):
        """
        Persist a Bug object.
        Used by Bug.create and Bug.update RPC endpoints.
        """
        if update_fields:
            bug.save(update_fields=update_fields)
        else:
            bug.save()
        return bug

    def remove(self, query):
        """
        Delete Bug objects matching query.
        Used by Bug.remove RPC endpoint.
        """
        return Bug.objects.filter(**query).delete()


bug_dao = BugDAO()


from django.conf import settings as _settings  # noqa: E402
if getattr(_settings, 'USE_FIRESTORE_DAOS', False):
    from tcms.dao.firestore.bugs.bug_dao import bug_dao  # noqa: F401, F811
