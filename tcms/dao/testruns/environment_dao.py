from tcms.testruns.models import Environment, EnvironmentProperty

_ENVIRONMENT_FIELDS = ("id", "name", "description")
_ENV_PROPERTY_FIELDS = ("id", "environment", "name", "value")


class EnvironmentDAO:
    def __init__(self):
        self._store = {}

    def _to_dict(self, env):
        return {field: getattr(env, field) for field in _ENVIRONMENT_FIELDS}

    def _compare(self, old, new, operation):
        if old != new:
            print(f"[EnvironmentDAO] MISMATCH in '{operation}':")
            print(f"  OLD: {old}")
            print(f"  NEW: {new}")
        else:
            print(f"[EnvironmentDAO] OK '{operation}': results match")

    def filter(self, query):
        old_result = list(
            Environment.objects.filter(**query)
            .values(*_ENVIRONMENT_FIELDS)
            .order_by("name", "description")
            .distinct()
        )

        new_result = [self._store[e["id"]] for e in old_result if e["id"] in self._store]
        if new_result:
            old_subset = [e for e in old_result if e["id"] in self._store]
            self._compare(old_subset, new_result, "filter")
        else:
            print("[EnvironmentDAO] filter: no data in new storage yet - skipping comparison")

        return old_result

    def get_by_id(self, env_id):
        old_result = Environment.objects.get(pk=env_id)

        new_result = self._store.get(env_id)
        if new_result is not None:
            self._compare(self._to_dict(old_result), new_result, "get_by_id")
        else:
            print(f"[EnvironmentDAO] get_by_id: env id={env_id} not in new storage yet - skipping comparison")

        return old_result

    def save(self, env):
        env.save()
        self._store[env.pk] = self._to_dict(env)
        print(f"[EnvironmentDAO] save: synced environment id={env.pk} to new storage")
        return env


class EnvironmentPropertyDAO:
    def __init__(self):
        self._store = {}

    def _to_dict(self, prop):
        return {field: getattr(prop, field) for field in _ENV_PROPERTY_FIELDS}

    def _compare(self, old, new, operation):
        if old != new:
            print(f"[EnvironmentPropertyDAO] MISMATCH in '{operation}':")
            print(f"  OLD: {old}")
            print(f"  NEW: {new}")
        else:
            print(f"[EnvironmentPropertyDAO] OK '{operation}': results match")

    def filter(self, query):
        old_result = list(
            EnvironmentProperty.objects.filter(**query)
            .values(*_ENV_PROPERTY_FIELDS)
            .order_by("environment", "name", "value")
            .distinct()
        )

        new_result = [self._store[p["id"]] for p in old_result if p["id"] in self._store]
        if new_result:
            old_subset = [p for p in old_result if p["id"] in self._store]
            self._compare(old_subset, new_result, "filter")
        else:
            print("[EnvironmentPropertyDAO] filter: no data in new storage yet - skipping comparison")

        return old_result

    def filter_objects(self, query):
        """Return queryset of EnvironmentProperty objects for view layer."""
        return EnvironmentProperty.objects.filter(**query).order_by("environment", "name", "value")

    def get_or_create(self, environment_id, name, value):
        prop, created = EnvironmentProperty.objects.get_or_create(
            environment_id=environment_id, name=name, value=value
        )
        self._store[prop.pk] = self._to_dict(prop)
        print(f"[EnvironmentPropertyDAO] get_or_create: synced property id={prop.pk} to new storage")
        return prop, created

    def remove(self, query):
        for prop in EnvironmentProperty.objects.filter(**query):
            self._store.pop(prop.pk, None)
        EnvironmentProperty.objects.filter(**query).delete()
        print(f"[EnvironmentPropertyDAO] remove: deleted properties matching {query}")


environment_dao = EnvironmentDAO()
environment_property_dao = EnvironmentPropertyDAO()