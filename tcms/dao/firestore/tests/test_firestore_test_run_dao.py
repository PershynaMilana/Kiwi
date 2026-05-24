from django.test import TestCase

from tcms.dao.firestore.firestore_test_case_dao import firestore_test_case_dao
from tcms.dao.firestore.firestore_test_run_dao import firestore_test_run_dao
from tcms.testcases.models import TestCaseStatus
from tcms.tests.factories import (
    BuildFactory, TestCaseFactory, TestPlanFactory, TestRunFactory, UserFactory,
)


class TestFirestoreTestRunDAO(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.manager = UserFactory()
        cls.plan = TestPlanFactory()
        cls.build = BuildFactory()
        cls.test_run = TestRunFactory(
            summary='Nightly Regression Run',
            manager=cls.manager,
            plan=cls.plan,
            build=cls.build,
        )
        firestore_test_run_dao.save(cls.test_run)

    def test_filter_by_pk(self):
        result = firestore_test_run_dao.filter({'pk': self.test_run.pk})
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['id'], self.test_run.pk)

    def test_filter_by_summary_icontains(self):
        result = firestore_test_run_dao.filter({'summary__icontains': 'nightly'})
        self.assertGreater(len(result), 0)

    def test_filter_by_plan(self):
        result = firestore_test_run_dao.filter({'plan': self.plan.pk})
        self.assertGreater(len(result), 0)
        self.assertTrue(all(r['plan'] == self.plan.pk for r in result))

    def test_filter_by_manager(self):
        result = firestore_test_run_dao.filter({'manager': self.manager.pk})
        self.assertGreater(len(result), 0)

    def test_filter_stores_denormalized_names(self):
        result = firestore_test_run_dao.filter({'pk': self.test_run.pk})
        doc = result[0]
        self.assertIn('plan__name', doc)
        self.assertIn('build__name', doc)
        self.assertIn('manager__username', doc)

    def test_filter_pk_in(self):
        run2 = TestRunFactory()
        firestore_test_run_dao.save(run2)
        result = firestore_test_run_dao.filter({'pk__in': [self.test_run.pk, run2.pk]})
        ids = {r['id'] for r in result}
        self.assertIn(self.test_run.pk, ids)
        self.assertIn(run2.pk, ids)

    def test_filter_nonexistent_returns_empty(self):
        result = firestore_test_run_dao.filter({'pk': -9999})
        self.assertEqual(result, [])

    def test_save_returns_run(self):
        test_run = TestRunFactory()
        returned = firestore_test_run_dao.save(test_run)
        self.assertEqual(returned.pk, test_run.pk)

    def test_remove_deletes_from_firestore(self):
        test_run = TestRunFactory()
        firestore_test_run_dao.save(test_run)
        run_pk = test_run.pk

        firestore_test_run_dao.remove({'pk': run_pk})

        result = firestore_test_run_dao.filter({'pk': run_pk})
        self.assertEqual(result, [])

    def test_add_and_remove_case(self):
        test_run = TestRunFactory()
        firestore_test_run_dao.save(test_run)
        confirmed = TestCaseStatus.objects.get(is_confirmed=True)
        case = TestCaseFactory(case_status=confirmed)
        firestore_test_case_dao.save(case)

        firestore_test_run_dao.add_case(test_run, case)
        self.assertTrue(test_run.executions.filter(case=case).exists())

        firestore_test_run_dao.remove_case(test_run.pk, case.pk)
        self.assertFalse(test_run.executions.filter(case=case).exists())

    def test_add_and_remove_cc(self):
        test_run = TestRunFactory()
        firestore_test_run_dao.save(test_run)
        user = UserFactory()

        firestore_test_run_dao.add_cc(test_run, user)
        self.assertIn(user.email, firestore_test_run_dao.get_cc(test_run))

        firestore_test_run_dao.remove_cc(test_run, user)
        self.assertNotIn(user.email, firestore_test_run_dao.get_cc(test_run))
