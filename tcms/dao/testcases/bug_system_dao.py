from tcms.testcases.models import BugSystem

_FIELDS = ("id", "name", "tracker_type", "base_url", "api_url", "api_username", "api_password")
_PUBLIC_FIELDS = ("id", "name", "tracker_type", "base_url", "api_url", "api_username")


class BugSystemDAO:
    def __init__(self):
        self._store = {}

    def _to_dict(self, bug_system):
        return {field: getattr(bug_system, field) for field in _FIELDS}

    def _compare(self, old, new, operation):
        if old != new:
            print(f"[BugSystemDAO] MISMATCH in '{operation}':")
            print(f"  OLD: {old}")
            print(f"  NEW: {new}")
        else:
            print(f"[BugSystemDAO] OK '{operation}': results match")

    def filter(self, query):
        old_result = list(
            BugSystem.objects.filter(**query)
            .values(*_PUBLIC_FIELDS)
            .order_by("id")
            .distinct()
        )

        new_result = [
            {k: self._store[b["id"]][k] for k in _PUBLIC_FIELDS}
            for b in old_result if b["id"] in self._store
        ]
        if new_result:
            old_subset = [b for b in old_result if b["id"] in self._store]
            self._compare(old_subset, new_result, "filter")
        else:
            print("[BugSystemDAO] filter: no data in new storage yet - skipping comparison")

        return old_result

    def get_by_id(self, bug_system_id):
        old_result = BugSystem.objects.get(pk=bug_system_id)

        new_result = self._store.get(bug_system_id)
        if new_result is not None:
            self._compare(self._to_dict(old_result), new_result, "get_by_id")
        else:
            print(f"[BugSystemDAO] get_by_id: bug_system id={bug_system_id} not in new storage yet - skipping comparison")

        return old_result

    def save(self, bug_system):
        bug_system.save()
        self._store[bug_system.pk] = self._to_dict(bug_system)
        print(f"[BugSystemDAO] save: synced bug_system id={bug_system.pk} to new storage")
        return bug_system


bug_system_dao = BugSystemDAO()