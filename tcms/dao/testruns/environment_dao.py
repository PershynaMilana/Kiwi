from tcms.testruns.models import Environment, EnvironmentProperty

_ENVIRONMENT_FIELDS = ("id", "name", "description")
_ENV_PROPERTY_FIELDS = ("id", "environment", "name", "value")


class EnvironmentDAO:
    def filter(self, query):
        return list(
            Environment.objects.filter(**query)
            .values(*_ENVIRONMENT_FIELDS)
            .order_by("name", "description")
            .distinct()
        )

    def get_by_id(self, env_id):
        return Environment.objects.get(pk=env_id)

    def save(self, env):
        env.save()
        return env


class EnvironmentPropertyDAO:
    def filter(self, query):
        return list(
            EnvironmentProperty.objects.filter(**query)
            .values(*_ENV_PROPERTY_FIELDS)
            .order_by("environment", "name", "value")
            .distinct()
        )

    def filter_objects(self, query):
        """Return queryset of EnvironmentProperty objects for view layer."""
        return EnvironmentProperty.objects.filter(**query).order_by("environment", "name", "value")

    def get_or_create(self, environment_id, name, value):
        prop, created = EnvironmentProperty.objects.get_or_create(
            environment_id=environment_id, name=name, value=value
        )
        return prop, created

    def remove(self, query):
        EnvironmentProperty.objects.filter(**query).delete()


environment_dao = EnvironmentDAO()
environment_property_dao = EnvironmentPropertyDAO()

from django.conf import settings as _settings  # noqa: E402
if getattr(_settings, 'USE_FIRESTORE_DAOS', False):
    from tcms.dao.firestore.testruns.environment_dao import (  # noqa: F401, F811
        environment_dao,
        environment_property_dao,
    )
