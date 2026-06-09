from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType


class GroupDAO:
    def filter(self, query):
        return list(
            Group.objects.filter(**query)
            .values("id", "name")
            .order_by("id")
        )

    def get_by_id(self, group_id):
        return Group.objects.get(pk=group_id)

    def get_by_name(self, name):
        return Group.objects.get(name=name)

    def save(self, group):
        group.save()
        return group

    def permissions(self, group):
        """Return permission labels for the group as 'app_label.codename' strings."""
        perms = list(group.permissions.values("content_type_id", "codename"))
        ct_ids = list({p["content_type_id"] for p in perms})
        app_labels = {ct.pk: ct.app_label for ct in ContentType.objects.filter(pk__in=ct_ids)}
        seen = set()
        result = []
        for p in perms:
            label = f"{app_labels.get(p['content_type_id'], '')}.{p['codename']}"
            if label not in seen:
                seen.add(label)
                result.append(label)
        return sorted(result)

    def users(self, group):
        """Return users belonging to the group as list of {id, username} dicts."""
        seen = {}
        for user in group.user_set.values("id", "username"):
            seen[user["id"]] = user
        return list(seen.values())


group_dao = GroupDAO()
