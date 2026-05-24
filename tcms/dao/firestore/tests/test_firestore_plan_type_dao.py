from django.test import TestCase

from tcms.dao.firestore.firestore_plan_type_dao import firestore_plan_type_dao
from tcms.tests.factories import PlanTypeFactory


class TestFirestorePlanTypeDAO(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.plan_type = PlanTypeFactory(name='Regression Suite')
        firestore_plan_type_dao.save(cls.plan_type)

    def test_filter_by_pk(self):
        result = firestore_plan_type_dao.filter({'pk': self.plan_type.pk})
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['id'], self.plan_type.pk)

    def test_filter_by_name(self):
        result = firestore_plan_type_dao.filter({'name': self.plan_type.name})
        self.assertEqual(len(result), 1)

    def test_filter_by_name_icontains(self):
        result = firestore_plan_type_dao.filter({'name__icontains': 'regression'})
        self.assertGreater(len(result), 0)

    def test_filter_nonexistent_returns_empty(self):
        result = firestore_plan_type_dao.filter({'pk': -9999})
        self.assertEqual(result, [])

    def test_save_returns_plan_type(self):
        pt = PlanTypeFactory()
        returned = firestore_plan_type_dao.save(pt)
        self.assertEqual(returned.pk, pt.pk)
