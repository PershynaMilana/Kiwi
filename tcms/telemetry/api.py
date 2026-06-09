from django.utils.translation import gettext_lazy as _
from modernrpc.auth.basic import http_basic_auth_login_required
from modernrpc.core import rpc_method

from tcms.dao.utils import chunked_queryset
from tcms.management.models import Build, Priority, Version
from tcms.testcases.models import Category, TestCase, TestCaseStatus
from tcms.testruns.models import TestExecution, TestExecutionStatus, TestRun

_CHUNK = 90


def _resolve_execution_query(query):
    """
    Pre-resolve cross-collection FK traversals in a TestExecution filter query.
    Handles run__plan__in, build__version__in, run__summary__icontains, etc.
    """
    resolved = {}
    for k, v in query.items():
        if k.startswith("run__plan"):
            # TestExecution.run → TestRun.plan: two-hop FK
            if k == "run__plan__in":
                plan_ids = list(v) if isinstance(v, (list, tuple)) else [v]
            else:
                plan_lookup = k[len("run__plan__"):]
                from tcms.testplans.models import TestPlan
                plan_ids = list(TestPlan.objects.filter(**{plan_lookup: v}).values_list("pk", flat=True))
            run_ids = []
            for i in range(0, len(plan_ids), _CHUNK):
                run_ids.extend(
                    TestRun.objects.filter(plan_id__in=plan_ids[i:i + _CHUNK])
                    .values_list("pk", flat=True)
                )
            resolved["run_id__in"] = run_ids

        elif k.startswith("run__"):
            # TestExecution.run → TestRun: one-hop FK
            run_lookup = k[len("run__"):]
            run_ids = list(TestRun.objects.filter(**{run_lookup: v}).values_list("pk", flat=True))
            resolved["run_id__in"] = run_ids

        elif k.startswith("build__version"):
            # TestExecution.build → Build.version: two-hop FK
            if k == "build__version__in":
                version_ids = list(v) if isinstance(v, (list, tuple)) else [v]
            else:
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
            # TestExecution.build → Build: one-hop FK
            build_lookup = k[len("build__"):]
            build_ids = list(Build.objects.filter(**{build_lookup: v}).values_list("pk", flat=True))
            resolved["build_id__in"] = build_ids

        else:
            resolved[k] = v

    return resolved


@http_basic_auth_login_required
@rpc_method(name="Testing.breakdown")
def breakdown(query=None):
    """
    .. function:: RPC Testing.breakdown(query)

        Perform a search and return the statistics for the selected test cases

        :param query: Field lookups for :class:`tcms.testcases.models.TestCase`
        :type query: dict
        :return: Object, containing the statistics for the selected test cases
        :rtype: dict
    """
    if query is None:
        query = {}

    from django.conf import settings
    if getattr(settings, 'USE_FIRESTORE_DAOS', False):
        from tcms.dao.firestore.testcases.test_case_dao import _resolve_testcase_query
        query = _resolve_testcase_query(query)

    test_cases = list(TestCase.objects.filter(**query))

    manual_count = sum(1 for tc in test_cases if not tc.is_automated)
    automated_count = sum(1 for tc in test_cases if tc.is_automated)
    count = {
        "manual": manual_count,
        "automated": automated_count,
        "all": manual_count + automated_count,
    }

    priorities = _get_field_count_map(test_cases, "priority")
    categories = _get_field_count_map(test_cases, "category")

    return {
        "count": count,
        "priorities": priorities,
        "categories": categories,
    }


def _get_field_count_map(test_cases, field_type):
    """
    Count test cases by priority or category, split by confirmed/unconfirmed status.
    Avoids cross-collection FK traversal by pre-loading related objects.
    """
    confirmed_ids = set(
        TestCaseStatus.objects.filter(is_confirmed=True).values_list("pk", flat=True)
    )

    if field_type == "priority":
        related_map = {p.pk: p.value for p in Priority.objects.all()}
        get_val = lambda tc: related_map.get(tc.priority_id)
    else:
        related_map = {c.pk: c.name for c in Category.objects.all()}
        get_val = lambda tc: related_map.get(tc.category_id)

    confirmed_counts = {}
    other_counts = {}
    for tc in test_cases:
        val = get_val(tc)
        if tc.case_status_id in confirmed_ids:
            confirmed_counts[val] = confirmed_counts.get(val, 0) + 1
        else:
            other_counts[val] = other_counts.get(val, 0) + 1

    return {
        str(_("CONFIRMED")): confirmed_counts,
        str(_("OTHER")): other_counts,
    }


@http_basic_auth_login_required
@rpc_method(name="Testing.status_matrix")
def status_matrix(query=None):
    """
    .. function:: RPC Testing.status_matrix(query)

        Perform a search and return data_set needed to visualize the status matrix
        of test plans, test cases and test executions

        :param query: Field lookups for :class:`tcms.testcases.models.TestPlan`
        :type query: dict
        :return: A dictionary, containing the information about test executions
        :rtype: dict
    """
    if query is None:
        query = {}

    from django.conf import settings
    if getattr(settings, 'USE_FIRESTORE_DAOS', False):
        query = _resolve_execution_query(query)

    executions = list(TestExecution.objects.filter(**query))

    # Collect unique IDs — guard against Firestore data-corruption (string FK ids)
    case_ids = list({e.case_id for e in executions if isinstance(e.case_id, int)})
    run_ids = list({e.run_id for e in executions if isinstance(e.run_id, int)})

    # Batch fetch related objects
    from tcms.testcases.models import TestCase as TC
    from tcms.testruns.models import TestRun as TR
    case_summary_map = {tc.pk: tc.summary for tc in chunked_queryset(TC, "pk", case_ids)}
    run_map = {r.pk: r for r in chunked_queryset(TR, "pk", run_ids)}

    # Build test_cases list (unique, sorted by case_id)
    test_cases = sorted(
        [{"case_id": cid, "case__summary": case_summary_map.get(cid)} for cid in case_ids],
        key=lambda x: x["case_id"],
    )

    # Build executions dict keyed by "case_id-run_id" — skip corrupted FK rows
    test_executions = {}
    for e in executions:
        if not (isinstance(e.case_id, int) and isinstance(e.run_id, int)):
            continue
        key = f"{e.case_id}-{e.run_id}"
        test_executions[key] = {
            "pk": e.pk,
            "case_id": e.case_id,
            "run_id": e.run_id,
            "status_id": e.status_id,
            "key": key,
        }

    test_runs = {r_id: run_map[r_id].summary for r_id in run_ids if r_id in run_map}
    test_plans = {r_id: run_map[r_id].plan_id for r_id in run_ids if r_id in run_map}

    status_colors = dict(TestExecutionStatus.objects.values_list("pk", "color"))

    return {
        "cases": test_cases,
        "executions": test_executions,
        "plans": test_plans,
        "runs": test_runs,
        "statusColors": status_colors,
    }


@http_basic_auth_login_required
@rpc_method(name="Testing.execution_trends")
def execution_trends(query=None):
    if query is None:
        query = {}

    data_set = {}
    categories = []
    colors = []
    counts = {}

    for status in TestExecutionStatus.objects.all():
        data_set[status.name] = []
        colors.append(status.color)
    data_set[str(_("TOTAL"))] = []
    colors.append("black")

    # Pre-load status map to avoid N+1 lookups (select_related is ignored by gcloudc)
    status_map = {s.pk: s for s in TestExecutionStatus.objects.all()}

    status_count = {
        "positive": 0,
        "negative": 0,
        "neutral": 0,
    }
    run_id = 0
    from django.conf import settings
    if getattr(settings, 'USE_FIRESTORE_DAOS', False):
        query = _resolve_execution_query(query)

    for test_execution in TestExecution.objects.filter(**query).order_by("run_id"):
        # Guard against Firestore data-corruption (string FK ids)
        if not isinstance(test_execution.run_id, int):
            continue
        status = status_map.get(test_execution.status_id)
        if status is None:
            continue

        if status.weight > 0:
            status_count["positive"] += 1
        elif status.weight < 0:
            status_count["negative"] += 1
        else:
            status_count["neutral"] += 1

        if test_execution.run_id == run_id:
            if status.name in counts:
                counts[status.name] += 1
            else:
                counts[status.name] = 1
        else:
            _append_status_counts_to_result(counts, data_set)
            counts = {status.name: 1}
            run_id = test_execution.run_id
            categories.append(run_id)

    _append_status_counts_to_result(counts, data_set)

    for _key, value in data_set.items():
        del value[0]

    return {
        "categories": categories,
        "data_set": data_set,
        "colors": colors,
        "status_count": status_count,
    }


def _append_status_counts_to_result(counts, result):
    total = 0
    for status_name in filter(lambda x: x != _("TOTAL"), result.keys()):
        status_count = counts.get(status_name, 0)
        result.get(status_name).append(status_count)
        total += status_count
    result.get(str(_("TOTAL"))).append(total)


@http_basic_auth_login_required
@rpc_method(name="Testing.test_case_health")
def test_case_health(query=None):
    if query is None:
        query = {}

    from django.conf import settings
    if getattr(settings, 'USE_FIRESTORE_DAOS', False):
        query = _resolve_execution_query(query)

    all_executions = list(TestExecution.objects.filter(**query))

    # Pre-load weights and case summaries — avoids cross-collection filter/annotation
    status_weight_map = {s.pk: s.weight for s in TestExecutionStatus.objects.all()}
    # Guard against Firestore data-corruption (string FK ids)
    case_ids = list({e.case_id for e in all_executions if isinstance(e.case_id, int)})
    case_summary_map = {tc.pk: tc.summary for tc in chunked_queryset(TestCase, "pk", case_ids)}

    data = {}
    for e in all_executions:
        if not isinstance(e.case_id, int):  # skip corrupted FK rows
            continue
        if e.case_id not in data:
            data[e.case_id] = {
                "case_id": e.case_id,
                "case_summary": case_summary_map.get(e.case_id),
                "count": {"all": 0, "fail": 0},
            }
        data[e.case_id]["count"]["all"] += 1
        if status_weight_map.get(e.status_id, 0) < 0:
            data[e.case_id]["count"]["fail"] += 1

    _remove_all_excellent_executions(data)

    data = list(data.values())
    data.sort(key=_sort_by_failing_rate, reverse=True)

    if len(data) > 30:
        data = data[:30]

    return data


@http_basic_auth_login_required
@rpc_method(name="Testing.individual_test_case_health")
def individual_test_case_health_simple(query=None):
    if query is None:
        query = {}

    from django.conf import settings
    if getattr(settings, 'USE_FIRESTORE_DAOS', False):
        query = _resolve_execution_query(query)

    executions = list(TestExecution.objects.filter(**query))

    # Guard against Firestore data-corruption (string FK ids)
    run_ids = list({e.run_id for e in executions if isinstance(e.run_id, int)})
    run_plan_map = {r.pk: r.plan_id for r in chunked_queryset(TestRun, "pk", run_ids)}

    status_map = {s.pk: s for s in TestExecutionStatus.objects.all()}

    res = []
    for e in executions:
        if not (isinstance(e.case_id, int) and isinstance(e.run_id, int)):
            continue  # skip corrupted FK rows
        status = status_map.get(e.status_id)
        res.append({
            "run__plan": run_plan_map.get(e.run_id),
            "case_id": e.case_id,
            "status__name": status.name if status else None,
            "status__weight": status.weight if status else None,
        })

    res.sort(key=lambda x: (
        x["case_id"] or 0,
        x["run__plan"] or 0,
        x["status__weight"] or 0,
    ))
    return res


def _remove_all_excellent_executions(data):
    for key in list(data.keys()):
        if data[key]["count"]["fail"] == 0:
            data.pop(key)


def _count_test_executions(data, test_executions, status):
    for value in test_executions:
        data[value["case_id"]]["count"][status] = value["count"]


def _sort_by_failing_rate(element):
    return element["count"]["fail"] / element["count"]["all"]
