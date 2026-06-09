"""
PropertyDAO wraps property CRUD for TestCase, TestRun, and TestExecution.

Each model has its own Property model:
  - tcms.testcases.models.Property  (FK: case)
  - tcms.testruns.models.Property   (FK: run)
  - tcms.testruns.models.TestExecutionProperty  (FK: execution)

The DAO is parameterized per model type via static factory methods.
"""
from django.forms.models import model_to_dict


class PropertyDAO:
    def __init__(self, model_class, fk_field, label):
        """
        :param model_class: The Django model class for properties (e.g. testcases.Property)
        :param fk_field: The FK field name on the property model (e.g. "case_id", "run_id")
        :param label: Human-readable label for logging (e.g. "TestCaseProperty")
        """
        self._model = model_class
        self._fk_field = fk_field
        self._label = label

    # ------------------------------------------------------------------
    # READ operations
    # ------------------------------------------------------------------

    def _resolve_query(self, query):
        """Pre-resolve FK traversals that Firestore cannot perform as joins."""
        from tcms.testruns.models import TestExecution
        resolved = {}
        for k, v in query.items():
            if self._fk_field == "execution_id" and k.startswith("execution__"):
                sub_key = k[len("execution__"):]
                exec_ids = list(TestExecution.objects.filter(**{sub_key: v}).values_list("pk", flat=True))
                resolved["execution_id__in"] = exec_ids
            else:
                resolved[k] = v
        return resolved

    def filter(self, query, value_fields, order_by):
        """
        Return serialized property records matching query.
        value_fields: tuple of field names to include in result dicts.
        order_by: tuple of field names used for Python-side sorting.
        """
        query = self._resolve_query(query)
        # .values().order_by() is a composite-index projection query in Firestore.
        # Fetch full objects, build dicts, and sort in Python instead.
        objs = list(self._model.objects.filter(**query).order_by())

        def _sort_key(obj):
            return tuple(getattr(obj, f.lstrip("-"), None) or "" for f in order_by)

        objs.sort(key=_sort_key)

        def _to_dict(obj):
            d = {}
            for f in value_fields:
                # FK fields like "execution" should emit the _id value
                val = getattr(obj, f + "_id", None)
                if val is None:
                    val = getattr(obj, f, None)
                d[f] = val
            return d

        return [_to_dict(obj) for obj in objs]

    # ------------------------------------------------------------------
    # WRITE operations
    # ------------------------------------------------------------------

    def get_or_create(self, obj_id, name, value):
        """
        Create a property if it doesn't exist (duplicates skipped).
        Returns serialized property dict.
        """
        kwargs = {self._fk_field: obj_id, "name": name, "value": value}
        prop, _ = self._model.objects.get_or_create(**kwargs)
        return model_to_dict(prop)

    def remove(self, query):
        """
        Delete property records matching query.
        """
        self._model.objects.filter(**query).delete()


# Per-model singleton instances
def _make_testcase_property_dao():
    from tcms.testcases.models import Property
    return PropertyDAO(Property, "case_id", "TestCasePropertyDAO")


def _make_testrun_property_dao():
    from tcms.testruns.models import Property
    return PropertyDAO(Property, "run_id", "TestRunPropertyDAO")


def _make_testexecution_property_dao():
    from tcms.testruns.models import TestExecutionProperty
    return PropertyDAO(TestExecutionProperty, "execution_id", "TestExecutionPropertyDAO")


testcase_property_dao = _make_testcase_property_dao()
testrun_property_dao = _make_testrun_property_dao()
testexecution_property_dao = _make_testexecution_property_dao()
