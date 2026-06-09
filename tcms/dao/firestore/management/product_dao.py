from tcms.management.models import Product

_PRODUCT_FIELDS = (
    "id",
    "name",
    "description",
    "classification",
)


class ProductDAO:
    # ------------------------------------------------------------------
    # READ operations
    # ------------------------------------------------------------------

    def filter(self, query):
        """
        Return a list of product dicts matching query.
        Used by the Product.filter RPC endpoint.
        """
        return [
            {"id": obj.id, "name": obj.name, "description": obj.description,
             "classification": obj.classification_id}
            for obj in Product.objects.filter(**query).order_by("id")
        ]

    # ------------------------------------------------------------------
    # WRITE operations
    # ------------------------------------------------------------------

    def save(self, product, update_fields=None):
        """
        Persist a Product object.
        Used by Product.create and Product.update RPC endpoints.
        """
        if update_fields:
            product.save(update_fields=update_fields)
        else:
            product.save()
        return product


product_dao = ProductDAO()
