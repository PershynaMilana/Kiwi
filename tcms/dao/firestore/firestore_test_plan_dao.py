from django.db.models import Count

from tcms.dao.firestore.client import get_firestore_client
from tcms.dao.firestore.post_filtering.test_plan_post_filterer import TestPlanPostFilterer
from tcms.testplans.models import TestPlan

_COLLECTION = 'test_plans'
_PLAN_CASES_COLLECTION = 'test_plan_cases'

_TEST_PLAN_FIELDS = (
    'id', 'name', 'text', 'create_date', 'is_active', 'extra_link',
    'product_version', 'product', 'author', 'type', 'parent',
)


class FirestoreTestPlanDAO:
    """
    Firestore-backed DAO for TestPlan.

    filter()  — reads from Firestore, applies post-filtering in Python.
    save()    — dual-write: persists via ORM then syncs the document to Firestore.

    filter_objects() and get_by_id() are not implemented here because they
    return Django ORM objects required by the view layer. Keep using the
    ORM DAO for those until the view layer is decoupled.
    """

    def __init__(self):
        db = get_firestore_client()
        self._collection = db.collection(_COLLECTION)
        self._plan_cases_collection = db.collection(_PLAN_CASES_COLLECTION)
        self._post_filterer = TestPlanPostFilterer()

    # ------------------------------------------------------------------
    # internal helpers
    # ------------------------------------------------------------------

    def _to_dict(self, plan):
        result = {field: getattr(plan, field) for field in _TEST_PLAN_FIELDS}
        result['product_version'] = plan.product_version_id
        result['product'] = plan.product_id
        result['author'] = plan.author_id
        result['type'] = plan.type_id
        result['parent'] = plan.parent_id
        extra = (
            TestPlan.objects.filter(pk=plan.pk)
            .annotate(Count('children'))
            .values('product_version__value', 'product__name', 'author__username', 'type__name', 'children__count')
            .first()
        ) or {}
        result.update(extra)
        return result

    def _doc_ref(self, plan_id):
        return self._collection.document(str(plan_id))

    # ------------------------------------------------------------------
    # READ
    # ------------------------------------------------------------------

    def filter(self, query):
        """
        Fetch all TestPlan documents from Firestore and apply criteria
        on the application side (post-filtering).

        :param query: ORM-style filter kwargs, e.g. {'name__icontains': 'foo', 'product': 61}
        :return: list of plan dicts
        """
        all_docs = [doc.to_dict() for doc in self._collection.stream()]
        return self._post_filterer.filter(all_docs, query)

    # ------------------------------------------------------------------
    # WRITE
    # ------------------------------------------------------------------

    def save(self, plan, update_fields=None):
        """
        Persist a TestPlan: ORM save first, then sync the document to Firestore.
        """
        if update_fields:
            plan.save(update_fields=update_fields)
        else:
            plan.save()

        self._doc_ref(plan.pk).set(self._to_dict(plan))
        return plan

    def add_case(self, plan, case):
        """
        Link a test case to a plan: delegates to ORM model method,
        then records the relation in Firestore.
        """
        test_case_plan = plan.add_case(case)

        self._plan_cases_collection.document(f'{plan.pk}_{case.pk}').set({
            'plan_id': plan.pk,
            'case_id': case.pk,
            'sortkey': test_case_plan.sortkey,
        })

        from django.forms.models import model_to_dict
        result = model_to_dict(case, exclude=['component', 'plan', 'tag'])
        result['create_date'] = case.create_date
        result['sortkey'] = test_case_plan.sortkey
        return result

    def remove_case(self, plan_id, case_id):
        """
        Unlink a test case from a plan in both ORM and Firestore.
        """
        from tcms.testcases.models import TestCasePlan
        TestCasePlan.objects.filter(case=case_id, plan=plan_id).delete()

        self._plan_cases_collection.document(f'{plan_id}_{case_id}').delete()

    def update_case_order(self, plan_id, case_id, sortkey):
        """
        Update the sort order of a case within a plan in both ORM and Firestore.
        """
        from tcms.testcases.models import TestCasePlan
        TestCasePlan.objects.filter(case=case_id, plan=plan_id).update(sortkey=sortkey)  # pylint:disable=objects-update-used

        doc_ref = self._plan_cases_collection.document(f'{plan_id}_{case_id}')
        doc_ref.update({'sortkey': sortkey})


firestore_test_plan_dao = FirestoreTestPlanDAO()
