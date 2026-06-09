from tcms.testruns.models import TestExecutionProperty

_FIELDS = ("id", "execution", "name", "value")


class TestExecutionPropertyDAO:
    def filter(self, query):
        return list(
            TestExecutionProperty.objects.filter(**query)
            .values(*_FIELDS)
            .order_by("execution_id", "name", "value")
        )

    def get_or_create(self, execution_id, name, value):
        prop, created = TestExecutionProperty.objects.get_or_create(
            execution_id=execution_id, name=name, value=value
        )
        return prop, created

    def remove(self, query):
        TestExecutionProperty.objects.filter(**query).delete()


test_execution_property_dao = TestExecutionPropertyDAO()
