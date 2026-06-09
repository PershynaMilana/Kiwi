from tcms.management.models import Build

_BUILD_FIELDS = (
    "id",
    "name",
    "version",
    "is_active",
)


class BuildDAO:
    # ------------------------------------------------------------------
    # READ operations
    # ------------------------------------------------------------------

    def filter(self, query):
        """
        Return a list of build dicts matching query.
        Used by the Build.filter RPC endpoint.
        """
        return list(
            Build.objects.filter(**query)
            .values(*_BUILD_FIELDS, "version__value")
            .order_by("version", "id")
            .distinct()
        )

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


from django.conf import settings as _settings  # noqa: E402
if getattr(_settings, 'USE_FIRESTORE_DAOS', False):
    from tcms.dao.firestore.management.build_dao import build_dao  # noqa: F401, F811
