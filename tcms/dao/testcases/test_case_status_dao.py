from tcms.testcases.models import TestCaseStatus

_FIELDS = ("id", "name", "description", "is_confirmed")


class TestCaseStatusDAO:
    def filter_objects(self, query):
        return TestCaseStatus.objects.filter(**query)

    def filter(self, query):
        return list(
            TestCaseStatus.objects.filter(**query)
            .values(*_FIELDS)
            .order_by("id")
            .distinct()
        )

    def get_by_id(self, status_id):
        return TestCaseStatus.objects.get(pk=status_id)

    def save(self, status):
        status.save()
        return status


test_case_status_dao = TestCaseStatusDAO()

from django.conf import settings as _settings  # noqa: E402
if getattr(_settings, 'USE_FIRESTORE_DAOS', False):
    from tcms.dao.firestore.testcases.test_case_status_dao import test_case_status_dao  # noqa: F401, F811
