from tcms.testcases.models import Category

_FIELDS = ("id", "name", "product", "description")


class CategoryDAO:
    def __init__(self):
        self._store = {}

    def _to_dict(self, category):
        result = {field: getattr(category, field) for field in _FIELDS}
        result["product"] = category.product_id
        return result

    def _compare(self, old, new, operation):
        if old != new:
            print(f"[CategoryDAO] MISMATCH in '{operation}':")
            print(f"  OLD: {old}")
            print(f"  NEW: {new}")
        else:
            print(f"[CategoryDAO] OK '{operation}': results match")

    def filter(self, query):
        old_result = list(
            Category.objects.filter(**query)
            .values(*_FIELDS)
            .order_by("id")
            .distinct()
        )

        new_result = [self._store[c["id"]] for c in old_result if c["id"] in self._store]
        if new_result:
            old_subset = [c for c in old_result if c["id"] in self._store]
            self._compare(old_subset, new_result, "filter")
        else:
            print("[CategoryDAO] filter: no data in new storage yet - skipping comparison")

        return old_result

    def get_by_id(self, category_id):
        old_result = Category.objects.get(pk=category_id)

        new_result = self._store.get(category_id)
        if new_result is not None:
            self._compare(self._to_dict(old_result), new_result, "get_by_id")
        else:
            print(f"[CategoryDAO] get_by_id: category id={category_id} not in new storage yet - skipping comparison")

        return old_result

    def save(self, category):
        category.save()
        self._store[category.pk] = self._to_dict(category)
        print(f"[CategoryDAO] save: synced category id={category.pk} to new storage")
        return category


category_dao = CategoryDAO()