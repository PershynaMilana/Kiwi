from django.forms.models import model_to_dict

from tcms.testcases.models import TestCase
from tcms.testruns.models import TestExecution, TestRun

_TEST_RUN_FIELDS = (
    "id",
    "start_date",
    "stop_date",
    "planned_start",
    "planned_stop",
    "summary",
    "notes",
    "plan",
    "build",
    "manager",
    "default_tester",
)


class TestRunDAO:
    # ------------------------------------------------------------------
    # READ operations
    # ------------------------------------------------------------------

    def filter(self, query):
        """
        Return a list of test run dicts matching query.
        Used by the TestRun.filter RPC endpoint.
        """
        _EXTRA_FIELDS = (
            "plan__name",
            "build__name",
            "build__version",
            "build__version__value",
            "build__version__product",
            "manager__username",
            "default_tester__username",
        )
        return list(
            TestRun.objects.filter(**query)
            .values(*_TEST_RUN_FIELDS, *_EXTRA_FIELDS)
            .order_by("id")
            .distinct()
        )

    def filter_objects(self, *args, **kwargs):
        """Return a TestRun queryset for use in views and templates."""
        return TestRun.objects.filter(*args, **kwargs)

    def get_by_id(self, run_id):
        """Return a single TestRun object by primary key."""
        return TestRun.objects.get(pk=run_id)

    # ------------------------------------------------------------------
    # WRITE operations
    # ------------------------------------------------------------------

    def save(self, run, update_fields=None):
        """
        Persist a TestRun object.
        Used by TestRun.create and TestRun.update RPC endpoints.
        """
        if update_fields:
            run.save(update_fields=update_fields)
        else:
            run.save()
        return run

    def remove(self, query):
        """
        Delete TestRun objects matching query.
        Used by TestRun.remove RPC endpoint.
        """
        return TestRun.objects.filter(**query).delete()

    # ------------------------------------------------------------------
    # TestExecution / add_case / remove_case / get_cases
    # ------------------------------------------------------------------

    @staticmethod
    def _annotate_executions(executions_iterable):
        result = []
        for execution in executions_iterable:
            serialized = model_to_dict(execution)
            serialized["properties"] = list(
                execution.properties().values("name", "value")
            )
            result.append(serialized)
        return result

    def add_case(self, run, case):
        """
        Add a TestCase to the given TestRun, creating a TestExecution.
        Used by the TestRun.add_case RPC endpoint.
        """
        if run.executions.filter(case=case).exists():
            return self._annotate_executions(run.executions.filter(case=case))

        if not case.case_status.is_confirmed:
            raise RuntimeError(f"TC-{case.pk} status is not confirmed")

        sortkey = 10
        last_te = run.executions.order_by("sortkey").last()
        if last_te:
            sortkey += last_te.sortkey

        return self._annotate_executions(
            run.create_execution(case=case, sortkey=sortkey)
        )

    def remove_case(self, run_id, case_id):
        """
        Remove TestExecution(s) for the given case from the given run.
        Used by the TestRun.remove_case RPC endpoint.
        """
        TestExecution.objects.filter(run=run_id, case=case_id).delete()

    def get_cases(self, run_id):
        """
        Return test cases attached to the given run, augmented with execution info.
        Used by the TestRun.get_cases RPC endpoint.
        """
        result = list(
            TestCase.objects.filter(executions__run_id=run_id).values(
                "id",
                "create_date",
                "is_automated",
                "script",
                "arguments",
                "extra_link",
                "summary",
                "requirement",
                "notes",
                "text",
                "case_status",
                "category",
                "priority",
                "author",
                "default_tester",
                "reviewer",
            )
        )

        executions = TestExecution.objects.filter(run_id=run_id).values(
            "case", "pk", "status__name"
        )
        extra_info = {row["case"]: row for row in executions.iterator()}
        for case in result:
            info = extra_info[case["id"]]
            case["execution_id"] = info["pk"]
            case["status"] = info["status__name"]

        return result

    # ------------------------------------------------------------------
    # CC operations
    # ------------------------------------------------------------------

    def add_cc(self, run, user):
        """
        Add user to test run CC list.
        Used by the TestRun.add_cc RPC endpoint.
        """
        run.add_cc(user)

    def remove_cc(self, run, user):
        """
        Remove user from test run CC list.
        Used by the TestRun.remove_cc RPC endpoint.
        """
        run.remove_cc(user)

    def get_cc(self, run):
        """
        Return CC email list for the given test run.
        Used by the TestRun.get_cc RPC endpoint.
        """
        return list(run.cc.values_list("email", flat=True))


test_run_dao = TestRunDAO()


from django.conf import settings as _settings  # noqa: E402
if getattr(_settings, 'USE_FIRESTORE_DAOS', False):
    from tcms.dao.firestore.testruns.test_run_dao import test_run_dao  # noqa: F401, F811
