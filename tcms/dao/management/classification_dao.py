from tcms.management.models import Classification

_FIELDS = ("id", "name")


class ClassificationDAO:
    def __init__(self):
        self._store = {}

    def _to_dict(self, classification):
        return {field: getattr(classification, field) for field in _FIELDS}

    def _compare(self, old, new, operation):
        if old != new:
            print(f"[ClassificationDAO] MISMATCH in '{operation}':")
            print(f"  OLD: {old}")
            print(f"  NEW: {new}")
        else:
            print(f"[ClassificationDAO] OK '{operation}': results match")

    def filter(self, query):
        old_result = list(
            Classification.objects.filter(**query)
            .values(*_FIELDS)
            .order_by("id")
            .distinct()
        )

        new_result = [self._store[c["id"]] for c in old_result if c["id"] in self._store]
        if new_result:
            old_subset = [c for c in old_result if c["id"] in self._store]
            self._compare(old_subset, new_result, "filter")
        else:
            print("[ClassificationDAO] filter: no data in new storage yet - skipping comparison")

        return old_result

    def get_by_id(self, classification_id):
        old_result = Classification.objects.get(pk=classification_id)

        new_result = self._store.get(classification_id)
        if new_result is not None:
            self._compare(self._to_dict(old_result), new_result, "get_by_id")
        else:
            print(f"[ClassificationDAO] get_by_id: classification id={classification_id} not in new storage yet - skipping comparison")

        return old_result

    def save(self, classification):
        classification.save()
        self._store[classification.pk] = self._to_dict(classification)
        print(f"[ClassificationDAO] save: synced classification id={classification.pk} to new storage")
        return classification


classification_dao = ClassificationDAO()