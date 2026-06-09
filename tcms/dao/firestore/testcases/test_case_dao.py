from datetime import timedelta


def _to_timedelta(val):
    """Coerce a Firestore-deserialized duration value to timedelta, handling strings."""
    if val is None:
        return timedelta(0)
    if isinstance(val, timedelta):
        return val
    if isinstance(val, (int, float)):
        return timedelta(microseconds=val)
    if isinstance(val, str):
        # stored as microsecond integer string or "H:MM:SS[.ffffff]"
        try:
            return timedelta(microseconds=int(val))
        except ValueError:
            pass
        import re
        m = re.match(r'(-?)(\d+):(\d{2}):(\d{2})(?:\.(\d+))?$', val)
        if m:
            sign = -1 if m.group(1) else 1
            h, mn, s = int(m.group(2)), int(m.group(3)), int(m.group(4))
            us = int(m.group(5).ljust(6, '0')[:6]) if m.group(5) else 0
            return sign * timedelta(hours=h, minutes=mn, seconds=s, microseconds=us)
    return timedelta(0)

from django.contrib.auth import get_user_model
from django.forms.models import model_to_dict

from tcms.dao.firestore.utils import (
    chunked_queryset, ensure_safe_json_integers,
    generate_safe_pk, int_pk_only, resolve_ids_by_lookup,
    resolve_string_field_ids, resolve_user_ids, _STRING_OPS,
)
from tcms.management.models import Component, Priority, Tag
from tcms.testcases.models import Category, TestCase, TestCasePlan, TestCaseStatus
from tcms.testcases.models import TestCaseComponent, TestCaseTag

_CHUNK = 90

# TestCase text fields that use gcloudc's special-index mechanism for string
# operators (icontains, startswith, …).  Pre-existing Firestore documents don't
# have the computed index fields, so we must filter these in Python.
_TESTCASE_TEXT_FIELDS = frozenset({
    'summary', 'notes', 'script', 'requirement',
    'extra_link', 'arguments', 'text',
})


def _resolve_testcase_query(query):
    """
    Pre-resolve cross-collection traversals in a TestCase filter query into direct-field filters.
    Handles M2M fields (plan, component, tag) and FK traversals (author, case_status, category).
    Returns a (resolved_query, case_id_constraint_sets) tuple.
    case_id_constraints is a list of sets; take their intersection when building the pk__in filter.
    """
    from tcms.testruns.models import TestExecution, TestRun

    User = get_user_model()
    case_id_constraints = []
    resolved = {}

    for k, v in query.items():
        # TestCase.plan M2M traversal (through TestCasePlan)
        if k in ("plan", "plan__in"):
            plan_ids = list(v) if isinstance(v, (list, tuple)) else [v]
            cids = set()
            for i in range(0, len(plan_ids), _CHUNK):
                cids.update(
                    TestCasePlan.objects.filter(plan_id__in=plan_ids[i:i + _CHUNK])
                    .values_list("case_id", flat=True)
                )
            case_id_constraints.append(cids)

        # TestCase.component M2M traversal (through TestCaseComponent)
        elif k in ("component", "component__in"):
            comp_ids = list(v) if isinstance(v, (list, tuple)) else [v]
            cids = set()
            for i in range(0, len(comp_ids), _CHUNK):
                cids.update(
                    TestCaseComponent.objects.filter(component_id__in=comp_ids[i:i + _CHUNK])
                    .values_list("case_id", flat=True)
                )
            case_id_constraints.append(cids)

        elif k.startswith("component__"):
            comp_lookup = k[len("component__"):]
            comp_ids = resolve_ids_by_lookup(Component, comp_lookup, v)
            cids = set()
            for i in range(0, len(comp_ids), _CHUNK):
                cids.update(
                    TestCaseComponent.objects.filter(component_id__in=comp_ids[i:i + _CHUNK])
                    .values_list("case_id", flat=True)
                )
            case_id_constraints.append(cids)

        # TestCase.tag M2M traversal (through TestCaseTag)
        elif k.startswith("tag__"):
            tag_lookup = k[len("tag__"):]
            tag_ids = resolve_ids_by_lookup(Tag, tag_lookup, v)
            cids = set()
            for i in range(0, len(tag_ids), _CHUNK):
                cids.update(
                    TestCaseTag.objects.filter(tag_id__in=tag_ids[i:i + _CHUNK])
                    .values_list("case_id", flat=True)
                )
            case_id_constraints.append(cids)

        # TestCase.executions reverse FK traversal (TestCase → TestExecution)
        elif k == "executions":
            ids = list(v) if isinstance(v, (list, tuple)) else [v]
            cids = set(
                TestExecution.objects.filter(pk__in=ids).values_list("case_id", flat=True)
            )
            case_id_constraints.append(cids)

        elif k.startswith("executions__"):
            sub_key = k[len("executions__"):]
            if sub_key.startswith("run__"):
                run_sub = sub_key[len("run__"):]
                _TESTRUN_TEXT = frozenset({'summary', 'notes'})
                if run_sub == "in":
                    run_ids = list(v) if isinstance(v, (list, tuple)) else [v]
                elif '__' in run_sub:
                    run_field, run_op = run_sub.rsplit('__', 1)
                    if run_field in _TESTRUN_TEXT and run_op in _STRING_OPS:
                        run_ids = resolve_string_field_ids(TestRun, run_field, run_op, v)
                    else:
                        run_ids = list(TestRun.objects.filter(**{run_sub: v}).values_list("pk", flat=True))
                else:
                    run_ids = list(TestRun.objects.filter(**{run_sub: v}).values_list("pk", flat=True))
                cids = set()
                for i in range(0, len(run_ids), _CHUNK):
                    cids.update(
                        TestExecution.objects.filter(run_id__in=run_ids[i:i + _CHUNK])
                        .values_list("case_id", flat=True)
                    )
            else:
                cids = set(
                    TestExecution.objects.filter(**{sub_key: v})
                    .values_list("case_id", flat=True)
                )
            case_id_constraints.append(cids)

        # author FK traversal (TestCase.author → User)
        elif k.startswith("author__"):
            user_ids = resolve_user_ids(k[len("author__"):], v)
            resolved["author_id__in"] = user_ids

        # default_tester FK traversal
        elif k.startswith("default_tester__"):
            user_ids = resolve_user_ids(k[len("default_tester__"):], v)
            resolved["default_tester_id__in"] = user_ids

        # case_status FK traversal (e.g. case_status__is_confirmed)
        # but case_status__in=[id1, id2] is a direct FK ID filter, not a traversal
        elif k == "case_status__in":
            resolved["case_status_id__in"] = v

        elif k.startswith("case_status__"):
            status_ids = list(
                TestCaseStatus.objects.filter(**{k[len("case_status__"):]: v})
                .values_list("pk", flat=True)
            )
            resolved["case_status_id__in"] = status_ids

        # category FK traversal
        elif k.startswith("category__"):
            cat_ids = list(Category.objects.filter(**{k[len("category__"):]: v}).values_list("pk", flat=True))
            resolved["category_id__in"] = cat_ids

        else:
            # Detect string operators on text fields and filter in Python to
            # bypass gcloudc's special-index mechanism (pre-existing documents
            # don't have the computed _idx_icontains_* fields).
            if '__' in k:
                field, op = k.rsplit('__', 1)
                if field in _TESTCASE_TEXT_FIELDS and op in _STRING_OPS:
                    matched_ids = resolve_string_field_ids(TestCase, field, op, v)
                    case_id_constraints.append(set(matched_ids))
                    continue
            resolved[k] = v

    if case_id_constraints:
        final_ids = case_id_constraints[0]
        for s in case_id_constraints[1:]:
            final_ids = final_ids & s
        resolved["pk__in"] = list(final_ids)

    return resolved

_TEST_CASE_FIELDS = (
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
    "setup_duration",
    "testing_duration",
)

_FK_FIELDS = {"case_status", "category", "priority", "author", "default_tester", "reviewer"}


def _fetch_case_related_maps(cases):
    """Batch-fetch all related objects needed for test case dicts."""
    User = get_user_model()
    # Guard against Firestore data corruption where FK id fields are stored as
    # the field-name string (e.g. 'case_status_id') instead of an integer.
    status_ids = list({c.case_status_id for c in cases if c.case_status_id and isinstance(c.case_status_id, int)})
    category_ids = list({c.category_id for c in cases if c.category_id and isinstance(c.category_id, int)})
    priority_ids = list({c.priority_id for c in cases if c.priority_id and isinstance(c.priority_id, int)})
    user_ids = set()
    for c in cases:
        for uid in (c.author_id, c.default_tester_id, c.reviewer_id):
            if uid and isinstance(uid, int):
                user_ids.add(uid)

    statuses = {s.pk: s.name for s in chunked_queryset(TestCaseStatus, "pk", status_ids)}
    categories = {cat.pk: cat.name for cat in chunked_queryset(Category, "pk", category_ids)}
    priorities = {p.pk: p.value for p in chunked_queryset(Priority, "pk", priority_ids)}
    users = {u.pk: u.username for u in chunked_queryset(User, "pk", list(user_ids))}

    return statuses, categories, priorities, users


def _case_to_dict(case, statuses, categories, priorities, users):
    """Build a case dict from a TestCase instance using pre-fetched related maps."""
    d = {}
    for field in _TEST_CASE_FIELDS:
        if field in _FK_FIELDS:
            d[field] = getattr(case, f"{field}_id")
        else:
            d[field] = getattr(case, field)
    d["expected_duration"] = _to_timedelta(case.setup_duration) + _to_timedelta(case.testing_duration)
    d["case_status__name"] = statuses.get(case.case_status_id)
    d["category__name"] = categories.get(case.category_id)
    d["priority__value"] = priorities.get(case.priority_id)
    d["author__username"] = users.get(case.author_id)
    d["default_tester__username"] = users.get(case.default_tester_id)
    d["reviewer__username"] = users.get(case.reviewer_id)
    return d


class TestCaseDAO:
    def filter(self, query):
        """
        Return a list of test case dicts matching query.
        Used by the TestCase.filter RPC endpoint.
        """
        resolved = _resolve_testcase_query(query)

        if "pk__in" in resolved and not resolved["pk__in"]:
            return []

        case_ids = resolved.pop("pk__in", None)
        if case_ids is not None:
            cases = []
            for i in range(0, len(case_ids), _CHUNK):
                cases.extend(TestCase.objects.filter(pk__in=case_ids[i:i + _CHUNK], **resolved))
            cases.sort(key=lambda c: c.pk)
        else:
            cases = list(TestCase.objects.filter(**resolved).order_by("id"))

        cases = int_pk_only(cases)
        statuses, categories, priorities, users = _fetch_case_related_maps(cases)
        result = [_case_to_dict(c, statuses, categories, priorities, users) for c in cases]
        return [ensure_safe_json_integers(d) for d in result]

    def filter_objects(self, **kwargs):
        """Return a TestCase queryset for use in views and templates."""
        return TestCase.objects.filter(**kwargs)

    def get_by_id(self, case_id):
        """Return a single TestCase object by primary key."""
        return TestCase.objects.get(pk=case_id)

    def history(self, case, query):
        """Return history records for the given test case."""
        return list(case.history.filter(**query).values())

    def sortkeys(self, query):
        """Return {str(case_id): sortkey} mapping for TestCasePlan records."""
        result = {}
        for record in TestCasePlan.objects.filter(**query):
            result[str(record.case_id)] = record.sortkey
        return result

    def get_notification_cc(self, case):
        """Return notification CC list for the given test case."""
        return case.emailing.get_cc_list()

    def save(self, case, update_fields=None):
        """Persist a TestCase object."""
        if case.pk is None:
            case.pk = generate_safe_pk(TestCase)
        if update_fields:
            case.save(update_fields=update_fields)
        else:
            case.save()
        return case

    def remove(self, query):
        """Delete TestCase objects matching query."""
        return TestCase.objects.filter(**query).delete()

    def add_component(self, case, component_obj):
        """Add a component to the given test case."""
        case.add_component(component_obj)
        return model_to_dict(component_obj)

    def remove_component(self, case, component_obj):
        """Remove a component from the given test case."""
        case.remove_component(component_obj)

    def add_notification_cc(self, case, cc_list):
        """Add emails to notification CC list for the given test case."""
        case.emailing.add_cc(cc_list)

    def remove_notification_cc(self, case, cc_list):
        """Remove emails from notification CC list for the given test case."""
        case.emailing.remove_cc(cc_list)


test_case_dao = TestCaseDAO()
