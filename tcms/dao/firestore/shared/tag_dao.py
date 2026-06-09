from tcms.management.models import Tag
from tcms.dao.firestore.utils import resolve_ids_by_lookup

_CHUNK = 90


def _query_junction(JunctionModel, entity_id_field, entity_ids):
    """Fetch (tag_id, entity_id) pairs from junction table in chunks."""
    # Normalise entity_ids: keep integers and coerce numeric strings to int.
    # JavaScript sends data-pk values as strings through JSON-RPC, and
    # Firestore data-corruption produces alphanumeric doc IDs we must skip.
    clean = []
    for eid in entity_ids:
        if isinstance(eid, int):
            clean.append(eid)
        elif isinstance(eid, str):
            try:
                clean.append(int(eid))
            except ValueError:
                pass
    entity_ids = clean
    rows = []
    for i in range(0, len(entity_ids), _CHUNK):
        chunk = entity_ids[i:i + _CHUNK]
        rows.extend(
            JunctionModel.objects.filter(**{f"{entity_id_field}__in": chunk})
            .values("tag_id", entity_id_field)
        )
    return rows


def _fetch_tags_by_ids(tag_ids, extra_query):
    """Fetch Tag objects in chunks, optionally with an extra filter."""
    tags = {}
    for i in range(0, len(tag_ids), _CHUNK):
        chunk = tag_ids[i:i + _CHUNK]
        for t in Tag.objects.filter(pk__in=chunk, **extra_query):
            tags[t.pk] = t
    return tags


class TagDAO:
    # ------------------------------------------------------------------
    # WRITE operations
    # ------------------------------------------------------------------

    def add_tag(self, model_obj, tag):
        """
        Add tag to a model object via the junction table directly.
        Avoids M2M .add() which can silently fail in gcloudc.
        """
        from tcms.testplans.models import TestPlan, TestPlanTag
        from tcms.testcases.models import TestCase, TestCaseTag
        from tcms.testruns.models import TestRun, TestRunTag

        if isinstance(model_obj, TestPlan):
            TestPlanTag.objects.get_or_create(plan_id=model_obj.pk, tag_id=tag.pk)
        elif isinstance(model_obj, TestCase):
            TestCaseTag.objects.get_or_create(case_id=model_obj.pk, tag_id=tag.pk)
        elif isinstance(model_obj, TestRun):
            TestRunTag.objects.get_or_create(run_id=model_obj.pk, tag_id=tag.pk)
        else:
            model_obj.add_tag(tag)

    def remove_tag(self, model_obj, tag):
        """
        Remove tag from a model object via the junction table directly.
        """
        from tcms.testplans.models import TestPlan, TestPlanTag
        from tcms.testcases.models import TestCase, TestCaseTag
        from tcms.testruns.models import TestRun, TestRunTag

        if isinstance(model_obj, TestPlan):
            TestPlanTag.objects.filter(plan_id=model_obj.pk, tag_id=tag.pk).delete()
        elif isinstance(model_obj, TestCase):
            TestCaseTag.objects.filter(case_id=model_obj.pk, tag_id=tag.pk).delete()
        elif isinstance(model_obj, TestRun):
            TestRunTag.objects.filter(run_id=model_obj.pk, tag_id=tag.pk).delete()
        else:
            model_obj.remove_tag(tag)

    # ------------------------------------------------------------------
    # READ operations
    # ------------------------------------------------------------------

    def get_tags(self, model_obj):
        """
        Get all tags for a model object.
        Returns list of {"id": ..., "name": ...} dicts.
        """
        return list(model_obj.tag.values("id", "name"))

    def filter(self, query, extra_fields=None):
        """
        Return a list of tag dicts matching query.
        Used by the Tag.filter RPC endpoint.
        """
        from tcms.testplans.models import TestPlanTag
        from tcms.testcases.models import TestCaseTag
        from tcms.testruns.models import TestExecution, TestRunTag
        from tcms.bugs.models import Bug

        _JUNCTION_MAP = {
            "plan__in": (TestPlanTag,       "plan_id", "plan"),
            "plan":     (TestPlanTag,       "plan_id", "plan"),
            "case__in": (TestCaseTag,       "case_id", "case"),
            "case":     (TestCaseTag,       "case_id", "case"),
            "run__in":  (TestRunTag,        "run_id",  "run"),
            "run":      (TestRunTag,        "run_id",  "run"),
            "bug__in":  (Bug.tags.through,  "bug_id",  "bug"),
            "bug":      (Bug.tags.through,  "bug_id",  "bug"),
            "bugs__in": (Bug.tags.through,  "bug_id",  "bug"),
            "bugs":     (Bug.tags.through,  "bug_id",  "bug"),
        }

        junction_key = next((k for k in _JUNCTION_MAP if k in query), None)

        # Handle case__executions__* traversals (Tag → TestCaseTag → TestCase → TestExecution)
        if junction_key is None:
            case_exec_key = next(
                (k for k in query if k == "case__executions" or k.startswith("case__executions__")),
                None,
            )
            if case_exec_key is not None:
                val = query[case_exec_key]
                if case_exec_key == "case__executions":
                    ids = list(val) if isinstance(val, (list, tuple)) else [val]
                    case_ids = list(TestExecution.objects.filter(pk__in=ids).values_list("case_id", flat=True))
                else:
                    sub_key = case_exec_key[len("case__executions__"):]
                    case_ids = list(
                        TestExecution.objects.filter(**{sub_key: val}).values_list("case_id", flat=True)
                    )
                remaining_query = {k: v for k, v in query.items() if k != case_exec_key}
                junction_rows = _query_junction(TestCaseTag, "case_id", case_ids)
                if not junction_rows:
                    return []
                tag_ids = list({row["tag_id"] for row in junction_rows})
                tags = _fetch_tags_by_ids(tag_ids, remaining_query)
                result = []
                seen = set()
                for row in junction_rows:
                    tag = tags.get(row["tag_id"])
                    if tag is None:
                        continue
                    k = (row["tag_id"], row["case_id"])
                    if k in seen:
                        continue
                    seen.add(k)
                    result.append({"id": tag.pk, "name": tag.name, "case": row["case_id"]})
                return result

        if junction_key:
            JunctionModel, entity_id_field, entity_field_name = _JUNCTION_MAP[junction_key]
            entity_val = query[junction_key]
            remaining_query = {k: v for k, v in query.items() if k != junction_key}

            entity_ids = list(entity_val) if isinstance(entity_val, (list, tuple)) else [entity_val]

            junction_rows = _query_junction(JunctionModel, entity_id_field, entity_ids)
            if not junction_rows:
                return []

            tag_ids = list({row["tag_id"] for row in junction_rows})
            tags = _fetch_tags_by_ids(tag_ids, remaining_query)

            result = []
            seen = set()
            for row in junction_rows:
                tag = tags.get(row["tag_id"])
                if tag is None:
                    continue
                key = (row["tag_id"], row[entity_id_field])
                if key in seen:
                    continue
                seen.add(key)
                result.append({"id": tag.pk, "name": tag.name, entity_field_name: row[entity_id_field]})
            return result

        # Simple direct query — no M2M reverse relation filter.
        # Intercept any string operator (name__icontains etc.) and resolve in Python
        # to bypass gcloudc's special-index mechanism.
        str_op_keys = [k for k in query if '__' in k and k.rsplit('__', 1)[1] in
                       {'startswith', 'istartswith', 'icontains', 'contains', 'iexact', 'endswith', 'iendswith'}]
        if str_op_keys:
            remaining = {k: v for k, v in query.items() if k not in str_op_keys}
            # Start with PKs matching all string-op filters intersected
            matching_pks = None
            for sk in str_op_keys:
                pks = set(resolve_ids_by_lookup(Tag, sk, query[sk]))
                matching_pks = pks if matching_pks is None else matching_pks & pks
            remaining["pk__in"] = list(matching_pks or set())
            if not remaining["pk__in"]:
                return []
            return [{"id": t.pk, "name": t.name}
                    for t in Tag.objects.filter(**remaining).order_by("id")]
        return list(Tag.objects.filter(**query).values("id", "name").order_by("id"))

    @staticmethod
    def get_or_create(user, tag_name):
        """Get an existing tag or create one with a safe PK (< 2^31)."""
        try:
            return Tag.objects.get(name=tag_name), False
        except Tag.DoesNotExist:
            pass
        if not user.has_perm("management.add_tag"):
            raise Tag.DoesNotExist(tag_name)
        from tcms.dao.firestore.utils import generate_safe_pk
        tag = Tag(name=tag_name)
        tag.pk = generate_safe_pk(Tag)
        tag.save()
        return tag, True

    @staticmethod
    def get_by_name(tag_name):
        """Fetch a Tag by name from ORM."""
        return Tag.objects.get(name=tag_name)


tag_dao = TagDAO()
