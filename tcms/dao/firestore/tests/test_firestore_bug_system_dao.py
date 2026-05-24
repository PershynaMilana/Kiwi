from django.test import TestCase

from tcms.dao.firestore.firestore_bug_system_dao import firestore_bug_system_dao
from tcms.testcases.models import BugSystem


class TestFirestoreBugSystemDAO(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.bug_system = BugSystem.objects.create(
            name='GitHub Issues',
            tracker_type='GitHub',
            base_url='https://github.com/example/repo',
            api_url='https://api.github.com',
            api_username='bot',
        )
        firestore_bug_system_dao.save(cls.bug_system)

    def test_filter_by_pk(self):
        result = firestore_bug_system_dao.filter({'pk': self.bug_system.pk})
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['id'], self.bug_system.pk)

    def test_filter_by_name(self):
        result = firestore_bug_system_dao.filter({'name': self.bug_system.name})
        self.assertEqual(len(result), 1)

    def test_filter_by_name_icontains(self):
        result = firestore_bug_system_dao.filter({'name__icontains': 'github'})
        self.assertGreater(len(result), 0)

    def test_api_password_not_stored(self):
        result = firestore_bug_system_dao.filter({'pk': self.bug_system.pk})
        self.assertNotIn('api_password', result[0])

    def test_filter_nonexistent_returns_empty(self):
        result = firestore_bug_system_dao.filter({'pk': -9999})
        self.assertEqual(result, [])

    def test_save_returns_bug_system(self):
        bs = BugSystem.objects.create(name='JIRA Instance', tracker_type='Jira')
        returned = firestore_bug_system_dao.save(bs)
        self.assertEqual(returned.pk, bs.pk)
