from django.db.models import Count
from django.forms.models import model_to_dict

from tcms.testcases.models import TestCase, TestCasePlan
from tcms.testplans.models import TestPlan

_TEST_PLAN_FIELDS = (
    "id",
    "name",
    "text",
    "create_date",
    "is_active",
    "extra_link",
    "product_version",
    "product",
    "author",
    "type",
    "parent",
)


class TestPlanDAO:
    # ------------------------------------------------------------------
    # READ operations
    # ------------------------------------------------------------------

    def filter(self, query):
        """
        Return a list of test plan dicts matching query.
        Used by the TestPlan.filter RPC endpoint.
        """
        return list(
            TestPlan.objects.filter(**query)
            .values(
                *_TEST_PLAN_FIELDS,
                "product_version__value",
                "product__name",
                "author__username",
                "type__name",
            )
            .annotate(Count("children"))
            .order_by("product", "id")
            .distinct()
        )

    def filter_objects(self, **kwargs):
        """
        Return a TestPlan queryset for use in views and templates.
        """
        return TestPlan.objects.filter(**kwargs)

    def get_by_id(self, plan_id):
        """
        Return a single TestPlan object by primary key.
        """
        return TestPlan.objects.get(pk=plan_id)

    # ------------------------------------------------------------------
    # WRITE operations
    # ------------------------------------------------------------------

    def save(self, plan, update_fields=None):
        """
        Persist a TestPlan object.
        Used by TestPlan.create and TestPlan.update RPC endpoints.
        """
        if update_fields:
            plan.save(update_fields=update_fields)
        else:
            plan.save()
        return plan

    def add_case(self, plan, case):
        """
        Link a test case to the given test plan.
        Used by the TestPlan.add_case RPC endpoint.
        """
        test_case_plan = plan.add_case(case)

        result = model_to_dict(case, exclude=["component", "plan", "tag"])
        result["create_date"] = case.create_date
        result["sortkey"] = test_case_plan.sortkey
        return result

    def remove_case(self, plan_id, case_id):
        """
        Unlink a test case from the given test plan.
        Used by the TestPlan.remove_case RPC endpoint.
        """
        TestCasePlan.objects.filter(case=case_id, plan=plan_id).delete()

    def update_case_order(self, plan_id, case_id, sortkey):
        """
        Update display order of a test case within a test plan.
        Used by the TestPlan.update_case_order RPC endpoint.
        """
        TestCasePlan.objects.filter(  # pylint:disable=objects-update-used
            case=case_id, plan=plan_id
        ).update(sortkey=sortkey)

    def tree(self, plan):
        """
        Return the DFS-ordered ancestry tree for the given test plan.
        Used by the TestPlan.tree RPC endpoint.
        """
        result = []
        for record in plan.tree_as_list():
            result.append(
                {
                    "id": record.pk,
                    "name": record.name,
                    "parent_id": record.parent_id,
                    "tree_depth": record.tree_depth,
                    "url": record.get_full_url(),
                }
            )
        return result


test_plan_dao = TestPlanDAO()


from django.conf import settings as _settings  # noqa: E402
if getattr(_settings, 'USE_FIRESTORE_DAOS', False):
    from tcms.dao.firestore.testplans.test_plan_dao import test_plan_dao  # noqa: F401, F811
