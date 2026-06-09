from django.contrib.auth.models import Group


class GroupDAO:
    def filter(self, query):
        return list(
            Group.objects.filter(**query)
            .values("id", "name")
            .order_by("id")
            .distinct()
        )

    def get_by_id(self, group_id):
        return Group.objects.get(pk=group_id)

    def get_by_name(self, name):
        return Group.objects.get(name=name)

    def save(self, group):
        group.save()
        return group


group_dao = GroupDAO()


from django.conf import settings as _settings  # noqa: E402
if getattr(_settings, 'USE_FIRESTORE_DAOS', False):
    from tcms.dao.firestore.kiwi_auth.group_dao import group_dao  # noqa: F401, F811
