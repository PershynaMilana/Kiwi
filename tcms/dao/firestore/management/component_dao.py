from tcms.management.models import Component
from tcms.testcases.models import TestCaseComponent
from tcms.dao.firestore.utils import resolve_ids_by_lookup, _STRING_OPS

_COMPONENT_FIELDS = (
    "id",
    "name",
    "product",
    "initial_owner",
    "initial_qa_contact",
    "description",
)

_CHUNK = 90


def _component_to_row(comp, cases_value=None):
    """Build a component dict from an ORM object. FK fields become _id integers."""
    d = {field: getattr(comp, field) for field in _COMPONENT_FIELDS}
    d["product"] = comp.product_id
    d["initial_owner"] = comp.initial_owner_id
    d["initial_qa_contact"] = comp.initial_qa_contact_id
    d["cases"] = cases_value
    return d


class ComponentDAO:
    # ------------------------------------------------------------------
    # READ operations
    # ------------------------------------------------------------------

    def _resolve_case_ids(self, key, val):
        """
        Resolve a cases__* key to a list of TestCase IDs.
        Returns None if the key is not a cases traversal.
        """
        from tcms.testruns.models import TestExecution

        if key in ("cases", "cases__in"):
            return list(val) if isinstance(val, (list, tuple)) else [val]

        if key.startswith("cases__executions__"):
            sub_key = key[len("cases__executions__"):]
            # Filter TestExecution by the sub-key (e.g. run=run_id)
            return list(
                TestExecution.objects.filter(**{sub_key: val}).values_list("case_id", flat=True)
            )

        if key == "cases__executions":
            # Direct execution ID filter
            ids = list(val) if isinstance(val, (list, tuple)) else [val]
            return list(
                TestExecution.objects.filter(pk__in=ids).values_list("case_id", flat=True)
            )

        return None

    def filter(self, query):
        """
        Return a list of component dicts matching query.
        Used by the Component.filter RPC endpoint.
        """
        # Intercept M2M reverse traversal: Component.cases → TestCase (no JOINs in Firestore)
        cases_key = next((k for k in query if k.startswith("cases") or k == "cases"), None)
        case_ids = None
        if cases_key is not None:
            case_ids = self._resolve_case_ids(cases_key, query[cases_key])

        if case_ids is not None:
            remaining_query = {k: v for k, v in query.items() if k != cases_key}

            junction_rows = []
            for i in range(0, len(case_ids), _CHUNK):
                chunk = case_ids[i:i + _CHUNK]
                junction_rows.extend(
                    TestCaseComponent.objects.filter(case_id__in=chunk)
                    .values("case_id", "component_id")
                )
            if not junction_rows:
                return []

            component_ids = list({row["component_id"] for row in junction_rows})
            components = {}
            for i in range(0, len(component_ids), _CHUNK):
                chunk = component_ids[i:i + _CHUNK]
                for c in Component.objects.filter(pk__in=chunk, **remaining_query):
                    components[c.pk] = c

            result = []
            seen = set()
            for row in sorted(junction_rows, key=lambda r: (r["component_id"], r["case_id"])):
                comp = components.get(row["component_id"])
                if comp is None:
                    continue
                pair = (row["case_id"], comp.pk)
                if pair in seen:
                    continue
                seen.add(pair)
                result.append(_component_to_row(comp, cases_value=row["case_id"]))
        else:
            # Simple query — no M2M traversal; return each component once with cases=None.
            # Resolve string operators (name__icontains etc.) in Python to bypass gcloudc.
            str_op_keys = [k for k in query if '__' in k and k.rsplit('__', 1)[1] in _STRING_OPS]
            if str_op_keys:
                remaining = {k: v for k, v in query.items() if k not in str_op_keys}
                matching_pks = None
                for sk in str_op_keys:
                    pks = set(resolve_ids_by_lookup(Component, sk, query[sk]))
                    matching_pks = pks if matching_pks is None else matching_pks & pks
                remaining["pk__in"] = list(matching_pks or set())
                comps = Component.objects.filter(**remaining).order_by("id") if remaining["pk__in"] else []
            else:
                comps = Component.objects.filter(**query).order_by("id")
            result = [_component_to_row(c) for c in comps]

        return result

    def filter_objects(self, **kwargs):
        """
        Return a Component queryset for use in views and templates.
        """
        return Component.objects.filter(**kwargs)

    def get_by_id(self, component_id):
        """
        Return a single Component object by primary key.
        """
        return Component.objects.get(pk=component_id)

    def get_by_name_and_product(self, name, product):
        """
        Return a single Component object by name and product.
        Used by TestCase.add_component RPC endpoint.
        """
        return Component.objects.get(name=name, product=product)

    # ------------------------------------------------------------------
    # WRITE operations
    # ------------------------------------------------------------------

    def save(self, component, update_fields=None):
        """
        Persist a Component object.
        Used by Component.create and Component.update RPC endpoints.
        """
        if update_fields:
            component.save(update_fields=update_fields)
        else:
            component.save()
        return component


component_dao = ComponentDAO()
