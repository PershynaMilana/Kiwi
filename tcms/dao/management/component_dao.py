from tcms.management.models import Component

_COMPONENT_FIELDS = (
    "id",
    "name",
    "product",
    "initial_owner",
    "initial_qa_contact",
    "description",
)


class ComponentDAO:
    # ------------------------------------------------------------------
    # READ operations
    # ------------------------------------------------------------------

    def filter(self, query):
        """
        Return a list of component dicts matching query.
        Used by the Component.filter RPC endpoint.
        """
        return list(
            Component.objects.filter(**query)
            .values(*_COMPONENT_FIELDS, "cases")
            .order_by("id")
            .distinct()
        )

    def filter_objects(self, **kwargs):
        """
        Return a Component queryset for use in views and templates.
        """
        return Component.objects.filter(**kwargs)

    def get_by_id(self, component_id):
        """
        Return a single Component object by primary key.
        """
        return Component.objects.get(pk=component_id)

    def get_by_name_and_product(self, name, product):
        """
        Return a single Component object by name and product.
        Used by TestCase.add_component RPC endpoint.
        """
        return Component.objects.get(name=name, product=product)

    # ------------------------------------------------------------------
    # WRITE operations
    # ------------------------------------------------------------------

    def save(self, component, update_fields=None):
        """
        Persist a Component object.
        Used by Component.create and Component.update RPC endpoints.
        """
        if update_fields:
            component.save(update_fields=update_fields)
        else:
            component.save()
        return component


component_dao = ComponentDAO()


from django.conf import settings as _settings  # noqa: E402
if getattr(_settings, 'USE_FIRESTORE_DAOS', False):
    from tcms.dao.firestore.management.component_dao import component_dao  # noqa: F401, F811
