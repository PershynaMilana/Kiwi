from django.test import TestCase

from tcms.bugs.models import Bug, Severity
from tcms.dao.firestore.firestore_bug_dao import firestore_bug_dao
from tcms.tests.factories import BuildFactory, ProductFactory, UserFactory, VersionFactory


def _make_bug(reporter, product, version, build, summary='Test Bug'):
    return Bug.objects.create(
        summary=summary,
        reporter=reporter,
        product=product,
        version=version,
        build=build,
    )


class TestFirestoreBugDAO(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.reporter = UserFactory()
        cls.product = ProductFactory()
        cls.version = VersionFactory(product=cls.product)
        cls.build = BuildFactory(version=cls.version)
        cls.bug = _make_bug(
            cls.reporter, cls.product, cls.version, cls.build,
            summary='Login fails with valid credentials',
        )
        firestore_bug_dao.save(cls.bug)

    def test_filter_by_pk(self):
        result = firestore_bug_dao.filter({'pk': self.bug.pk})
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['id'], self.bug.pk)

    def test_filter_by_status(self):
        result = firestore_bug_dao.filter({'status': True})
        self.assertTrue(all(r['status'] for r in result))

    def test_filter_by_reporter_id(self):
        result = firestore_bug_dao.filter({'reporter_id': self.reporter.pk})
        self.assertGreater(len(result), 0)

    def test_filter_with_names_stores_usernames(self):
        result = firestore_bug_dao.filter_with_names({'pk': self.bug.pk})
        self.assertEqual(len(result), 1)
        self.assertIn('reporter__username', result[0])
        self.assertIn('product__name', result[0])

    def test_filter_canonical_returns_id_fields(self):
        result = firestore_bug_dao.filter_canonical({'pk': self.bug.pk})
        self.assertEqual(len(result), 1)
        doc = result[0]
        self.assertIn('reporter_id', doc)
        self.assertIn('product_id', doc)

    def test_filter_nonexistent_returns_empty(self):
        result = firestore_bug_dao.filter({'pk': -9999})
        self.assertEqual(result, [])

    def test_save_returns_bug(self):
        bug = _make_bug(self.reporter, self.product, self.version, self.build)
        returned = firestore_bug_dao.save(bug)
        self.assertEqual(returned.pk, bug.pk)

    def test_remove_deletes_from_firestore(self):
        bug = _make_bug(self.reporter, self.product, self.version, self.build)
        firestore_bug_dao.save(bug)
        pk = bug.pk

        firestore_bug_dao.remove({'pk': pk})

        result = firestore_bug_dao.filter({'pk': pk})
        self.assertEqual(result, [])
