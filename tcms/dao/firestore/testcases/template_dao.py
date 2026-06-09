from tcms.testcases.models import Template

_FIELDS = ("id", "name", "text")


class TemplateDAO:
    def filter(self, query):
        return [
            {"id": obj.id, "name": obj.name, "text": obj.text}
            for obj in Template.objects.filter(**query).order_by("id")
        ]

    def filter_objects(self, query):
        return Template.objects.filter(**query).order_by("id")

    def get_by_id(self, template_id):
        return Template.objects.get(pk=template_id)

    def save(self, template):
        template.save()
        return template


template_dao = TemplateDAO()
