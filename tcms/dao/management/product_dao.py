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
        return list(
            Product.objects.filter(**query)
            .values(*_PRODUCT_FIELDS)
            .order_by("id")
            .distinct()
        )

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


from django.conf import settings as _settings  # noqa: E402
if getattr(_settings, 'USE_FIRESTORE_DAOS', False):
    from tcms.dao.firestore.management.product_dao import product_dao  # noqa: F401, F811
