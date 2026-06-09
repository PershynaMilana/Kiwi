from tcms.kiwi_auth.models import UserActivationKey

_FIELDS = ("id", "user", "activation_key", "key_expires")


class UserActivationKeyDAO:
    def get_by_user(self, user_id):
        return UserActivationKey.objects.get(user_id=user_id)

    def set_random_key_for_user(self, user, force=False):
        return UserActivationKey.set_random_key_for_user(user, force=force)

    def save(self, key):
        key.save()
        return key


user_activation_key_dao = UserActivationKeyDAO()
