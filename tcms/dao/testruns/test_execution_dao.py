from datetime import timedelta

from django.db.models import F
from django.db.models.functions import Coalesce

from tcms.testruns.models import TestExecution

_TEST_EXECUTION_FIELDS = (
    "id",
    "assignee",
    "tested_by",
    "case_text_version",
    "start_date",
    "stop_date",
    "sortkey",
    "run",
    "case",
    "status",
    "build",
)


class TestExecutionDAO:
    # ------------------------------------------------------------------
    # READ operations
    # ------------------------------------------------------------------

    def filter(self, query):
        """
        Return a list of test execution dicts matching query.
        Used by the TestExecution.filter RPC endpoint.
        """
        return list(
            TestExecution.objects.annotate(
                expected_duration=(
                    Coalesce("case__setup_duration", timedelta(0))
                    + Coalesce("case__testing_duration", timedelta(0))
                ),
                actual_duration=F("stop_date") - F("start_date"),
            )
            .filter(**query)
            .values(
                *_TEST_EXECUTION_FIELDS,
                "assignee__username",
                "tested_by__username",
                "case__summary",
                "build__name",
                "status__name",
                "status__icon",
                "status__color",
                "expected_duration",
                "actual_duration",
            )
            .order_by("id")
            .distinct()
        )

    def get_by_id(self, execution_id):
        """
        Return a single TestExecution object by primary key.
        """
        return TestExecution.objects.get(pk=execution_id)

    # ------------------------------------------------------------------
    # WRITE operations
    # ------------------------------------------------------------------

    def save(self, execution, update_fields=None):
        """
        Persist a TestExecution object.
        Used by TestExecution.create and TestExecution.update RPC endpoints.
        """
        if update_fields:
            execution.save(update_fields=update_fields)
        else:
            execution.save()
        return execution

    def remove(self, query):
        """
        Delete TestExecution objects matching query.
        Used by TestExecution.remove RPC endpoint.
        """
        return TestExecution.objects.filter(**query).delete()


test_execution_dao = TestExecutionDAO()


from django.conf import settings as _settings  # noqa: E402
if getattr(_settings, 'USE_FIRESTORE_DAOS', False):
    from tcms.dao.firestore.testruns.test_execution_dao import test_execution_dao  # noqa: F401, F811
