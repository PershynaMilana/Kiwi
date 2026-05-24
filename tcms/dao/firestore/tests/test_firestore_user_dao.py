from django.test import TestCase

from tcms.dao.firestore.firestore_user_dao import firestore_user_dao
from tcms.tests.factories import UserFactory


class TestFirestoreUserDAO(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = UserFactory(username='test_fs_user', email='test_fs_user@example.com')
        firestore_user_dao.save(cls.user)

    def test_filter_by_pk(self):
        result = firestore_user_dao.filter({'pk': self.user.pk})
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['id'], self.user.pk)

    def test_filter_by_username(self):
        result = firestore_user_dao.filter({'username': self.user.username})
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['username'], self.user.username)

    def test_filter_by_email(self):
        result = firestore_user_dao.filter({'email': self.user.email})
        self.assertEqual(len(result), 1)

    def test_filter_by_email_icontains(self):
        result = firestore_user_dao.filter({'email__icontains': 'test_fs_user'})
        self.assertGreater(len(result), 0)

    def test_filter_active_users(self):
        result = firestore_user_dao.filter({'is_active': True})
        self.assertTrue(all(r['is_active'] for r in result))

    def test_filter_pk_in(self):
        user2 = UserFactory()
        firestore_user_dao.save(user2)
        result = firestore_user_dao.filter({'pk__in': [self.user.pk, user2.pk]})
        ids = {r['id'] for r in result}
        self.assertIn(self.user.pk, ids)
        self.assertIn(user2.pk, ids)

    def test_filter_nonexistent_returns_empty(self):
        result = firestore_user_dao.filter({'pk': -9999})
        self.assertEqual(result, [])

    def test_password_not_stored(self):
        result = firestore_user_dao.filter({'pk': self.user.pk})
        self.assertNotIn('password', result[0])

    def test_deactivate_updates_firestore(self):
        user = UserFactory()
        firestore_user_dao.save(user)
        firestore_user_dao.deactivate(user)

        result = firestore_user_dao.filter({'pk': user.pk})
        self.assertEqual(len(result), 1)
        self.assertFalse(result[0]['is_active'])

    def test_save_returns_user(self):
        user = UserFactory()
        returned = firestore_user_dao.save(user)
        self.assertEqual(returned.pk, user.pk)
