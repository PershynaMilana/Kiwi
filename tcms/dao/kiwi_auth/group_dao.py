from django.contrib.auth.models import Group


class GroupDAO:
    def __init__(self):
        self._store = {}

    def _to_dict(self, group):
        return {"id": group.pk, "name": group.name}

    def _compare(self, old, new, operation):
        if old != new:
            print(f"[GroupDAO] MISMATCH in '{operation}':")
            print(f"  OLD: {old}")
            print(f"  NEW: {new}")
        else:
            print(f"[GroupDAO] OK '{operation}': results match")

    def filter(self, query):
        old_result = list(
            Group.objects.filter(**query)
            .values("id", "name")
            .order_by("id")
            .distinct()
        )

        new_result = [self._store[g["id"]] for g in old_result if g["id"] in self._store]
        if new_result:
            old_subset = [g for g in old_result if g["id"] in self._store]
            self._compare(old_subset, new_result, "filter")
        else:
            print("[GroupDAO] filter: no data in new storage yet - skipping comparison")

        return old_result

    def get_by_id(self, group_id):
        old_result = Group.objects.get(pk=group_id)

        new_result = self._store.get(group_id)
        if new_result is not None:
            self._compare(self._to_dict(old_result), new_result, "get_by_id")
        else:
            print(f"[GroupDAO] get_by_id: group id={group_id} not in new storage yet - skipping comparison")

        return old_result

    def get_by_name(self, name):
        old_result = Group.objects.get(name=name)

        new_result = self._store.get(old_result.pk)
        if new_result is not None:
            self._compare(self._to_dict(old_result), new_result, "get_by_name")
        else:
            print(f"[GroupDAO] get_by_name: group '{name}' not in new storage yet - skipping comparison")

        return old_result

    def save(self, group):
        group.save()
        self._store[group.pk] = self._to_dict(group)
        print(f"[GroupDAO] save: synced group id={group.pk} to new storage")
        return group


group_dao = GroupDAO()
