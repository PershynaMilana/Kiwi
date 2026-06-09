from tcms.management.models import Version

_VERSION_FIELDS = (
    "id",
    "value",
    "product",
)


class VersionDAO:
    # ------------------------------------------------------------------
    # READ operations
    # ------------------------------------------------------------------

    def filter(self, query):
        """
        Return a list of version dicts matching query.
        Used by the Version.filter RPC endpoint.
        """
        return list(
            Version.objects.filter(**query)
            .values(*_VERSION_FIELDS, "product__name")
            .order_by("product", "id")
            .distinct()
        )

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


from django.conf import settings as _settings  # noqa: E402
if getattr(_settings, 'USE_FIRESTORE_DAOS', False):
    from tcms.dao.firestore.management.version_dao import version_dao  # noqa: F401, F811
