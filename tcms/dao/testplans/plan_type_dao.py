from tcms.testplans.models import PlanType

_FIELDS = ("id", "name", "description")


class PlanTypeDAO:
    def filter(self, query):
        return list(
            PlanType.objects.filter(**query)
            .values(*_FIELDS)
            .order_by("id")
            .distinct()
        )

    def get_by_id(self, plan_type_id):
        return PlanType.objects.get(pk=plan_type_id)

    def save(self, plan_type):
        plan_type.save()
        return plan_type


plan_type_dao = PlanTypeDAO()

from django.conf import settings as _settings  # noqa: E402
if getattr(_settings, 'USE_FIRESTORE_DAOS', False):
    from tcms.dao.firestore.testplans.plan_type_dao import plan_type_dao  # noqa: F401, F811
