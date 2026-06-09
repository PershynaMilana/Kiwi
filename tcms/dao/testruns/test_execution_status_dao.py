from tcms.testruns.models import TestExecutionStatus

_FIELDS = ("id", "name", "weight", "icon", "color")


class TestExecutionStatusDAO:
    def filter_objects(self, query):
        return TestExecutionStatus.objects.filter(**query).order_by("-weight", "name")

    def filter(self, query):
        return list(
            TestExecutionStatus.objects.filter(**query)
            .values(*_FIELDS)
            .order_by("id")
            .distinct()
        )

    def get_by_id(self, status_id):
        return TestExecutionStatus.objects.get(pk=status_id)

    def save(self, status):
        status.save()
        return status


test_execution_status_dao = TestExecutionStatusDAO()

from django.conf import settings as _settings  # noqa: E402
if getattr(_settings, 'USE_FIRESTORE_DAOS', False):
    from tcms.dao.firestore.testruns.test_execution_status_dao import test_execution_status_dao  # noqa: F401, F811
