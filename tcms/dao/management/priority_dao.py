from tcms.management.models import Priority

_FIELDS = ("id", "value", "is_active")


class PriorityDAO:
    def __init__(self):
        self._store = {}

    def _to_dict(self, priority):
        return {field: getattr(priority, field) for field in _FIELDS}

    def _compare(self, old, new, operation):
        if old != new:
            print(f"[PriorityDAO] MISMATCH in '{operation}':")
            print(f"  OLD: {old}")
            print(f"  NEW: {new}")
        else:
            print(f"[PriorityDAO] OK '{operation}': results match")

    def filter(self, query):
        old_result = list(
            Priority.objects.filter(**query)
            .values(*_FIELDS)
            .order_by("id")
            .distinct()
        )

        new_result = [self._store[p["id"]] for p in old_result if p["id"] in self._store]
        if new_result:
            old_subset = [p for p in old_result if p["id"] in self._store]
            self._compare(old_subset, new_result, "filter")
        else:
            print("[PriorityDAO] filter: no data in new storage yet - skipping comparison")

        return old_result

    def get_by_id(self, priority_id):
        old_result = Priority.objects.get(pk=priority_id)

        new_result = self._store.get(priority_id)
        if new_result is not None:
            self._compare(self._to_dict(old_result), new_result, "get_by_id")
        else:
            print(f"[PriorityDAO] get_by_id: priority id={priority_id} not in new storage yet - skipping comparison")

        return old_result

    def save(self, priority):
        priority.save()
        self._store[priority.pk] = self._to_dict(priority)
        print(f"[PriorityDAO] save: synced priority id={priority.pk} to new storage")
        return priority


priority_dao = PriorityDAO()