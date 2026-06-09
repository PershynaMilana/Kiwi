from tcms.testcases.models import Category

class CategoryDAO:
    def filter(self, query):
        return [
            {"id": obj.id, "name": obj.name, "product": obj.product_id,
             "description": obj.description}
            for obj in Category.objects.filter(**query).order_by("id")
        ]

    def get_by_id(self, category_id):
        return Category.objects.get(pk=category_id)

    def save(self, category):
        category.save()
        return category


category_dao = CategoryDAO()
