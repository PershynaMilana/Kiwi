from tcms.testcases.models import TestCaseStatus

_FIELDS = ("id", "name", "description", "is_confirmed")


def _status_to_dict(s):
    return {
        "id": s.id,
        "name": s.name,
        "description": s.description,
        "is_confirmed": s.is_confirmed,
    }


class TestCaseStatusDAO:
    def filter_objects(self, query):
        return TestCaseStatus.objects.filter(**query)

    def filter(self, query):
        # gcloudc projection queries (.values()) require every projected field
        # to be declared as a Firestore index.  TestCaseStatus is a tiny
        # lookup table (2-3 rows), so fetching full objects and converting
        # to dicts in Python is simpler and avoids all projection issues.
        return [
            _status_to_dict(s)
            for s in TestCaseStatus.objects.filter(**query).order_by("id")
        ]

    def get_by_id(self, status_id):
        return TestCaseStatus.objects.get(pk=status_id)

    def save(self, status):
        status.save()
        return status


test_case_status_dao = TestCaseStatusDAO()
