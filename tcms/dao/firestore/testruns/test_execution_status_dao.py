from tcms.testruns.models import TestExecutionStatus

_FIELDS = ("id", "name", "weight", "icon", "color")


class TestExecutionStatusDAO:
    def filter_objects(self, query):
        # order_by("-weight", "name") requires a composite index in Firestore.
        # Fetch unordered and sort in Python instead.
        # Also filter out large-PK records (gcloudc auto-IDs) that are duplicates
        # of safe-PK records created via admin.
        all_statuses = list(TestExecutionStatus.objects.filter(**query).order_by())
        safe = [s for s in all_statuses if isinstance(s.pk, int) and s.pk < 2 ** 31]
        # Fall back to all records if no safe-PK ones exist yet (fresh install)
        statuses = safe if safe else all_statuses
        # Deduplicate by name, keeping the smallest PK per name
        seen = {}
        for s in sorted(statuses, key=lambda x: x.pk or 0):
            if s.name not in seen:
                seen[s.name] = s
        statuses = list(seen.values())

        def _sort_key(s):
            try:
                w = -int(s.weight)
            except (TypeError, ValueError):
                w = 0
            return (w, s.name or "")

        statuses.sort(key=_sort_key)
        return statuses

    def filter(self, query):
        return list(
            TestExecutionStatus.objects.filter(**query)
            .values(*_FIELDS)
            .order_by("id")
        )

    def get_by_id(self, status_id):
        return TestExecutionStatus.objects.get(pk=status_id)

    def save(self, status):
        status.save()
        return status


test_execution_status_dao = TestExecutionStatusDAO()
