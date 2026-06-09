from tcms.bugs.models import Severity

class SeverityDAO:
    def filter(self, query):
        return [
            {"id": obj.id, "name": obj.name, "weight": obj.weight,
             "icon": obj.icon, "color": obj.color}
            for obj in Severity.objects.filter(**query).order_by("id")
        ]

    def get_by_id(self, severity_id):
        return Severity.objects.get(pk=severity_id)

    def save(self, severity):
        severity.save()
        return severity


severity_dao = SeverityDAO()
