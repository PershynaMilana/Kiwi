from django.test import TestCase

from tcms.dao.firestore.firestore_test_execution_dao import firestore_test_execution_dao
from tcms.tests.factories import TestExecutionFactory, TestRunFactory, UserFactory


class TestFirestoreTestExecutionDAO(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_run = TestRunFactory()
        cls.assignee = UserFactory()
        cls.execution = TestExecutionFactory(run=cls.test_run, assignee=cls.assignee)
        firestore_test_execution_dao.save(cls.execution)

    def test_filter_by_pk(self):
        result = firestore_test_execution_dao.filter({'pk': self.execution.pk})
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['id'], self.execution.pk)

    def test_filter_by_run(self):
        result = firestore_test_execution_dao.filter({'run': self.test_run.pk})
        self.assertGreater(len(result), 0)
        self.assertTrue(all(r['run'] == self.test_run.pk for r in result))

    def test_filter_by_assignee(self):
        result = firestore_test_execution_dao.filter({'assignee': self.assignee.pk})
        self.assertGreater(len(result), 0)

    def test_filter_stores_denormalized_names(self):
        result = firestore_test_execution_dao.filter({'pk': self.execution.pk})
        doc = result[0]
        self.assertIn('assignee__username', doc)
        self.assertIn('case__summary', doc)
        self.assertIn('build__name', doc)
        self.assertIn('status__name', doc)

    def test_filter_stores_expected_duration_as_int(self):
        result = firestore_test_execution_dao.filter({'pk': self.execution.pk})
        doc = result[0]
        self.assertIsInstance(doc['expected_duration'], int)

    def test_filter_actual_duration_is_none_when_no_dates(self):
        execution = TestExecutionFactory(start_date=None, stop_date=None)
        firestore_test_execution_dao.save(execution)
        result = firestore_test_execution_dao.filter({'pk': execution.pk})
        self.assertIsNone(result[0]['actual_duration'])

    def test_filter_pk_in(self):
        exec2 = TestExecutionFactory()
        firestore_test_execution_dao.save(exec2)
        result = firestore_test_execution_dao.filter({'pk__in': [self.execution.pk, exec2.pk]})
        ids = {r['id'] for r in result}
        self.assertIn(self.execution.pk, ids)
        self.assertIn(exec2.pk, ids)

    def test_filter_nonexistent_returns_empty(self):
        result = firestore_test_execution_dao.filter({'pk': -9999})
        self.assertEqual(result, [])

    def test_save_returns_execution(self):
        execution = TestExecutionFactory()
        returned = firestore_test_execution_dao.save(execution)
        self.assertEqual(returned.pk, execution.pk)

    def test_remove_deletes_from_firestore(self):
        execution = TestExecutionFactory()
        firestore_test_execution_dao.save(execution)
        pk = execution.pk

        firestore_test_execution_dao.remove({'pk': pk})

        result = firestore_test_execution_dao.filter({'pk': pk})
        self.assertEqual(result, [])
