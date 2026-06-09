from tcms.testcases.models import Template

_FIELDS = ("id", "name", "text")


class TemplateDAO:
    def filter(self, query):
        return list(
            Template.objects.filter(**query)
            .values(*_FIELDS)
            .order_by("id")
            .distinct()
        )

    def filter_objects(self, query):
        return Template.objects.filter(**query).order_by("id")

    def get_by_id(self, template_id):
        return Template.objects.get(pk=template_id)

    def save(self, template):
        template.save()
        return template


template_dao = TemplateDAO()

from django.conf import settings as _settings  # noqa: E402
if getattr(_settings, 'USE_FIRESTORE_DAOS', False):
    from tcms.dao.firestore.testcases.template_dao import template_dao  # noqa: F401, F811
