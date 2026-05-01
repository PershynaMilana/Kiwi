from datetime import timedelta

from django.db.models.functions import Coalesce
from django.forms.models import model_to_dict

from tcms.testcases.models import TestCase, TestCasePlan

_TEST_CASE_FIELDS = (
    "id",
    "create_date",
    "is_automated",
    "script",
    "arguments",
    "extra_link",
    "summary",
    "requirement",
    "notes",
    "text",
    "case_status",
    "category",
    "priority",
    "author",
    "default_tester",
    "reviewer",
    "setup_duration",
    "testing_duration",
)


class TestCaseDAO:
    def __init__(self):
        self._store = {}
        # junction collection: relation_type -> list of {entity1_id, entity2_id, ...}
        self._relations_store = {}

    # ------------------------------------------------------------------
    # internal helpers
    # ------------------------------------------------------------------

    def _to_dict(self, case):
        result = {field: getattr(case, field) for field in _TEST_CASE_FIELDS}
        result["case_status"] = case.case_status_id
        result["category"] = case.category_id
        result["priority"] = case.priority_id
        result["author"] = case.author_id
        result["default_tester"] = case.default_tester_id
        result["reviewer"] = case.reviewer_id
        result["expected_duration"] = (
            (case.setup_duration or timedelta(0)) + (case.testing_duration or timedelta(0))
        )
        extra = TestCase.objects.filter(pk=case.pk).values(
            "case_status__name", "category__name", "priority__value",
            "author__username", "default_tester__username", "reviewer__username",
        ).first() or {}
        result.update(extra)
        return result

    def _compare(self, old, new, operation):
        if old != new:
            print(f"[TestCaseDAO] MISMATCH in '{operation}':")
            print(f"  OLD: {old}")
            print(f"  NEW: {new}")
        else:
            print(f"[TestCaseDAO] OK '{operation}': results match")

    def _add_relation(self, collection, entry):
        if collection not in self._relations_store:
            self._relations_store[collection] = []
        if entry not in self._relations_store[collection]:
            self._relations_store[collection].append(entry)

    def _remove_relation(self, collection, match):
        if collection in self._relations_store:
            self._relations_store[collection] = [
                r for r in self._relations_store[collection]
                if not all(r.get(k) == v for k, v in match.items())
            ]

    def _get_relations(self, collection, match):
        return [
            r for r in self._relations_store.get(collection, [])
            if all(r.get(k) == v for k, v in match.items())
        ]

    # ------------------------------------------------------------------
    # READ operations
    # ------------------------------------------------------------------

    def filter(self, query):
        """
        Return a list of test case dicts matching query.
        Used by the TestCase.filter RPC endpoint.
        """
        old_result = list(
            TestCase.objects.annotate(
                expected_duration=Coalesce("setup_duration", timedelta(0))
                + Coalesce("testing_duration", timedelta(0))
            )
            .filter(**query)
            .values(
                *_TEST_CASE_FIELDS,
                "case_status__name",
                "category__name",
                "priority__value",
                "author__username",
                "default_tester__username",
                "reviewer__username",
                "expected_duration",
            )
            .order_by("id")
            .distinct()
        )

        new_result = [self._store[c["id"]] for c in old_result if c["id"] in self._store]
        if new_result:
            old_subset = [c for c in old_result if c["id"] in self._store]
            self._compare(old_subset, new_result, "filter")
        else:
            print("[TestCaseDAO] filter: no data in new storage yet - skipping comparison")

        return old_result

    def filter_objects(self, **kwargs):
        """Return a TestCase queryset for use in views and templates."""
        return TestCase.objects.filter(**kwargs)

    def get_by_id(self, case_id):
        """Return a single TestCase object by primary key."""
        old_result = TestCase.objects.get(pk=case_id)

        new_result = self._store.get(case_id)
        if new_result is not None:
            self._compare(self._to_dict(old_result), new_result, "get_by_id")
        else:
            print(f"[TestCaseDAO] get_by_id: case id={case_id} not in new storage yet - skipping comparison")

        return old_result

    def history(self, case, query):
        """
        Return history records for the given test case.
        Used by the TestCase.history RPC endpoint.
        """
        old_result = list(case.history.filter(**query).values())
        print(f"[TestCaseDAO] history: case id={case.pk}, {len(old_result)} record(s)")
        return old_result

    def sortkeys(self, query):
        """
        Return {str(case_id): sortkey} mapping for TestCasePlan records.
        Used by the TestCase.sortkeys RPC endpoint.
        """
        result = {}
        for record in TestCasePlan.objects.filter(**query):
            result[str(record.case_id)] = record.sortkey

        print(f"[TestCaseDAO] sortkeys: {len(result)} record(s)")
        return result

    def get_notification_cc(self, case):
        """
        Return notification CC list for the given test case.
        Used by the TestCase.get_notification_cc RPC endpoint.
        """
        old_result = case.emailing.get_cc_list()

        new_relations = self._get_relations("testcase_notification_cc", {"testcase_id": case.pk})
        if new_relations:
            new_emails = sorted(r["email"] for r in new_relations)
            self._compare(sorted(old_result), new_emails, "get_notification_cc")
        else:
            print(f"[TestCaseDAO] get_notification_cc: case id={case.pk} not in new storage yet - skipping comparison")

        return old_result

    # ------------------------------------------------------------------
    # WRITE operations
    # ------------------------------------------------------------------

    def save(self, case, update_fields=None):
        """
        Persist a TestCase object.
        Used by TestCase.create and TestCase.update RPC endpoints.
        """
        if update_fields:
            case.save(update_fields=update_fields)
        else:
            case.save()

        self._store[case.pk] = self._to_dict(case)
        print(f"[TestCaseDAO] save: synced case id={case.pk} to new storage")
        return case

    def remove(self, query):
        """
        Delete TestCase objects matching query.
        Used by TestCase.remove RPC endpoint.
        """
        deleted = TestCase.objects.filter(**query).delete()
        print(f"[TestCaseDAO] remove: deleted {deleted[0]} case(s)")
        return deleted

    def add_component(self, case, component_obj):
        """
        Add a component to the given test case.
        Used by the TestCase.add_component RPC endpoint.
        """
        case.add_component(component_obj)
        self._add_relation(
            "testcase_component",
            {"testcase_id": case.pk, "component_id": component_obj.pk},
        )
        print(f"[TestCaseDAO] add_component: added component id={component_obj.pk} to case id={case.pk}")
        return model_to_dict(component_obj)

    def remove_component(self, case, component_obj):
        """
        Remove a component from the given test case.
        Used by the TestCase.remove_component RPC endpoint.
        """
        case.remove_component(component_obj)
        self._remove_relation(
            "testcase_component",
            {"testcase_id": case.pk, "component_id": component_obj.pk},
        )
        print(f"[TestCaseDAO] remove_component: removed component id={component_obj.pk} from case id={case.pk}")

    def add_notification_cc(self, case, cc_list):
        """
        Add emails to notification CC list for the given test case.
        Used by the TestCase.add_notification_cc RPC endpoint.
        """
        case.emailing.add_cc(cc_list)
        for email in cc_list:
            self._add_relation(
                "testcase_notification_cc",
                {"testcase_id": case.pk, "email": email},
            )
        print(f"[TestCaseDAO] add_notification_cc: added {cc_list} to case id={case.pk}")

    def remove_notification_cc(self, case, cc_list):
        """
        Remove emails from notification CC list for the given test case.
        Used by the TestCase.remove_notification_cc RPC endpoint.
        """
        case.emailing.remove_cc(cc_list)
        for email in cc_list:
            self._remove_relation(
                "testcase_notification_cc",
                {"testcase_id": case.pk, "email": email},
            )
        print(f"[TestCaseDAO] remove_notification_cc: removed {cc_list} from case id={case.pk}")


test_case_dao = TestCaseDAO()
