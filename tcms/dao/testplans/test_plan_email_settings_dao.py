from tcms.testplans.models import TestPlanEmailSettings

_FIELDS = (
    "id",
    "plan",
    "auto_to_plan_author",
    "auto_to_case_owner",
    "auto_to_case_default_tester",
    "notify_on_plan_update",
    "notify_on_case_update",
)


class TestPlanEmailSettingsDAO:
    def get_by_plan(self, plan_id):
        return TestPlanEmailSettings.objects.get(plan_id=plan_id)

    def save(self, settings):
        settings.save()
        return settings


test_plan_email_settings_dao = TestPlanEmailSettingsDAO()
