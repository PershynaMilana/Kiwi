from django.test import TestCase

from tcms.dao.firestore.firestore_classification_dao import firestore_classification_dao
from tcms.tests.factories import ClassificationFactory


class TestFirestoreClassificationDAO(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.classification = ClassificationFactory(name='Backend Services')
        firestore_classification_dao.save(cls.classification)

    def test_filter_by_pk(self):
        result = firestore_classification_dao.filter({'pk': self.classification.pk})
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['id'], self.classification.pk)

    def test_filter_by_name(self):
        result = firestore_classification_dao.filter({'name': self.classification.name})
        self.assertEqual(len(result), 1)

    def test_filter_by_name_icontains(self):
        result = firestore_classification_dao.filter({'name__icontains': 'backend'})
        self.assertGreater(len(result), 0)

    def test_filter_nonexistent_returns_empty(self):
        result = firestore_classification_dao.filter({'pk': -9999})
        self.assertEqual(result, [])

    def test_save_returns_classification(self):
        cls_obj = ClassificationFactory()
        returned = firestore_classification_dao.save(cls_obj)
        self.assertEqual(returned.pk, cls_obj.pk)
