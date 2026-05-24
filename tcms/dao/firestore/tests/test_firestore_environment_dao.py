from django.test import TestCase

from tcms.dao.firestore.firestore_environment_dao import (
    firestore_environment_dao,
    firestore_environment_property_dao,
)
from tcms.testruns.models import Environment


class TestFirestoreEnvironmentDAO(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = Environment.objects.create(name='Staging', description='Staging environment')
        firestore_environment_dao.save(cls.env)

    def test_filter_by_pk(self):
        result = firestore_environment_dao.filter({'pk': self.env.pk})
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['id'], self.env.pk)

    def test_filter_by_name(self):
        result = firestore_environment_dao.filter({'name': self.env.name})
        self.assertEqual(len(result), 1)

    def test_filter_by_name_icontains(self):
        result = firestore_environment_dao.filter({'name__icontains': 'staging'})
        self.assertGreater(len(result), 0)

    def test_filter_nonexistent_returns_empty(self):
        result = firestore_environment_dao.filter({'pk': -9999})
        self.assertEqual(result, [])

    def test_save_returns_environment(self):
        env = Environment.objects.create(name='Production')
        returned = firestore_environment_dao.save(env)
        self.assertEqual(returned.pk, env.pk)


class TestFirestoreEnvironmentPropertyDAO(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = Environment.objects.create(name='QA Env')
        firestore_environment_dao.save(cls.env)
        cls.prop, _ = firestore_environment_property_dao.get_or_create(
            cls.env.pk, 'browser', 'Chrome'
        )

    def test_filter_by_pk(self):
        result = firestore_environment_property_dao.filter({'pk': self.prop.pk})
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['id'], self.prop.pk)

    def test_filter_by_name(self):
        result = firestore_environment_property_dao.filter({'name': 'browser'})
        self.assertGreater(len(result), 0)

    def test_filter_by_environment_id(self):
        result = firestore_environment_property_dao.filter({'environment_id': self.env.pk})
        self.assertGreater(len(result), 0)
        self.assertTrue(all(r['environment_id'] == self.env.pk for r in result))

    def test_get_or_create_idempotent(self):
        prop2, created = firestore_environment_property_dao.get_or_create(
            self.env.pk, 'browser', 'Chrome'
        )
        self.assertFalse(created)
        self.assertEqual(prop2.pk, self.prop.pk)

    def test_remove_deletes_from_firestore(self):
        env = Environment.objects.create(name='Temp Env')
        firestore_environment_dao.save(env)
        prop, _ = firestore_environment_property_dao.get_or_create(env.pk, 'os', 'Linux')

        firestore_environment_property_dao.remove({'pk': prop.pk})

        result = firestore_environment_property_dao.filter({'pk': prop.pk})
        self.assertEqual(result, [])
