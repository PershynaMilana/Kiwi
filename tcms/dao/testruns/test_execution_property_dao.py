from tcms.testruns.models import TestExecutionProperty

_FIELDS = ("id", "execution", "name", "value")


class TestExecutionPropertyDAO:
    def filter(self, query):
        return list(
            TestExecutionProperty.objects.filter(**query)
            .values(*_FIELDS)
            .order_by("execution", "name", "value")
            .distinct()
        )

    def get_or_create(self, execution_id, name, value):
        prop, created = TestExecutionProperty.objects.get_or_create(
            execution_id=execution_id, name=name, value=value
        )
        return prop, created

    def remove(self, query):
        TestExecutionProperty.objects.filter(**query).delete()


test_execution_property_dao = TestExecutionPropertyDAO()

from django.conf import settings as _settings  # noqa: E402
if getattr(_settings, 'USE_FIRESTORE_DAOS', False):
    from tcms.dao.firestore.testruns.test_execution_property_dao import test_execution_property_dao  # noqa: F401, F811
