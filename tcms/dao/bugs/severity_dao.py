from tcms.bugs.models import Severity

_FIELDS = ("id", "name", "weight", "icon", "color")


class SeverityDAO:
    def filter(self, query):
        return list(
            Severity.objects.filter(**query)
            .values(*_FIELDS)
            .order_by("id")
            .distinct()
        )

    def get_by_id(self, severity_id):
        return Severity.objects.get(pk=severity_id)

    def save(self, severity):
        severity.save()
        return severity


severity_dao = SeverityDAO()

from django.conf import settings as _settings  # noqa: E402
if getattr(_settings, 'USE_FIRESTORE_DAOS', False):
    from tcms.dao.firestore.bugs.severity_dao import severity_dao  # noqa: F401, F811
