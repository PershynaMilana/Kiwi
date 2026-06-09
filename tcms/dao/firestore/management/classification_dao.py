from tcms.management.models import Classification

class ClassificationDAO:
    def filter(self, query):
        return [
            {"id": obj.id, "name": obj.name}
            for obj in Classification.objects.filter(**query).order_by("id")
        ]

    def get_by_id(self, classification_id):
        return Classification.objects.get(pk=classification_id)

    def save(self, classification):
        classification.save()
        return classification


classification_dao = ClassificationDAO()
