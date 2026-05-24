from django.test import TestCase

from tcms.dao.firestore.firestore_template_dao import firestore_template_dao
from tcms.testcases.models import Template


class TestFirestoreTemplateDAO(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.template = Template.objects.create(name='Smoke Test Template', text='Given When Then')
        firestore_template_dao.save(cls.template)

    def test_filter_by_pk(self):
        result = firestore_template_dao.filter({'pk': self.template.pk})
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['id'], self.template.pk)

    def test_filter_by_name(self):
        result = firestore_template_dao.filter({'name': self.template.name})
        self.assertEqual(len(result), 1)

    def test_filter_by_name_icontains(self):
        result = firestore_template_dao.filter({'name__icontains': 'smoke'})
        self.assertGreater(len(result), 0)

    def test_filter_nonexistent_returns_empty(self):
        result = firestore_template_dao.filter({'pk': -9999})
        self.assertEqual(result, [])

    def test_save_returns_template(self):
        t = Template.objects.create(name='Another Template', text='Steps here')
        returned = firestore_template_dao.save(t)
        self.assertEqual(returned.pk, t.pk)
