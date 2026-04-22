from tcms.bugs.models import Severity

_FIELDS = ("id", "name", "weight", "icon", "color")


class SeverityDAO:
    def __init__(self):
        self._store = {}

    def _to_dict(self, severity):
        return {field: getattr(severity, field) for field in _FIELDS}

    def _compare(self, old, new, operation):
        if old != new:
            print(f"[SeverityDAO] MISMATCH in '{operation}':")
            print(f"  OLD: {old}")
            print(f"  NEW: {new}")
        else:
            print(f"[SeverityDAO] OK '{operation}': results match")

    def filter(self, query):
        old_result = list(
            Severity.objects.filter(**query)
            .values(*_FIELDS)
            .order_by("id")
            .distinct()
        )

        new_result = [self._store[s["id"]] for s in old_result if s["id"] in self._store]
        if new_result:
            old_subset = [s for s in old_result if s["id"] in self._store]
            self._compare(old_subset, new_result, "filter")
        else:
            print("[SeverityDAO] filter: no data in new storage yet - skipping comparison")

        return old_result

    def get_by_id(self, severity_id):
        old_result = Severity.objects.get(pk=severity_id)

        new_result = self._store.get(severity_id)
        if new_result is not None:
            self._compare(self._to_dict(old_result), new_result, "get_by_id")
        else:
            print(f"[SeverityDAO] get_by_id: severity id={severity_id} not in new storage yet - skipping comparison")

        return old_result

    def save(self, severity):
        severity.save()
        self._store[severity.pk] = self._to_dict(severity)
        print(f"[SeverityDAO] save: synced severity id={severity.pk} to new storage")
        return severity


severity_dao = SeverityDAO()