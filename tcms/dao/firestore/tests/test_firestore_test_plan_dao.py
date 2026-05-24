from django.test import TestCase

from tcms.dao.firestore.firestore_test_case_dao import firestore_test_case_dao
from tcms.dao.firestore.firestore_test_plan_dao import firestore_test_plan_dao
from tcms.testcases.models import TestCaseStatus
from tcms.tests.factories import (
    ProductFactory, TestCaseFactory, TestPlanFactory, UserFactory, VersionFactory,
)


class TestFirestoreTestPlanDAO(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = UserFactory()
        cls.product = ProductFactory()
        cls.version = VersionFactory(product=cls.product)
        cls.plan = TestPlanFactory(
            name='Master Regression Plan',
            author=cls.author,
            product=cls.product,
            product_version=cls.version,
        )
        firestore_test_plan_dao.save(cls.plan)

    def test_filter_by_pk(self):
        result = firestore_test_plan_dao.filter({'pk': self.plan.pk})
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['id'], self.plan.pk)

    def test_filter_by_name_icontains(self):
        result = firestore_test_plan_dao.filter({'name__icontains': 'regression'})
        self.assertGreater(len(result), 0)

    def test_filter_by_product(self):
        result = firestore_test_plan_dao.filter({'product': self.product.pk})
        self.assertGreater(len(result), 0)
        self.assertTrue(all(r['product'] == self.product.pk for r in result))

    def test_filter_by_author(self):
        result = firestore_test_plan_dao.filter({'author': self.author.pk})
        self.assertGreater(len(result), 0)

    def test_filter_stores_denormalized_names(self):
        result = firestore_test_plan_dao.filter({'pk': self.plan.pk})
        doc = result[0]
        self.assertIn('author__username', doc)
        self.assertIn('product__name', doc)
        self.assertIn('product_version__value', doc)
        self.assertIn('type__name', doc)

    def test_filter_pk_in(self):
        plan2 = TestPlanFactory()
        firestore_test_plan_dao.save(plan2)
        result = firestore_test_plan_dao.filter({'pk__in': [self.plan.pk, plan2.pk]})
        ids = {r['id'] for r in result}
        self.assertIn(self.plan.pk, ids)
        self.assertIn(plan2.pk, ids)

    def test_filter_nonexistent_returns_empty(self):
        result = firestore_test_plan_dao.filter({'pk': -9999})
        self.assertEqual(result, [])

    def test_save_returns_plan(self):
        plan = TestPlanFactory()
        returned = firestore_test_plan_dao.save(plan)
        self.assertEqual(returned.pk, plan.pk)

    def test_add_and_remove_case(self):
        plan = TestPlanFactory()
        firestore_test_plan_dao.save(plan)
        confirmed = TestCaseStatus.objects.get(is_confirmed=True)
        case = TestCaseFactory(case_status=confirmed)
        firestore_test_case_dao.save(case)

        firestore_test_plan_dao.add_case(plan, case)
        self.assertIn(case, plan.cases.all())

        firestore_test_plan_dao.remove_case(plan.pk, case.pk)
        self.assertNotIn(case, plan.cases.all())
