from django.test import TestCase

from tcms.dao.firestore.firestore_product_dao import firestore_product_dao
from tcms.tests.factories import ClassificationFactory, ProductFactory


class TestFirestoreProductDAO(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.classification = ClassificationFactory()
        cls.product = ProductFactory(name='Kiwi TCMS', classification=cls.classification)
        firestore_product_dao.save(cls.product)

    def test_filter_by_pk(self):
        result = firestore_product_dao.filter({'pk': self.product.pk})
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['id'], self.product.pk)

    def test_filter_by_name(self):
        result = firestore_product_dao.filter({'name': self.product.name})
        self.assertEqual(len(result), 1)

    def test_filter_by_name_icontains(self):
        result = firestore_product_dao.filter({'name__icontains': 'kiwi'})
        self.assertGreater(len(result), 0)

    def test_filter_by_classification_id(self):
        result = firestore_product_dao.filter({'classification_id': self.classification.pk})
        self.assertGreater(len(result), 0)
        self.assertTrue(all(r['classification_id'] == self.classification.pk for r in result))

    def test_filter_nonexistent_returns_empty(self):
        result = firestore_product_dao.filter({'pk': -9999})
        self.assertEqual(result, [])

    def test_save_returns_product(self):
        prod = ProductFactory()
        returned = firestore_product_dao.save(prod)
        self.assertEqual(returned.pk, prod.pk)
