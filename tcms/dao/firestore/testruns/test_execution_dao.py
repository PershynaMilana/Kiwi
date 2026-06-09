from datetime import timedelta

from django.contrib.auth import get_user_model

from tcms.dao.firestore.testcases.test_case_dao import _to_timedelta

from tcms.dao.firestore.utils import (
    chunked_queryset, ensure_safe_json_integers,
    generate_safe_pk, int_pk_only, normalize_datetimes,
    resolve_string_field_ids, _STRING_OPS,
)
from tcms.management.models import Build
from tcms.testcases.models import TestCase
from tcms.testruns.models import TestExecution, TestExecutionStatus

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

_FK_FIELDS = {"assignee", "tested_by", "run", "case", "status", "build"}


def _fetch_execution_related_maps(executions):
    """Batch-fetch all related objects needed for execution dicts."""
    User = get_user_model()
    user_ids = set()
    case_ids = set()
    build_ids = set()
    status_ids = set()
    for e in executions:
        for uid in (e.assignee_id, e.tested_by_id):
            if uid and isinstance(uid, int):
                user_ids.add(uid)
        if e.case_id and isinstance(e.case_id, int):
            case_ids.add(e.case_id)
        if e.build_id and isinstance(e.build_id, int):
            build_ids.add(e.build_id)
        if e.status_id and isinstance(e.status_id, int):
            status_ids.add(e.status_id)

    users = {u.pk: u.username for u in chunked_queryset(User, "pk", list(user_ids))}
    cases = {tc.pk: tc for tc in chunked_queryset(TestCase, "pk", list(case_ids))}
    builds = {b.pk: b.name for b in chunked_queryset(Build, "pk", list(build_ids))}
    statuses = {s.pk: s for s in chunked_queryset(TestExecutionStatus, "pk", list(status_ids))}

    return users, cases, builds, statuses


def _execution_to_dict(execution, users, cases, builds, statuses):
    """Build an execution dict from a TestExecution instance using pre-fetched related maps."""
    d = {}
    for field in _TEST_EXECUTION_FIELDS:
        if field in _FK_FIELDS:
            d[field] = getattr(execution, f"{field}_id")
        else:
            d[field] = getattr(execution, field)

    d["assignee__username"] = users.get(execution.assignee_id)
    d["tested_by__username"] = users.get(execution.tested_by_id)

    tc = cases.get(execution.case_id)
    d["case__summary"] = tc.summary if tc else None
    d["expected_duration"] = (
        (_to_timedelta(tc.setup_duration) + _to_timedelta(tc.testing_duration))
        if tc else timedelta(0)
    )

    d["build__name"] = builds.get(execution.build_id)

    status = statuses.get(execution.status_id)
    d["status__name"] = status.name if status else None
    d["status__icon"] = status.icon if status else None
    d["status__color"] = status.color if status else None

    if execution.stop_date and execution.start_date:
        d["actual_duration"] = execution.stop_date - execution.start_date
    else:
        d["actual_duration"] = None

    return d


_CHUNK = 90


def _resolve_execution_query(query):
    """Pre-resolve cross-collection traversals in a TestExecution filter query."""
    from tcms.management.models import Priority, Version
    from tcms.testcases.models import Category, TestCase
    from tcms.testplans.models import TestPlan
    from tcms.testruns.models import TestRun

    resolved = {}
    case_id_constraints = []

    for k, v in query.items():
        if k.startswith("case__"):
            sub_key = k[len("case__"):]
            if sub_key.startswith("priority__"):
                priority_ids = list(Priority.objects.filter(**{sub_key[len("priority__"):]: v}).values_list("pk", flat=True))
                case_ids = set(TestCase.objects.filter(priority_id__in=priority_ids).values_list("pk", flat=True))
            elif sub_key.startswith("category__"):
                category_ids = list(Category.objects.filter(**{sub_key[len("category__"):]: v}).values_list("pk", flat=True))
                case_ids = set(TestCase.objects.filter(category_id__in=category_ids).values_list("pk", flat=True))
            else:
                case_ids = set(TestCase.objects.filter(**{sub_key: v}).values_list("pk", flat=True))
            case_id_constraints.append(case_ids)

        elif k.startswith("run__plan"):
            # Two-hop: TestExecution.run → TestRun.plan
            if k == "run__plan__in":
                plan_ids = list(v) if isinstance(v, (list, tuple)) else [v]
            else:
                plan_lookup = k[len("run__plan__"):]
                plan_ids = list(TestPlan.objects.filter(**{plan_lookup: v}).values_list("pk", flat=True))
            run_ids = []
            for i in range(0, len(plan_ids), _CHUNK):
                run_ids.extend(
                    TestRun.objects.filter(plan_id__in=plan_ids[i:i + _CHUNK])
                    .values_list("pk", flat=True)
                )
            resolved["run_id__in"] = run_ids

        elif k.startswith("run__"):
            # One-hop: TestExecution.run → TestRun
            if k == "run__in":
                resolved["run_id__in"] = list(v) if isinstance(v, (list, tuple)) else [v]
            else:
                run_lookup = k[len("run__"):]
                # Detect string operators on TestRun text fields (e.g. summary__icontains)
                # and resolve in Python to bypass gcloudc's special-index mechanism.
                _TESTRUN_TEXT = frozenset({'summary', 'notes'})
                if '__' in run_lookup:
                    run_field, run_op = run_lookup.rsplit('__', 1)
                    if run_field in _TESTRUN_TEXT and run_op in _STRING_OPS:
                        run_ids = resolve_string_field_ids(TestRun, run_field, run_op, v)
                    else:
                        run_ids = list(TestRun.objects.filter(**{run_lookup: v}).values_list("pk", flat=True))
                else:
                    run_ids = list(TestRun.objects.filter(**{run_lookup: v}).values_list("pk", flat=True))
                resolved["run_id__in"] = run_ids

        elif k.startswith("build__version__"):
            # Two or three-hop: TestExecution.build → Build.version → Version.*
            version_lookup = k[len("build__version__"):]
            if version_lookup == "in":
                version_ids = list(v) if isinstance(v, (list, tuple)) else [v]
            else:
                version_ids = list(Version.objects.filter(**{version_lookup: v}).values_list("pk", flat=True))
            build_ids = []
            for i in range(0, len(version_ids), _CHUNK):
                build_ids.extend(
                    Build.objects.filter(version_id__in=version_ids[i:i + _CHUNK])
                    .values_list("pk", flat=True)
                )
            resolved["build_id__in"] = build_ids

        elif k.startswith("build__"):
            # One-hop: TestExecution.build → Build
            if k == "build__in":
                resolved["build_id__in"] = list(v) if isinstance(v, (list, tuple)) else [v]
            else:
                build_lookup = k[len("build__"):]
                build_ids = list(Build.objects.filter(**{build_lookup: v}).values_list("pk", flat=True))
                resolved["build_id__in"] = build_ids

        else:
            resolved[k] = v

    if case_id_constraints:
        final_ids = case_id_constraints[0]
        for s in case_id_constraints[1:]:
            final_ids = final_ids & s
        resolved["case_id__in"] = list(final_ids)

    return resolved


class TestExecutionDAO:
    def filter(self, query):
        """
        Return a list of test execution dicts matching query.
        Used by the TestExecution.filter RPC endpoint.
        """
        query = _resolve_execution_query(query)
        executions = int_pk_only(list(TestExecution.objects.filter(**query).order_by("id")))
        users, cases, builds, statuses = _fetch_execution_related_maps(executions)
        result = [_execution_to_dict(e, users, cases, builds, statuses) for e in executions]
        return [ensure_safe_json_integers(d) for d in result]

    def get_by_id(self, execution_id):
        """Return a single TestExecution object by primary key."""
        return TestExecution.objects.get(pk=execution_id)

    def save(self, execution, update_fields=None):
        """Persist a TestExecution object."""
        if execution.pk is None:
            execution.pk = generate_safe_pk(TestExecution)
        normalize_datetimes(execution)
        if update_fields:
            execution.save(update_fields=update_fields)
        else:
            execution.save()
        return execution

    def remove(self, query):
        """Delete TestExecution objects matching query."""
        return TestExecution.objects.filter(**query).delete()

    def history(self, execution):
        """
        Return history records for the given test execution.
        Avoids FK traversal in .values() by batch-fetching user usernames.
        """
        User = get_user_model()
        # order_by("-history_date") combined with filter(id=...) requires a
        # composite index on testruns_historicaltestexecution(id, history_date).
        # Use .order_by() to suppress ordering and sort in Python instead.
        # Also avoid .values() projection (requires indexed fields); fetch full objects.
        raw = list(execution.history.order_by())
        raw.sort(key=lambda h: h.history_date, reverse=True)
        user_ids = list({h.history_user_id for h in raw if h.history_user_id})
        username_map = {u.pk: u.username for u in chunked_queryset(User, "pk", user_ids)}
        return [
            {
                "history_date": h.history_date,
                "history_change_reason": h.history_change_reason,
                "history_user__username": username_map.get(h.history_user_id),
            }
            for h in raw
        ]


test_execution_dao = TestExecutionDAO()
