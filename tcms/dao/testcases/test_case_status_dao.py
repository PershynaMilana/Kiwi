from tcms.testcases.models import TestCaseStatus

_FIELDS = ("id", "name", "description", "is_confirmed")


class TestCaseStatusDAO:
    def __init__(self):
        self._store = {}

    def _to_dict(self, status):
        return {field: getattr(status, field) for field in _FIELDS}

    def _compare(self, old, new, operation):
        if old != new:
            print(f"[TestCaseStatusDAO] MISMATCH in '{operation}':")
            print(f"  OLD: {old}")
            print(f"  NEW: {new}")
        else:
            print(f"[TestCaseStatusDAO] OK '{operation}': results match")

    def filter(self, query):
        old_result = list(
            TestCaseStatus.objects.filter(**query)
            .values(*_FIELDS)
            .order_by("id")
            .distinct()
        )

        new_result = [self._store[s["id"]] for s in old_result if s["id"] in self._store]
        if new_result:
            old_subset = [s for s in old_result if s["id"] in self._store]
            self._compare(old_subset, new_result, "filter")
        else:
            print("[TestCaseStatusDAO] filter: no data in new storage yet - skipping comparison")

        return old_result

    def get_by_id(self, status_id):
        old_result = TestCaseStatus.objects.get(pk=status_id)

        new_result = self._store.get(status_id)
        if new_result is not None:
            self._compare(self._to_dict(old_result), new_result, "get_by_id")
        else:
            print(f"[TestCaseStatusDAO] get_by_id: status id={status_id} not in new storage yet - skipping comparison")

        return old_result

    def save(self, status):
        status.save()
        self._store[status.pk] = self._to_dict(status)
        print(f"[TestCaseStatusDAO] save: synced status id={status.pk} to new storage")
        return status


test_case_status_dao = TestCaseStatusDAO()