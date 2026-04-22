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
    def __init__(self):
        self._store = {}

    def _to_dict(self, settings):
        result = {field: getattr(settings, field) for field in _FIELDS}
        result["plan"] = settings.plan_id
        return result

    def _compare(self, old, new, operation):
        if old != new:
            print(f"[TestPlanEmailSettingsDAO] MISMATCH in '{operation}':")
            print(f"  OLD: {old}")
            print(f"  NEW: {new}")
        else:
            print(f"[TestPlanEmailSettingsDAO] OK '{operation}': results match")

    def get_by_plan(self, plan_id):
        old_result = TestPlanEmailSettings.objects.get(plan_id=plan_id)

        new_result = self._store.get(old_result.pk)
        if new_result is not None:
            self._compare(self._to_dict(old_result), new_result, "get_by_plan")
        else:
            print(f"[TestPlanEmailSettingsDAO] get_by_plan: plan_id={plan_id} not in new storage yet - skipping comparison")

        return old_result

    def save(self, settings):
        settings.save()
        self._store[settings.pk] = self._to_dict(settings)
        print(f"[TestPlanEmailSettingsDAO] save: synced settings id={settings.pk} to new storage")
        return settings


test_plan_email_settings_dao = TestPlanEmailSettingsDAO()
