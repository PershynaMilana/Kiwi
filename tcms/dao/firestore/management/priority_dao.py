from tcms.management.models import Priority

class PriorityDAO:
    def filter(self, query):
        return [
            {"id": obj.id, "value": obj.value, "is_active": obj.is_active}
            for obj in Priority.objects.filter(**query).order_by("id")
        ]

    def filter_objects(self, query):
        return Priority.objects.filter(**query).order_by("id")

    def get_by_id(self, priority_id):
        return Priority.objects.get(pk=priority_id)

    def save(self, priority):
        priority.save()
        return priority


priority_dao = PriorityDAO()
