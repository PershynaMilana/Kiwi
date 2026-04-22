from tcms.testcases.models import TestCaseEmailSettings

_FIELDS = (
    "id",
    "case",
    "notify_on_case_update",
    "notify_on_case_delete",
    "auto_to_case_author",
    "auto_to_case_tester",
    "auto_to_run_manager",
    "auto_to_run_tester",
    "auto_to_execution_assignee",
    "cc_list",
)


class TestCaseEmailSettingsDAO:
    def __init__(self):
        self._store = {}

    def _to_dict(self, settings):
        result = {field: getattr(settings, field) for field in _FIELDS}
        result["case"] = settings.case_id
        return result

    def _compare(self, old, new, operation):
        if old != new:
            print(f"[TestCaseEmailSettingsDAO] MISMATCH in '{operation}':")
            print(f"  OLD: {old}")
            print(f"  NEW: {new}")
        else:
            print(f"[TestCaseEmailSettingsDAO] OK '{operation}': results match")

    def get_by_case(self, case_id):
        old_result = TestCaseEmailSettings.objects.get(case_id=case_id)

        new_result = self._store.get(old_result.pk)
        if new_result is not None:
            self._compare(self._to_dict(old_result), new_result, "get_by_case")
        else:
            print(f"[TestCaseEmailSettingsDAO] get_by_case: case_id={case_id} not in new storage yet - skipping comparison")

        return old_result

    def save(self, settings):
        settings.save()
        self._store[settings.pk] = self._to_dict(settings)
        print(f"[TestCaseEmailSettingsDAO] save: synced settings id={settings.pk} to new storage")
        return settings


test_case_email_settings_dao = TestCaseEmailSettingsDAO()
