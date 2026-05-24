from django.test import TestCase

from tcms.dao.firestore.firestore_test_case_dao import firestore_test_case_dao
from tcms.tests.factories import (
    CategoryFactory, ComponentFactory, TestCaseFactory, UserFactory,
)


class TestFirestoreTestCaseDAO(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = UserFactory()
        cls.category = CategoryFactory()
        cls.case = TestCaseFactory(
            summary='Login with valid credentials',
            author=cls.author,
            category=cls.category,
        )
        firestore_test_case_dao.save(cls.case)

    def test_filter_by_pk(self):
        result = firestore_test_case_dao.filter({'pk': self.case.pk})
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['id'], self.case.pk)

    def test_filter_by_summary_icontains(self):
        result = firestore_test_case_dao.filter({'summary__icontains': 'valid credentials'})
        self.assertGreater(len(result), 0)

    def test_filter_by_author(self):
        result = firestore_test_case_dao.filter({'author': self.author.pk})
        self.assertGreater(len(result), 0)
        self.assertTrue(all(r['author'] == self.author.pk for r in result))

    def test_filter_by_category(self):
        result = firestore_test_case_dao.filter({'category': self.category.pk})
        self.assertGreater(len(result), 0)

    def test_filter_stores_denormalized_names(self):
        result = firestore_test_case_dao.filter({'pk': self.case.pk})
        doc = result[0]
        self.assertIn('author__username', doc)
        self.assertIn('category__name', doc)
        self.assertIn('priority__value', doc)

    def test_filter_stores_duration_as_int(self):
        result = firestore_test_case_dao.filter({'pk': self.case.pk})
        doc = result[0]
        self.assertIsNone(doc['setup_duration'])
        self.assertIsNone(doc['testing_duration'])
        self.assertIsInstance(doc['expected_duration'], int)

    def test_filter_pk_in(self):
        case2 = TestCaseFactory()
        firestore_test_case_dao.save(case2)
        result = firestore_test_case_dao.filter({'pk__in': [self.case.pk, case2.pk]})
        ids = {r['id'] for r in result}
        self.assertIn(self.case.pk, ids)
        self.assertIn(case2.pk, ids)

    def test_filter_nonexistent_returns_empty(self):
        result = firestore_test_case_dao.filter({'pk': -9999})
        self.assertEqual(result, [])

    def test_save_returns_case(self):
        case = TestCaseFactory()
        returned = firestore_test_case_dao.save(case)
        self.assertEqual(returned.pk, case.pk)

    def test_remove_deletes_from_firestore(self):
        case = TestCaseFactory()
        firestore_test_case_dao.save(case)
        case_pk = case.pk

        firestore_test_case_dao.remove({'pk': case_pk})

        result = firestore_test_case_dao.filter({'pk': case_pk})
        self.assertEqual(result, [])

    def test_add_and_remove_component(self):
        case = TestCaseFactory()
        firestore_test_case_dao.save(case)
        component = ComponentFactory()

        firestore_test_case_dao.add_component(case, component)
        self.assertIn(component, case.component.all())

        firestore_test_case_dao.remove_component(case, component)
        self.assertNotIn(component, case.component.all())

    def test_add_and_remove_notification_cc(self):
        case = TestCaseFactory()
        firestore_test_case_dao.save(case)
        emails = ['notify@example.com']

        firestore_test_case_dao.add_notification_cc(case, emails)
        self.assertIn('notify@example.com', case.emailing.get_cc_list())

        firestore_test_case_dao.remove_notification_cc(case, emails)
        self.assertNotIn('notify@example.com', case.emailing.get_cc_list())
