from tcms.kiwi_auth.models import UserActivationKey

_FIELDS = ("id", "user", "activation_key", "key_expires")


class UserActivationKeyDAO:
    def __init__(self):
        self._store = {}

    def _to_dict(self, key):
        result = {field: getattr(key, field) for field in _FIELDS}
        result["user"] = key.user_id
        return result

    def _compare(self, old, new, operation):
        if old != new:
            print(f"[UserActivationKeyDAO] MISMATCH in '{operation}':")
            print(f"  OLD: {old}")
            print(f"  NEW: {new}")
        else:
            print(f"[UserActivationKeyDAO] OK '{operation}': results match")

    def get_by_user(self, user_id):
        old_result = UserActivationKey.objects.get(user_id=user_id)

        new_result = self._store.get(old_result.pk)
        if new_result is not None:
            self._compare(self._to_dict(old_result), new_result, "get_by_user")
        else:
            print(f"[UserActivationKeyDAO] get_by_user: user_id={user_id} not in new storage yet - skipping comparison")

        return old_result

    def set_random_key_for_user(self, user, force=False):
        # delegates to model classmethod, then syncs to new storage
        key = UserActivationKey.set_random_key_for_user(user, force=force)
        self._store[key.pk] = self._to_dict(key)
        print(f"[UserActivationKeyDAO] set_random_key_for_user: synced key id={key.pk} to new storage")
        return key

    def save(self, key):
        key.save()
        self._store[key.pk] = self._to_dict(key)
        print(f"[UserActivationKeyDAO] save: synced key id={key.pk} to new storage")
        return key


user_activation_key_dao = UserActivationKeyDAO()
