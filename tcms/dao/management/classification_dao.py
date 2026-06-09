from tcms.management.models import Classification

_FIELDS = ("id", "name")


class ClassificationDAO:
    def filter(self, query):
        return list(
            Classification.objects.filter(**query)
            .values(*_FIELDS)
            .order_by("id")
            .distinct()
        )

    def get_by_id(self, classification_id):
        return Classification.objects.get(pk=classification_id)

    def save(self, classification):
        classification.save()
        return classification


classification_dao = ClassificationDAO()

from django.conf import settings as _settings  # noqa: E402
if getattr(_settings, 'USE_FIRESTORE_DAOS', False):
    from tcms.dao.firestore.management.classification_dao import classification_dao  # noqa: F401, F811
