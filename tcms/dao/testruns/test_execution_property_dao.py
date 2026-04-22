from tcms.testruns.models import TestExecutionProperty

_FIELDS = ("id", "execution", "name", "value")


class TestExecutionPropertyDAO:
    def __init__(self):
        self._store = {}

    def _to_dict(self, prop):
        result = {field: getattr(prop, field) for field in _FIELDS}
        result["execution"] = prop.execution_id
        return result

    def _compare(self, old, new, operation):
        if old != new:
            print(f"[TestExecutionPropertyDAO] MISMATCH in '{operation}':")
            print(f"  OLD: {old}")
            print(f"  NEW: {new}")
        else:
            print(f"[TestExecutionPropertyDAO] OK '{operation}': results match")

    def filter(self, query):
        old_result = list(
            TestExecutionProperty.objects.filter(**query)
            .values(*_FIELDS)
            .order_by("execution", "name", "value")
            .distinct()
        )

        new_result = [self._store[p["id"]] for p in old_result if p["id"] in self._store]
        if new_result:
            old_subset = [p for p in old_result if p["id"] in self._store]
            self._compare(old_subset, new_result, "filter")
        else:
            print("[TestExecutionPropertyDAO] filter: no data in new storage yet - skipping comparison")

        return old_result

    def get_or_create(self, execution_id, name, value):
        prop, created = TestExecutionProperty.objects.get_or_create(
            execution_id=execution_id, name=name, value=value
        )
        self._store[prop.pk] = self._to_dict(prop)
        print(f"[TestExecutionPropertyDAO] get_or_create: synced property id={prop.pk} to new storage")
        return prop, created

    def remove(self, query):
        for prop in TestExecutionProperty.objects.filter(**query):
            self._store.pop(prop.pk, None)
        TestExecutionProperty.objects.filter(**query).delete()
        print(f"[TestExecutionPropertyDAO] remove: deleted properties matching {query}")


test_execution_property_dao = TestExecutionPropertyDAO()