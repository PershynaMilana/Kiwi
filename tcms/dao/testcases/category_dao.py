from tcms.testcases.models import Category

_FIELDS = ("id", "name", "product", "description")


class CategoryDAO:
    def filter(self, query):
        return list(
            Category.objects.filter(**query)
            .values(*_FIELDS)
            .order_by("id")
            .distinct()
        )

    def get_by_id(self, category_id):
        return Category.objects.get(pk=category_id)

    def save(self, category):
        category.save()
        return category


category_dao = CategoryDAO()

from django.conf import settings as _settings  # noqa: E402
if getattr(_settings, 'USE_FIRESTORE_DAOS', False):
    from tcms.dao.firestore.testcases.category_dao import category_dao  # noqa: F401, F811
