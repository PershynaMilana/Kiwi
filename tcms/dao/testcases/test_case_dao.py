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
    # ------------------------------------------------------------------
    # READ operations
    # ------------------------------------------------------------------

    def filter(self, query):
        """
        Return a list of test case dicts matching query.
        Used by the TestCase.filter RPC endpoint.
        """
        return list(
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

    def filter_objects(self, **kwargs):
        """Return a TestCase queryset for use in views and templates."""
        return TestCase.objects.filter(**kwargs)

    def get_by_id(self, case_id):
        """Return a single TestCase object by primary key."""
        return TestCase.objects.get(pk=case_id)

    def history(self, case, query):
        """
        Return history records for the given test case.
        Used by the TestCase.history RPC endpoint.
        """
        return list(case.history.filter(**query).values())

    def sortkeys(self, query):
        """
        Return {str(case_id): sortkey} mapping for TestCasePlan records.
        Used by the TestCase.sortkeys RPC endpoint.
        """
        result = {}
        for record in TestCasePlan.objects.filter(**query):
            result[str(record.case_id)] = record.sortkey
        return result

    def get_notification_cc(self, case):
        """
        Return notification CC list for the given test case.
        Used by the TestCase.get_notification_cc RPC endpoint.
        """
        return case.emailing.get_cc_list()

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
        return case

    def remove(self, query):
        """
        Delete TestCase objects matching query.
        Used by TestCase.remove RPC endpoint.
        """
        return TestCase.objects.filter(**query).delete()

    def add_component(self, case, component_obj):
        """
        Add a component to the given test case.
        Used by the TestCase.add_component RPC endpoint.
        """
        case.add_component(component_obj)
        return model_to_dict(component_obj)

    def remove_component(self, case, component_obj):
        """
        Remove a component from the given test case.
        Used by the TestCase.remove_component RPC endpoint.
        """
        case.remove_component(component_obj)

    def add_notification_cc(self, case, cc_list):
        """
        Add emails to notification CC list for the given test case.
        Used by the TestCase.add_notification_cc RPC endpoint.
        """
        case.emailing.add_cc(cc_list)

    def remove_notification_cc(self, case, cc_list):
        """
        Remove emails from notification CC list for the given test case.
        Used by the TestCase.remove_notification_cc RPC endpoint.
        """
        case.emailing.remove_cc(cc_list)


test_case_dao = TestCaseDAO()


from django.conf import settings as _settings  # noqa: E402
if getattr(_settings, 'USE_FIRESTORE_DAOS', False):
    from tcms.dao.firestore.testcases.test_case_dao import test_case_dao  # noqa: F401, F811
