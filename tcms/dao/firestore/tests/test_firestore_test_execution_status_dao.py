from django.test import TestCase

from tcms.dao.firestore.firestore_test_execution_status_dao import firestore_test_execution_status_dao
from tcms.testruns.models import TestExecutionStatus


class TestFirestoreTestExecutionStatusDAO(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.status = TestExecutionStatus.objects.order_by('pk').first()
        firestore_test_execution_status_dao.save(cls.status)

    def test_filter_by_pk(self):
        result = firestore_test_execution_status_dao.filter({'pk': self.status.pk})
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['id'], self.status.pk)

    def test_filter_by_name(self):
        result = firestore_test_execution_status_dao.filter({'name': self.status.name})
        self.assertGreater(len(result), 0)

    def test_filter_stores_icon_and_color(self):
        result = firestore_test_execution_status_dao.filter({'pk': self.status.pk})
        self.assertIn('icon', result[0])
        self.assertIn('color', result[0])

    def test_filter_nonexistent_returns_empty(self):
        result = firestore_test_execution_status_dao.filter({'pk': -9999})
        self.assertEqual(result, [])

    def test_save_returns_status(self):
        returned = firestore_test_execution_status_dao.save(self.status)
        self.assertEqual(returned.pk, self.status.pk)
