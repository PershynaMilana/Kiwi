from tcms.testcases.models import BugSystem

_FIELDS = ("id", "name", "tracker_type", "base_url", "api_url", "api_username", "api_password")
_PUBLIC_FIELDS = ("id", "name", "tracker_type", "base_url", "api_url", "api_username")


class BugSystemDAO:
    def filter_objects(self, query):
        return BugSystem.objects.filter(**query)

    def filter(self, query):
        return list(
            BugSystem.objects.filter(**query)
            .values(*_PUBLIC_FIELDS)
            .order_by("id")
            .distinct()
        )

    def get_by_id(self, bug_system_id):
        return BugSystem.objects.get(pk=bug_system_id)

    def save(self, bug_system):
        bug_system.save()
        return bug_system


bug_system_dao = BugSystemDAO()

from django.conf import settings as _settings  # noqa: E402
if getattr(_settings, 'USE_FIRESTORE_DAOS', False):
    from tcms.dao.firestore.testcases.bug_system_dao import bug_system_dao  # noqa: F401, F811
