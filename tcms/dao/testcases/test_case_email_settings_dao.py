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
    def get_by_case(self, case_id):
        return TestCaseEmailSettings.objects.get(case_id=case_id)

    def save(self, settings):
        settings.save()
        return settings


test_case_email_settings_dao = TestCaseEmailSettingsDAO()
