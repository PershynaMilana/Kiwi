from tcms.testplans.models import PlanType

_FIELDS = ("id", "name", "description")


class PlanTypeDAO:
    def __init__(self):
        self._store = {}

    def _to_dict(self, plan_type):
        return {field: getattr(plan_type, field) for field in _FIELDS}

    def _compare(self, old, new, operation):
        if old != new:
            print(f"[PlanTypeDAO] MISMATCH in '{operation}':")
            print(f"  OLD: {old}")
            print(f"  NEW: {new}")
        else:
            print(f"[PlanTypeDAO] OK '{operation}': results match")

    def filter(self, query):
        old_result = list(
            PlanType.objects.filter(**query)
            .values(*_FIELDS)
            .order_by("id")
            .distinct()
        )

        new_result = [self._store[p["id"]] for p in old_result if p["id"] in self._store]
        if new_result:
            old_subset = [p for p in old_result if p["id"] in self._store]
            self._compare(old_subset, new_result, "filter")
        else:
            print("[PlanTypeDAO] filter: no data in new storage yet - skipping comparison")

        return old_result

    def get_by_id(self, plan_type_id):
        old_result = PlanType.objects.get(pk=plan_type_id)

        new_result = self._store.get(plan_type_id)
        if new_result is not None:
            self._compare(self._to_dict(old_result), new_result, "get_by_id")
        else:
            print(f"[PlanTypeDAO] get_by_id: plan_type id={plan_type_id} not in new storage yet - skipping comparison")

        return old_result

    def save(self, plan_type):
        plan_type.save()
        self._store[plan_type.pk] = self._to_dict(plan_type)
        print(f"[PlanTypeDAO] save: synced plan_type id={plan_type.pk} to new storage")
        return plan_type


plan_type_dao = PlanTypeDAO()