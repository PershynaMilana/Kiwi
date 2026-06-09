from django.contrib.auth import get_user_model
from django.forms.models import model_to_dict

from tcms.dao.firestore.utils import (
    chunked_queryset, ensure_safe_json_integers,
    generate_safe_pk, int_pk_only, normalize_datetimes,
    resolve_string_field_ids, resolve_user_ids, _STRING_OPS,
)
from tcms.management.models import Build, Version
from tcms.testcases.models import TestCase
from tcms.testplans.models import TestPlan
from tcms.testruns.models import TestExecution, TestExecutionStatus, TestRun

_USER_TRAVERSAL_PREFIXES = ("manager__", "default_tester__")

_CHUNK = 90

# TestRun text fields that require Python-side string-operator filtering.
_TESTRUN_TEXT_FIELDS = frozenset({'summary', 'notes'})


def _resolve_testrun_query(query):
    """
    Pre-resolve cross-collection traversals in a TestRun filter query.
    Handles user FK traversals, build/version FK traversals, and tag M2M traversals.
    """
    from tcms.management.models import Tag
    from tcms.testruns.models import TestRunTag

    User = get_user_model()
    run_id_constraints = []
    resolved = {}

    for k, v in query.items():
        if k.startswith("manager__"):
            user_lookup = k[len("manager__"):]
            user_ids = resolve_user_ids(user_lookup, v)
            resolved["manager_id__in"] = user_ids

        elif k.startswith("default_tester__"):
            user_lookup = k[len("default_tester__"):]
            user_ids = resolve_user_ids(user_lookup, v)
            resolved["default_tester_id__in"] = user_ids

        elif k.startswith("build__version__"):
            # Two-hop FK: TestRun.build → Build.version → Version.product_id (or other field)
            version_lookup = k[len("build__version__"):]
            version_ids = list(Version.objects.filter(**{version_lookup: v}).values_list("pk", flat=True))
            build_ids = []
            for i in range(0, len(version_ids), _CHUNK):
                build_ids.extend(
                    Build.objects.filter(version_id__in=version_ids[i:i + _CHUNK])
                    .values_list("pk", flat=True)
                )
            resolved["build_id__in"] = build_ids

        elif k.startswith("build__"):
            # One-hop FK: TestRun.build → Build
            build_lookup = k[len("build__"):]
            build_ids = list(Build.objects.filter(**{build_lookup: v}).values_list("pk", flat=True))
            resolved["build_id__in"] = build_ids

        elif k.startswith("tag__"):
            # M2M traversal via TestRunTag junction
            tag_lookup = k[len("tag__"):]
            tag_ids = list(Tag.objects.filter(**{tag_lookup: v}).values_list("pk", flat=True))
            rids = set()
            for i in range(0, len(tag_ids), _CHUNK):
                rids.update(
                    TestRunTag.objects.filter(tag_id__in=tag_ids[i:i + _CHUNK])
                    .values_list("run_id", flat=True)
                )
            run_id_constraints.append(rids)

        else:
            # Detect string operators on text fields and filter in Python to
            # bypass gcloudc's special-index mechanism.
            if '__' in k:
                field, op = k.rsplit('__', 1)
                if field in _TESTRUN_TEXT_FIELDS and op in _STRING_OPS:
                    matched_ids = resolve_string_field_ids(TestRun, field, op, v)
                    run_id_constraints.append(set(matched_ids))
                    continue
            resolved[k] = v

    if run_id_constraints:
        final_ids = run_id_constraints[0]
        for s in run_id_constraints[1:]:
            final_ids = final_ids & s
        resolved["pk__in"] = list(final_ids)

    return resolved

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

_FK_FIELDS = {"plan", "build", "manager", "default_tester"}


def _fetch_run_related_maps(runs):
    """Batch-fetch all related objects needed for test run dicts."""
    User = get_user_model()
    plan_ids = list({r.plan_id for r in runs if r.plan_id and isinstance(r.plan_id, int)})
    build_ids = list({r.build_id for r in runs if r.build_id and isinstance(r.build_id, int)})
    user_ids = set()
    for r in runs:
        for uid in (r.manager_id, r.default_tester_id):
            if uid and isinstance(uid, int):
                user_ids.add(uid)

    plans = {p.pk: p.name for p in chunked_queryset(TestPlan, "pk", plan_ids)}
    builds = {b.pk: b for b in chunked_queryset(Build, "pk", build_ids)}
    users = {u.pk: u.username for u in chunked_queryset(User, "pk", list(user_ids))}

    version_ids = list({b.version_id for b in builds.values() if b.version_id and isinstance(b.version_id, int)})
    versions = {v.pk: v for v in chunked_queryset(Version, "pk", version_ids)}

    return plans, builds, versions, users


def _run_to_dict(run, plans, builds, versions, users):
    """Build a run dict from a TestRun instance using pre-fetched related maps."""
    d = {}
    for field in _TEST_RUN_FIELDS:
        if field in _FK_FIELDS:
            d[field] = getattr(run, f"{field}_id")
        else:
            d[field] = getattr(run, field)
    d["plan__name"] = plans.get(run.plan_id)
    build = builds.get(run.build_id)
    if build:
        d["build__name"] = build.name
        d["build__version"] = build.version_id
        version = versions.get(build.version_id)
        d["build__version__value"] = version.value if version else None
        d["build__version__product"] = version.product_id if version else None
    else:
        d["build__name"] = None
        d["build__version"] = None
        d["build__version__value"] = None
        d["build__version__product"] = None
    d["manager__username"] = users.get(run.manager_id)
    d["default_tester__username"] = users.get(run.default_tester_id)
    return d


class TestRunDAO:
    def filter(self, query):
        """
        Return a list of test run dicts matching query.
        Used by the TestRun.filter RPC endpoint.
        """
        query = _resolve_testrun_query(query)
        if "pk__in" in query and not query["pk__in"]:
            return []
        runs = int_pk_only(list(TestRun.objects.filter(**query).order_by("id")))
        plans, builds, versions, users = _fetch_run_related_maps(runs)
        result = [_run_to_dict(r, plans, builds, versions, users) for r in runs]
        return [ensure_safe_json_integers(d) for d in result]

    def filter_objects(self, *args, **kwargs):
        """Return a TestRun queryset for use in views and templates."""
        return TestRun.objects.filter(*args, **kwargs)

    def get_by_id(self, run_id):
        """Return a single TestRun object by primary key."""
        return TestRun.objects.get(pk=run_id)

    def save(self, run, update_fields=None):
        """Persist a TestRun object."""
        if run.pk is None:
            run.pk = generate_safe_pk(TestRun)
        normalize_datetimes(run)
        if update_fields:
            run.save(update_fields=update_fields)
        else:
            run.save()
        return run

    def remove(self, query):
        """Delete TestRun objects matching query."""
        return TestRun.objects.filter(**query).delete()

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
        """Add a TestCase to the given TestRun, creating a TestExecution."""
        if run.executions.filter(case=case).exists():
            return self._annotate_executions(run.executions.filter(case=case))

        if not case.case_status.is_confirmed:
            raise RuntimeError(f"TC-{case.pk} status is not confirmed")

        sortkey = 10
        # values_list("sortkey") is a projection query requiring db_index=True.
        # Fetch full objects and extract sortkey in Python instead.
        valid = [e.sortkey for e in run.executions.all() if e.sortkey is not None]
        if valid:
            sortkey += max(valid)

        return self._annotate_executions(
            run.create_execution(case=case, sortkey=sortkey)
        )

    def remove_case(self, run_id, case_id):
        """Remove TestExecution(s) for the given case from the given run."""
        TestExecution.objects.filter(run=run_id, case=case_id).delete()

    def get_cases(self, run_id):
        """
        Return test cases attached to the given run, augmented with execution info.
        Used by the TestRun.get_cases RPC endpoint.
        """
        exec_list = list(TestExecution.objects.filter(run_id=run_id))
        case_ids = [e.case_id for e in exec_list]

        # Build status name map without FK traversal
        status_name_map = {s.pk: s.name for s in TestExecutionStatus.objects.all()}
        extra_info = {
            e.case_id: {"pk": e.pk, "status__name": status_name_map.get(e.status_id)}
            for e in exec_list
        }

        _VALUE_FIELDS = (
            "id", "create_date", "is_automated", "script", "arguments",
            "extra_link", "summary", "requirement", "notes", "text",
            "case_status", "category", "priority", "author", "default_tester", "reviewer",
        )
        result = []
        for i in range(0, len(case_ids), 90):
            chunk = case_ids[i:i + 90]
            result.extend(TestCase.objects.filter(pk__in=chunk).values(*_VALUE_FIELDS))

        for case in result:
            info = extra_info.get(case["id"], {})
            case["execution_id"] = info.get("pk")
            case["status"] = info.get("status__name")

        return result

    def add_cc(self, run, user):
        """Add user to test run CC list."""
        run.add_cc(user)

    def remove_cc(self, run, user):
        """Remove user from test run CC list."""
        run.remove_cc(user)

    def get_cc(self, run):
        """Return CC email list for the given test run."""
        from tcms.testruns.models import TestRunCC
        User = get_user_model()
        user_ids = list(TestRunCC.objects.filter(run_id=run.pk).values_list("user_id", flat=True))
        if not user_ids:
            return []
        return list(User.objects.filter(pk__in=user_ids).values_list("email", flat=True))


test_run_dao = TestRunDAO()
