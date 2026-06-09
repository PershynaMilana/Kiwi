from tcms.testcases.models import BugSystem

_FIELDS = ("id", "name", "tracker_type", "base_url", "api_url", "api_username", "api_password")
_PUBLIC_FIELDS = ("id", "name", "tracker_type", "base_url", "api_url", "api_username")


class BugSystemDAO:
    def filter_objects(self, query):
        return BugSystem.objects.filter(**query)

    def filter(self, query):
        return [
            {"id": obj.id, "name": obj.name, "tracker_type": obj.tracker_type,
             "base_url": obj.base_url, "api_url": obj.api_url,
             "api_username": obj.api_username}
            for obj in BugSystem.objects.filter(**query).order_by("id")
        ]

    def get_by_id(self, bug_system_id):
        return BugSystem.objects.get(pk=bug_system_id)

    def save(self, bug_system):
        bug_system.save()
        return bug_system


bug_system_dao = BugSystemDAO()
