from tcms.testruns.models import Environment, EnvironmentProperty

_ENVIRONMENT_FIELDS = ("id", "name", "description")
_ENV_PROPERTY_FIELDS = ("id", "environment", "name", "value")


class EnvironmentDAO:
    def filter(self, query):
        return [
            {"id": obj.id, "name": obj.name, "description": obj.description}
            for obj in Environment.objects.filter(**query).order_by("name", "id")
        ]

    def get_by_id(self, env_id):
        return Environment.objects.get(pk=env_id)

    def save(self, env):
        env.save()
        return env


class EnvironmentPropertyDAO:
    def filter(self, query):
        return [
            {"id": obj.id, "environment": obj.environment_id,
             "name": obj.name, "value": obj.value}
            for obj in EnvironmentProperty.objects.filter(**query)
            .order_by("environment_id", "name", "value")
        ]

    def filter_objects(self, query):
        """Return queryset of EnvironmentProperty objects for view layer."""
        # Convert queryset values to a list for __in lookups (gcloudc doesn't support subqueries)
        resolved = {}
        for k, v in query.items():
            if k.endswith("__in") and hasattr(v, 'values_list'):
                resolved[k] = list(v.values_list("pk", flat=True))
            else:
                resolved[k] = v
        return EnvironmentProperty.objects.filter(**resolved).order_by("environment_id", "name", "value")

    def get_or_create(self, environment_id, name, value):
        prop, created = EnvironmentProperty.objects.get_or_create(
            environment_id=environment_id, name=name, value=value
        )
        return prop, created

    def remove(self, query):
        EnvironmentProperty.objects.filter(**query).delete()


environment_dao = EnvironmentDAO()
environment_property_dao = EnvironmentPropertyDAO()
