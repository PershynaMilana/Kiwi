from django.test import TestCase

from tcms.dao.firestore.firestore_version_dao import firestore_version_dao
from tcms.tests.factories import ProductFactory, VersionFactory


class TestFirestoreVersionDAO(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = ProductFactory()
        cls.version = VersionFactory(value='1.0.0', product=cls.product)
        firestore_version_dao.save(cls.version)

    def test_filter_by_pk(self):
        result = firestore_version_dao.filter({'pk': self.version.pk})
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['id'], self.version.pk)

    def test_filter_by_value(self):
        result = firestore_version_dao.filter({'value': self.version.value})
        self.assertGreater(len(result), 0)
        self.assertTrue(all(r['value'] == self.version.value for r in result))

    def test_filter_by_product_id(self):
        result = firestore_version_dao.filter({'product_id': self.product.pk})
        self.assertGreater(len(result), 0)
        self.assertTrue(all(r['product_id'] == self.product.pk for r in result))

    def test_filter_stores_product_name(self):
        result = firestore_version_dao.filter({'pk': self.version.pk})
        self.assertEqual(result[0]['product__name'], self.product.name)

    def test_filter_nonexistent_returns_empty(self):
        result = firestore_version_dao.filter({'pk': -9999})
        self.assertEqual(result, [])

    def test_save_returns_version(self):
        v = VersionFactory()
        returned = firestore_version_dao.save(v)
        self.assertEqual(returned.pk, v.pk)
