from django.test import TestCase

from tcms.dao.firestore.firestore_test_case_status_dao import firestore_test_case_status_dao
from tcms.testcases.models import TestCaseStatus


class TestFirestoreTestCaseStatusDAO(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.status = TestCaseStatus.objects.first()
        firestore_test_case_status_dao.save(cls.status)

    def test_filter_by_pk(self):
        result = firestore_test_case_status_dao.filter({'pk': self.status.pk})
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['id'], self.status.pk)

    def test_filter_by_name(self):
        result = firestore_test_case_status_dao.filter({'name': self.status.name})
        self.assertGreater(len(result), 0)

    def test_filter_by_is_confirmed(self):
        result = firestore_test_case_status_dao.filter({'is_confirmed': self.status.is_confirmed})
        self.assertGreater(len(result), 0)
        self.assertTrue(all(r['is_confirmed'] == self.status.is_confirmed for r in result))

    def test_filter_nonexistent_returns_empty(self):
        result = firestore_test_case_status_dao.filter({'pk': -9999})
        self.assertEqual(result, [])

    def test_save_returns_status(self):
        returned = firestore_test_case_status_dao.save(self.status)
        self.assertEqual(returned.pk, self.status.pk)
