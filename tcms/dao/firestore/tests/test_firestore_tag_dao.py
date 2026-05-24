from django.test import TestCase

from tcms.dao.firestore.firestore_tag_dao import firestore_tag_dao
from tcms.tests.factories import TagFactory, TestPlanFactory, TestCaseFactory, TestRunFactory


class TestFirestoreTagDAO(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tag = TagFactory(name='smoke-test')
        firestore_tag_dao.save(cls.tag)

    def test_save_syncs_to_firestore(self):
        tag = TagFactory(name='regression')
        returned = firestore_tag_dao.save(tag)
        self.assertEqual(returned.pk, tag.pk)

    def test_add_and_remove_tag_testplan(self):
        plan = TestPlanFactory()
        tag = TagFactory(name='plan-tag')
        firestore_tag_dao.save(tag)

        firestore_tag_dao.add_tag(plan, tag)
        self.assertIn(tag, plan.tag.all())

        firestore_tag_dao.remove_tag(plan, tag)
        self.assertNotIn(tag, plan.tag.all())

    def test_add_and_remove_tag_testcase(self):
        case = TestCaseFactory()
        tag = TagFactory(name='case-tag')
        firestore_tag_dao.save(tag)

        firestore_tag_dao.add_tag(case, tag)
        self.assertIn(tag, case.tag.all())

        firestore_tag_dao.remove_tag(case, tag)
        self.assertNotIn(tag, case.tag.all())

    def test_add_and_remove_tag_testrun(self):
        run = TestRunFactory()
        tag = TagFactory(name='run-tag')
        firestore_tag_dao.save(tag)

        firestore_tag_dao.add_tag(run, tag)
        self.assertIn(tag, run.tag.all())

        firestore_tag_dao.remove_tag(run, tag)
        self.assertNotIn(tag, run.tag.all())
