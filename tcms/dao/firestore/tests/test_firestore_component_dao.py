from django.test import TestCase

from tcms.dao.firestore.firestore_component_dao import firestore_component_dao
from tcms.tests.factories import ComponentFactory, ProductFactory


class TestFirestoreComponentDAO(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = ProductFactory()
        cls.component = ComponentFactory(name='Auth Module', product=cls.product)
        firestore_component_dao.save(cls.component)

    def test_filter_by_pk(self):
        result = firestore_component_dao.filter({'pk': self.component.pk})
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['id'], self.component.pk)

    def test_filter_by_name(self):
        result = firestore_component_dao.filter({'name': self.component.name})
        self.assertEqual(len(result), 1)

    def test_filter_by_product_id(self):
        result = firestore_component_dao.filter({'product_id': self.product.pk})
        self.assertGreater(len(result), 0)
        self.assertTrue(all(r['product_id'] == self.product.pk for r in result))

    def test_filter_nonexistent_returns_empty(self):
        result = firestore_component_dao.filter({'pk': -9999})
        self.assertEqual(result, [])

    def test_save_returns_component(self):
        comp = ComponentFactory()
        returned = firestore_component_dao.save(comp)
        self.assertEqual(returned.pk, comp.pk)
