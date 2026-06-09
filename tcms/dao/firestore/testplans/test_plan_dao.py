from django.contrib.auth import get_user_model
from django.forms.models import model_to_dict

from tcms.dao.firestore.utils import (
    chunked_queryset, chunked_values, ensure_safe_json_integers,
    generate_safe_pk, int_pk_only, resolve_ids_by_lookup,
    resolve_string_field_ids, resolve_user_ids, _STRING_OPS,
)
from tcms.management.models import Product, Version
from tcms.testcases.models import TestCase, TestCasePlan
from tcms.testplans.models import PlanType, TestPlan

_TEST_PLAN_FIELDS = (
    "id",
    "name",
    "text",
    "create_date",
    "is_active",
    "extra_link",
    "product_version",
    "product",
    "author",
    "type",
    "parent",
)

_FK_FIELDS = {"product_version", "product", "author", "type", "parent"}


def _plan_to_dict(plan, versions, products, authors, types, children_counts):
    """Build a plan dict from a TestPlan instance using pre-fetched related maps."""
    d = {}
    for field in _TEST_PLAN_FIELDS:
        if field in _FK_FIELDS:
            d[field] = getattr(plan, f"{field}_id")
        else:
            d[field] = getattr(plan, field)
    d["product_version__value"] = versions.get(plan.product_version_id)
    d["product__name"] = products.get(plan.product_id)
    d["author__username"] = authors.get(plan.author_id)
    d["type__name"] = types.get(plan.type_id)
    d["children__count"] = children_counts.get(plan.pk, 0)
    return d


def _fetch_related_maps(plans):
    """Batch-fetch all related objects needed for plan dicts."""
    User = get_user_model()
    version_ids = list({p.product_version_id for p in plans if p.product_version_id and isinstance(p.product_version_id, int)})
    product_ids = list({p.product_id for p in plans if p.product_id and isinstance(p.product_id, int)})
    author_ids = list({p.author_id for p in plans if p.author_id and isinstance(p.author_id, int)})
    type_ids = list({p.type_id for p in plans if p.type_id and isinstance(p.type_id, int)})
    plan_ids = [p.pk for p in plans]

    versions = {v.pk: v.value for v in chunked_queryset(Version, "pk", version_ids)}
    products = {pr.pk: pr.name for pr in chunked_queryset(Product, "pk", product_ids)}
    authors = {u.pk: u.username for u in chunked_queryset(User, "pk", author_ids)}
    types = {t.pk: t.name for t in chunked_queryset(PlanType, "pk", type_ids)}

    children_counts = {}
    for row in chunked_values(TestPlan, "parent_id", plan_ids, "parent_id"):
        pid = row["parent_id"]
        children_counts[pid] = children_counts.get(pid, 0) + 1

    return versions, products, authors, types, children_counts


_CHUNK = 90
_IN_SUFFIXES = ("__in",)


def _resolve_plan_query(query):
    """
    Pre-resolve cross-collection traversals in a TestPlan filter query.
    Returns (resolved_query, plan_id_constraint_sets).
    Take the intersection of plan_id_constraint_sets when building pk__in.
    """
    from tcms.management.models import Tag
    from tcms.testplans.models import TestPlanTag

    User = get_user_model()
    plan_id_constraints = []
    resolved = {}

    for k, v in query.items():
        if k.startswith("author__"):
            user_lookup = k[len("author__"):]
            user_ids = resolve_user_ids(user_lookup, v)
            resolved["author_id__in"] = user_ids

        elif k.startswith("tag__"):
            tag_lookup = k[len("tag__"):]
            # resolve_ids_by_lookup handles string operators (name__icontains etc.) in Python
            tag_ids = resolve_ids_by_lookup(Tag, tag_lookup, v)
            pids = set()
            for i in range(0, len(tag_ids), _CHUNK):
                pids.update(
                    TestPlanTag.objects.filter(tag_id__in=tag_ids[i:i + _CHUNK])
                    .values_list("plan_id", flat=True)
                )
            plan_id_constraints.append(pids)

        elif k.startswith("cases__"):
            # cases is M2M reverse, then sub-lookup on TestCase
            # Must decompose FK traversals within the TestCase sub-query too
            sub_key = k[len("cases__"):]
            if sub_key.startswith("default_tester__") or sub_key.startswith("author__"):
                # User FK traversal inside TestCase
                prefix = "default_tester__" if sub_key.startswith("default_tester__") else "author__"
                User = get_user_model()
                user_lookup = sub_key[len(prefix):]
                user_ids = resolve_user_ids(user_lookup, v)
                tc_field = prefix[:-2] + "_id__in"  # e.g. "default_tester_id__in"
                case_ids = list(TestCase.objects.filter(**{tc_field: user_ids}).values_list("pk", flat=True))
            else:
                # resolve_ids_by_lookup handles string operators (summary__icontains etc.) in Python
                case_ids = resolve_ids_by_lookup(TestCase, sub_key, v)
            pids = set()
            for i in range(0, len(case_ids), _CHUNK):
                pids.update(
                    TestCasePlan.objects.filter(case_id__in=case_ids[i:i + _CHUNK])
                    .values_list("plan_id", flat=True)
                )
            plan_id_constraints.append(pids)

        elif k in ("cases", "cases__in"):
            case_val = v
            case_ids = list(case_val) if isinstance(case_val, (list, tuple)) else [case_val]
            pids = set()
            for i in range(0, len(case_ids), _CHUNK):
                pids.update(
                    TestCasePlan.objects.filter(case_id__in=case_ids[i:i + _CHUNK])
                    .values_list("plan_id", flat=True)
                )
            plan_id_constraints.append(pids)

        elif k == "product__in":
            resolved["product_id__in"] = list(v) if isinstance(v, (list, tuple)) else [v]

        elif k == "product":
            resolved["product_id"] = v

        elif k == "parent__in":
            resolved["parent_id__in"] = list(v) if isinstance(v, (list, tuple)) else [v]

        elif k == "parent":
            resolved["parent_id"] = v

        else:
            # Detect string operators on TestPlan text fields and filter in
            # Python to bypass gcloudc's special-index mechanism.
            _TESTPLAN_TEXT_FIELDS = frozenset({'name', 'text', 'extra_link'})
            if '__' in k:
                field, op = k.rsplit('__', 1)
                if field in _TESTPLAN_TEXT_FIELDS and op in _STRING_OPS:
                    matched_ids = resolve_string_field_ids(TestPlan, field, op, v)
                    plan_id_constraints.append(set(matched_ids))
                    continue
            resolved[k] = v

    if plan_id_constraints:
        final_ids = plan_id_constraints[0]
        for s in plan_id_constraints[1:]:
            final_ids = final_ids & s
        existing = resolved.get("pk__in")
        if existing is not None:
            resolved["pk__in"] = list(set(existing) & final_ids)
        else:
            resolved["pk__in"] = list(final_ids)

    return resolved


def _chunked_plan_filter(query):
    """
    Execute TestPlan.objects.filter(**query) in chunks when the query contains
    large __in lists that would exceed the gcloudc 100-subquery limit.
    Pre-resolves cross-collection traversals before querying.
    Returns a sorted-by-id list of TestPlan instances.
    """
    query = _resolve_plan_query(query)

    if "pk__in" in query and not query["pk__in"]:
        return []

    # Handle large __in lists
    in_key = next(
        (k for k in query if any(k.endswith(s) for s in _IN_SUFFIXES) and isinstance(query[k], (list, tuple))),
        None,
    )
    if in_key is not None and len(query[in_key]) > _CHUNK:
        ids = list(query[in_key])
        remaining = {k: v for k, v in query.items() if k != in_key}
        seen = {}
        for i in range(0, len(ids), _CHUNK):
            chunk = ids[i:i + _CHUNK]
            for plan in TestPlan.objects.filter(**{in_key: chunk}, **remaining).order_by():
                seen[plan.pk] = plan
        return sorted(seen.values(), key=lambda p: p.pk)
    # order_by() clears Meta.ordering=["name"] — any explicit ordering combined
    # with a filter field requires a composite index in Firestore. Sort in Python.
    return sorted(
        TestPlan.objects.filter(**query).order_by(),
        key=lambda p: p.pk,
    )


class TestPlanDAO:
    def filter(self, query):
        """
        Return a list of test plan dicts matching query.
        Used by the TestPlan.filter RPC endpoint.
        """
        plans = int_pk_only(list(_chunked_plan_filter(query)))
        versions, products, authors, types, children_counts = _fetch_related_maps(plans)
        result = [
            _plan_to_dict(p, versions, products, authors, types, children_counts)
            for p in plans
        ]
        return [ensure_safe_json_integers(d) for d in result]

    def filter_objects(self, **kwargs):
        """
        Return a TestPlan queryset for use in views and templates.
        """
        return TestPlan.objects.filter(**kwargs)

    def get_by_id(self, plan_id):
        """Return a single TestPlan object by primary key."""
        return TestPlan.objects.get(pk=plan_id)

    def save(self, plan, update_fields=None):
        """Persist a TestPlan object."""
        if plan.pk is None:
            plan.pk = generate_safe_pk(TestPlan)
        if update_fields:
            plan.save(update_fields=update_fields)
        else:
            plan.save()
        return plan

    def add_case(self, plan, case):
        """Link a test case to the given test plan."""
        # Avoid plan.add_case(case) which does order_by("-sortkey") — requires a
        # composite index on testcases_testcaseplan(plan_id, sortkey). Instead,
        # fetch all sortkeys unordered and compute the next value in Python.
        sortkeys = list(
            TestCasePlan.objects.filter(plan_id=plan.pk).values_list("sortkey", flat=True)
        )
        valid = [s for s in sortkeys if s is not None]
        next_sortkey = (max(valid) + 10) if valid else 0

        test_case_plan, _ = TestCasePlan.objects.get_or_create(
            plan=plan,
            case=case,
            defaults={"sortkey": next_sortkey},
        )
        result = model_to_dict(case, exclude=["component", "plan", "tag"])
        result["create_date"] = case.create_date
        result["sortkey"] = test_case_plan.sortkey
        return result

    def remove_case(self, plan_id, case_id):
        """Unlink a test case from the given test plan."""
        TestCasePlan.objects.filter(case=case_id, plan=plan_id).delete()

    def update_case_order(self, plan_id, case_id, sortkey):
        """Update display order of a test case within a test plan."""
        TestCasePlan.objects.filter(  # pylint:disable=objects-update-used
            case=case_id, plan=plan_id
        ).update(sortkey=sortkey)

    def tree(self, plan):
        """Return the DFS-ordered ancestry tree for the given test plan."""
        result = []
        for record in plan.tree_as_list():
            result.append(
                ensure_safe_json_integers({
                    "id": record.pk,
                    "name": record.name,
                    "parent_id": record.parent_id,
                    "tree_depth": record.tree_depth,
                    "url": record.get_full_url(),
                })
            )
        return result


test_plan_dao = TestPlanDAO()
