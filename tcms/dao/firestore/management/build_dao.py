from tcms.dao.firestore.utils import chunked_queryset, int_pk_only
from tcms.management.models import Build, Version

_CHUNK = 90


def _resolve_build_query(query):
    """Pre-resolve cross-collection traversals in a Build filter query."""
    from tcms.testplans.models import TestPlan

    resolved = {}
    for k, v in query.items():
        if k.startswith("version__plans"):
            # Two-hop FK: Build.version → Version.plans (TestPlan reverse FK)
            if k == "version__plans" or k == "version__plans__in":
                plan_ids = list(v) if isinstance(v, (list, tuple)) else [v]
            else:
                plan_lookup = k[len("version__plans__"):]
                plan_ids = list(TestPlan.objects.filter(**{plan_lookup: v}).values_list("pk", flat=True))
            version_ids = list(
                TestPlan.objects.filter(pk__in=plan_ids).values_list("product_version_id", flat=True)
            )
            resolved["version_id__in"] = version_ids

        elif k.startswith("version__"):
            # One-hop FK: Build.version → Version
            version_lookup = k[len("version__"):]
            if version_lookup == "in":
                resolved["version_id__in"] = list(v) if isinstance(v, (list, tuple)) else [v]
            else:
                version_ids = list(
                    Version.objects.filter(**{version_lookup: v}).values_list("pk", flat=True)
                )
                resolved["version_id__in"] = version_ids

        else:
            resolved[k] = v

    return resolved

_BUILD_FIELDS = (
    "id",
    "name",
    "version",
    "is_active",
)


def _builds_to_dicts(builds):
    """Convert Build instances to dicts, batch-fetching related version values."""
    version_ids = list({b.version_id for b in builds if b.version_id and isinstance(b.version_id, int)})
    versions = {v.pk: v.value for v in chunked_queryset(Version, "pk", version_ids)}
    return [
        {
            "id": b.id,
            "name": b.name,
            "version": b.version_id,
            "is_active": b.is_active,
            "version__value": versions.get(b.version_id),
        }
        for b in builds
    ]


class BuildDAO:
    # ------------------------------------------------------------------
    # READ operations
    # ------------------------------------------------------------------

    def filter(self, query):
        """
        Return a list of build dicts matching query.
        Used by the Build.filter RPC endpoint.
        """
        query = _resolve_build_query(query)

        # Firestore requires a composite index for any multi-field query.
        # Build.Meta.ordering = ["name"] also appends an implicit ORDER BY name,
        # turning even a single-field filter into a 2-field composite index.
        #
        # Strategy: apply exactly one field filter in ORM (with .order_by() to
        # suppress Meta ordering), then apply all remaining filters in Python.
        #
        # Priority: version_id* (most selective) → is_active → first key.
        orm_key = next(
            (k for k in query if k == "version_id" or k.startswith("version_id__")),
            None,
        ) or next(iter(query), None)

        if orm_key:
            orm_query = {orm_key: query[orm_key]}
            python_filters = {k: v for k, v in query.items() if k != orm_key}
        else:
            orm_query = {}
            python_filters = {}

        builds = int_pk_only(list(Build.objects.filter(**orm_query).order_by()))

        for k, v in python_filters.items():
            if k.endswith("__in"):
                field = k[:-4]
                builds = [b for b in builds if getattr(b, field, None) in v]
            else:
                builds = [b for b in builds if getattr(b, k, None) == v]

        builds.sort(key=lambda b: (b.version_id or 0, b.id or 0))
        return _builds_to_dicts(builds)

    def get_by_id(self, build_id):
        """
        Return a single Build object by primary key.
        """
        return Build.objects.get(pk=build_id)

    # ------------------------------------------------------------------
    # WRITE operations
    # ------------------------------------------------------------------

    def save(self, build, update_fields=None):
        """
        Persist a Build object.
        Used by Build.create and Build.update RPC endpoints.
        """
        if update_fields:
            build.save(update_fields=update_fields)
        else:
            build.save()
        return build


build_dao = BuildDAO()
