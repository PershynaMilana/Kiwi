from django.test import TestCase

from tcms.dao.firestore.firestore_build_dao import firestore_build_dao
from tcms.tests.factories import BuildFactory, VersionFactory


class TestFirestoreBuildDAO(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.version = VersionFactory()
        cls.build = BuildFactory(name='Test Build Alpha', version=cls.version)
        firestore_build_dao.save(cls.build)

    def test_filter_by_pk(self):
        result = firestore_build_dao.filter({'pk': self.build.pk})
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['id'], self.build.pk)

    def test_filter_by_name(self):
        result = firestore_build_dao.filter({'name': self.build.name})
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['name'], self.build.name)

    def test_filter_by_name_icontains(self):
        result = firestore_build_dao.filter({'name__icontains': 'alpha'})
        self.assertGreater(len(result), 0)

    def test_filter_nonexistent_returns_empty(self):
        result = firestore_build_dao.filter({'pk': -9999})
        self.assertEqual(result, [])

    def test_filter_stores_version_value(self):
        result = firestore_build_dao.filter({'pk': self.build.pk})
        self.assertEqual(result[0]['version__value'], self.version.value)

    def test_save_returns_build(self):
        build = BuildFactory()
        returned = firestore_build_dao.save(build)
        self.assertEqual(returned.pk, build.pk)
