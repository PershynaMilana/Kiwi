from django.test import TestCase

from tcms.dao.firestore.firestore_priority_dao import firestore_priority_dao
from tcms.management.models import Priority


class TestFirestorePriorityDAO(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.priority = Priority.objects.first()
        firestore_priority_dao.save(cls.priority)

    def test_filter_by_pk(self):
        result = firestore_priority_dao.filter({'pk': self.priority.pk})
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['id'], self.priority.pk)

    def test_filter_by_value(self):
        result = firestore_priority_dao.filter({'value': self.priority.value})
        self.assertEqual(len(result), 1)

    def test_filter_active_only(self):
        result = firestore_priority_dao.filter({'is_active': True})
        self.assertTrue(all(r['is_active'] for r in result))

    def test_filter_nonexistent_returns_empty(self):
        result = firestore_priority_dao.filter({'pk': -9999})
        self.assertEqual(result, [])

    def test_save_returns_priority(self):
        returned = firestore_priority_dao.save(self.priority)
        self.assertEqual(returned.pk, self.priority.pk)
