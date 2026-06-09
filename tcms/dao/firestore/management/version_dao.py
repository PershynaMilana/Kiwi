from tcms.dao.firestore.utils import chunked_queryset, int_pk_only
from tcms.management.models import Product, Version

_VERSION_FIELDS = (
    "id",
    "value",
    "product",
)


def _versions_to_dicts(versions):
    """Convert Version instances to dicts, batch-fetching related product names."""
    product_ids = list({v.product_id for v in versions if v.product_id and isinstance(v.product_id, int)})
    products = {p.pk: p.name for p in chunked_queryset(Product, "pk", product_ids)}
    return [
        {
            "id": v.id,
            "value": v.value,
            "product": v.product_id,
            "product__name": products.get(v.product_id),
        }
        for v in versions
    ]


class VersionDAO:
    # ------------------------------------------------------------------
    # READ operations
    # ------------------------------------------------------------------

    def filter(self, query):
        """
        Return a list of version dicts matching query.
        Used by the Version.filter RPC endpoint.
        """
        resolved = {}
        for k, v in query.items():
            if k == "product__in":
                resolved["product_id__in"] = list(v) if isinstance(v, (list, tuple)) else [v]
            elif k == "product":
                resolved["product_id"] = v
            else:
                resolved[k] = v
        query = resolved
        # order_by("product_id", "id") combined with any filter requires a
        # composite index. Use .order_by() to suppress Meta ordering and sort in Python.
        orm_key = next(
            (k for k in query if k == "product_id" or k.startswith("product_id__")),
            None,
        ) or next(iter(query), None)

        if orm_key:
            orm_query = {orm_key: query[orm_key]}
            python_filters = {k: v for k, v in query.items() if k != orm_key}
        else:
            orm_query = {}
            python_filters = {}

        versions = int_pk_only(list(Version.objects.filter(**orm_query).order_by()))

        for k, v in python_filters.items():
            if k.endswith("__in"):
                field = k[:-4]
                versions = [obj for obj in versions if getattr(obj, field, None) in v]
            else:
                versions = [obj for obj in versions if getattr(obj, k, None) == v]

        versions.sort(key=lambda v: (v.product_id or 0, v.id or 0))
        return _versions_to_dicts(versions)

    # ------------------------------------------------------------------
    # WRITE operations
    # ------------------------------------------------------------------

    def save(self, version, update_fields=None):
        """
        Persist a Version object.
        Used by Version.create and Version.update RPC endpoints.
        """
        if update_fields:
            version.save(update_fields=update_fields)
        else:
            version.save()
        return version


version_dao = VersionDAO()
