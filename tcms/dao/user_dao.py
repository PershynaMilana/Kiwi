from django.contrib.auth import get_user_model

from tcms.utils import user as user_utils

User = get_user_model()  # pylint: disable=invalid-name

# Fields we expose publicly (no password, no sensitive internals)
_USER_FIELDS = (
    "email",
    "first_name",
    "id",
    "is_active",
    "is_staff",
    "is_superuser",
    "last_name",
    "username",
)


class UserDAO:
    # ------------------------------------------------------------------
    # READ operations
    # ------------------------------------------------------------------

    def filter(self, query):
        """
        Return a list of user dicts matching query.
        Used by the User.filter RPC endpoint.
        """
        return list(
            User.objects.filter(**query)
            .values(*_USER_FIELDS)
            .order_by("id")
            .distinct()
        )

    def get_by_id(self, user_id):
        """
        Return a single User object by primary key.
        Used by User.update RPC endpoint.
        """
        return User.objects.get(pk=user_id)

    def get_by_username(self, username):
        """
        Return a single User object by username.
        Used by User.join_group RPC endpoint.
        """
        return User.objects.get(username=username)

    def filter_objects(self, query):
        """
        Return a list of User objects matching query.
        Used internally by deactivate (needs objects, not dicts).
        """
        return list(User.objects.filter(**query))

    # ------------------------------------------------------------------
    # WRITE operations
    # ------------------------------------------------------------------

    def save(self, user, update_fields=None):
        """
        Persist a User object.
        Used by User.update RPC endpoint.
        """
        if update_fields:
            user.save(update_fields=update_fields)
        else:
            user.save()
        return user

    def deactivate(self, user):
        """
        Deactivate a user (sets is_active=False, clears permissions/groups).
        Used by User.deactivate RPC endpoint.
        """
        user_utils.deactivate(user)

    def add_to_group(self, user, group):
        """
        Add a user to a group.
        Used by User.join_group RPC endpoint.
        """
        user.groups.add(group)


user_dao = UserDAO()


from django.conf import settings as _settings  # noqa: E402
if getattr(_settings, 'USE_FIRESTORE_DAOS', False):
    from tcms.dao.firestore.user_dao import user_dao  # noqa: F401, F811
