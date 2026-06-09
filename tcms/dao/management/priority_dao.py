from tcms.management.models import Priority

_FIELDS = ("id", "value", "is_active")


class PriorityDAO:
    def filter(self, query):
        return list(
            Priority.objects.filter(**query)
            .values(*_FIELDS)
            .order_by("id")
            .distinct()
        )

    def filter_objects(self, query):
        return Priority.objects.filter(**query).order_by("id")

    def get_by_id(self, priority_id):
        return Priority.objects.get(pk=priority_id)

    def save(self, priority):
        priority.save()
        return priority


priority_dao = PriorityDAO()

from django.conf import settings as _settings  # noqa: E402
if getattr(_settings, 'USE_FIRESTORE_DAOS', False):
    from tcms.dao.firestore.management.priority_dao import priority_dao  # noqa: F401, F811
