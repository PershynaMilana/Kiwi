from tcms.testplans.models import PlanType

class PlanTypeDAO:
    def filter(self, query):
        return [
            {"id": obj.id, "name": obj.name, "description": obj.description}
            for obj in PlanType.objects.filter(**query).order_by("id")
        ]

    def get_by_id(self, plan_type_id):
        return PlanType.objects.get(pk=plan_type_id)

    def save(self, plan_type):
        plan_type.save()
        return plan_type


plan_type_dao = PlanTypeDAO()
